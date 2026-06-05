# V4.8.5 — учёт ограничений, компромиссов и реалистичных рекомендаций

Добавлена доработка для типовой ситуации системного аналитика: целевое архитектурное решение понятно, но его нельзя внедрить напрямую из-за бюджета, сроков, стека, запрета на новый сервис или запрета менять source-систему.

## Что добавлено

1. Новые входные параметры:
   - режим проектирования: эталонный / баланс / компромисс / минимально безопасный;
   - бюджет и сроки;
   - можно ли добавлять новый сервис;
   - можно ли добавлять новую инфраструктуру;
   - можно ли менять source-систему;
   - допустимый остаточный риск;
   - текстовое объяснение компромисса.

2. Новый раздел отчёта **«Ограничения, компромиссы и реалистичный вариант»**:
   - жёсткие ограничения;
   - реалистичный v1;
   - целевой вариант без ограничений;
   - остаточные риски;
   - что нельзя выкидывать даже в компромиссе;
   - Phase 2 / архитектурный долг.

3. Новые варианты архитектуры:
   - **Compromise: Source Outbox + Embedded/Platform Publisher** — когда новый сервис дорогой/запрещён, но можно минимально добавить outbox/status в source;
   - **Compromise: CDC/Polling + Enrichment Export** — когда source нельзя менять, и нужно честно оформить решение как snapshot/export с reconciliation, а не как полноценное domain event.

4. Усилены anti-pattern checks:
   - компромисс без явного rationale;
   - нужен новый publisher, но новый сервис запрещён;
   - source read-only + обязательное enriched event;
   - нужна Kafka/очередь, но новая инфраструктура запрещена.

5. Усилен backlog:
   - ADR trade-off;
   - owner остаточного риска;
   - дата пересмотра временного решения;
   - Safe MVP vs Phase 2 hardening.

## Проверенный жёсткий кейс

Кейс: договоры обновляются в source-сервисе; событие надо отправить через Kafka; перед публикацией нужно REST-обогащение; Kafka одна; source не имеет Kafka-инфры; новый сервис слишком дорогой; source можно менять только минимально.

Результат: инструмент выбирает **Compromise: Source Outbox + Embedded/Platform Publisher**, а не абстрактный идеальный publisher-сервис. В отчёте явно фиксируются:

- source владеет фактом изменения;
- publisher технический, может быть job/module/platform adapter;
- enrichment выполняется после commit через pending outbox;
- в Kafka уходит финальный enriched event;
- риски coupling и Phase 2 по выносу publisher-а отдельно.

## Проверки

Выполнены:

```bash
python -m py_compile integration_architect_pro.py
python test_integration_architect.py
python test_sa_full_coverage.py
python test_rank_guard.py
python test_v48_product_sections.py
python test_v48_1_hard_process.py
```

Все основные regression/full/rank/product/hard-process проверки прошли успешно.
