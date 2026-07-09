# CogProxy DQE v0.4.2 — full user audit

Дата проверки: 2026-07-09.

Цель проверки: убедиться, что CogProxy работает как пользовательский CLI-инструмент, не заточен только под `bug_analysis` и не ломает основные сценарии `run`, `compare`, `--out`, `--json`, `--task-file`, `--provider-cmd`, benchmark runners.

## Итог

Вердикт: **рабочее CLI-ядро для пользователя готово в текущих границах**.

Что подтверждено:

- архив распаковывается и ставится через `pip install -e .`;
- console command `cogproxy-dqe` работает из произвольной директории;
- `python -m cogproxy_dqe` работает;
- metadata package name и runtime version согласованы: `cogproxy-dqe 0.4.2`;
- все 5 pack'ов запускаются: `universal`, `system_design`, `requirements_qa`, `research_analysis`, `bug_analysis`;
- все 4 mode'а запускаются: `fast`, `standard`, `deep`, `audit`;
- `--out` создаёт пользовательские артефакты;
- `--json` и `--receipt` возвращают валидный JSON;
- `--task-file` работает;
- `compare` работает для не-bug pack'ов;
- `--provider-cmd` реально прокидывает prompt во внешний CLI provider через stdin и сохраняет результат;
- `--require-provider` корректно падает с exit code `2`, если модель не вызвалась;
- `bug_analysis` работает не только на старом demo, но и на новом unseen invoice-case;
- offline benchmark 40 bug-cases воспроизводится;
- real-LLM runner теперь пишет `benchmark_report.md` и `results.json`.

Что **не** подтверждено:

- реальный uplift `CogProxy + сильная LLM > та же LLM без CogProxy`, потому что в этой среде нет настоящего CLI-доступа к GPT/Claude/Gemini;
- полноценная автономная отладка distributed bugs без stacktrace;
- запуск тестов целевого проекта, git blame, call graph, воспроизведение багов в сервисах.

## Проверка установки

Команды:

```bash
python -m venv /mnt/data/full_audit_v041/venv_v042
/mnt/data/full_audit_v041/venv_v042/bin/python -m pip install -e .
/mnt/data/full_audit_v041/venv_v042/bin/cogproxy-dqe --version
/mnt/data/full_audit_v041/venv_v042/bin/python - <<'PY'
from importlib.metadata import version
print(version('cogproxy-dqe'))
PY
```

Результат:

```text
cogproxy-dqe 0.4.2
metadata cogproxy-dqe 0.4.2
```

Исправление относительно v0.4.1: package metadata теперь называется `cogproxy-dqe`, а не `cogproxy-dqe-core`, чтобы пользовательская команда и package name не расходились.

## Unit / compile checks

Команды:

```bash
python -m compileall -q cogproxy_dqe tests tools
python -m unittest discover -s tests -v
```

Результат:

```text
18/18 tests OK
```

## Проверка pack'ов и mode'ов

Проверены `run --json --out` для всех комбинаций:

| pack | fast | standard | deep | audit |
|---|---:|---:|---:|---:|
| universal | OK | OK | OK | OK |
| system_design | OK | OK | OK | OK |
| requirements_qa | OK | OK | OK | OK |
| research_analysis | OK | OK | OK | OK |
| bug_analysis | OK | OK | OK | OK |

Для каждого запуска проверялось:

- exit code `0`;
- stdout является валидным JSON;
- `receipt.pack` совпадает с запрошенным pack;
- `receipt.quality.quality_score` присутствует;
- `report.md`, `receipt.json`, `claims.json` созданы;
- для `bug_analysis` дополнительно созданы `bug_report.md`, `bug_evidence.json`, `llm_prompt.txt`.

## Проверка, что не заточен только под bug_analysis

Запускались новые, не benchmark-задачи:

### system_design

Задача: сервис доставки лекарств с резервом в аптеке, курьером с температурным режимом, отменой, возвратом денег, SLA.

Проверено наличие в отчёте:

- температурный режим;
- резерв;
- SLA;
- инвариант;
- курьер.

Результат: **OK**.

### requirements_qa

Задача: `POST /orders`, `STOCK_EMPTY`, `CANCELLED`, повторная оплата с `idempotencyKey`.

Проверено наличие:

- `STOCK_EMPTY`;
- `CANCELLED`;
- `idempotencyKey`;
- `TC-`;
- покрытие требований.

Результат: **OK**.

### research_analysis

