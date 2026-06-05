# Full check report v4.9.7

## Что проверено

- Синтаксис Python: `python -m py_compile integration_architect_pro.py`.
- Полный набор автотестов: `74 passed`.
- Smoke/regression на form-only сценариях без больших текстовых матриц.
- Проверка, что production-hardening не сломал старые кейсы: E2E/Saga, enrichment-before-Kafka, webhook, legacy file-only, BFF/Customer360, DWH, regulatory.

## Найденные дефекты после v4.9.6

1. **Form-only DB + Kafka dual-write мог уходить в Basic API + DB.**
   Причина: `event_needed` определялся в основном по текстовым матрицам `systems_matrix/process_steps`, а не по выбранным пользователем form-полям `allowed_channels`, `business_situations`, `result_model`, `change_policy`.

2. **Outbox мог не попасть в `pattern_ids` для form-only Kafka-сценария.**
   Причина: `outbox_needed` также зависел от каналов, распознанных из текстовых матриц, а не от явного form-only Kafka/event intent.

3. **Read-only/source-forbidden сценарий с требованием события мог ошибочно уходить в Basic API.**
   Исправлено: source/core no-change теперь ведёт к `non_invasive_extension`, если это не file-only/legacy batch.

4. **File-only legacy мог проиграть non-invasive extension.**
   Исправлено: batch/file integration сохраняет приоритет для SFTP/file-only кейсов.

5. **Financial webhook без signature/raw body мог быть недостаточно жёстко заблокирован production gate.**
   Исправлено: для внешнего/финансового webhook отсутствие подтверждённой signature/raw body теперь даёт `RED` через production gate, даже если главным top-level остаётся Financial Operation State Machine.

6. **Thin webhook / snapshot export с `current_at_publish` мог несправедливо считаться бизнес-конфликтом.**
   Исправлено: если это `thin_event`/`snapshot_export` и в контракте есть markers (`dataAsOf`, `sourceEventId`, `aggregateVersion`, `dataVersion` и т.п.), конфликт не создаётся. Anti-pattern остаётся high-risk как осознанный компромисс, чтобы архитектор явно зафиксировал consistency level.

## Добавленные regression tests

Файл: `test_v49_7_form_only_regressions.py`

Проверяет:

- form-only DB + Kafka dual-write выбирает `Event-driven + Transactional Outbox`;
- financial external webhook без signature/raw body получает `RED`;
- source read-only event request выбирает `Non-invasive Existing Process Extension`, а не Basic API;
- thin-event current-at-publish с markers не создаёт business conflict.

## Итог

Текущая версия после проверки ближе к production-grade именно для твоей цели: пользователь может выбирать ответы из формы, а не обязан заполнять большие текстовые матрицы, чтобы движок понял класс интеграции.

```text
74 passed
```
