from __future__ import annotations

"""Small user-facing evaluator for one-shot vs DQE comparison.

This is not a scientific benchmark. It gives immediate local feedback: did the
DQE answer cover sections, risks, actionability, specificity and traceability
better than a one-shot baseline? For real proof, run the same evaluator on a
larger frozen task set with human rubrics.
"""

import json
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional

from .artifacts import extract_domain_terms
from .contract import compile_task_contract
from .models import Mode
from .providers import BaseProvider, DeterministicProvider, ProviderError, make_provider
from .runtime import run_dqe
from .verifiers import has_section


RUBRIC = {
    "required_sections": 0.25,
    "risk_awareness": 0.18,
    "actionability": 0.18,
    "specificity": 0.18,
    "traceability_or_artifacts": 0.14,
    "honesty": 0.07,
}


@dataclass
class EvalScore:
    total: float
    dimensions: Dict[str, float]
    notes: List[str]

    def to_dict(self):
        return asdict(self)


def score_answer(task: str, answer: str, pack_name: str, mode: str = Mode.STANDARD.value) -> EvalScore:
    contract = compile_task_contract(task, pack_name=pack_name, mode=mode)
    lower = answer.lower()
    dims: Dict[str, float] = {}
    notes: List[str] = []

    section_hits = sum(1 for s in contract.required_sections if has_section(answer, s))
    dims["required_sections"] = section_hits / max(1, len(contract.required_sections))
    if dims["required_sections"] < 0.8:
        notes.append("мало обязательных секций под pack")

    risk_markers = ["риск", "отказ", "ошиб", "огранич", "нельзя", "не надо", "слом"]
    dims["risk_awareness"] = min(1.0, sum(1 for m in risk_markers if m in lower) / 3)
    if dims["risk_awareness"] < 0.7:
        notes.append("слабая явная работа с рисками")

    action_markers = ["реализ", "провер", "добав", "запустить", "шаг", "api", "таблица", "тест", "метрик"]
    dims["actionability"] = min(1.0, sum(1 for m in action_markers if m in lower) / 4)
    if dims["actionability"] < 0.7:
        notes.append("мало конкретных действий/артефактов")

    terms = extract_domain_terms(task)
    term_hits = sum(1 for t in terms if t.lower() in lower)
    dims["specificity"] = term_hits / max(1, min(len(terms), 8))
    if terms and dims["specificity"] < 0.5:
        notes.append("ответ слабо использует конкретику запроса")

    artifact_markers = ["|", "tc-", "r-", "endpoint", "state", "инвариант", "idempotency", "trace", "coverage", "outbox", "inbox"]
    dims["traceability_or_artifacts"] = min(1.0, sum(1 for m in artifact_markers if m in lower) / 4)
    if dims["traceability_or_artifacts"] < 0.5:
        notes.append("нет явных таблиц/TC/API/state/traceability")

    honesty_markers = ["не доказ", "чернов", "гипот", "нужн", "источник", "receipt", "огранич"]
    dims["honesty"] = min(1.0, sum(1 for m in honesty_markers if m in lower) / 3)

    total = sum(dims[k] * RUBRIC[k] for k in RUBRIC)
    return EvalScore(round(total, 3), {k: round(v, 3) for k, v in dims.items()}, notes)


def make_baseline_answer(task: str, provider: BaseProvider) -> tuple[str, bool]:
    prompt = "Ответь напрямую на задачу пользователя одним обычным one-shot ответом.\n\n" + task
    if isinstance(provider, DeterministicProvider):
        return (
            "# One-shot baseline\n\n"
            "Нужно проанализировать задачу, описать решение, риски и следующие шаги. "
            "Без специализированного DQE-процесса ответ остаётся общим черновиком.",
            False,
        )
    try:
        return provider.complete(prompt, role="baseline"), True
    except ProviderError as exc:
        return f"# One-shot baseline\n\nProvider error: {exc}", False


def compare(task: str, pack_name: str, mode: str, provider_cmd: Optional[str] = None, extra_context: Optional[dict] = None) -> Dict[str, object]:
    provider = make_provider(provider_cmd)
    baseline_answer, baseline_called_model = make_baseline_answer(task, provider)
    dqe_result = run_dqe(task, pack_name=pack_name, mode=mode, provider=provider, extra_context=extra_context)

    baseline_score = score_answer(task, baseline_answer, pack_name, mode)
    dqe_score = score_answer(task, dqe_result.final_answer, pack_name, mode)
    uplift = round(dqe_score.total - baseline_score.total, 3)

    return {
        "mode": mode,
        "pack": pack_name,
        "synthetic_offline": not baseline_called_model and not dqe_result.receipt["proxy_calls_model"],
        "baseline": {"score": baseline_score.to_dict(), "called_model": baseline_called_model, "answer": baseline_answer},
        "dqe": {"score": dqe_score.to_dict(), "receipt": dqe_result.receipt, "answer": dqe_result.final_answer},
        "uplift": uplift,
        "verdict": "DQE better on this rubric" if uplift > 0.05 else "No meaningful uplift on this rubric",
    }


def compare_to_json(payload: Dict[str, object]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2)
