# Реальная проверка сложных кейсов v4.8.8

## Договоры enriched event один Kafka topic source без Kafka

- Рекомендация: Compromise: Source Outbox + Embedded/Platform Publisher (100%)
- Готовность/уверенность: 73%
- Coverage отчёта: 100%, missing: —
- Паттерны: REST API + OpenAPI, Transactional Outbox, Integration Publisher / Event Enrichment, Kafka/Event Streaming, Inbox / Idempotent Consumer, Fallback / Graceful Degradation, PostgreSQL OLTP, Highload Controls
- Anti-patterns/риски: Компромиссный режим без явного обоснования, Клиентский процесс без статусов, Ownership события смешан с наличием Kafka-инфраструктуры, Не определена свежесть enrichment-данных

## Кредитная заявка E2E БКИ антифрод скоринг CRM DWH

- Рекомендация: Финансовая операция / машина состояний (100%)
- Готовность/уверенность: 57%
- Coverage отчёта: 86%, missing: rollout
- Паттерны: API Gateway / Edge, REST API + OpenAPI, PostgreSQL OLTP, Transactional Outbox, Inbox / Idempotent Consumer, Saga / Process Manager, Fallback / Graceful Degradation, Highload Controls
- Anti-patterns/риски: Конфликт бизнес-требований, Компромиссный режим без явного обоснования, Деньги + кэш/устаревание, Регуляторный процесс без строгой фиксации свежести, Клиентский процесс без статусов, Highload + низкая latency + цепочка

## Customer 360 hot screen 7 источников partial response

- Рекомендация: BFF / API composition с partial response (100%)
- Готовность/уверенность: 53%
- Coverage отчёта: 86%, missing: rollout
- Паттерны: API Gateway / Edge, REST API + OpenAPI, Fallback / Graceful Degradation, Business-driven Read Model, Cache / Fast Read Path, PostgreSQL OLTP, Highload Controls
- Anti-patterns/риски: Компромиссный режим без явного обоснования, Регуляторный процесс без строгой фиксации свежести, Нет idempotency key при at-least-once/retry, Highload + низкая latency + цепочка, Нет retention для больших данных

## Legacy SFTP страховой партнёр batch сверка

- Рекомендация: Пакетная/файловая интеграция (100%)
- Готовность/уверенность: 73%
- Coverage отчёта: 86%, missing: rollout
- Паттерны: Batch/File/SFTP, PostgreSQL OLTP
- Anti-patterns/риски: Компромиссный режим без явного обоснования, Регуляторный процесс без строгой фиксации свежести, Клиентский процесс без статусов, Нужны события, но event broker не выбран

## ЦБ multiple loan purposes изменение модели

- Рекомендация: Справочник / versioned cache (100%)
- Готовность/уверенность: 89%
- Coverage отчёта: 86%, missing: rollout
- Паттерны: REST API + OpenAPI, Business-driven Read Model, Cache / Fast Read Path, PostgreSQL OLTP
- Anti-patterns/риски: Конфликт бизнес-требований, Компромиссный режим без явного обоснования

## DWH раздувает prod DB сырые БКИ отчёты

- Рекомендация: Синхронизация данных / source-of-truth sync (100%)
- Готовность/уверенность: 81%
- Coverage отчёта: 86%, missing: rollout
- Паттерны: CDC, Inbox / Idempotent Consumer, PostgreSQL OLTP, Highload Controls
- Anti-patterns/риски: Компромиссный режим без явного обоснования, Регуляторный процесс без строгой фиксации свежести, Нужны события, но event broker не выбран

## External BKI API login password secrets

- Рекомендация: Фоновая обработка / async job (100%)
- Готовность/уверенность: 97%
- Coverage отчёта: 86%, missing: rollout
- Паттерны: API Gateway / Edge, REST API + OpenAPI, Inbox / Idempotent Consumer, Fallback / Graceful Degradation, PostgreSQL OLTP, Highload Controls
- Anti-patterns/риски: Компромиссный режим без явного обоснования

