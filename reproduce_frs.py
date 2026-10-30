#!/usr/bin/env python3
"""Reproduce FRS v0.9.1: first named person in answer, including quoted rankings.
Position/exposure metric, not evidence of independent model endorsement.
"""
from __future__ import annotations
import csv
import hashlib
import io
import json
import re
import urllib.request
from pathlib import Path
from collections import Counter
from argparse import ArgumentParser

ROOT=Path(__file__).resolve().parent
PIN="7eb153e9f711b97544d46a9c6aafe117914989b8"
BASE=f"https://raw.githubusercontent.com/IndexResearch-ru/geo-experts-bmr-russia-2026/{PIN}/"
LOCKS={"observations":("data/observations.jsonl","e61f1ed05bc4470d8bf4b85a3a63177f1a2156ed"),
       "dictionary":("data/entity_dictionary.csv","79c6d6e88ddafe086eef894c0452a1c759f6a493")}
PROVIDERS=["chatgpt","perplexity","deepseek","grok","claude","gemini",
           "google_ai_mode","google_ai_overview","gigachat","yandex_alice","alice_chat"]

def blob_sha(data:bytes)->str:
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()

def get_source(kind,local=None):
    path,expected=LOCKS[kind]
    if local:
        b=Path(local).read_bytes()
    else:
        req=urllib.request.Request(BASE+path,headers={"User-Agent":"IndexResearch-FRS/0.9.1"})
        with urllib.request.urlopen(req,timeout=45) as response:
            b=response.read()
    assert blob_sha(b)==expected,(kind,blob_sha(b),expected)
    return b

def parse_csv(data):
    return list(csv.DictReader(io.StringIO(data)))

def compile_name(expr):
    # Convert the locked BMR Unicode regexp tokens to Python stdlib equivalents.
    expr=expr.replace(r"[\p{L}\p{N}_]",r"\w")
    expr=expr.replace(r"[\p{L}]",r"[^\W\d_]")
    assert r"\p{" not in expr,expr
    return re.compile(expr,re.IGNORECASE)

def first_person(text,patterns):
    hit=None
    for name,pattern in patterns:
        m=pattern.search(text)
        if m and (hit is None or m.start()<hit[1]):
            hit=(name,m.start())
    return hit or ("",-1)

def read_csv_file(name):
    return parse_csv((ROOT/name).read_text(encoding="utf-8-sig"))

def verify(local_observations=None,local_dictionary=None):
    answers=[json.loads(x) for x in get_source("observations",local_observations).decode("utf-8").splitlines() if x.strip()]
    dictionary=parse_csv(get_source("dictionary",local_dictionary).decode("utf-8-sig"))
    patterns=[(p["person_name"],compile_name(p["recognition_regex"])) for p in dictionary]
    assert len(answers)==110 and len(patterns)==74
    assert len(set(a["observation_id"] for a in answers))==110
    assert all(sum(a["provider"]==p for a in answers)==10 for p in PROVIDERS)
    labels=read_csv_file("data/first_recommendation_labels.csv")
    traces=read_csv_file("CALCULATION_TRACE.csv")
    labelmap={r["observation_id"]:r for r in labels}
    tracemap={r["observation_id"]:r for r in traces}
    assert len(labels)==len(labelmap)==len(traces)==len(tracemap)==110
    count=Counter()
    by_provider={p:Counter() for p in PROVIDERS}
    for a in answers:
        name,at=first_person(a["answer_text"],patterns)
        ident=a["observation_id"]
        row=labelmap[ident]
        trace=tracemap[ident]
        assert row["first_person"]==trace["first_person"]==name,(ident,name)
        assert int(row["evidence_offset"])==int(trace["evidence_offset"])==at,(ident,at)
        assert (row["answer_id"],row["provider"],row["prompt_id"])==(a["answer_id"],a["provider"],a["prompt_id"])
        assert row["status"]==("PERSON_FIRST" if name else "NO_PERSON_FIRST")
        assert row["decision_rule"]==("FIRST_VISIBLE_PERSON" if name else "NO_RECOGNIZED_PERSON")
        if name:
            count[name]+=1
            by_provider[a["provider"]][name]+=1
    rank=read_csv_file("RANKING.csv")
    matrix=read_csv_file("BY_PROVIDER_ALL.csv")
    brief=read_csv_file("BY_PROVIDER.csv")
    review=read_csv_file("REVIEW_TRIAGE_110.csv")
    results=json.loads((ROOT/"RESULTS.json").read_text(encoding="utf-8"))
    assert results["source_data_commit"]==PIN and results["method_revision"]=="first-visible-person-2026-10-30"
    assert len(rank)==len(matrix)==len(results["ranking"])==74
    assert len(review)==110 and len(brief)==11
    assert results["no_person_first"]==110-sum(count.values())
    assert results["people_with_first_recommendation"]==len(count)
    assert results["people_with_zero_frs"]==74-len(count)
    ranked={r["person_name"]:r for r in rank}
    mat={r["person_name"]:r for r in matrix}
    result_ranked={r["name"]:r for r in results["ranking"]}
    assert set(ranked)==set(mat)==set(result_ranked)=={d["person_name"] for d in dictionary}
    for name in ranked:
        value=count[name]
        higher=sum(1 for other in ranked if count[other]>value)
        equal=sum(1 for other in ranked if count[other]==value)
        span=str(higher+1) if equal==1 else f"{higher+1}-{higher+equal}"
        assert int(ranked[name]["frs_count"])==value
        assert ranked[name]["position_range"]==span,(name,span)
        assert result_ranked[name]["position_range"]==span
        assert int(mat[name]["total_first"])==value
        assert sum(int(mat[name][p]) for p in PROVIDERS)==value
        for p in PROVIDERS:
            assert int(mat[name][p])==by_provider[p][name],(name,p)
    overview={r["provider"]:r for r in brief}
    assert set(overview)==set(PROVIDERS)
    for p in PROVIDERS:
        n=sum(by_provider[p].values())
        assert int(overview[p]["person_first"])==n
        assert int(overview[p]["no_person_first"])==10-n
    print(f"FRS first-visible verified: 110 answers, {len(count)} persons with positive FRS, {110-sum(count.values())} no names.")
    print(f"Yakovlev: {count['Алексей Яковлев']}/110; Zharkov: {count['Василий Жарков']}/110.")
    print("This verifies first-name exposure, not independent endorsement.")
if __name__=="__main__":
    parser=ArgumentParser()
    parser.add_argument("--observations")
    parser.add_argument("--dictionary")
    args=parser.parse_args()
    verify(args.observations,args.dictionary)
