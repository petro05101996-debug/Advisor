# Проверка v4.9.2 на публичных real-world integration кейсах
Дата: 2026-06-03

Проверка основана на публичных архитектурных кейсах и паттернах: transactional outbox, saga, API Composition/BFF, webhook idempotency, SFTP/H2H batch, strangler migration. Цель — не повторить текст источников, а проверить, выдаёт ли инструмент применимый архитектурный вывод.

## Сводка
| Кейс | Вывод инструмента | Readiness | Полезность | Первые риски/замечания |
|---|---:|---:|---|---|
| Outbox: заказ + Kafka | Financial Operation State Machine | 95% | API Gateway / Edge, REST API + OpenAPI, PostgreSQL OLTP, Transactional Outbox, Inbox / Idempotent Consumer, Fallback / Graceful Degradation | нет критичного шума |
| Saga: заказ/оплата/склад/доставка | Fan-out/Fan-in Orchestrated Process | 66% | API Gateway / Edge, REST API + OpenAPI, Saga / Process Manager, Transactional Outbox, Inbox / Idempotent Consumer, Kafka/Event Streaming | money_cache_final_decision_forbidden, sync_chain, highload_low_latency_chain |
| BFF/API Composition: карточка 360 | BFF/API Composition with Partial Response | 69% | API Gateway / Edge, REST API + OpenAPI, Fallback / Graceful Degradation, Business-driven Read Model, Cache / Fast Read Path, PostgreSQL OLTP | sync_chain, highload_low_latency_chain |
| Webhook: Stripe-like duplicate payments | Financial Operation State Machine | 87% | API Gateway / Edge, REST API + OpenAPI, Webhook/Callback, PostgreSQL OLTP, Transactional Outbox, Inbox / Idempotent Consumer | highload_low_latency_chain |
| SFTP/H2H: банковский batch + сверка | Batch/File Integration | 95% | Batch/File/SFTP, PostgreSQL OLTP | нет критичного шума |
| Migration: mission-critical FX core | Financial Operation State Machine | 69% | API Gateway / Edge, REST API + OpenAPI, PostgreSQL OLTP, Transactional Outbox, Inbox / Idempotent Consumer, Fallback / Graceful Degradation | sync_chain, highload_low_latency_chain |

## Исправления по результатам интернет-кейсов
- Убран ложный шум `event_without_broker`: дефолтная Kafka-топология `multi_topic_ok` больше не означает, что события обязательно нужны.
- Убран ложный `compromise_without_rationale` из обычных кейсов: default `existing_only/minimal_table_only` больше не считается опасным компромиссом сам по себе.
- Для `api_composition/customer_360` добавлена нормализация в `multi_source_aggregation/many_sources_one_consumer`, чтобы BFF/partial response не падал в Basic API.
- Клиентский экран без статусов больше не ругается для обычного sync-read/BFF, только для tracking/callback/status-like сценариев.
- Для `migration_strangler` добавлена нормализация в migration/strangler variant.
- Для webhook + financial flow Financial State Machine теперь включает webhook/queue слой, а не теряет специфику callback-интеграции.

## Вывод
Инструмент рабочий как deterministic instructor: даёт не просто название паттерна, а MVP/production, контроли, анти-паттерны, readiness и ADR-заготовку. После исправлений он лучше проходит публичные реальные кейсы без ложного шума по event broker и без деградации BFF в Basic API.

Ограничение остаётся: если пользователь не описывает шаги в реально многошаговом процессе, инструмент правильно блокирует финальное решение или требует выбрать модель управления цепочкой. Это не баг, а quality gate.
