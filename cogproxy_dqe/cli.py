from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .evaluator import compare, compare_to_json
from .packs import default_registry
from .runtime import run_dqe


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cogproxy-dqe", description="CogProxy Distributed Quality Engine core")
    parser.add_argument("--version", action="store_true", help="Print version")
    sub = parser.add_subparsers(dest="command")

    run = sub.add_parser("run", help="Run DQE pipeline")
    source = run.add_mutually_exclusive_group(required=True)
    source.add_argument("--task", help="Task text")
    source.add_argument("--task-file", help="Path to file with task text")
    run.add_argument("--pack", default="universal", help="Domain pack name")
    run.add_argument("--mode", default="standard", choices=["fast", "standard", "deep", "audit"], help="Execution mode")
    run.add_argument("--provider-cmd", default=None, help="External CLI provider command. It receives prompt on stdin.")
    run.add_argument("--require-provider", action="store_true", help="Fail with exit code 2 if --provider-cmd is supplied but the model is not called successfully.")
    run.add_argument("--log-file", default=None, help="Bug analysis: path to log file")
    run.add_argument("--stacktrace-file", default=None, help="Bug analysis: path to stacktrace file")
    run.add_argument("--project-dir", default=None, help="Bug analysis: project source code directory")
    run.add_argument("--docs-dir", default=None, help="Bug analysis: documentation directory")
    run.add_argument("--max-workers", type=int, default=4, help="Parallel worker count for deep/audit modes")
    run.add_argument("--out", default=None, help="Directory to write report.md, receipt.json, claims.json")
    run.add_argument("--json", action="store_true", help="Print full JSON result")
    run.add_argument("--receipt", action="store_true", help="Print only JSON receipt")

    cmp = sub.add_parser("compare", help="Compare one-shot baseline vs DQE on the same task")
    cmp_source = cmp.add_mutually_exclusive_group(required=True)
    cmp_source.add_argument("--task", help="Task text")
    cmp_source.add_argument("--task-file", help="Path to file with task text")
    cmp.add_argument("--pack", default="universal", help="Domain pack name")
    cmp.add_argument("--mode", default="standard", choices=["fast", "standard", "deep", "audit"], help="Execution mode")
    cmp.add_argument("--provider-cmd", default=None, help="External CLI provider command")
    cmp.add_argument("--require-provider", action="store_true", help="Fail with exit code 2 if --provider-cmd is supplied but either baseline or DQE did not call the model successfully.")
    cmp.add_argument("--log-file", default=None, help="Bug analysis: path to log file")
    cmp.add_argument("--stacktrace-file", default=None, help="Bug analysis: path to stacktrace file")
    cmp.add_argument("--project-dir", default=None, help="Bug analysis: project source code directory")
    cmp.add_argument("--docs-dir", default=None, help="Bug analysis: documentation directory")
    cmp.add_argument("--out", default=None, help="Directory to write compare.json, baseline.md, dqe.md")
    cmp.add_argument("--json", action="store_true", help="Print full JSON compare result")

    packs = sub.add_parser("packs", help="List built-in packs")
    packs.add_argument("--json", action="store_true")
    return parser


def _read_task(args: argparse.Namespace) -> str:
    if args.task is not None:
        return args.task
    path = Path(args.task_file)
    return path.read_text(encoding="utf-8")




def _bug_context_from_args(args: argparse.Namespace) -> dict:
    ctx = {}
    for key in ["log_file", "stacktrace_file", "project_dir", "docs_dir"]:
        value = getattr(args, key, None)
        if value:
            ctx[key] = value
    return ctx



def _safe_stdout(text: str) -> None:
    """Write CLI output in a conservative way."""
    sys.stdout.write(text + "\n")
    sys.stdout.flush()

