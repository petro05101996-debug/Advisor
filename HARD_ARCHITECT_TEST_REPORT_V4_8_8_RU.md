# Жёсткая проверка Integration Architect Pro v4.8.8

## Что проверено

1. Полный встроенный pytest-набор.
2. `py_compile` основного файла.
3. Старт HTTP-интерфейса на `127.0.0.1:8110`.
4. Дополнительные brutal-smoke сценарии как архитектор/системный аналитик:
   - highload E2E кредитная заявка с fan-out/fan-in, БКИ, CRM, DWH, уведомлениями;
   - договоры: source-сервис без Kafka, одно Kafka-событие, REST enrichment перед публикацией;
   - договоры: enrichment required, но Outbox/CDC не разрешены/не заявлены;
   - плохая синхронная финансовая цепочка с внешним партнёром;
   - multi-source Customer 360 с partial response;
   - legacy file-only batch exchange.

## Найденная проблема

Исходный архив имел регрессию: тест `test_required_enrichment_flags_no_outbox_or_cdc_allowed` падал.

Смысл дефекта: если enrichment перед Kafka обязателен, но в форме нет `add_outbox`, нет существующего `outbox` и нет CDC, инструмент мог не показывать критичный анти-паттерн `enrichment_requires_change_but_outbox_not_allowed` из-за слишком мягкой трактовки `source_change_policy=minimal_table_only`.

## Исправление

Уточнено правило `source_can_add_minimal_outbox`: теперь минимальная изменяемость source-системы не считается автоматическим разрешением на Outbox, когда пользователь фактически указал только `add_event` и не указал `add_outbox` / существующий `outbox` / CDC.

## Результаты после исправления

```text
40 passed in 0.37s
45 passed in 0.42s  # с дополнительным test_v48_8_brutal_smoke.py
```

HTTP smoke:

```text
python integration_architect_pro.py
GET http://127.0.0.1:8110/ -> HTML UI returned
```

## Архитектурный вывод

Инструмент рабочий и уже полезен как deterministic rule-engine для первичного проектирования и аудита интеграций. Он покрывает не только простые REST/Kafka/DWH/file кейсы, но и сложные ситуации: E2E процесс vs слой доставки события, enrichment-before-Kafka, ownership события, компромисс из-за запрета нового сервиса/инфраструктуры, highload, lowload, legacy, partial response, блокировку плохих синхронных цепочек.

## Что покрывается хорошо

- Разделение top-level архитектуры и внутренних слоёв.
- Saga / orchestrated E2E для сложных процессов.
- Outbox/Inbox/Kafka/retry/DLQ для событийных процессов.
- Enrichment перед Kafka с вопросами ownership, consistency и sourceEventId/outboxEventId.
- Компромиссы: новый сервис нельзя, инфраструктуру нельзя, source менять нельзя/почти нельзя.
- Legacy/file/batch и DWH как отдельные слои, а не core-flow.
- Multi-source aggregation / BFF partial response.
- Quality gate и readiness score.
- ADR, capacity-lite, diagrams, contracts, DB sketch.

## Остаточные ограничения

1. Это не заменяет архитектурное ревью: правила детерминированные, поэтому спорные организационные ограничения всё равно надо фиксировать в ADR.
2. Capacity planning lite — ориентир, не sizing.
3. Ввод всё ещё требует дисциплины: если пользователь не заполнит business_situations, systems/steps, fields и constraints, качество вывода падает.
4. Для production-grade надо поддерживать regression pack на каждый новый кейс, иначе легко сломать ranking/anti-patterns.

## Итог

После исправления — можно считать версию рабочей для жёсткого тестового использования. Для реального применения как помощника системного аналитика я бы держал обязательный pipeline:

```text
py_compile -> pytest -> brutal smoke -> ручной просмотр 2-3 markdown отчётов
```
