from __future__ import annotations

from typing import Iterable, List

from .models import TaskContract, VerificationFinding
from .packs import default_registry
from .verifiers import has_section


def repair_answer(answer: str, contract: TaskContract, findings: Iterable[VerificationFinding]) -> str:
    pack = default_registry().get(contract.pack_name)
    repaired = answer.strip()
    applied: List[str] = []

    for section in contract.required_sections:
        if not has_section(repaired, section):
            guidance = pack.section_guidance.get(section, "Раскрыть секцию по цели пользователя.")
            repaired += f"\n\n## {section}\n{guidance}"
            applied.append(f"added:{section}")

    codes = {f.code for f in findings}
    if "missing_risk_analysis" in codes and not any(word in repaired.lower() for word in ["риск", "огранич", "отказ"]):
        repaired += (
            "\n\n## Риски и ограничения\n"
            "- Нет сильного verifier'а — горизонтальное масштабирование превращается в дорогую генерацию вариантов.\n"
            "- Слишком общий режим ухудшит latency и стоимость для простых запросов.\n"
            "- LLM-judge нельзя считать финальным арбитром качества без детерминированных проверок."
        )
        applied.append("added:risk_analysis")

    if "not_actionable" in codes:
        repaired += (
            "\n\n## Проверяемые следующие шаги\n"
            "1. Зафиксировать contract schema и обязательные quality dimensions.\n"
            "2. Реализовать 2–3 domain packs и прогнать A/B на реальных задачах.\n"
            "3. Считать quality uplift, стоимость, latency и число пропущенных критических дефектов."
        )
        applied.append("added:action_plan")

    if "unsupported_critical_claims" in codes:
        repaired += (
            "\n\n## Пометка по доказательности\n"
            "Фактические утверждения без источников должны считаться гипотезами до проверки. "
            "Для audit-режима нужно подключить retrieval/source verifier или явно передать документы."
        )
        applied.append("added:evidence_warning")

    if applied:
        repaired += "\n\n<!-- dqe_repair: " + ",".join(applied) + " -->"
    return repaired
