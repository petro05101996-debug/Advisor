# Real-case check: CogProxy DQE v0.3.2

## Case

Real defect from a previous CogProxy archive: `cogproxy_dqe_core_clean.zip` had a CLI import failure.

Command used to reproduce:

```bash
python - <<'PY'
from cogproxy_dqe_core.cli import main
main(['test'])
PY
```

Actual stacktrace:

```text
Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
  File "/mnt/data/real_case_eval/clean/cogproxy_dqe_core/cli.py", line 17, in <module>
    def main(argv: Optional[List[str]] = None) -> None:
                   ^^^^^^^^
NameError: name 'Optional' is not defined
```

Ground truth:

```text
Root cause: `Optional` and `List` are used in `cli.py` type annotations without importing them.
Fix: add `from typing import Optional, List` or use future annotations / builtin-compatible annotation style.
Regression: smoke test that imports the CLI module and runs CLI basics.
```

## Important finding during this check

The first run exposed a bug in CogProxy's own Python traceback parser: when a frame such as `<stdin>` has no source-code line, the parser could consume the next `File ...` frame as if it were source code. Result: it lost the real failing frame `cli.py:17`.

Fixed in v0.3.2:

- Python tracebacks are now parsed line-by-line.
- Source-code line after a frame is optional.
- A following `File ...` line is not consumed as source code.
- Added a regression test for this exact stacktrace shape.

## v0.3.2 result on this real case

CogProxy output correctly identified:

- exception type: `NameError`
- exception message: `name 'Optional' is not defined`
- real failing frame: `cli.py:17 in <module>`
- failing line: `def main(argv: Optional[List[str]] = None) -> None:`
- root cause class: symbol used without import/definition
- minimal fix: `from typing import Optional, List`
- regression idea: smoke test for CLI/module import + compileall/unit tests

Generated artifacts:

```text
bug_report.md
bug_evidence.json
claims.json
llm_prompt.txt
receipt.json
report.md
```

## Manual score for this case

| Criterion | Score | Comment |
|---|---:|---|
| Root cause | 1.0 | Correct: missing typing import / undefined symbol. |
| File and line localization | 1.0 | Correctly found `cli.py:17`. |
| Evidence chain | 0.9 | Shows stacktrace + snippet. Some extra low-value search snippets remain. |
| Fix quality | 0.9 | Correct minimal fix. Does not directly emit a patch. |
| Regression test | 0.8 | Suggests smoke import test and compileall. |
| No hallucination | 0.85 | Mostly grounded; still lists extra suspect files due token search. |

Overall offline usefulness estimate: **~88/100 for this specific bug class**.

## What this proves

This proves CogProxy v0.3.2 is useful for a real import/runtime failure when the stacktrace contains enough information. It can localize the failing file/line, extract the relevant snippet, explain the likely root cause and suggest a minimal fix.

## What this does not prove

This does not prove full autonomous debugging on complex production systems. This case is stacktrace-driven and statically obvious once the correct frame is extracted.

Still not proven:

- CogProxy + real LLM beats the same LLM without CogProxy.
- Multi-service root cause analysis.
- Bugs requiring runtime reproduction, config, database state, or distributed tracing.
- Reliable scoring of external model output.

## Regression tests added

Two tests were added:

```text
test_python_stacktrace_frame_without_source_line_is_not_lost
test_bug_analysis_explains_missing_typing_import_case
```

Full test run:

```text
17/17 tests OK
compileall OK
version: cogproxy-dqe 0.3.2
```
