from __future__ import annotations
"""Run the same bug benchmark with a real CLI LLM provider.

This script compares:
A) raw one-shot LLM prompt
B) CogProxy bug_analysis + the same CLI LLM provider

Example:
  python tools/run_real_llm_bug_benchmark.py \
    --cases benchmarks/bug_analysis_40 \
    --provider-cmd "your-llm-cli --model your-model" \
    --out benchmark_results/real_llm_run
"""

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from cogproxy_dqe.providers import make_provider  # noqa: E402
from cogproxy_dqe.runtime import run_dqe  # noqa: E402
from tools.run_bug_benchmark import score_answer, collect_project_text  # noqa: E402


def raw_baseline_prompt(case_dir: Path, gt: dict) -> str:
    task = (case_dir / "task.txt").read_text(encoding="utf-8", errors="replace")
    log = (case_dir / "log.txt").read_text(encoding="utf-8", errors="replace")
    stack = (case_dir / "stacktrace.txt").read_text(encoding="utf-8", errors="replace")
    project_text = collect_project_text(case_dir, limit_chars=100000)
    return f"""
Ты senior debugging assistant. Найди root cause бага по логу, stacktrace, коду и документации.
Не фантазируй. Если доказательств мало — скажи. Дай ответ строго по структуре:
1. Наиболее вероятная причина
2. Цепочка доказательств log → stacktrace → code/docs
3. Альтернативные гипотезы
4. Как проверить за 15 минут
5. Минимальный fix
6. Regression tests

# Task
{task}

# Log
{log}

# Stacktrace
{stack}

# Project and docs
{project_text}
""".strip() + "\n"


def run(cases_dir: Path, provider_cmd: str, out_dir: Path) -> dict:
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)
    provider = make_provider(provider_cmd)
    rows = []
    for case_dir in sorted(p for p in cases_dir.iterdir() if p.is_dir()):
        gt = json.loads((case_dir / "ground_truth.json").read_text(encoding="utf-8"))
        prompt = raw_baseline_prompt(case_dir, gt)
        baseline_answer = provider.complete(prompt, role="baseline_bug_analysis")
        baseline_score = score_answer(baseline_answer, gt)
        dqe_result = run_dqe(
            task=(case_dir / "task.txt").read_text(encoding="utf-8"),
            pack_name="bug_analysis",
            mode="audit",
            provider=provider,
            extra_context={
                "log_file": str(case_dir / "log.txt"),
                "stacktrace_file": str(case_dir / "stacktrace.txt"),
                "project_dir": str(case_dir / "project"),
                "docs_dir": str(case_dir / "docs"),
            },
        )
        dqe_answer = dqe_result.final_answer
        dqe_score = score_answer(dqe_answer, gt)
        d = out_dir / gt["case_id"]
        d.mkdir()
        (d / "baseline_prompt.txt").write_text(prompt, encoding="utf-8")
        (d / "baseline.md").write_text(baseline_answer, encoding="utf-8")
        (d / "dqe.md").write_text(dqe_answer, encoding="utf-8")
        (d / "receipt.json").write_text(json.dumps(dqe_result.receipt, ensure_ascii=False, indent=2), encoding="utf-8")
        rows.append({
            "case_id": gt["case_id"],
            "title": gt["title"],
            "baseline_total": baseline_score["total"],
            "dqe_total": dqe_score["total"],
            "uplift": round(dqe_score["total"] - baseline_score["total"], 1),
            "baseline": baseline_score,
            "dqe": dqe_score,
            "proxy_calls_model": dqe_result.receipt.get("proxy_calls_model"),
        })
    n = len(rows)
    summary = {
        "n": n,
        "baseline_avg": round(sum(r["baseline_total"] for r in rows) / n, 2),
        "dqe_avg": round(sum(r["dqe_total"] for r in rows) / n, 2),
        "avg_uplift": round(sum(r["uplift"] for r in rows) / n, 2),
        "root_exact_baseline": sum(1 for r in rows if r["baseline"]["root_score"] == 1.0),
        "root_exact_dqe": sum(1 for r in rows if r["dqe"]["root_score"] == 1.0),
        "file_exact_baseline": sum(1 for r in rows if r["baseline"]["file_score"] == 1.0),
        "file_exact_dqe": sum(1 for r in rows if r["dqe"]["file_score"] == 1.0),
        "fix_exact_baseline": sum(1 for r in rows if r["baseline"]["fix_score"] == 1.0),
        "fix_exact_dqe": sum(1 for r in rows if r["dqe"]["fix_score"] == 1.0),
    }
    (out_dir / "results.json").write_text(json.dumps({"summary": summary, "rows": rows}, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# CogProxy real CLI-LLM bug-analysis benchmark",
        "",
        "This run compares raw one-shot provider output against CogProxy bug_analysis using the same provider command.",
        "If the provider is a fake/local stub, this only validates plumbing, not real LLM quality uplift.",
        "",
        f"- Cases: {n}",
        f"- Baseline average: {summary['baseline_avg']}/100",
        f"- CogProxy average: {summary['dqe_avg']}/100",
        f"- Average uplift: {summary['avg_uplift']}",
        f"- Root cause exact: baseline {summary['root_exact_baseline']}/{n}, CogProxy {summary['root_exact_dqe']}/{n}",
        f"- File+line localization: baseline {summary['file_exact_baseline']}/{n}, CogProxy {summary['file_exact_dqe']}/{n}",
        f"- Fix exact: baseline {summary['fix_exact_baseline']}/{n}, CogProxy {summary['fix_exact_dqe']}/{n}",
        "",
        "| case | baseline | cogproxy | uplift | proxy_called |",
        "|---|---:|---:|---:|---|",
    ]
    for r in rows:
        lines.append(f"| {r['case_id']} | {r['baseline_total']} | {r['dqe_total']} | {r['uplift']} | {r['proxy_calls_model']} |")
    (out_dir / "benchmark_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"summary": summary, "rows": rows}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", default=str(PROJECT_ROOT / "benchmarks" / "bug_analysis_40"))
    ap.add_argument("--provider-cmd", required=True)
    ap.add_argument("--out", default=str(PROJECT_ROOT / "benchmark_results" / "real_llm_run"))
    args = ap.parse_args()
    payload = run(Path(args.cases), args.provider_cmd, Path(args.out))
    print(json.dumps(payload["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
