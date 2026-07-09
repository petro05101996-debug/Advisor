# CogProxy DQE v0.4.2 — Run Report

Проверено из свежей рабочей директории и после editable-install.

## Команды

```bash
python -m compileall -q cogproxy_dqe tests tools
python -m unittest discover -s tests -v
python -m venv /mnt/data/full_audit_v041/venv_v042
/mnt/data/full_audit_v041/venv_v042/bin/python -m pip install -e .
/mnt/data/full_audit_v041/venv_v042/bin/cogproxy-dqe --version
python tools/run_bug_benchmark.py --cases benchmarks/bug_analysis_40 --out /mnt/data/full_audit_v041/v042_benchmark
```

## Результаты

```text
compileall OK
18/18 tests OK
cogproxy-dqe 0.4.2
metadata cogproxy-dqe 0.4.2
offline benchmark 40 cases OK
```

См. полный аудит: `FULL_USER_AUDIT_V0_4_2.md`.
