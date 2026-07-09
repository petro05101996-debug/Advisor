# CogProxy v0.4.0 — bug-analysis uplift benchmark

## Важное ограничение

Этот прогон НЕ вызывает настоящую внешнюю LLM. В текущей среде нет доступного CLI/API-провайдера модели. Поэтому это не финальное доказательство “CogProxy + LLM лучше LLM без CogProxy”.

Что реально проверено: CogProxy как слой подготовки evidence/контекста и offline bug-analysis сравнен с one-shot baseline на 40 баг-кейсах с ground truth. Это проверяет, даёт ли ядро полезный uplift само по себе и готов ли benchmark-контур для настоящей модели.

## Методика

- 40 кейсов: Python, JS/TS, Java, Go, DB/SQL, config/dependency, contract drift.
- У каждого кейса есть `ground_truth.json`: ожидаемые файлы/строки, root-cause terms, fix terms, regression-test terms, forbidden terms.
- Baseline: прямой one-shot анализ по логу/stacktrace/project text без CogProxy evidence graph.
- CogProxy: `run_dqe(... pack=bug_analysis, mode=audit)` с log, stacktrace, project-dir, docs-dir.
- Scoring: 100 баллов = root cause 35 + file/line 25 + fix 20 + regression test 15 + hallucination guard 5.

## Итоговые цифры

- Cases: 40
- Baseline average: 79.06/100
- CogProxy average: 96.81/100
- Average uplift: +17.75
- Root cause exact: baseline 16/40, CogProxy 39/40
- File+line localization: baseline 38/40, CogProxy 40/40
- Fix exact: baseline 17/40, CogProxy 32/40

## Что показал benchmark

CogProxy резко улучшает именно те вещи, ради которых он нужен пользователю: локализацию файла/строки, связку stacktrace → code snippet → hypothesis, и формирование исправления/regression test. На типовых stacktrace-driven багax uplift получился сильный.

Но это НЕ значит, что доказан uplift на реальной LLM. Для этого нужно прогнать тот же benchmark с реальным `--provider-cmd` и затем оценить baseline LLM vs CogProxy+LLM.

## Топ улучшений

| case | baseline | CogProxy | uplift |
|---|---:|---:|---:|
| bug_022_go_nil_pointer | 30.0 | 100.0 | +70.0 |
| bug_001_real_missing_typing_import | 47.5 | 100.0 | +52.5 |
| bug_004_index_empty_items | 62.5 | 100.0 | +37.5 |
| bug_013_json_decode_html | 62.5 | 100.0 | +37.5 |
| bug_015_config_base_url | 62.5 | 100.0 | +37.5 |
| bug_019_uuid_value | 62.5 | 100.0 | +37.5 |
| bug_021_java_number_format | 62.5 | 100.0 | +37.5 |
| bug_029_custom_domain | 62.5 | 100.0 | +37.5 |
| bug_008_js_undefined_id | 72.5 | 100.0 | +27.5 |
| bug_012_attribute_none | 72.5 | 100.0 | +27.5 |

## Слабые / без uplift

| case | baseline | CogProxy | uplift | comment |
|---|---:|---:|---:|---|
| bug_005_date_valueerror | 90.0 | 90.0 | 0.0 | baseline already strong or scoring too strict |
| bug_006_integrity_duplicate | 90.0 | 90.0 | 0.0 | baseline already strong or scoring too strict |
| bug_010_java_npe_order_customer | 100.0 | 100.0 | 0.0 | baseline already strong or scoring too strict |
| bug_014_timeout_dependency | 82.5 | 82.5 | 0.0 | baseline already strong or scoring too strict |
| bug_031_contract_variant | 100.0 | 100.0 | 0.0 | baseline already strong or scoring too strict |
| bug_032_contract_variant | 100.0 | 100.0 | 0.0 | baseline already strong or scoring too strict |
| bug_033_contract_variant | 100.0 | 100.0 | 0.0 | baseline already strong or scoring too strict |
| bug_034_contract_variant | 100.0 | 100.0 | 0.0 | baseline already strong or scoring too strict |
| bug_035_contract_variant | 100.0 | 100.0 | 0.0 | baseline already strong or scoring too strict |
| bug_036_contract_variant | 100.0 | 100.0 | 0.0 | baseline already strong or scoring too strict |
| bug_037_contract_variant | 100.0 | 100.0 | 0.0 | baseline already strong or scoring too strict |
| bug_038_contract_variant | 100.0 | 100.0 | 0.0 | baseline already strong or scoring too strict |
| bug_039_contract_variant | 100.0 | 100.0 | 0.0 | baseline already strong or scoring too strict |
| bug_040_contract_variant | 100.0 | 100.0 | 0.0 | baseline already strong or scoring too strict |

## Важные исправления после первого прогона

Первый benchmark на v0.3.2 нашёл слабые места: ImportError/ModuleNotFoundError, UUID parsing, Java NumberFormatException, Redis connection refused/config. После этого в v0.4.0 добавлены специальные гипотезы и fix plans для этих классов ошибок.

Также добавлены улучшения resolution:
- stacktrace-referenced files now bypass general project index limit;
- ambiguous basename resolution prefers file containing exact source line from stacktrace;
- Go stacktrace `/path/file.go:line` parsing added;
- custom `Violation` exceptions are recognized better.

## Как воспроизвести

```bash
cd cogproxy_dqe_user_core_v0_4_benchmark
python tools/run_bug_benchmark.py --cases benchmarks/bug_analysis_40 --out ./benchmark_results/local_run
```

## Что нужно для настоящего LLM-uplift benchmark

Этот archive содержит cases и scorer. Следующий честный шаг: добавить runner, который вызывает одну и ту же реальную CLI-модель в двух режимах: raw baseline prompt и CogProxy evidence prompt. Тогда можно честно мерить `LLM` vs `CogProxy+LLM`.

## Runner для настоящей CLI-модели

В архив добавлен отдельный runner:

```bash
python tools/run_real_llm_bug_benchmark.py \
  --cases benchmarks/bug_analysis_40 \
  --provider-cmd "your-llm-cli --model your-model" \
  --out benchmark_results/real_llm_run
```

Он сравнивает:

- baseline: raw one-shot prompt с логом, stacktrace, кодом и документацией;
- CogProxy: тот же кейс, но через `bug_analysis`, evidence extraction и structured prompt;
- provider: одна и та же CLI-модель в обоих режимах.

В этой среде runner не был запущен с реальной моделью, потому что доступного CLI LLM provider нет.
