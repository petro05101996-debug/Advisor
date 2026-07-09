from __future__ import annotations
"""End-to-end smoke audit for user workflows.

This is not a scientific LLM benchmark. It checks that the package is usable from
CLI, that all domain packs run in all modes, output files are written, provider
plumbing works, and benchmark scripts execute.
"""

import argparse
import json
import subprocess
import sys
import textwrap
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

TASKS = {
    "universal": "Нужно оценить идею инструмента для проверки документации и дать рабочий план запуска MVP без завышенных обещаний.",
    "system_design": "Спроектируй сервис онлайн-редактирования документов: совместное редактирование, операции, версии, конфликтные правки, хранение истории и SLA 200 мс на применение операции.",
    "requirements_qa": "API автоплатежа должен создавать подписку только если заявка ACTIVE. Если заявка CLOSED или сумма ниже минимальной, вернуть ошибку. Повторный запрос с тем же idempotencyKey не должен создавать дубль.",
    "research_analysis": "Проанализируй идею CogProxy как усилителя LLM: где есть польза, что не доказано, какой MVP и какие метрики проверки нужны.",
    "bug_analysis": "Find root cause from stacktrace and project code.",
}
MODES = ["fast", "standard", "deep", "audit"]
PACKS = list(TASKS)


def run(cmd: list[str], timeout: int = 120) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=PROJECT_ROOT, text=True, capture_output=True, timeout=timeout)


def write_fake_provider(out_root: Path) -> Path:
    provider = out_root / "fake_provider.py"
    provider.write_text(
        """
import sys
prompt = sys.stdin.read()
print('# Fake provider answer')
print('Received prompt length:', len(prompt))
print('Root cause / analysis should be grounded in evidence. Fix: add guard or contract check. Regression test: cover the negative branch.')
""".strip()
        + "\n",
        encoding="utf-8",
    )
    return provider


def bug_case_args(case_id: str = "bug_001_real_missing_typing_import") -> list[str]:
    case = PROJECT_ROOT / "benchmarks" / "bug_analysis_40" / case_id
    return [
        "--project-dir", str(case / "project"),
        "--log-file", str(case / "log.txt"),
        "--stacktrace-file", str(case / "stacktrace.txt"),
    ]