Задача: локальный агент для тестирования документации и сервисов без API-ключей.

Проверено наличие:

- MVP;
- метрик;
- блока “Что не доказано”;
- критики.

Результат: **OK**.

### universal

Задача: стоит ли делать инструмент, который превращает документацию в тест-кейсы и отчёт.

Проверено наличие:

- цель;
- решение;
- риски;
- следующие шаги.

Результат: **OK**.

### unseen bug_analysis

Создан новый invoice-case вне benchmark:

```python
def load_invoice(invoice_id):
    return None

def build_invoice_response(invoice_id):
    invoice = load_invoice(invoice_id)
    return {"total": invoice.total, "id": invoice_id}
```

Stacktrace:

```text
AttributeError: 'NoneType' object has no attribute 'total'
File "/srv/app/src/invoice.py", line 6, in build_invoice_response
```

Документация:

```text
If invoice is missing, API must return INVOICE_NOT_FOUND and must not raise 500.
```

CogProxy нашёл в отчёте:

- `AttributeError`;
- `invoice.py`;
- `invoice.total`;
- `INVOICE_NOT_FOUND`;
- regression test.

Результат: **OK**.

## Проверка compare

Проверены pack'и:

| pack | compare result |
|---|---:|
| universal | OK |
| system_design | OK |
| requirements_qa | OK |
| research_analysis | OK |

Проверялось создание:

- `compare.json`;
- `baseline.md`;
- `dqe.md`.

## Проверка provider-cmd

Использовался fake provider, который читает stdin и пишет stdout. Это не проверка качества LLM, но проверка канала:

```text
CogProxy → stdin → provider → stdout → CogProxy → model_analysis/receipt
```

Проверено:

| сценарий | результат |
|---|---:|
| `system_design` + fake provider + `--require-provider` | OK, `proxy_calls_model=true` |
| `bug_analysis` + fake provider + `--require-provider` | OK, `proxy_calls_model=true`, создан `model_analysis.md` |
| missing provider + `--require-provider` | OK, exit code `2` |

## Benchmark checks

Offline benchmark 40 cases:

```bash
python tools/run_bug_benchmark.py \
  --cases benchmarks/bug_analysis_40 \
  --out /mnt/data/full_audit_v041/v042_benchmark
```

Результат:

```text
n: 40
baseline_avg: 79.06
cogproxy_avg: 96.81
avg_uplift: 17.75
root_exact_baseline: 16/40
root_exact_dqe: 39/40
file_exact_baseline: 38/40
file_exact_dqe: 40/40
fix_exact_baseline: 17/40
fix_exact_dqe: 32/40
```

Важно: это **offline benchmark**, он не доказывает LLM-uplift.

Real LLM runner plumbing:

- проверен на 3 кейсах с fake provider;
- создан `benchmark_report.md`;
- создан `results.json`;
- `proxy_called=True` по строкам отчёта.

Полный запуск 40 кейсов с настоящей моделью нужно делать у пользователя через реальный CLI provider: Codex CLI, Claude Code, Gemini CLI, Ollama или другой stdin/stdout wrapper.

## Найденные проблемы и исправления в v0.4.2

1. **Package metadata была менее удобной для пользователя.**
   - Было: package name `cogproxy-dqe-core`, command `cogproxy-dqe`.
   - Стало: package name `cogproxy-dqe`, command `cogproxy-dqe`.

2. **Real LLM benchmark runner не писал markdown-отчёт.**
   - Было: только `results.json`.
   - Стало: `results.json` + `benchmark_report.md`.

3. **Добавлен smoke script для пользовательских сценариев.**
   - Новый файл: `tools/smoke_user_workflows.py`.
   - Он проверяет run/compare/out/json/task-file/provider/benchmarks.

## Честный продуктовый статус

Готово:

- как CLI-инструмент для локального запуска;
- как evidence builder для bug/root-cause analysis;
- как генератор первичных QA/system-design/research артефактов;
- как wrapper вокруг внешнего CLI provider;
- как среда для настоящего LLM benchmark у пользователя.

Не готово:

- как автономный отладчик сложного проекта;
- как доказанный усилитель LLM без запуска реальной LLM;
- как инструмент, который сам поднимает сервисы, запускает интеграционные тесты и доказывает root cause.

Финальная формула текущей версии:

```text
CogProxy v0.4.2 = рабочий CLI quality layer + bug evidence builder + provider wrapper.
Не финальный автономный инженер, но уже проверяемый инструмент для пользователя.
```
