# Integration Architect Pro v5.0.5 — hard-fix report

## Что исправлено

1. **Privacy false-positive по `receipt/GDPR/erasure`**
   - Добавлен negation detection: `no GDPR erasure`, `not privacy deletion`, `not erasure request`, `receipt means acknowledgement` и русские аналоги.
   - `command receipt`, `POS receipt`, `delivery receipt`, `payment receipt` больше не ведут в privacy workflow без явного DSAR/right-to-be-forgotten/legal-hold контекста.

2. **Producer-side enrichment vs selective consumer**
   - Разведены два разных смысла single/shared Kafka topic:
     - `consume/read/filter FROM shared topic` → `Shared Topic Selective Consumer`.
     - `publish/send enriched event TO only existing topic` → `Outbox + REST Enrichment Publisher` или `Compromise: CDC/Polling + Enrichment Export`.
   - Добавлены функции `shared_topic_consumer_signal()` и `kafka_destination_enrichment_signal()`.

3. **CDC как слой, а не всегда top-level**
   - CDC modernization больше не перебивает enrichment publisher/export, когда CDC используется как read-only источник для формирования enriched event.
   - DWH/Data Lake остаётся top-level для data lake/raw/bronze/silver/schema drift/lineage/watermark/backfill.

4. **Loyalty/POS receipt ledger**
   - Добавлен класс/вариант `Financial/Loyalty Ledger State Machine`.
   - POS receipt + loyalty points/balance/refund/reversal трактуется как ledger/state-machine с idempotency, unique operation, audit и reconciliation, а не privacy.
   - При этом обычный `Loyalty`-consumer в Event Choreography больше не перехватывает верхнеуровневую архитектуру.

5. **Batch/SFTP и near-real-time без лишнего broker-noise**
   - Для file/batch/DWH/near-real-time/BFF/query flow не создаётся критичный anti-pattern `event_target_but_broker_forbidden`, если Kafka/queue не являются смыслом кейса.
   - SFTP/file-only кейсы могут быть спроектированы даже без полного описания process steps, если есть явный file/batch контекст.

6. **Wide E2E/Saga не подменяется enrichment layer**
   - Для широких E2E/fan-out/Saga кейсов enrichment publisher остаётся видимым compromise-layer в первых альтернативах, но не становится top-level вместо Orchestrated E2E/Fan-out/Fan-in.

## Проверки

Полная регрессия:

```text
130 passed in 0.95s
```

Добавлен новый regression-файл:

```text
test_v50_5_hard_regression_fixes.py
```

Он закрывает:

- IoT command receipt + explicit `no GDPR erasure` → не privacy.
- Contract changes + REST enrichment + publish to only existing Kafka topic → не selective consumer.
- POS receipt loyalty points → ledger/state-machine.
- SFTP batch import → Batch/File Integration без broker-noise.
- Pricing personalization under 100ms → Near Real-time Decision Flow без broker-noise.

## Ручной hard-smoke после фиксов

| Кейс | Результат |
|---|---|
| Healthcare lab webhook | `Webhook Intake + Inbox Processing` |
| CDC into Data Lake | `Data Pipeline / DWH` |
| Real GDPR erasure | `Privacy / Data Erasure Orchestration Pipeline` |
| Shared Kafka topic consumer filtering | `Shared Topic Selective Consumer + Idempotent Sink` |
| IoT command receipt, no GDPR | not privacy |
| Producer-side enriched event to only Kafka topic | enrichment publisher/export, not selective consumer |
| POS loyalty receipt | `Financial/Loyalty Ledger State Machine` |
| Vendor SFTP import | `Batch/File Integration` |
| Pricing <100ms decision | `Near Real-time Decision Flow` |

## Итоговая оценка

- Техническая стабильность: **10/10**
- Регрессия старых кейсов: **10/10**
- Закрытие ранее найденных hard-багов: **9/10**
- Полезность для системного аналитика с human review: **9+/10**
- Автопроектировщик без ревью архитектора: **7.5/10**

Ограничение остаётся честным: это сильный инструктор/помощник SA, но финальное архитектурное решение всё равно должно проходить human review, особенно для финансовых, юридических и highload-кейсов.
