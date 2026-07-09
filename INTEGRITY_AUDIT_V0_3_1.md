# CogProxy DQE v0.3.1 Integrity Audit

## Scope
Audited v0.3 bug_analysis release against v0.2 user-core archive to check whether any existing user-facing functionality was removed or broken.

## File-level comparison v0.2 → v0.3
Removed files: none.

Added files:
- `cogproxy_dqe/bug_analysis.py`
- `examples/bug_analysis_demo/app/orders.py`
- `examples/bug_analysis_demo/app/users.py`
- `examples/bug_analysis_demo/docs/orders.md`
- `examples/bug_analysis_demo/log.txt`
- `examples/bug_analysis_demo/stacktrace.txt`

Changed existing files intentionally:
- `cogproxy_dqe/__init__.py` — version bump.
- `cogproxy_dqe/cli.py` — bug-analysis flags, output artifact writer, fixed large JSON stdout handling.
- `cogproxy_dqe/contract.py` — bug/stacktrace task detection and risk level markers.
- `cogproxy_dqe/evaluator.py` — compare passes extra bug context to DQE.
- `cogproxy_dqe/packs.py` — registered `bug_analysis` domain pack.
- `cogproxy_dqe/runtime.py` — passes extra context and bug evidence to verifier context.
- `cogproxy_dqe/workers.py` — dispatches generation to bug analyzer for `bug_analysis` pack.
- `pyproject.toml` — version bump.
- `tests/test_core.py` — added bug-analysis tests.
- Reports/docs updated.

## Regression checks
- `python -m compileall -q cogproxy_dqe tests`: OK
- `python -m unittest discover -s tests -v`: 15/15 OK
- `python -m cogproxy_dqe --version`: OK, `cogproxy-dqe 0.3.1`
- `python -m cogproxy_dqe packs`: OK, all packs listed, including previous packs and `bug_analysis`.
- `run --json`: OK after v0.3.1 stdout fix.
- `compare --json`: OK.
- `run --out` with `bug_analysis`: OK, writes `report.md`, `receipt.json`, `claims.json`, `bug_report.md`, `bug_evidence.json`, `llm_prompt.txt`.

## Pack smoke checks
Checked `run --receipt` for:
- `universal`: fast, standard, deep, audit — OK
- `system_design`: fast, standard, deep, audit — OK
- `requirements_qa`: fast, standard, deep, audit — OK
- `research_analysis`: fast, standard, deep, audit — OK
- `bug_analysis`: fast, standard, deep, audit — OK

## Bug-analysis functional check
Demo project:
- `app/orders.py` uses `user["id"]`.
- `app/users.py` returns `None`.
- stacktrace points to `orders.py:5` with `TypeError: 'NoneType' object is not subscriptable`.

Result:
- Parsed exception: `TypeError` / `'NoneType' object is not subscriptable`.
- Parsed frame: `examples/bug_analysis_demo/app/orders.py:5 in build_payload`.
- Evidence includes stacktrace, `orders.py`, `users.py`, docs.
- Report names likely cause: nullable/None value used as object/dict without guard.
- Report includes `find_by_order`, `user["id"]`, `orders.py`, `None`, fix plan, regression test direction.

## Found and fixed during audit
Found: v0.3 `run --json` could fail in this sandbox with `BlockingIOError` when printing a large JSON payload.
Fix in v0.3.1:
- CLI now writes a smaller user-facing JSON payload instead of dumping huge internal intermediate prompts.
- JSON output still contains `final_answer`, `receipt`, `contract`, and `claims`.
- Full debug artifacts remain available through `--out` files.

## Honest limitations not fixed yet
- `bug_analysis` evidence is useful but not a full call graph.
- No real LLM uplift is proven until benchmark against the same external CLI model is run.
- Receipt still cannot deeply judge provider answer correctness.
- Large-project stacktrace-first resolver should be improved so stacktrace files bypass the global indexing cap.
- Ambiguous basename stacktraces still need stronger path/function ranking.

## Conclusion
No v0.2 user-facing files were removed. Existing packs and CLI flows still work. v0.3 added `bug_analysis`; v0.3.1 fixes the JSON output issue found during audit.
