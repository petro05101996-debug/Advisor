# CogProxy DQE User Core v0.4.2

Рабочее ядро Distributed Quality Engine, перепроектированное **с точки зрения пользователя**: результат должен быть полезным артефактом, а не красивым pipeline ради pipeline.

v0.4.2 включает `bug_analysis`, benchmark harness, CLI-provider readiness checks и полный пользовательский smoke-аудит всех pack'ов. Исторически v0.3 добавил `bug_analysis` — модуль анализа багов по логу, stacktrace, коду и документации. Цель модуля: помочь внешней модели не гадать, а получить компактный evidence bundle и найти root cause в сложном проекте.

## Что умеет ядро

- `system_design`: архитектурный черновик — инварианты, state model, API, таблицы БД, critical flows, риски и план реализации.
- `requirements_qa`: нормализованные требования, test cases, negative checks, traceability matrix и вопросы.
- `research_analysis`: тезис, критика, MVP, метрики проверки и вывод.
- `bug_analysis`: exception, stack frames, подозрительные файлы, snippets кода/документации, гипотезы root cause, шаги проверки, fix plan, regression tests, prompt для модели.
- `receipt` честный: offline-режим не выдаёт 100% качества; claims не считаются verified автоматически.
- `compare`: one-shot baseline vs DQE по локальной рубрике.
- `--out`: запись отчётов и диагностических артефактов.

## Быстрый старт

```bash
cd cogproxy_dqe_user_core_v0_4_1_cli_ready
python -m cogproxy_dqe --version
python -m cogproxy_dqe packs
```

## Bug analysis: только лог + stacktrace + проект

```bash
python -m cogproxy_dqe run \
  --task "Клиент прислал баг: падает сборка payload заказа. Найди причину." \
  --pack bug_analysis \
  --mode audit \
  --project-dir examples/bug_analysis_demo \
  --docs-dir examples/bug_analysis_demo/docs \
  --log-file examples/bug_analysis_demo/log.txt \
  --stacktrace-file examples/bug_analysis_demo/stacktrace.txt \
  --out ./out_bug
```

Будут созданы:

```text
out_bug/report.md          # основной отчёт
out_bug/bug_report.md      # отдельный bug report
out_bug/bug_evidence.json  # frames, snippets, hypotheses, prompt
out_bug/llm_prompt.txt     # prompt для внешней модели
out_bug/receipt.json
out_bug/claims.json
```

С внешней CLI-моделью:

```bash
python -m cogproxy_dqe run \
  --task "Клиент прислал баг: найди root cause" \
  --pack bug_analysis \
  --mode audit \
  --project-dir ./my_project \
  --log-file ./bug.log \
  --stacktrace-file ./stacktrace.txt \
  --provider-cmd "your-llm-cli --model your-model" \
  --require-provider \
  --out ./out_bug
```

Команда provider должна читать prompt из stdin и писать ответ в stdout. DQE не принимает ответ модели как истину: он сохраняет evidence и отделяет гипотезы от подтверждённых фактов.

## System design пример

```bash
python -m cogproxy_dqe run \
  --task "Спроектируй сервис автоплатежей для ОПИФ: нужна заявка, статусы SUCCESS/FAILED, отключение и повторные попытки" \
  --pack system_design \
  --mode deep
```

## QA пример

```bash
python -m cogproxy_dqe run \
  --task "API должен вернуть статус SUCCESS. Если заявка закрыта, операция запрещена." \
  --pack requirements_qa \
  --mode audit
```

## Compare: увидеть пользу для пользователя

```bash
python -m cogproxy_dqe compare \
  --task "API должен вернуть статус SUCCESS. Если заявка закрыта, операция запрещена." \
  --pack requirements_qa \
  --mode audit
```

Offline compare синтетический: он не доказывает реальный uplift LLM, но показывает, что DQE-артефакт структурно полезнее обычного one-shot черновика.



### CLI provider readiness

Если вы хотите гарантировать, что внешняя CLI-модель реально была вызвана, используйте `--require-provider`. Без этого флага CogProxy может сохранить offline fallback, а статус нужно смотреть в `receipt.json` (`proxy_calls_model`).

```bash
python -m cogproxy_dqe run \
  --task "Найди root cause" \
  --pack bug_analysis \
  --mode audit \
  --project-dir ./my_project \
  --log-file ./bug.log \
  --stacktrace-file ./stacktrace.txt \
  --provider-cmd "your-llm-cli --model your-model" \
  --require-provider \
  --out ./out_bug
```


## Full user smoke audit

Проверка, что ядро не заточено только под bug_analysis и проходит основные пользовательские сценарии:

```bash
python tools/smoke_user_workflows.py --out smoke_results/local
```

Проверяются:

- `run` для `universal`, `system_design`, `requirements_qa`, `research_analysis`, `bug_analysis` во всех режимах `fast/standard/deep/audit`;
- `compare` для не-bug pack'ов;
- `--task-file`;
- `--provider-cmd` + `--require-provider`;
- offline benchmark 40 bug cases;
- real-LLM runner plumbing через fake provider.

## Тесты

```bash
python -m compileall -q cogproxy_dqe tests
python -m unittest discover -s tests -v
```

Проверено: 18/18 tests OK.

## Честное ограничение

`bug_analysis` без внешней модели — это не магический отладчик. Это evidence collector + heuristic root-cause assistant: он сужает поиск, показывает подозрительные строки, строит объяснимые гипотезы и готовит качественный prompt для модели. С внешней CLI-моделью модуль уже даёт ей релевантный контекст проекта, чтобы она искала причину, а не отвечала общими советами.


## v0.3.1 integrity note
A later integrity audit fixed CLI `--json` large-output handling and confirmed no v0.2 files were removed. See `INTEGRITY_AUDIT_V0_3_1.md`.

## Benchmark: bug_analysis uplift

Offline proxy benchmark on 40 bug cases:

```bash
python tools/run_bug_benchmark.py \
  --cases benchmarks/bug_analysis_40 \
  --out benchmark_results/local_run
```

Real CLI LLM benchmark, when you have a provider:

```bash
python tools/run_real_llm_bug_benchmark.py \
  --cases benchmarks/bug_analysis_40 \
  --provider-cmd "your-llm-cli --model your-model" \
  --out benchmark_results/real_llm_run
```

Read `BENCHMARK_REPORT.md` for the offline benchmark results. Read `FULL_USER_AUDIT_V0_4_2.md` for end-to-end user-flow checks across all packs and modes.
