from __future__ import annotations

import re
from typing import List, Optional

from .models import Mode, TaskContract
from .packs import DomainPack, default_registry


def _normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


def infer_task_type(task: str, pack: DomainPack) -> str:
    text = task.lower()
    if pack.name != "universal":
        return pack.output_type
    if any(w in text for w in ["stacktrace", "traceback", "exception", "ошибка", "лог", "баг", "root cause", "nullpointer", "nonetype"]):
        return "bug_root_cause_report"
    if any(w in text for w in ["архитект", "system design", "спроект", "сервис", "sla"]):
        return "architecture_proposal"
    if any(w in text for w in ["тест", "qa", "gherkin", "требован", "документац"]):
        return "qa_report"
    if any(w in text for w in ["исслед", "концепц", "анализ", "mvp", "метрик"]):
        return "research_strategy_report"
    if any(w in text for w in ["перепиши", "улучши текст", "письмо", "сообщение"]):
        return "writing"
    return "general_complex_answer"


def infer_risk_level(task: str, mode: str) -> str:
    text = task.lower()
    high_markers = ["юрид", "врач", "меди", "финанс", "банк", "прод", "безопас", "регуля", "деньги", "stacktrace", "traceback", "exception", "баг"]
    if mode == Mode.AUDIT.value:
        return "high"
    if any(m in text for m in high_markers):
        return "high"
    if len(text) > 1200 or mode == Mode.DEEP.value:
        return "medium"
    return "low"


def infer_constraints(task: str) -> List[str]:
    text = task.lower()
    constraints: List[str] = []
    if "жёст" in text or "жест" in text:
        constraints.append("дать критичный, некомплиментарный анализ")
    if "объектив" in text:
        constraints.append("отделять доказанное от гипотез")
    if "реализац" in text or "сделай" in text:
        constraints.append("дать реализуемые шаги, а не только концепцию")
    if "универс" in text:
        constraints.append("оценить границы универсальности")
    return constraints


def compile_task_contract(
    task: str,
    pack_name: Optional[str] = None,
    mode: str = Mode.STANDARD.value,
) -> TaskContract:
    if not task or not task.strip():
        raise ValueError("Task is empty")
    normalized_mode = mode.strip().lower()
    if normalized_mode not in {m.value for m in Mode}:
        raise ValueError(f"Unknown mode '{mode}'. Use: fast, standard, deep, audit")

    registry = default_registry()
    pack = registry.get(pack_name)
    clean_task = _normalize_space(task)
    task_type = infer_task_type(clean_task, pack)
    risk_level = infer_risk_level(clean_task, normalized_mode)
    constraints = infer_constraints(clean_task)

    success_criteria = list(pack.default_success_criteria)
    if constraints:
        success_criteria.extend(constraints)

    verification_modes = list(pack.verifier_names)
    if risk_level == "high" and "unsupported_claims" not in verification_modes:
        verification_modes.append("unsupported_claims")

    return TaskContract(
        goal=clean_task,
        task_type=task_type,
        pack_name=pack.name,
        mode=normalized_mode,
        risk_level=risk_level,
        output_type=pack.output_type,
        quality_dimensions=list(pack.quality_dimensions),
        required_sections=list(pack.required_sections),
        success_criteria=success_criteria,
        verification_modes=verification_modes,
        constraints=constraints,
        source_text=task,
        metadata={
            "pack_description": pack.description,
        },
    )
