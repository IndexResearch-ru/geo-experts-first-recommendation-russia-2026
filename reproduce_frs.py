#!/usr/bin/env python3
"""Verify FRS (First Recommendation Share) from 110 labeled answers.

FRS measures the share of answers whose first PERSONALLY RECOMMENDED
candidate is a given person. This is a mechanical re-calculation of initial
annotations, NOT an independent semantic review of those decisions.
Python 3.10+, standard library only.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
from pathlib import Path
import re
import urllib.request

ROOT = Path(__file__).resolve().parent
SOURCE_COMMIT = "7eb153e9f711b97544d46a9c6aafe117914989b8"
SOURCE_BASE = "https://raw.githubusercontent.com/IndexResearch-ru/geo-experts-bmr-russia-2026/" + SOURCE_COMMIT + "/"
EXPECTED_BLOBS = {
    "observations": ("data/observations.jsonl", "e61f1ed05bc4470d8bf4b85a3a63177f1a2156ed"),
    "dictionary": ("data/entity_dictionary.csv", "79c6d6e88ddafe086eef894c0452a1c759f6a493"),
}
PROVIDERS = (
    "chatgpt", "perplexity", "deepseek", "grok", "claude",
    "gemini", "google_ai_mode", "google_ai_overview", "gigachat",
    "yandex_alice", "alice_chat",
)

def git_blob_sha(payload: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(payload)).encode() + b"\0" + payload).hexdigest()

def read_pinned(kind: str, local: str | None = None) -> bytes:
    path, expected_sha = EXPECTED_BLOBS[kind]
    if local:
        data = Path(local).read_bytes()
    else:
        request = urllib.request.Request(SOURCE_BASE + path, headers={"User-Agent": "IndexResearch-FRS-reproducibility/0.9"})
        with urllib.request.urlopen(request, timeout=30) as response:
            data = response.read()
    actual_sha = git_blob_sha(data)
    if actual_sha != expected_sha:
        raise AssertionError(f"Pinned {kind} data changed: {actual_sha} != {expected_sha}")
    return data

def rows_from_csv(content: str):
    return list(csv.DictReader(content.splitlines()))

def match_person(name: str, text: str) -> bool:
    fn, ln = name.replace("c", "с").split(" ")
    def part(stem):
        return "".join("[её]" if ch.lower() in "её" else re.escape(ch) for ch in stem)
    first = part(fn[:3])
    if name == "Евгений Ванжула":
        first = "(?:" + first + "|Жен)"
    rule = re.compile(r"(?<!\w)" + first + r"\w*\s+" + part(ln[:4]) + r"\w*(?!\w)", re.I)
    return bool(rule.search(text))

def load_json(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))

def verify(observations_file=None, dictionary_file=None):
    obs = [json.loads(line) for line in read_pinned("observations", observations_file).decode("utf-8").splitlines() if line.strip()]
    dictionary = rows_from_csv(read_pinned("dictionary", dictionary_file).decode("utf-8-sig"))
    names = {row["person_name"] for row in dictionary}
    labels = rows_from_csv((ROOT / "data/first_recommendation_labels.csv").read_text(encoding="utf-8-sig"))
    assert len(obs) == 110 and len(dictionary) == len(names) == 74
    assert len(labels) == 110 and len({row["observation_id"] for row in labels}) == 110
    answers = {row["observation_id"]: row for row in obs}
    assert len(answers) == 110
    assert len({(row["provider"], row["prompt_id"]) for row in obs}) == 110
    assert {row["provider"] for row in obs} == set(PROVIDERS)
    assert all(sum(r["provider"] == p for r in obs) == 10 for p in PROVIDERS)
    assert all(row["status"] == "VALID" and row["answer_text"].strip() for row in obs)

    selected = Counter()
    by_provider = {provider: Counter() for provider in PROVIDERS}
    no_person_by_provider = Counter()
    no_person_ids = []
    for label in labels:
        id_ = label["observation_id"]
        original = answers[id_]
        assert (label["answer_id"], label["prompt_id"], label["provider"]) == (
            original["answer_id"], original["prompt_id"], original["provider"]
        ), id_
        name = label["first_person"]
        if name:
            assert label["status"] == "PERSON_FIRST" and name in names, id_
            assert match_person(name, original["answer_text"]), id_
            at = int(label["evidence_offset"])
            assert 0 <= at < len(original["answer_text"]), id_
            first = name.split(" ")[0].replace("ё", "е").lower()[:3]
            context = original["answer_text"][at:at+80].replace("ё", "е").lower()
            assert first in context, id_
            selected[name] += 1
            by_provider[original["provider"]][name] += 1
        else:
            assert label["status"] == "NO_PERSON_FIRST", id_
            assert int(label["evidence_offset"]) == -1, id_
            no_person_by_provider[original["provider"]] += 1
            no_person_ids.append(id_)

    assert sum(selected.values()) == 100 and len(no_person_ids) == 10
    assert len(selected) == 20
    assert selected["Алексей Яковлев"] == 58 and selected["Василий Жарков"] == 17

    reference = load_json("RESULTS.json")
    assert reference["status"] == "DRAFT_PENDING_INDEPENDENT_ANNOTATION_REVIEW"
    assert reference["dataset_answers"] == 110
    assert reference["source_data_commit"] == SOURCE_COMMIT
    rank_counts = {item["name"]: int(item["first_count"]) for item in reference["ranking"]}
    assert set(rank_counts) == names
    assert {person: selected.get(person, 0) for person in names} == rank_counts
    assert len([x for x in rank_counts.values() if x == 0]) == 54
    for row in reference["ranking"]:
        count = selected[row["name"]]
        start = 1 + sum(x > count for x in selected.values())
        end = sum(x >= count for x in rank_counts.values())
        span = str(start) if start == end else f"{start}-{end}"
        assert row["rank"] == start and row["position_range"] == span, row

    with (ROOT / "RANKING.csv").open(encoding="utf-8-sig", newline="") as file:
        ranking = list(csv.DictReader(file))
    assert len(ranking) == 74
    for row in ranking:
        assert selected.get(row["person_name"], 0) == int(row["frs_count"])
        assert row["position_range"] == next(x["position_range"] for x in reference["ranking"] if x["name"] == row["person_name"])

    with (ROOT / "BY_PROVIDER_ALL.csv").open(encoding="utf-8-sig", newline="") as file:
        matrix = list(csv.DictReader(file))
    assert len(matrix) == 74
    for row in matrix:
        person = row["person_name"]
        assert person in names
        assert sum(int(row[p]) for p in PROVIDERS) == selected.get(person, 0)
        assert all(int(row[p]) == by_provider[p][person] for p in PROVIDERS)

    for row in reference["per_provider"]:
        provider = row["provider"]
        assert provider in PROVIDERS and row["total_answers"] == 10
        assert row["no_person_first"] == no_person_by_provider[provider]
        assert {x["name"]: int(x["count"]) for x in row["ranking"]} == dict(by_provider[provider])

    triage = rows_from_csv((ROOT / "REVIEW_TRIAGE_110.csv").read_text(encoding="utf-8-sig"))
    assert len(triage) == 110
    assert {r["observation_id"] for r in triage} == set(answers)
    assert all(not r["independent_reviewer"] and not r["independent_label"] for r in triage)
    print("FRS INITIAL ANNOTATION CALCULATION PASSED")
    print("Answers: 110 | Provider interfaces: 11 | Candidate pool: 74 | Selected persons: 20 | No person: 10")
    print("Provisional: Yakovlev 58/110, Zharkov 17/110; independent coding is PENDING.")
    print("No claim of independent annotation review is made.")
    return reference

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--observations", help="Path to a local copy of the pinned BMR observations (optional)")
    parser.add_argument("--dictionary", help="Path to a local copy of the pinned BMR entity dictionary (optional)")
    args = parser.parse_args()
    verify(args.observations, args.dictionary)
