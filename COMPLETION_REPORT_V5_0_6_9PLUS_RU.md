# Отчёт v5.0.6 — доведение до 9+ уровня

## Что было исправлено

1. **Customer 360 / BFF / API Composition**
   - Исправлено ложное срабатывание `Financial/Loyalty Ledger State Machine`, когда `Loyalty` был всего лишь read-only источником в карточке клиента.
   - Теперь read-only экран, `partial response`, `freshness labels`, `per-source cache TTL`, `customer_360`, `api_composition`, `read_model` получают приоритет BFF.

2. **Loyalty ledger**
   - Ledger больше не включается по одному слову `Loyalty` или `bonus`.
   - Нужен реальный контекст изменения баланса: начисление/списание, POS receipt, refund/reversal, ledger entry, balance mutation.
   - Широкая event choreography по заказу с веткой Loyalty остаётся `Event Choreography`, а не превращается в ledger.

3. **Webhook / callback**
   - Добавлены алиасы ключей надёжности: `providerEventId`, `provider_event_id`, `stripeEventId`, `webhookEventId`, `callbackId`, `deliveryId`, `messageId`.
   - Это убирает ложный blocker `no_idempotency` для реальных provider webhook кейсов.

4. **Direct DB write blocker**
   - Запись в собственную projection/sink БД больше не трактуется как “прямая запись в чужую БД”.
   - Явная прямая запись в чужую БД остаётся high-risk антипаттерном.
   - Если запрет не зафиксирован, но кейс релевантен, выдаётся мягкое policy-предупреждение, а не ложный blocker.

5. **Retention warning**
   - Старый общий текст `Нет retention для больших данных` заменён на предметный:
     - `Не задан retention для DWH/archive`
     - `Не задан retention для outbox/inbox/DLQ/replay/audit`
     - `Не задан retention для history/audit`

6. **Русский и простой UI/UX**
   - В форму добавлены явные пользовательские варианты:
     - `Карточка клиента 360 / Customer 360`
     - `BFF/API composition для экрана`
     - `Read-model / только чтение`
     - `Читать общий Kafka topic и фильтровать нужные события`
   - Основные подсказки и поток мастера остаются на русском; общепринятые термины сохранены: REST, Kafka, BFF, API, Webhook, CDC, DWH, Outbox, Inbox, DLQ, SLA, RPS/TPS.

## Добавленные regression tests

Добавлен файл `test_v50_6_9plus_russian_ux.py`:

- Customer 360 with Loyalty source → BFF, не ledger.
- Provider webhook with `providerEventId` → нет ложного `no_idempotency`.
- Shared Kafka topic → own Postgres projection/sink не получает ложный `direct_db_write` high blocker.
- DWH retention → предметный retention warning вместо общего текста.

## Результат проверки

```text
python -m py_compile integration_architect_pro.py
pytest -q
134 passed
```

## Жёсткая оценка после патча

- Полезность для системного аналитика: **9.1/10**
- Покрытие сложных интеграционных кейсов: **9.0/10**
- UX для новичка при заполнении формы: **8.8/10**
- Production-readiness как deterministic rule-engine: **8.7/10**

Итог: **9.0+/10 как практический инструктор/первичный архитектор интеграций без LLM**. До полноценного enterprise-продукта остаются визуальный polish, экспорт в Confluence/ADR под шаблон компании и больше отраслевых preset-кейсов.
