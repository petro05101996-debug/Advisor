# Production hardening v4.9.8 — что добавлено

## Итог

Версия v4.9.8 переводит инструмент ближе к production-ready deterministic integration architect: добавлены нормализация входа, отдельный класс shared Kafka selective consumer, защита BFF/read-only flow от ложного idempotency blocker, дополнительные контракты, gates и регрессионные тесты.

## Ключевые изменения

1. Normalization layer для синонимов бизнес-ситуаций и ограничений.
2. Новый production case class: `shared_topic_selective_consumer`.
3. Новый паттерн: `Selective Kafka Consumer`.
4. Новый top-level variant: `Shared Topic Selective Consumer + Idempotent Sink`.
5. Контракт selective consumer: filter contract, metrics, commit policy, sink contract.
6. Production gate для shared-topic: replay/reprocess, idempotent sink, selective-consumer каркас.
7. Ослаблен ложный `no_idempotency` для read-only BFF/API composition.
8. UI/version синхронизированы на v4.9.8.
9. Regression suite расширен до 78 тестов.

## Проверенные жёсткие кейсы

| Кейс | Ожидаемый класс | Фактический результат |
|---|---|---|
| Общий Kafka topic, нужны 0.2% событий, source/topic менять нельзя | shared_topic_selective_consumer | Shared Topic Selective Consumer + Idempotent Sink |
| Договоры → REST enrichment → Kafka, source без Kafka | data_enrichment_pipeline | Outbox + REST Enrichment Publisher |
| Customer 360 hot screen, 7 источников, partial response | bff_api_composition | BFF/API Composition with Partial Response |
| Финансовый webhook с подписью, дублями и retry | financial/webhook intake layer | Financial Operation State Machine + webhook controls |
| Legacy migration без big bang | strangler_migration | Migration / Strangler Fig |

## Команда проверки

```bash
python -m py_compile integration_architect_pro.py
pytest -q
# 78 passed
```

## Что всё ещё требует архитектурного ревью

Инструмент остаётся deterministic rule-engine без LLM. Он не должен автоматически утверждать production-архитектуру без ревью архитектора, DBA, security и владельцев систем.