def record(rows: list[dict], case: str, ok: bool, proc: subprocess.CompletedProcess[str] | None = None, extra: dict | None = None) -> None:
    item = {"case": case, "ok": bool(ok)}
    if proc is not None:
        item.update({"code": proc.returncode, "stdout_head": proc.stdout[:500], "stderr_head": proc.stderr[:500]})
    if extra:
        item.update(extra)
    rows.append(item)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(PROJECT_ROOT / "smoke_results" / "local"))
    args = ap.parse_args()
    out_root = Path(args.out)
    if out_root.exists():
        import shutil
        shutil.rmtree(out_root)
    out_root.mkdir(parents=True)
    rows: list[dict] = []

    # Basic CLI
    for name, cmd in [
        ("version", [sys.executable, "-m", "cogproxy_dqe", "--version"]),
        ("packs", [sys.executable, "-m", "cogproxy_dqe", "packs"]),
        ("packs_json", [sys.executable, "-m", "cogproxy_dqe", "packs", "--json"]),
        ("help", [sys.executable, "-m", "cogproxy_dqe", "--help"]),
    ]:
        proc = run(cmd)
        record(rows, name, proc.returncode == 0, proc)

    # Run every pack in every mode.
    for pack, task in TASKS.items():
        for mode in MODES:
            out_dir = out_root / f"run_{pack}_{mode}"
            cmd = [sys.executable, "-m", "cogproxy_dqe", "run", "--task", task, "--pack", pack, "--mode", mode, "--out", str(out_dir), "--json"]
            if pack == "bug_analysis":
                cmd += bug_case_args()
            proc = run(cmd, timeout=180)
            ok = False
            details = {}
            try:
                payload = json.loads(proc.stdout)
                receipt = payload.get("receipt", {})
                ok = (
                    proc.returncode == 0
                    and receipt.get("pack") == pack
                    and "quality_score" in receipt.get("quality", {})
                    and (out_dir / "report.md").exists()
                    and (out_dir / "receipt.json").exists()
                    and (out_dir / "claims.json").exists()
                )
                if pack == "bug_analysis":
                    ok = ok and (out_dir / "bug_report.md").exists() and (out_dir / "bug_evidence.json").exists() and (out_dir / "llm_prompt.txt").exists()
                details = {"pack": receipt.get("pack"), "status": receipt.get("status"), "quality": receipt.get("quality", {}).get("quality_score")}
            except Exception as exc:  # pragma: no cover - smoke diagnostics
                details = {"parse_error": repr(exc)}
            record(rows, f"run_json_{pack}_{mode}", ok, proc, details)

    # Compare for non-bug packs.
    for pack in ["universal", "system_design", "requirements_qa", "research_analysis"]:
        out_dir = out_root / f"compare_{pack}"
        proc = run([sys.executable, "-m", "cogproxy_dqe", "compare", "--task", TASKS[pack], "--pack", pack, "--mode", "audit", "--out", str(out_dir), "--json"], timeout=180)
        ok = False
        try:
            payload = json.loads(proc.stdout)
            ok = proc.returncode == 0 and payload.get("pack") == pack and (out_dir / "compare.json").exists() and (out_dir / "baseline.md").exists() and (out_dir / "dqe.md").exists()
        except Exception:
            pass
        record(rows, f"compare_{pack}", ok, proc)

    # Task-file flow.
    task_file = out_root / "task_requirements.txt"
    task_file.write_text(TASKS["requirements_qa"], encoding="utf-8")
    out_dir = out_root / "task_file"
    proc = run([sys.executable, "-m", "cogproxy_dqe", "run", "--task-file", str(task_file), "--pack", "requirements_qa", "--mode", "audit", "--out", str(out_dir), "--receipt"])
    ok = False
    try:
        receipt = json.loads(proc.stdout)
        ok = proc.returncode == 0 and receipt.get("pack") == "requirements_qa" and (out_dir / "report.md").exists()
    except Exception:
        pass
    record(rows, "task_file_receipt", ok, proc)

    # Provider plumbing.
    provider = write_fake_provider(out_root)
    for pack in ["system_design", "bug_analysis"]:
        out_dir = out_root / f"provider_{pack}"
        cmd = [
            sys.executable, "-m", "cogproxy_dqe", "run",
            "--task", TASKS[pack], "--pack", pack, "--mode", "audit",
            "--provider-cmd", f"{sys.executable} {provider}", "--require-provider",
            "--out", str(out_dir), "--receipt",
        ]
        if pack == "bug_analysis":
            cmd += bug_case_args("bug_002_none_payload_user")
        proc = run(cmd, timeout=180)
        ok = False
        try:
            receipt = json.loads(proc.stdout)
            ok = proc.returncode == 0 and receipt.get("proxy_calls_model") is True and (out_dir / "report.md").exists()
            if pack == "bug_analysis":
                ok = ok and (out_dir / "model_analysis.md").exists()
        except Exception:
            pass
        record(rows, f"provider_success_{pack}", ok, proc)

    out_dir = out_root / "provider_missing"
    proc = run([sys.executable, "-m", "cogproxy_dqe", "run", "--task", "test", "--pack", "universal", "--provider-cmd", "/definitely/missing/provider", "--require-provider", "--out", str(out_dir), "--receipt"])
    record(rows, "provider_required_failure", proc.returncode == 2 and "ERROR" in proc.stderr, proc)

    # Benchmarks.
    bench_out = out_root / "benchmark_40"
    proc = run([sys.executable, "tools/run_bug_benchmark.py", "--cases", "benchmarks/bug_analysis_40", "--out", str(bench_out)], timeout=300)
    report = bench_out / "benchmark_report.md"
    record(rows, "offline_benchmark_40", proc.returncode == 0 and report.exists() and "Cases: 40" in report.read_text(encoding="utf-8"), proc)

    real_out = out_root / "real_llm_fake_provider_40"
    proc = run([sys.executable, "tools/run_real_llm_bug_benchmark.py", "--cases", "benchmarks/bug_analysis_40", "--provider-cmd", f"{sys.executable} {provider}", "--out", str(real_out)], timeout=420)
    report = real_out / "benchmark_report.md"
    record(rows, "real_llm_runner_fake_provider_40", proc.returncode == 0 and report.exists() and (real_out / "results.json").exists(), proc)

    passed = sum(1 for r in rows if r["ok"])
    summary = {"total": len(rows), "passed": passed, "failed": [r for r in rows if not r["ok"]], "rows": rows}
    (out_root / "smoke_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = ["# CogProxy full user smoke audit", "", f"Passed: {passed}/{len(rows)}", "", "| case | ok | code |", "|---|---:|---:|"]
    for r in rows:
        lines.append(f"| {r['case']} | {r['ok']} | {r.get('code', '')} |")
    if summary["failed"]:
        lines += ["", "## Failed cases"]
        for r in summary["failed"]:
            lines.append(f"- {r['case']}: code={r.get('code')} stderr={r.get('stderr_head','')[:200]}")
    (out_root / "smoke_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"total": len(rows), "passed": passed, "failed_count": len(summary["failed"]), "out": str(out_root)}, ensure_ascii=False, indent=2))
    return 0 if passed == len(rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
