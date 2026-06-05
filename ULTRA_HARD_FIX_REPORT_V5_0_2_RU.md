# ULTRA HARD FIX REPORT — v5.0.2

## Что исправлено

1. **Regulatory schema/model change**
   - Добавлен точный детектор `regulatory_schema_signal()`.
   - Кейс “ЦБ изменил модель кредита: одна цель займа → несколько целей займа” теперь классифицируется как `regulatory_schema_change`, а не как Batch/File или DWH.
   - Обычная регуляторная витрина/DWH-отчётность при этом не сломана и остаётся `Data Pipeline / DWH`.

2. **DWH/offload/storage-growth**
   - Кейс “prod DB растёт TB/year, DWH забирает раз в день” теперь получает top-level `Data Pipeline / DWH`, а не простой `Batch/File Integration`.
   - В DWH-контракты добавлены `watermark/offset`, `snapshot_id`, retention/archive, reconciliation и backfill.

3. **Webhook/callback**
   - Если `result_model=callback` или выбран `webhook_callback`, top-level становится `Webhook Intake + Inbox Processing`.
   - Financial state machine остаётся внутренним слоем, но не перехватывает входной webhook-контур.
   - В security-контракты добавлены raw body, signature, timestamp tolerance, secret rotation, provider retry policy и reconciliation.

4. **BFF/API Composition**
   - Fan-out для BFF больше не считается автоматическим RED-блокером, если явно выбраны partial response/fallback/freshness controls.
   - Для BFF с partial response sync-chain теперь получает medium warning вместо critical blocker.

5. **Regression safety**
   - Сохранены старые ожидания:
     - legacy file-only → `Batch/File Integration`;
     - regulatory reporting/DWH showcase → `Data Pipeline / DWH`;
     - no-change production extension → `Non-invasive Existing Process Extension`;
     - financial command flow → `Financial Operation State Machine`;
     - external partner login/password → `External API Adapter with Resilience`.

## Новые регрессионные тесты

Добавлен файл:

- `test_v50_2_ultra_hard_real_case_fixes.py`

Покрывает:

- ЦБ / изменение модели цели займа;
- prod DB TB/year + DWH offload;
- payment provider webhook with duplicates/out-of-order/reconciliation;
- Customer 360 BFF partial response.

## Проверка

```bash
pytest -q
```

Результат:

```text
114 passed
```
