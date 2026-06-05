# Production hardening report v4.9.6

## Что сделано

1. Добавлен слой `case_class -> top_level -> layers -> controls -> gate`.
2. Добавлены классы кейсов:
   - `dual_write_db_broker`
   - `webhook_intake`
   - `data_enrichment_pipeline`
   - `saga_orchestration`
   - `financial_state_machine`
   - `async_job_flow`
   - `bff_api_composition`
   - `read_model_cqrs`
   - `near_real_time_decision`
   - `strangler_migration`
   - `batch_file_exchange`
   - `dwh_pipeline`
   - `regulatory_schema_change`
   - `non_invasive_extension`
   - `basic_sync_api`
3. Добавлен `production_gate` с уровнями `RED / AMBER / YELLOW / GREEN`.
4. Добавлен `structured_result` для UI/экспорта/регрессионного сравнения.
5. Усилен webhook-контур:
   - `webhook_signature_required`
   - `webhook_raw_body_preserved`
   - `webhook_timestamp_tolerance`
   - `webhook_secret_rotation`
   - `webhook_provider_retry_policy_known`
   - `webhook_reconciliation_available`
6. Исправлено правило enrichment consistency:
   - `best_effort` для critical enrichment остаётся critical-risk;
   - `current_at_publish` теперь high-risk/acceptable compromise для snapshot/export/thin-event при наличии `dataAsOf/dataVersion/sourceEventId`, а не автоматический blocker.
7. Добавлен top-level вариант `Event-driven + Transactional Outbox` для DB + Kafka dual-write.
8. Добавлены invariant/regression tests для production-case classification.

## Проверка

```text
70 passed
```

## Главный эффект

Инструмент стал меньше “угадывать паттерн скорингом” и больше работает как deterministic decision engine:

```text
case_class -> допустимые top-level архитектуры -> внутренние слои -> обязательные controls -> production gate
```

Это снижает риск, что слой вроде DWH/cache/webhook/external adapter станет главным архитектурным решением в кейсе, где главным должен быть Outbox, Saga, Strangler или BFF.
