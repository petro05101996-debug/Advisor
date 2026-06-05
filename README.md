# Интеграционный архитектор Pro v5.0.9 RU — 9+ hardening pack

Детерминированный rule-engine без LLM для первичного проектирования и аудита интеграций. Версия **v5.0.9** закрывает ключевые production gaps: нормализует пользовательские синонимы, выделяет shared Kafka topic/selective consumer как отдельный класс кейса, точнее работает с BFF/Customer 360, webhook, migration/strangler и enrichment-before-Kafka, а также усиливает production gates и regression suite.


## Что усилено в v5.0.9

- **Customer 360/BFF больше не путается с Loyalty ledger**: если Loyalty является только read-only источником для карточки клиента, top-level остаётся BFF/API Composition.
- **Ledger включается только при реальных операциях с балансом/баллами**: начисление, списание, refund/reversal, POS receipt, ledger entry.
- **Webhook idempotency aliases**: `providerEventId`, `webhookEventId`, `stripeEventId`, `callbackId`, `deliveryId`, `messageId` распознаются как ключи надёжности.
- **Меньше ложных blockers**: запись в собственную projection/sink БД не трактуется как “прямая запись в чужую БД”.
- **Retention warnings стали предметными**: отдельно подсвечиваются DWH/archive, outbox/inbox/DLQ/replay/audit, history/audit.
- **UI проще для новичка**: добавлены явные варианты “Карточка клиента 360”, “BFF/API composition”, “Read-model”, “читать общий Kafka topic и фильтровать”.

## Что нового в v5.0.9


- **Normalization layer**: пользователь может писать `customer_360`, `api_composition`, `shared_kafka_topic`, `migration_modernization`, `saga`, `no_new_topic`, `source менять нельзя` — движок приводит это к внутренней модели.
- **Shared Kafka Topic / Selective Consumer**: отдельный production-класс для кейсов “читаем общий topic, нужны 0.2–5% событий, отдельный topic/source-change запрещены”. Выводит selective consumer, capacity/backpressure, filter ratio, lag, idempotent sink, DLQ/quarantine и replay.
- **BFF/API Composition hardening**: read-only Customer 360 больше не получает ложный critical `no_idempotency`; важнее timeout budget, partial response, freshness и degradation policy.
- **Production gates расширены**: shared-topic кейс блокируется без selective-consumer каркаса, at-least-once/idempotent sink и replay/reprocess policy.
- **Контракты selective consumer**: добавлен контракт фильтра, метрики, commit policy и sink contract.
- **Regression suite расширен**: теперь 134 теста, включая shared Kafka, alias normalization, read-only BFF idempotency и версию UI.
- **Quality gate требований**: показывает, можно ли проектировать сейчас, чего не хватает и какие вопросы критично уточнить.
- **Главная архитектура vs внутренние слои**: отчёт явно разделяет top-level решение и слои вроде DWH, webhook, cache, legacy adapter.
- **MVP-вариант и Production-вариант**: что обязательно сделать на первом этапе, а что нужно для production-grade.
- **ADR export**: отдельный блок с контекстом, решением, альтернативами и последствиями.
- **Опасные альтернативы / антипаттерны**: объясняет, почему нельзя делать синхронную цепочку, DWH в core-flow, callback без Inbox, кэш для денег и т.д.
- **Capacity planning lite**: грубая оценка peak RPS, потока MB/s, GB/day, retention и стартового порядка partitions/workers.
- **Дополнительные Mermaid-диаграммы**: context, event flow, data flow, failure flow.
- **Проверка текущего состояния против целевого**: какие capabilities уже есть и чего не хватает.
- **Отчёты для ролей**: бизнес, аналитик, разработчик, архитектор.
- **Библиотека похожих шаблонов**: REST, Kafka consumer, webhook, Saga, DWH, legacy, migration, reference data, card 360.
- **Trade-off / compromise mode**: отчёт разделяет целевую архитектуру, реалистичный v1, остаточные риски и Phase 2 hardening.
- **Компромиссные варианты для enrichment-before-Kafka**: embedded/platform publisher при запрете нового сервиса; CDC/polling export при read-only source.

## Запуск

```bash
python integration_architect_pro.py
```

Открыть:

```text
http://127.0.0.1:8110/
```

## Проверка