```json
[
  {
    "case": "Договоры enriched event один Kafka topic source без Kafka",
    "readiness": 73,
    "recommended": "Compromise: Source Outbox + Embedded/Platform Publisher",
    "score": 100,
    "patterns": [
      "REST API + OpenAPI",
      "Transactional Outbox",
      "Integration Publisher / Event Enrichment",
      "Kafka/Event Streaming",
      "Inbox / Idempotent Consumer",
      "Fallback / Graceful Degradation",
      "PostgreSQL OLTP",
      "Highload Controls"
    ],
    "anti": [
      "Компромиссный режим без явного обоснования",
      "Клиентский процесс без статусов",
      "Ownership события смешан с наличием Kafka-инфраструктуры",
      "Не определена свежесть enrichment-данных"
    ],
    "coverage": 100,
    "missing": []
  },
  {
    "case": "Кредитная заявка E2E БКИ антифрод скоринг CRM DWH",
    "readiness": 57,
    "recommended": "Financial Operation State Machine",
    "score": 100,
    "patterns": [
      "API Gateway / Edge",
      "REST API + OpenAPI",
      "PostgreSQL OLTP",
      "Transactional Outbox",
      "Inbox / Idempotent Consumer",
      "Saga / Process Manager",
      "Fallback / Graceful Degradation",
      "Highload Controls"
    ],
    "anti": [
      "Конфликт бизнес-требований",
      "Компромиссный режим без явного обоснования",
      "Деньги + кэш/устаревание",
      "Регуляторный процесс без строгой фиксации свежести",
      "Клиентский процесс без статусов",
      "Highload + низкая latency + цепочка"
    ],
    "coverage": 86,
    "missing": [
      "rollout"
    ]
  },
  {
    "case": "Customer 360 hot screen 7 источников partial response",
    "readiness": 53,
    "recommended": "BFF/API Composition with Partial Response",
    "score": 100,
    "patterns": [
      "API Gateway / Edge",
      "REST API + OpenAPI",
      "Fallback / Graceful Degradation",
      "Business-driven Read Model",
      "Cache / Fast Read Path",
      "PostgreSQL OLTP",
      "Highload Controls"
    ],
    "anti": [
      "Компромиссный режим без явного обоснования",
      "Регуляторный процесс без строгой фиксации свежести",
      "Нет idempotency key при at-least-once/retry",
      "Highload + низкая latency + цепочка",
      "Нет retention для больших данных"
    ],
    "coverage": 86,
    "missing": [
      "rollout"
    ]
  },
  {
    "case": "Legacy SFTP страховой партнёр batch сверка",
    "readiness": 73,
    "recommended": "Batch/File Integration",
    "score": 100,
    "patterns": [
      "Batch/File/SFTP",
      "PostgreSQL OLTP"
    ],
    "anti": [
      "Компромиссный режим без явного обоснования",
      "Регуляторный процесс без строгой фиксации свежести",
      "Клиентский процесс без статусов",
      "Нужны события, но event broker не выбран"
    ],
    "coverage": 86,
    "missing": [
      "rollout"
    ]
  },
  {
    "case": "ЦБ multiple loan purposes изменение модели",
    "readiness": 89,
    "recommended": "Reference Data API + Versioned Cache",
    "score": 100,
    "patterns": [
      "REST API + OpenAPI",
      "Business-driven Read Model",
      "Cache / Fast Read Path",
      "PostgreSQL OLTP"
    ],
    "anti": [
      "Конфликт бизнес-требований",
      "Компромиссный режим без явного обоснования"
    ],
    "coverage": 86,
    "missing": [
      "rollout"
    ]
  },
  {
    "case": "DWH раздувает prod DB сырые БКИ отчёты",
    "readiness": 81,
    "recommended": "Data Synchronization / Source-of-Truth Sync",
    "score": 100,
    "patterns": [
      "CDC",
      "Inbox / Idempotent Consumer",
      "PostgreSQL OLTP",
      "Highload Controls"
    ],
    "anti": [
      "Компромиссный режим без явного обоснования",
      "Регуляторный процесс без строгой фиксации свежести",
      "Нужны события, но event broker не выбран"
    ],
    "coverage": 86,
    "missing": [
      "rollout"
    ]
  },
  {
    "case": "External BKI API login password secrets",
    "readiness": 97,
    "recommended": "Async Job / Heavy Processing Flow",
    "score": 100,
    "patterns": [
      "API Gateway / Edge",
      "REST API + OpenAPI",
      "Inbox / Idempotent Consumer",
      "Fallback / Graceful Degradation",
      "PostgreSQL OLTP",
      "Highload Controls"
    ],
    "anti": [
      "Компромиссный режим без явного обоснования"
    ],
    "coverage": 86,
    "missing": [
      "rollout"
    ]
  }
]
```
