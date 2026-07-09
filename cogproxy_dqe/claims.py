from __future__ import annotations

import re
from typing import Iterable, List

from .models import Claim, WorkerResult, stable_id

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?。])\s+|\n+-\s+|\n+\d+[.)]\s+")


def classify_claim(text: str) -> str:
    lower = text.lower()
    if any(w in lower for w in ["риск", "может", "ограничение", "опас", "слом"]):
        return "risk"
    if any(w in lower for w in ["нужно", "долж", "следует", "must", "обязательно"]):
        return "requirement_or_recommendation"
    if any(w in lower for w in ["метрик", "считать", "измер", "benchmark", "бенчмарк"]):
        return "metric"
    if any(w in lower for w in ["архитект", "сервис", "компонент", "api", "бд", "kafka"]):
        return "design_decision"
    return "statement"


def _split_units(text: str) -> List[str]:
    units = []
    for chunk in _SENTENCE_SPLIT.split(text):
        cleaned = re.sub(r"^#+\s*", "", chunk).strip(" \t\n-•")
        cleaned = re.sub(r"\s+", " ", cleaned)
        if len(cleaned) < 25:
            continue
        if cleaned.lower().startswith(("роль:", "черновой вывод")):
            continue
        units.append(cleaned)
    return units


def extract_claims(results: Iterable[WorkerResult]) -> List[Claim]:
    claims: List[Claim] = []
    seen = set()
    for result in results:
        for unit in _split_units(result.content):
            claim_id = stable_id("c", result.worker_name + ":" + unit)
            if claim_id in seen:
                continue
            seen.add(claim_id)
            source_refs = []
            ref_match = re.search(r"(input:L\d+)", unit)
            if ref_match:
                source_refs.append(ref_match.group(1))
            claims.append(Claim(
                claim_id=claim_id,
                text=unit,
                claim_type=classify_claim(unit),
                origin=result.worker_name,
                confidence=result.confidence,
                source_refs=source_refs,
            ))
    return claims

_FACT_PATTERN = re.compile(
    r"\b\d+(?:[.,]\d+)?\s*(?:%|мс|ms|сек|руб|₽|x|раз|дней|лет)?\b|\b(?:исследование|paper|arxiv|закон|норма|стандарт|ГОСТ|ФЗ|SLA)\b",
    re.IGNORECASE,
)


def assign_claim_statuses(claims: List[Claim], provider_called: bool, evidence_present: bool = False) -> None:
    """Assign honest claim statuses.

    v0.1 counted too much as verified. In v0.2 claims are *not* verified just
    because they were generated. Offline claims become heuristic/unverified;
    claims with input refs become supported_by_input; factual claims without
    evidence become unsupported.
    """
    for claim in claims:
        if claim.source_refs:
            claim.status = "supported_by_input"
        elif claim.origin in {"evidence"} and evidence_present:
            claim.status = "supported_by_input"
        elif _FACT_PATTERN.search(claim.text) and not evidence_present:
            claim.status = "unsupported"
        elif claim.origin in {"critic", "counterexample", "repaired"}:
            claim.status = "heuristic_unverified"
        elif provider_called:
            claim.status = "model_generated_unverified"
        else:
            claim.status = "heuristic_unverified"
