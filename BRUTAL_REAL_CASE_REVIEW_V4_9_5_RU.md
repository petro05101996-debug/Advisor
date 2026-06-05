# BRUTAL REAL CASE REVIEW V4.9.5 RU

Проверка v4.9.4 на более грязных публичных/enterprise кейсах выявила несколько зон ложной уверенности. В v4.9.5 добавлены hardening rules и regression tests.

## Эталонные классы кейсов
- Transactional Outbox / dual-write DB+broker
- Saga / multi-service operation with compensation
- Stripe-like financial webhooks: duplicate events + signature/raw body verification
- Strangler migration / incremental monolith replacement
- Regulatory schema evolution: 1→N field cardinality
- DWH/raw-payload storage bloat and archive metadata pattern

## Найдено и исправлено
1. Финансовый webhook с dedupe, но без signature/raw body verification, раньше выглядел слишком безопасно. Добавлен anti-pattern `webhook_signature_not_defined`.
2. Сценарий “нужны события нескольким потребителям”, но форма запрещает Kafka/queue, раньше мог получить Basic API + высокий readiness. Добавлен critical anti-pattern `event_target_but_broker_forbidden`.
3. Regulatory change 1→N раньше не давал полноценный impact-analysis. Добавлен блок `impact_analysis`: DB/model, API, Events/Kafka, DWH/reports, UI/validation, legacy consumers, testing.
4. DWH raw payload / OLTP bloat теперь явно требует object/cold storage, metadata/status/archiveUri, purge/archive и reconciliation.

## Regression result
```
67 passed
```

## Case results
### BRUTAL_CASE_1_financial_webhook_signature
- Recommended: Financial Operation State Machine
- Readiness: 82
- Anti-patterns: webhook_signature_not_defined

### BRUTAL_CASE_2_event_but_broker_forbidden
- Recommended: Basic API + DB
- Readiness: 69
- Anti-patterns: event_target_but_broker_forbidden, event_without_broker

### BRUTAL_CASE_3_regulatory_multiple_loan_purposes
- Recommended: Data Synchronization / Source-of-Truth Sync
- Readiness: 95
- Anti-patterns: none

### BRUTAL_CASE_4_dwh_raw_payload_storage
- Recommended: Data Pipeline / DWH
- Readiness: 95
- Anti-patterns: none
