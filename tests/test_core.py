import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from cogproxy_dqe.claims import extract_claims
from cogproxy_dqe.contract import compile_task_contract
from cogproxy_dqe.models import WorkerResult
from cogproxy_dqe.runtime import run_dqe
from cogproxy_dqe.verifiers import has_section


ROOT = Path(__file__).resolve().parents[1]


class ContractTests(unittest.TestCase):
    def test_contract_uses_pack(self):
        contract = compile_task_contract("Спроектируй сервис заказов с SLA", pack_name="system_design", mode="deep")
        self.assertEqual(contract.pack_name, "system_design")
        self.assertIn("Инварианты и SLA", contract.required_sections)
        self.assertEqual(contract.mode, "deep")

    def test_unknown_pack_fails(self):
        with self.assertRaises(ValueError):
            compile_task_contract("test", pack_name="missing", mode="standard")


class RuntimeTests(unittest.TestCase):
    def test_run_deep_completes(self):
        result = run_dqe(
            "Проанализируй концепцию горизонтального масштабирования качества ИИ и дай реализацию",
            pack_name="research_analysis",
            mode="deep",
        )
        self.assertIn(result.receipt["status"], {"heuristic_scaffold", "model_checked", "input_supported", "heuristic_scaffold_with_findings"})
        self.assertGreaterEqual(result.receipt["graph"]["nodes_completed"], 8)
        self.assertIn("# Ответ DQE", result.final_answer)
        self.assertIn("Метрики проверки", result.final_answer)

    def test_audit_flags_provider_not_called_without_cmd(self):
        result = run_dqe("Проверь требования API: сервис должен вернуть статус SUCCESS", pack_name="requirements_qa", mode="audit")
        self.assertFalse(result.receipt["proxy_calls_model"])
        self.assertEqual(result.receipt["provider"], "deterministic")
        self.assertIn("claims", result.receipt)


    def test_system_design_output_is_user_artifact_not_checklist(self):
        result = run_dqe(
            "Спроектируй сервис автоплатежей для ОПИФ: нужна заявка, статусы SUCCESS/FAILED, отключение и повторные попытки",
            pack_name="system_design",
            mode="deep",
        )
        answer = result.final_answer.lower()
        self.assertIn("autopayments", answer)
        self.assertIn("idempotency", answer)
        self.assertIn("outbox", answer)
        self.assertIn("state model", answer)
        self.assertLessEqual(result.receipt["quality"]["quality_score"], 0.45)

    def test_requirements_qa_generates_test_cases(self):
        result = run_dqe(
            "API должен вернуть статус SUCCESS. Если заявка закрыта, операция запрещена.",
            pack_name="requirements_qa",
            mode="audit",
        )
        answer = result.final_answer
        self.assertIn("R-001", answer)
        self.assertIn("TC-001", answer)
        self.assertIn("Негативные проверки", answer)
        self.assertIn("SUCCESS", answer)

    def test_repair_adds_missing_section(self):
        result = run_dqe("Коротко сделай план", pack_name="universal", mode="standard")
        for section in result.contract.required_sections:
            self.assertTrue(has_section(result.intermediate["repaired_answer"], section), section)


class ClaimTests(unittest.TestCase):
    def test_claim_extractor_splits_bullets(self):
        claims = extract_claims([
            WorkerResult("w", "role", "- Нужно добавить verifier mesh для проверки качества.\n- Риск: без источников будет ложная уверенность.")
        ])
        self.assertGreaterEqual(len(claims), 2)
        self.assertTrue(any(c.claim_type == "risk" for c in claims))


