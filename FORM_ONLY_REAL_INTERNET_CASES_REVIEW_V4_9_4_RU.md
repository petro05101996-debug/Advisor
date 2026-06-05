# Проверка v4.9.4 на реальных интернет-кейсах через form-only вход


Проверка целенаправленно моделирует не свободный текст, а значения, которые собирает deterministic form-only wizard: scenario/entity/system count/target/enrichment/constraints/failures/artifacts.


## Результаты

- FORM_REAL_CASE_1_outbox_order_kafka → **Event Choreography**, score=100, anti=[]
- FORM_REAL_CASE_2_saga_order_payment_inventory → **Financial Operation State Machine**, score=100, anti=['sync_chain', 'highload_low_latency_chain', 'event_without_broker']
- FORM_REAL_CASE_3_stripe_like_webhook_duplicates → **Webhook Intake + Inbox Processing**, score=70, anti=[]
- FORM_REAL_CASE_4_customer_360 → **BFF/API Composition with Partial Response**, score=100, anti=[]
- FORM_REAL_CASE_5_sftp_batch → **Batch/File Integration**, score=100, anti=['direct_db_write']
- FORM_REAL_CASE_6_strangler_migration → **Migration / Strangler Fig**, score=100, anti=[]

## Что исправлено относительно v4.9.3

- Убрана подсказка “укажите название/системы”: пользователь действительно выбирает варианты из форм.
- Form-only builder теперь автоматически генерирует business statuses/final statuses.
- Автоматически добавляются idempotencyKey/eventId/externalEventId для retry, Kafka, webhook, money/application flows.
- Автоматически задаётся retention, чтобы отчёт не шумел no_retention для highload/webhook/BFF.
- При Kafka/application/money/callback сценариях builder сам добавляет Outbox/Event capabilities, если пользователь выбрал соответствующий target/scenario.

## Вывод

Инструмент рабочий: на проверенных публичных паттернах выбирает ожидаемые архитектуры и генерирует контролируемый E2E blueprint без LLM/free-text ввода.

## Дополнительное исправление после повторного прогона
- no_idempotency больше не срабатывает ложно, если form-only мастер сгенерировал уникальный business key: idempotencyKey/eventId/externalEventId/operationId/batchId/fileId/checksum.
- event_without_broker больше не срабатывает ложно для Saga/Process Manager, где допустима queue как транспорт команд.
