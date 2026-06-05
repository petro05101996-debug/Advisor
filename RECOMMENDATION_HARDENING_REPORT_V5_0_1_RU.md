# Recommendation Hardening v5.0.1

## Что исправлено

### 1. Добавлен слой `operation_kind`
Модель теперь перед применением блокеров и ranking определяет доминирующий тип потока:

- `query_readonly`
- `command_create_update`
- `financial_command`
- `webhook_event_intake`
- `kafka_event_consumer`
- `kafka_event_publisher`
- `batch_file_exchange`
- `dwh_offload`
- `migration`
- `regulatory_schema_change`
- `bff_composition`
- `external_partner_adapter`

Это устраняет главную проблему: раньше DWH, BFF, webhook, migration и regulatory-change могли получать generic рекомендации и generic idempotency-blocker.

### 2. Контекстные ключи надёжности вместо одного generic `idempotencyKey`
Теперь модель различает:

| Тип потока | Ожидаемый ключ/контроль |
|---|---|
| HTTP command / financial command | `Idempotency-Key` / `operation_id` + unique constraint |
| Webhook | `provider_event_id` / `delivery_id` + signature/raw body + Inbox |
| Kafka consumer | `event_id` + `aggregate_id/version` + consumer Inbox/idempotent sink |
| Kafka publisher | `outbox_id` / `source_event_id` / `aggregate_version` |
| Batch/file | `file_id` + `checksum` + `batch_id` |
| DWH/CDC | `watermark` / `offset` / `snapshot_id` + reconciliation |
| Migration | `migration_run_id` + source record id + checksum |
| Regulatory schema change | `schema_version/change_id` + migration/backfill/compatibility matrix |
| Read-only BFF/query | `correlation_id/request_id`; idempotency не является blocker |

### 3. Исправлен ranking top-level решений
Усилены правила:

- Regulatory schema change теперь top-level только для реального изменения модели/контрактов, а не для любой финансовой/ПДн/регуляторной чувствительности.
- DWH/offload теперь выбирает `Data Pipeline / DWH` и не получает ложный critical idempotency blocker.
- Customer 360 / BFF read-only теперь выбирает `BFF/API Composition with Partial Response`, а не Saga/External adapter.
- Legacy replacement теперь выбирает `Migration / Strangler Fig`; SOAP adapter остаётся внутренним layer/variant.
- Unstable external API теперь выбирает `External API Adapter with Resilience`, если это не webhook/BFF/core-flow.
- Payment webhook теперь выбирает `Webhook Intake + Inbox Processing`, а не Queue worker как top-level.

### 4. Добавлены регрессионные реальные кейсы
Добавлен файл `test_v50_1_recommendation_hardening.py` с проверками:

1. ЦБ изменил модель: одна цель займа → несколько целей.
2. DWH/offload и рост prod DB.
3. Customer 360 с partial response.
4. Legacy SOAP replacement через Strangler.
5. Нестабильное внешнее API/rate limits.
6. Duplicate payment webhook через Inbox.

## Итоговая проверка

```text
110 passed in 0.39s
```

## Практический эффект

Модель стала меньше давать ложные RED, лучше различает top-level архитектуру и внутренние слои, а рекомендации стали ближе к реальному системному анализу:

- не требует `idempotencyKey` там, где нужен `watermark`/`batchId`/`migrationRunId`;
- не подменяет BFF/Saga/DWH техническими слоями;
- не делает SOAP adapter главным решением при legacy migration;
- не превращает любое регуляторное/финансовое поле в regulatory-schema-change top-level;
- корректно поднимает webhook intake и external partner adapter в нужных сценариях.
