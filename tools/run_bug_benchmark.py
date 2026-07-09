from __future__ import annotations
import argparse, json, re, shutil, sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from cogproxy_dqe.runtime import run_dqe  # noqa: E402


def collect_project_text(case_dir: Path, limit_chars: int = 60000) -> str:
    chunks = []
    for root_name in ["project", "docs"]:
        root = case_dir / root_name
        if not root.exists():
            continue
        for p in sorted(root.rglob("*")):
            if not p.is_file():
                continue
            try:
                txt = p.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            chunks.append(f"### {root_name}/{p.relative_to(root)}\n{txt}")
            if sum(len(x) for x in chunks) > limit_chars:
                break
    return "\n\n".join(chunks)[:limit_chars]


def baseline_answer_raw(gt: dict, case_dir: Path) -> str:
    text = (case_dir / "stacktrace.txt").read_text(encoding="utf-8", errors="replace")
    text += "\n" + (case_dir / "log.txt").read_text(encoding="utf-8", errors="replace")
    text += "\n" + collect_project_text(case_dir)
    lower = text.lower()
    exc = "UnknownError"
    msg = ""
    m = re.search(r"([A-Za-z_.]*(?:Error|Exception|Violation|Fault|Failure|NullPointerException))[: ]+([^\n]*)", text)
    if m:
        exc = m.group(1).split(".")[-1]
        msg = m.group(2).strip()
    frame = "unknown"
    m = (
        re.search(r'File "([^"]+)", line (\d+)', text)
        or re.search(r"\(([^:()]+\.(?:java|kt)):(\d+)\)", text)
        or re.search(r"at\s+(?:[\w.$<>/]+\s+\()?([^()\s]+\.(?:js|ts|tsx|jsx)):(\d+):\d+", text)
    )
    if m:
        frame = f"{Path(m.group(1)).name}:{m.group(2)}"
    cause = "Ошибка по stacktrace, требуется проверить строку падения и входные данные."
    fix = "Проверить failing line, добавить валидацию и regression test."
    if any(x in lower for x in ["nonetype", "undefined", "nullpointer", "nil pointer", "has no attribute"]):
        cause = "Вероятно, null/None/undefined значение используется без проверки."
        fix = "Добавить guard/null-check и обработать отсутствующие данные."
    elif "keyerror" in lower or "field required" in lower:
        cause = "Вероятно, отсутствует ожидаемое поле в payload или произошёл drift контракта."
        fix = "Проверить контракт, добавить fallback/schema validation."
    elif any(x in lower for x in ["integrityerror", "unique constraint", "not-null"]):
        cause = "Вероятно, нарушено ограничение БД: дубль или отсутствующее обязательное поле."
        fix = "Проверить данные, idempotency/mapping и обработку constraint."
    elif any(x in lower for x in ["time data", "uuid", "jsondecode", "numberformat"]):
        cause = "Вероятно, формат входных данных не соответствует ожидаемому парсеру."
        fix = "Добавить валидацию формата и корректную обработку ошибки."
    elif any(x in lower for x in ["timeout", "connection", "502", "503"]):
        cause = "Вероятно, проблема внешней зависимости, конфигурации или timeout/retry политики."
        fix = "Проверить конфигурацию, таймауты, retry и dependency metrics."
    elif "not defined" in lower or "modulenotfound" in lower:
        cause = "Вероятно, отсутствует import или зависимость."
        fix = "Добавить import/dependency и smoke test."
    return (
        "# Baseline one-shot analysis\n\n"
        f"Exception: {exc}: {msg}\n\n"
        f"Suspected location: {frame}\n\n"
        f"Root cause: {cause}\n\n"
        f"Fix: {fix}\n\n"
        "Regression test: добавить тест, воспроизводящий ошибочный вход из лога/stacktrace.\n"
    )


