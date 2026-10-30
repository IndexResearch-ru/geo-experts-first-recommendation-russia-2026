# Источник корпуса FRS

FRS и BMR используют **одни и те же 110 исходных ответов**, полученные 30 октября 2026 года. Канонический корпус опубликован в [BMR data repository](https://github.com/IndexResearch-ru/geo-experts-bmr-russia-2026).

Входные файлы закреплены коммитом `7eb153e9f711b97544d46a9c6aafe117914989b8`. Git SHA зафиксированы в [SOURCE_LOCK.json](SOURCE_LOCK.json).

- [110 ответов](https://github.com/IndexResearch-ru/geo-experts-bmr-russia-2026/blob/7eb153e9f711b97544d46a9c6aafe117914989b8/data/observations.jsonl), полный текст каждой записи, ID и метаданные
- [Точные вопросы](https://github.com/IndexResearch-ru/geo-experts-bmr-russia-2026/blob/7eb153e9f711b97544d46a9c6aafe117914989b8/data/prompts.json), включая различия геоуточнения
- [Словарь 74 человек](https://github.com/IndexResearch-ru/geo-experts-bmr-russia-2026/blob/7eb153e9f711b97544d46a9c6aafe117914989b8/data/entity_dictionary.csv)
- [Общий протокол происхождения](https://github.com/IndexResearch-ru/geo-experts-bmr-russia-2026/blob/main/data/DATA_PROVENANCE.md)
- [Учет замены контактных данных](https://github.com/IndexResearch-ru/geo-experts-bmr-russia-2026/blob/main/data/contact_redactions.csv)

В FRS-репозитории публикуются только **аннотации, результат и доказательный отчет FRS**, без повторных копий всех ответов. У исходного BMR-корпуса при этом есть свои ограничения качества: записи отражают сообщения нейросетей, а не подтвержденные сведения о специалистах.

В момент подготовки FRS исходное имя, числитель и позиции не менялись. Первичная кодировка 110 ответов допускает спорные трактовки; перечень случаев и статус проверки ведется отдельно, никакие исправления пока не выдаются за состоявшиеся.
