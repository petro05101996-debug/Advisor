# v4.9.3 — E2E-проектирование через формы, без свободного описания

## Что изменено

Инструмент переведён в режим deterministic form-based wizard: пользователь выбирает ответы из готовых вариантов, а не описывает задачу словами.

## Новые блоки простого мастера

1. Главный объект: заявка, заказ, договор, клиент, операция, файл, отчётность, статус.
2. Количество систем: 2, 3, 4–5, 6+.
3. Источник правды: наш сервис/БД, внешняя система, legacy, DWH/реплика, несколько источников.
4. Получатель результата: API, Kafka/event, клиентский экран, DWH, внешний партнёр, файл/SFTP.
5. Enrichment: нет, REST перед отправкой, после события/в consumer, неизвестно.
6. Разрешённые изменения: API, таблицы/статусы, Outbox/Inbox, событие, CDC, read-only.
7. Ограничения: нельзя новый сервис, нельзя менять source, один Kafka topic, CDC нельзя, только REST, короткий срок.
8. Ошибки: timeout, дубли, out-of-order, poison message, replay, manual recovery.
9. Выходные артефакты: E2E blueprint, sequence diagram, API contract, event contract, error matrix, ADR/ТЗ, test plan, rollout plan.

## Что теперь генерируется автоматически

- project_name;
- business_goal;
- systems_matrix;
- process_steps;
- main_entity;
- fields;
- error_matrix;
- source_of_truth;
- change_policy;
- allowed_channels;
- forbidden_channels;
- enrichment_required;
- enrichment_channel;
- kafka_topology;
- source_has_kafka_infra;
- event_payload_intent;
- compromise_comment;
- rollout/testing/observability-related settings.

## Почему это важно

Так как инструмент не использует LLM, свободное описание задачи не должно быть основным интерфейсом. В v4.9.3 пользователь отвечает через формы, а приложение строит архитектурный черновик по правилам.

## Проверка

Добавлен regression test:

- `test_v49_3_form_only_e2e_ux.py`

Проверяет, что:

- в простом мастере нет обязательного свободного ввода `Системы через запятую` и `Название задачи`;
- появились form-only блоки E2E-проектирования;
- JavaScript генерирует systems/process/error/enrichment/kafka/compromise поля из выбранных вариантов.

Финальный прогон:

```text
58 passed
```