def score_answer(answer: str, gt: dict) -> dict:
    lower = answer.lower()

    def hit(term: str) -> bool:
        return term.lower() in lower

    root_hits = sum(hit(t) for t in gt.get("root_terms", []))
    fix_hits = sum(hit(t) for t in gt.get("fix_terms", []))
    test_hits = sum(hit(t) for t in gt.get("test_terms", []))
    file_hits = sum(hit(f) or hit(Path(f).name) for f in gt.get("expected_files", []))
    line_hits = sum((f":{ln}" in answer or f"line {ln}" in lower or (str(ln) in lower and file_hits > 0)) for ln in gt.get("expected_lines", []))
    forbidden_hits = sum(hit(t) for t in gt.get("forbidden_terms", []))
    root_score = 1.0 if root_hits >= max(2, min(3, len(gt.get("root_terms", [])))) else (0.5 if root_hits >= 1 else 0.0)
    file_score = 1.0 if file_hits >= 1 and line_hits >= 1 else (0.5 if file_hits >= 1 else 0.0)
    fix_score = 1.0 if fix_hits >= max(1, min(2, len(gt.get("fix_terms", [])))) else (0.5 if fix_hits >= 1 else 0.0)
    test_score = 1.0 if test_hits >= 1 or ("test" in lower or "тест" in lower or "regression" in lower) else 0.0
    hallucination_penalty = min(1.0, forbidden_hits * 0.5)
    total = 35 * root_score + 25 * file_score + 20 * fix_score + 15 * test_score + 5 * (1 - hallucination_penalty)
    return {
        "total": round(total, 1),
        "root_score": root_score,
        "file_score": file_score,
        "fix_score": fix_score,
        "test_score": test_score,
        "hallucination_penalty": hallucination_penalty,
        "root_hits": root_hits,
        "fix_hits": fix_hits,
        "test_hits": test_hits,
        "file_hits": file_hits,
        "forbidden_hits": forbidden_hits,
    }


def run_benchmark(cases_dir: Path, out_dir: Path) -> dict:
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)
    rows = []
    for case_dir in sorted(p for p in cases_dir.iterdir() if p.is_dir()):
        gt = json.loads((case_dir / "ground_truth.json").read_text(encoding="utf-8"))
        baseline = baseline_answer_raw(gt, case_dir)
        baseline_score = score_answer(baseline, gt)
        result = run_dqe(
            task=(case_dir / "task.txt").read_text(encoding="utf-8"),
            pack_name="bug_analysis",
            mode="audit",
            extra_context={
                "log_file": str(case_dir / "log.txt"),
                "stacktrace_file": str(case_dir / "stacktrace.txt"),
                "project_dir": str(case_dir / "project"),
                "docs_dir": str(case_dir / "docs"),
            },
        )
        dqe = result.final_answer
        dqe_score = score_answer(dqe, gt)
        row = {
            "case_id": gt["case_id"],
            "title": gt["title"],
            "language": gt["language"],
            "baseline_total": baseline_score["total"],
            "dqe_total": dqe_score["total"],
            "uplift": round(dqe_score["total"] - baseline_score["total"], 1),
            "baseline": baseline_score,
            "dqe": dqe_score,
            "dqe_status": result.receipt.get("status"),
            "proxy_calls_model": result.receipt.get("proxy_calls_model"),
        }
        rows.append(row)
        d = out_dir / gt["case_id"]
        d.mkdir()
        (d / "baseline.md").write_text(baseline, encoding="utf-8")
        (d / "dqe.md").write_text(dqe, encoding="utf-8")
        (d / "receipt.json").write_text(json.dumps(result.receipt, ensure_ascii=False, indent=2), encoding="utf-8")
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
    lines = ["# CogProxy bug-analysis benchmark", "", "This is an offline proxy benchmark. It does not prove real LLM uplift unless rerun with a real provider and human/LLM-judge scoring.", ""]
    lines += [f"- Cases: {n}", f"- Baseline average: {summary['baseline_avg']}/100", f"- CogProxy average: {summary['dqe_avg']}/100", f"- Average uplift: {summary['avg_uplift']}", f"- Root cause exact: baseline {summary['root_exact_baseline']}/{n}, CogProxy {summary['root_exact_dqe']}/{n}", f"- File+line localization: baseline {summary['file_exact_baseline']}/{n}, CogProxy {summary['file_exact_dqe']}/{n}", f"- Fix exact: baseline {summary['fix_exact_baseline']}/{n}, CogProxy {summary['fix_exact_dqe']}/{n}", ""]
    lines += ["| case | baseline | cogproxy | uplift |", "|---|---:|---:|---:|"]
    for r in rows:
        lines.append(f"| {r['case_id']} | {r['baseline_total']} | {r['dqe_total']} | {r['uplift']} |")
    (out_dir / "benchmark_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"summary": summary, "rows": rows}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", default=str(PROJECT_ROOT / "benchmarks" / "bug_analysis_40"))
    ap.add_argument("--out", default=str(PROJECT_ROOT / "benchmark_results" / "local_run"))
    args = ap.parse_args()
    payload = run_benchmark(Path(args.cases), Path(args.out))
    print(json.dumps(payload["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