class CLITests(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run(
            [sys.executable, "-m", "cogproxy_dqe", *args],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_version(self):
        proc = self.run_cli("--version")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("cogproxy-dqe", proc.stdout)

    def test_packs(self):
        proc = self.run_cli("packs")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("system_design", proc.stdout)

    def test_run_json(self):
        proc = self.run_cli("run", "--task", "Спроектируй сервис", "--pack", "system_design", "--mode", "deep", "--json")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertIn("final_answer", payload)
        self.assertEqual(payload["contract"]["pack_name"], "system_design")

    def test_compare_cli(self):
        proc = self.run_cli("compare", "--task", "API должен вернуть SUCCESS", "--pack", "requirements_qa", "--json")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertIn("uplift", payload)
        self.assertIn("baseline", payload)
        self.assertIn("dqe", payload)

    def test_run_receipt(self):
        proc = self.run_cli("run", "--task", "Проанализируй требования", "--pack", "requirements_qa", "--receipt")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertIn("quality", payload)


if __name__ == "__main__":
    unittest.main()

class BugAnalysisTests(unittest.TestCase):
    def _make_bug_project(self):
        import tempfile
        root = Path(tempfile.mkdtemp(prefix="dqe_bug_project_"))
        app = root / "app"
        docs = root / "docs"
        app.mkdir()
        docs.mkdir()
        (app / "users.py").write_text(
            "USERS = {1: {'id': 10, 'name': 'Ann'}}\n\n"
            "def find_by_order(order_id):\n"
            "    # External CRM may not contain user for a new order yet.\n"
            "    return None\n",
            encoding="utf-8",
        )
        (app / "orders.py").write_text(
            "from app import users\n\n"
            "def build_payload(order_id):\n"
            "    user = users.find_by_order(order_id)\n"
            "    payload = {\n"
            "        'user_id': user['id'],\n"
            "        'order_id': order_id,\n"
            "    }\n"
            "    return payload\n",
            encoding="utf-8",
        )
        (docs / "orders.md").write_text(
            "# Orders\n\nCRM can return no user for freshly imported orders. Service must return a domain error, not 500.\n",
            encoding="utf-8",
        )
        stacktrace = root / "stacktrace.txt"
        stacktrace.write_text(
            "Traceback (most recent call last):\n"
            f"  File \"{app / 'orders.py'}\", line 6, in build_payload\n"
            "    'user_id': user['id'],\n"
            "TypeError: 'NoneType' object is not subscriptable\n",
            encoding="utf-8",
        )
        log = root / "log.txt"
        log.write_text("ERROR requestId=req-42 failed to build order payload for order_id=999\n", encoding="utf-8")
        return root, app, docs, log, stacktrace

    def test_bug_analysis_finds_nullable_root_cause(self):
        root, app, docs, log, stacktrace = self._make_bug_project()
        result = run_dqe(
            "Клиент прислал баг: падает сборка payload заказа. Найди причину по логу и stacktrace.",
            pack_name="bug_analysis",
            mode="audit",
            extra_context={
                "project_dir": str(root),
                "docs_dir": str(docs),
                "log_file": str(log),
                "stacktrace_file": str(stacktrace),
            },
        )
        answer = result.final_answer.lower()
        self.assertIn("nullable", answer)
        self.assertIn("orders.py", answer)
        self.assertIn("user['id']", answer)
        self.assertIn("find_by_order", answer)
        self.assertIn("regression", answer)
        self.assertEqual(result.contract.pack_name, "bug_analysis")
        self.assertIn("bug_analysis", result.intermediate["workers"]["generate"]["artifacts"])

    def test_bug_analysis_cli_writes_artifacts(self):
        root, app, docs, log, stacktrace = self._make_bug_project()
        out = root / "out"
        proc = subprocess.run(
            [
                sys.executable, "-m", "cogproxy_dqe", "run",
                "--task", "Найди root cause по stacktrace",
                "--pack", "bug_analysis",
                "--mode", "audit",
                "--project-dir", str(root),
                "--docs-dir", str(docs),
                "--log-file", str(log),
                "--stacktrace-file", str(stacktrace),
                "--out", str(out),
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertTrue((out / "bug_report.md").exists())
        self.assertTrue((out / "bug_evidence.json").exists())
        self.assertTrue((out / "llm_prompt.txt").exists())
        self.assertIn("orders.py", (out / "bug_report.md").read_text(encoding="utf-8"))

class RealCaseRegressionTests(unittest.TestCase):
    def test_python_stacktrace_frame_without_source_line_is_not_lost(self):
        from cogproxy_dqe.bug_analysis import parse_stacktrace
        stacktrace = (
            "Traceback (most recent call last):\n"
            "  File \"<stdin>\", line 1, in <module>\n"
            "  File \"/repo/cogproxy_dqe_core/cli.py\", line 17, in <module>\n"
            "    def main(argv: Optional[List[str]] = None) -> None:\n"
            "                   ^^^^^^^^\n"
            "NameError: name 'Optional' is not defined\n"
        )
        exception_type, exception_message, frames = parse_stacktrace(stacktrace)
        self.assertEqual(exception_type, "NameError")
        self.assertIn("Optional", exception_message)
        self.assertEqual(len(frames), 2)
        self.assertEqual(frames[-1].file, "/repo/cogproxy_dqe_core/cli.py")
        self.assertEqual(frames[-1].line, 17)
        self.assertIn("Optional[List[str]]", frames[-1].code)

    def test_bug_analysis_explains_missing_typing_import_case(self):
        root = Path(tempfile.mkdtemp(prefix="dqe_real_bug_"))
        project = root / "cogproxy_dqe_core"
        project.mkdir()
        (project / "cli.py").write_text(
            "import argparse\nimport json\nimport sys\n\n"
            "def main(argv: Optional[List[str]] = None) -> None:\n"
            "    print(argv)\n",
            encoding="utf-8",
        )
        stacktrace = root / "stacktrace.txt"
        stacktrace.write_text(
            "Traceback (most recent call last):\n"
            "  File \"<stdin>\", line 1, in <module>\n"
            f"  File \"{project / 'cli.py'}\", line 5, in <module>\n"
            "    def main(argv: Optional[List[str]] = None) -> None:\n"
            "                   ^^^^^^^^\n"
            "NameError: name 'Optional' is not defined\n",
            encoding="utf-8",
        )
        log = root / "log.txt"
        log.write_text("CLI import failed before argument parsing.\n", encoding="utf-8")
        result = run_dqe(
            "Реальный баг: CLI падает при импорте. Найди root cause.",
            pack_name="bug_analysis",
            mode="audit",
            extra_context={"project_dir": str(project), "log_file": str(log), "stacktrace_file": str(stacktrace)},
        )
        answer = result.final_answer.lower()
        self.assertIn("используется символ без импорта", answer)
        self.assertIn("optional", answer)
        self.assertIn("from typing import optional, list", answer)
        self.assertIn("cli.py", answer)

class CLIProviderReadinessTests(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run(
            [sys.executable, "-m", "cogproxy_dqe", *args],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_require_provider_fails_when_cli_model_not_called(self):
        root = Path(tempfile.mkdtemp(prefix="dqe_cli_provider_fail_"))
        project = root / "project"
        project.mkdir()
        (project / "cli.py").write_text(
            "def main(argv: Optional[List[str]] = None):\n    return argv\n",
            encoding="utf-8",
        )
        stack = root / "stacktrace.txt"
        stack.write_text(
            "Traceback (most recent call last):\n"
            f"  File \"{project / 'cli.py'}\", line 1, in <module>\n"
            "    def main(argv: Optional[List[str]] = None):\n"
            "NameError: name 'Optional' is not defined\n",
            encoding="utf-8",
        )
        log = root / "log.txt"
        log.write_text("import failed\n", encoding="utf-8")
        out = root / "out"
        proc = self.run_cli(
            "run",
            "--task", "Найди root cause",
            "--pack", "bug_analysis",
            "--mode", "audit",
            "--project-dir", str(project),
            "--log-file", str(log),
            "--stacktrace-file", str(stack),
            "--provider-cmd", "/definitely/missing/llm",
            "--require-provider",
            "--out", str(out),
        )
        self.assertEqual(proc.returncode, 2)
        self.assertIn("external model was not called", proc.stderr)
        self.assertTrue((out / "model_analysis.md").exists())