def _write_run_outputs(out_dir: str, result) -> None:
    path = Path(out_dir)
    path.mkdir(parents=True, exist_ok=True)
    (path / "report.md").write_text(result.final_answer, encoding="utf-8")
    (path / "receipt.json").write_text(json.dumps(result.receipt, ensure_ascii=False, indent=2), encoding="utf-8")
    (path / "claims.json").write_text(json.dumps([c.to_dict() for c in result.claims], ensure_ascii=False, indent=2), encoding="utf-8")
    gen = result.intermediate.get("workers", {}).get("generate", {})
    artifacts = gen.get("artifacts", {}) if isinstance(gen, dict) else {}
    if result.contract.pack_name == "bug_analysis":
        if artifacts.get("bug_report"):
            (path / "bug_report.md").write_text(artifacts["bug_report"], encoding="utf-8")
        if artifacts.get("bug_analysis"):
            (path / "bug_evidence.json").write_text(json.dumps(artifacts["bug_analysis"], ensure_ascii=False, indent=2), encoding="utf-8")
        if artifacts.get("llm_prompt"):
            (path / "llm_prompt.txt").write_text(artifacts["llm_prompt"], encoding="utf-8")
        if artifacts.get("model_analysis"):
            (path / "model_analysis.md").write_text(str(artifacts["model_analysis"]), encoding="utf-8")


def _write_compare_outputs(out_dir: str, payload: dict) -> None:
    path = Path(out_dir)
    path.mkdir(parents=True, exist_ok=True)
    (path / "compare.json").write_text(compare_to_json(payload), encoding="utf-8")
    (path / "baseline.md").write_text(payload["baseline"]["answer"], encoding="utf-8")
    (path / "dqe.md").write_text(payload["dqe"]["answer"], encoding="utf-8")



def _run_payload_json(result) -> str:
    """Return user-facing JSON without dumping huge internal prompts/intermediate state."""
    payload = {
        "final_answer": result.final_answer,
        "receipt": result.receipt,
        "contract": result.contract.to_dict(),
        "claims": [c.to_dict() for c in result.claims],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)

def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.version:
        print(f"cogproxy-dqe {__version__}")
        return 0

    if args.command == "packs":
        registry = default_registry()
        if args.json:
            _safe_stdout(json.dumps({"packs": registry.names()}, ensure_ascii=False, indent=2))
        else:
            for name in registry.names():
                pack = registry.get(name)
                print(f"{name}: {pack.description}")
        return 0

    if args.command == "run":
        try:
            task = _read_task(args)
            result = run_dqe(task=task, pack_name=args.pack, mode=args.mode, provider_cmd=args.provider_cmd, max_workers=args.max_workers, extra_context=_bug_context_from_args(args))
            if args.out:
                _write_run_outputs(args.out, result)
            if args.require_provider and args.provider_cmd and not result.receipt.get("proxy_calls_model"):
                hint = f" See {args.out}/model_analysis.md and receipt.json." if args.out else ""
                print("ERROR: --provider-cmd was supplied but the external model was not called successfully." + hint, file=sys.stderr)
                return 2
        except Exception as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 2

        if args.receipt:
            _safe_stdout(json.dumps(result.receipt, ensure_ascii=False, indent=2))
        elif args.json:
            _safe_stdout(_run_payload_json(result))
        else:
            print(result.final_answer)
            if args.out:
                print(f"\n[written] {args.out}/report.md, receipt.json, claims.json", file=sys.stderr)
        return 0

    if args.command == "compare":
        try:
            task = _read_task(args)
            payload = compare(task=task, pack_name=args.pack, mode=args.mode, provider_cmd=args.provider_cmd, extra_context=_bug_context_from_args(args))
            if args.out:
                _write_compare_outputs(args.out, payload)
            if args.require_provider and args.provider_cmd:
                baseline_called = bool(payload.get("baseline", {}).get("called_model"))
                dqe_called = bool(payload.get("dqe", {}).get("receipt", {}).get("proxy_calls_model"))
                if not (baseline_called and dqe_called):
                    hint = f" See {args.out}/compare.json." if args.out else ""
                    print("ERROR: --provider-cmd was supplied but baseline or DQE did not call the external model successfully." + hint, file=sys.stderr)
                    return 2
        except Exception as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 2

        if args.json:
            _safe_stdout(compare_to_json(payload))
        else:
            print("# Compare: one-shot vs DQE")
            print(f"Pack: {payload['pack']} | Mode: {payload['mode']}")
            print(f"Baseline score: {payload['baseline']['score']['total']}")
            print(f"DQE score: {payload['dqe']['score']['total']}")
            print(f"Uplift: {payload['uplift']}")
            print(f"Verdict: {payload['verdict']}")
            if payload.get("synthetic_offline"):
                print("Note: synthetic offline comparison, no real model called.")
            if args.out:
                print(f"[written] {args.out}/compare.json, baseline.md, dqe.md", file=sys.stderr)
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
