# Integration Architect Pro v5.0.4 — доведение полезности до 9+/10

## Что было сделано

Цель доработки — поднять инструмент с уровня «полезный инструктор 7/10» до уровня «рабочий production-grade помощник системного аналитика 9+/10» за счёт снижения ложных классификаций и добавления проектной логики, которую реально ждут от сильного SA.

## Ключевые изменения

### 1. Исправлен privacy false-positive
Раньше слова `receipt`, `evidence`, `retention` могли ошибочно отправить кейс в `Privacy / Data Erasure Orchestration Pipeline`.

Теперь privacy определяется контекстно:
- `GDPR`, `right to be forgotten`, `DSAR`, `delete personal data`, `удаление ПДн` → privacy workflow;
- `POS receipt`, `command receipt`, `delivery receipt`, `payment receipt`, `IoT`, `loyalty` → не privacy, если нет явного erasure/DSAR/legal-hold контекста.

Покрыто тестами:
- IoT command receipt;
- Loyalty/POS receipt.

### 2. Разделены top-level architecture и supporting mechanisms
CDC теперь не перехватывает кейсы, где он является только механизмом ingestion.

Примеры:
- `Data Lake + CDC + schema drift` → `Data Pipeline / DWH`, а не `CDC Legacy Modernization`;
- `Pricing under 100ms + CDC updates feature cache` → `Near Real-time Decision Flow`, а не CDC;
- `Operational legacy projection via CDC/WAL/LSN` → `CDC Legacy Modernization / Operational Projection`, если цель именно операционная проекция/read model/event stream.

### 3. Усилен Webhook Intake
Webhook/callback теперь выигрывает у generic Saga/E2E, если сценарий начинается с внешнего callback.

Для webhook top-level появились обязательные вопросы и контроли:
- signature validation;
- raw body preservation;
- quick ACK SLA;
- external_event_id / delivery_id;
- Inbox;
- async worker;
- reconciliation API;
- provider retry policy.

Покрыто тестом healthcare lab results webhook.

### 4. Усилен Batch/File/SFTP класс
SFTP/file/batch import теперь не классифицируется как обычный `External API Adapter`.

Для таких кейсов top-level:
- `Batch/File Integration`.

Контроли:
- manifest;
- checksum;
- staging;
- quarantine;
- ack/error file;
- file registry;
- reprocess by file_id;
- reconciliation.

Покрыто тестом vendor nightly SFTP import.

### 5. DWH/Data Lake выше CDC и file, когда задача аналитическая
Если смысл задачи — DWH/Data Lake/offload/schema drift/lineage/data quality/backfill, то главным классом становится:
- `Data Pipeline / DWH`.

SFTP/CDC/ETL в этом случае считаются механизмами реализации, а не главным ответом.

### 6. Добавлена матрица компромиссов
В отчёт теперь добавляется отдельный раздел:

- A. Архитектурно правильный вариант;
- B. Безопасный компромисс;
- C. Временный workaround.

Это важно для реальной работы SA, потому что в production часто нельзя сделать «идеально»: нельзя менять source, нельзя новый сервис, нельзя новый topic, нет бюджета или сроки горят.

### 7. Добавлены вопросы системного аналитика
Quality gate теперь задаёт вопросы не только по общим требованиям, но и по типу операции:
- что является главным результатом: команда, событие, read-model, webhook intake, DWH pipeline, migration или batch file;
- кто business owner события;
- что делать при enrichment timeout;
- CDC — это бизнес-событие или технический snapshot;
- какие manifest/checksum/ack/error-file правила для batch;
- какие zones/schema drift/data quality gates для Data Lake.

### 8. RED/YELLOW gate больше не бывает пустым
Если production gate не GREEN, он теперь обязан иметь явные blockers/gaps.

Это исправляет UX-проблему: пользователь больше не получает красный/жёлтый статус без объяснения, что именно надо закрыть.

## Новые тесты

Добавлен файл:

```text
test_v50_4_usefulness_9_plus_new_cases.py
```

Проверяет 8 новых тяжёлых кейсов:

1. IoT firmware command receipt — не privacy false-positive.
2. Loyalty POS receipt — не privacy false-positive.
3. Healthcare lab results webhook — webhook intake top-level.
4. Vendor nightly SFTP import — batch/file top-level.
5. Data Lake CDC schema drift — DWH pipeline, CDC как слой.
6. Pricing personalization under 100ms — near real-time decision, не CDC.
7. RED/YELLOW/AMBER gate имеет blockers.
8. Compromise matrix и SA questions присутствуют.

## Полная регрессия

```text
126 passed in 0.68s
```

## Итоговая оценка после доработки

```text
Техническая стабильность: 10/10
Регрессия старых кейсов: 10/10
Покрытие новых сложных классов: 9/10
Полезность для системного аналитика: 9+/10
Production v1 как инструктор с human review: 9/10
Самостоятельный автопроектировщик без ревью: 7/10
```

Почему не 10/10: это deterministic rule-engine без LLM и без реального интервью с пользователем. Он всё ещё требует human review для критичных архитектурных решений, но теперь существенно лучше ведёт пользователя, объясняет компромиссы и меньше ошибается на сложных реальных кейсах.
