# Final hard-process fix report v4.8.2

Проверено после доработки:

- Readiness score больше не расходится между резюме и ADR export.
- Quality Gate больше не спрашивает «какой idempotency key», если idempotency/unique key уже указан; вместо этого просит уточнить TTL, scope, replay same response policy и conflict policy.
- DDL не дублирует системные поля status/version/correlation_id, даже если пользователь ввёл их в fields.
- Capacity planning оставляет совместимый числовой minimum partitions/workers и дополнительно выводит диапазон для нагрузочного теста.
- Context diagram для сложных процессов больше не рисует всё линейной цепочкой; ветки идут от Process Manager / State Machine, DWH/async выводятся non-blocking.
- Audit score caps стали жёстче: critical consistency/reliability/observability problems режут промежуточные оценки, а не только overall verdict.

Тесты:

```text
32 passed
```

Сгенерирован отчёт: generated_integration_architect_reports/hard_credit_integration_final_check.md
