# CogProxy DQE v0.4.1 — CLI Readiness Report

## Verdict

CLI integration is ready for controlled use with an external CLI LLM provider.

What is verified:

- package can be installed with `pip install -e .`;
- console entrypoint `cogproxy-dqe` works;
- `python -m cogproxy_dqe` works;
- `--provider-cmd` receives prompt via stdin;
- provider stdout is captured and saved to `model_analysis.md`;
- `receipt.json` correctly marks `provider=cli` and `proxy_calls_model=true` when provider succeeds;
- bad provider command is now detectable with `--require-provider` and exits with code `2`;
- real-LLM benchmark runner can execute through a CLI provider command.

## Important limitation

This check used a fake local CLI provider, not a real LLM binary. So this proves CLI plumbing/readiness, not real LLM quality uplift.

## Checks run

### Core tests

```bash
python -m compileall -q cogproxy_dqe tests tools
python -m unittest discover -s tests -v
```

Result:

```text
18/18 tests OK
```

### Package install and entrypoint

```bash
python -m venv /mnt/data/cli_readiness_check/venv_041
/mnt/data/cli_readiness_check/venv_041/bin/python -m pip install -e .
/mnt/data/cli_readiness_check/venv_041/bin/cogproxy-dqe --version
/mnt/data/cli_readiness_check/venv_041/bin/python - <<'PY'
from importlib.metadata import version
print(version('cogproxy-dqe-core'))
PY
```

Result:

```text
cogproxy-dqe 0.4.1
metadata-version 0.4.1
```

### CLI provider success path

Command shape tested:

```bash
cogproxy-dqe run \
  --task "CLI import fails. Find root cause." \
  --pack bug_analysis \
  --mode audit \
  --project-dir benchmarks/bug_analysis_40/bug_001_real_missing_typing_import/project \
  --log-file benchmarks/bug_analysis_40/bug_001_real_missing_typing_import/log.txt \
  --stacktrace-file benchmarks/bug_analysis_40/bug_001_real_missing_typing_import/stacktrace.txt \
  --provider-cmd "python fake_llm.py" \
  --require-provider \
  --out out
```

Verified artifacts:

```text
bug_evidence.json
bug_report.md
claims.json
llm_prompt.txt
model_analysis.md
receipt.json
report.md
```

Verified receipt:

```json
{
  "provider": "cli",
  "proxy_calls_model": true,
  "status": "input_supported"
}
```

### CLI provider failure path

Bad provider command with `--require-provider` now fails loudly:

```text
exit=2
ERROR: --provider-cmd was supplied but the external model was not called successfully.
```

Artifacts are still written for diagnosis, including `model_analysis.md` with provider error.

### Real LLM benchmark runner plumbing

Tested with fake provider on two cases:

```bash
python tools/run_real_llm_bug_benchmark.py \
  --cases /tmp/two_cases \
  --provider-cmd "python fake_llm.py" \
  --out /tmp/real_runner_out
```

Result:

```json
{
  "n": 2,
  "baseline_avg": 47.5,
  "dqe_avg": 100.0,
  "avg_uplift": 52.5,
  "root_exact_baseline": 0,
  "root_exact_dqe": 2,
  "file_exact_baseline": 0,
  "file_exact_dqe": 2,
  "fix_exact_baseline": 0,
  "fix_exact_dqe": 2
}
```

This confirms the runner calls the same CLI provider for baseline and CogProxy path and writes `results.json`.

### Offline benchmark regression

```bash
python tools/run_bug_benchmark.py \
  --cases benchmarks/bug_analysis_40 \
  --out /tmp/v041_offline_bench
```

Result:

```json
{
  "n": 40,
  "baseline_avg": 79.06,
  "dqe_avg": 96.81,
  "avg_uplift": 17.75,
  "root_exact_baseline": 16,
  "root_exact_dqe": 39,
  "file_exact_baseline": 38,
  "file_exact_dqe": 40,
  "fix_exact_baseline": 17,
  "fix_exact_dqe": 32
}
```

## Changes made in v0.4.1 during readiness check

- Fixed package metadata version: `pyproject.toml` now matches runtime `__version__`.
- Added `--require-provider` to `run` and `compare` commands.
- Added regression test for bad provider command behavior.
- Updated README with CLI provider readiness note.

## Ready command for real CLI LLM

```bash
cogproxy-dqe run \
  --task "Клиент прислал баг. Найди root cause." \
  --pack bug_analysis \
  --mode audit \
  --project-dir ./my_project \
  --docs-dir ./docs \
  --log-file ./bug.log \
  --stacktrace-file ./stacktrace.txt \
  --provider-cmd "your-llm-cli --model your-model" \
  --require-provider \
  --out ./out_bug
```

Check after run:

```bash
cat ./out_bug/receipt.json
cat ./out_bug/model_analysis.md
```

Expected receipt fields:

```json
{
  "provider": "cli",
  "proxy_calls_model": true
}
```