```bash
python -m py_compile integration_architect_pro.py
pytest -q
# ожидаемо: 134 passed
python test_integration_architect.py
python test_sa_full_coverage.py
python test_rank_guard.py
python test_v48_product_sections.py
```

Ожидаемый результат:

```text
18/18 regression tests passed
16/16 full SA scenario tests passed
3/3 rank guard tests passed
2/2 v4.8 product section tests passed
```

## Как пользоваться

### Для новичка

Используйте верхний блок **“Заполнение для человека, который не знает архитектурные термины”**:

1. Выберите бизнес-ситуацию карточкой.
2. Введите название задачи.
3. Перечислите системы через запятую.
4. Ответьте на простые вопросы про нагрузку, скорость, свежесть, риски и внешние системы.
5. Нажмите **“Собрать черновик из ответов”**.
6. Нажмите **“Сформировать отчёт”**.

### Для системного аналитика

Нажмите **“Я аналитик, покажи всё”** и уточните матрицы:

- системы;
- шаги процесса;
- ошибки;
- поля данных;
- контракты;
- DWH/legacy/security/observability.

## Как читать отчёт

Ключевые разделы v5.0.9:

1. **Quality gate требований** — можно ли доверять проектированию.
2. **Ограничения, компромиссы и реалистичный вариант** — что можно сделать сейчас, чем это хуже целевого решения и какие контроли нельзя выкинуть.
3. **Главная архитектура и внутренние слои** — что является каркасом решения, а что слоем.
3. **MVP-вариант** — минимально безопасная реализация.
4. **Production-вариант** — что нужно для промышленного уровня.
5. **Почему не выбраны опасные альтернативы** — антипаттерны.
6. **Capacity planning lite** — грубая оценка нагрузки.
7. **Проверка текущего состояния против целевого** — разрывы capabilities.
8. **ADR export** — готовая основа для Confluence/ADR.
9. **Дополнительные диаграммы** — context/event/data/failure flow.

## Ограничение

Инструмент не заменяет архитектурное ревью. Он помогает системному аналитику собрать бизнес-контекст, найти риски, подготовить архитектурную основу и ADR.

## Что усилено в v5.0.9

- **Active-active financial write**: если по балансу/деньгам есть active-active, multi-region write, split-brain или double-spend, production gate больше не становится GREEN. Инструмент требует single-writer per account/shard, append-only ledger, operationId/idempotency, consensus/conflict-resolution, reconciliation и manual correction.
- **Highload Stream Ingestion / Stream Processing**: IoT/telemetry/realtime alerting больше не ранжируется как DWH top-level. DWH/Data Lake теперь трактуется как downstream-потребитель, а главный каркас — ingestion, partition key, watermark/event time, late-event policy, hot partition controls, replay и DLQ/quarantine.
- **Multi-tenant noisy neighbor**: добавлен отдельный риск для общего consumer pool / shared topic, где один крупный tenant создаёт lag остальным. Проверяются tenantId partitioning, quotas, separate consumer pools, fair scheduling, backpressure и lag per tenant metrics.
- **Privacy + legal hold / retention exception**: при удалении ПДн теперь отдельно подсвечивается, что часть данных может быть нельзя физически удалить. Нужно разделять deletion, anonymization/pseudonymization, retention exception register, evidence per system и audit trail.
- **Production packaging**: добавлен Dockerfile, запуск через HOST/PORT, bind по умолчанию `0.0.0.0`, ограничение размера POST через `MAX_POST_BYTES` и healthcheck.
- **Regression suite расширен до 138 тестов**: добавлены adversarial-тесты на active-active financial write, IoT stream ingestion, multi-tenant noisy neighbor и privacy legal hold.

## Запуск в Docker

```bash
docker build -t integration-architect-pro .
docker run --rm -p 8110:8110 integration-architect-pro
```

После запуска открыть:

```text
http://localhost:8110
```


## v5.0.9 UX/mobile additions

- Добавлен мобильный вариант: viewport, одно-колоночные карточки, крупные поля/кнопки, sticky submit для телефона.
- Добавлен отдельный ультракороткий путь проектирования: пользователь выбирает интервью-кейс и несколько ограничений, полное заполнение формы необязательно.
- В результате добавлена карта цепочки сервисов и данных: что делает каждый сервис, как идут интеграционные взаимодействия и какие таблицы/хранилища участвуют.
- В Markdown-отчёт добавлен раздел 17A с цепочкой сервисов, БД и интеграций.
