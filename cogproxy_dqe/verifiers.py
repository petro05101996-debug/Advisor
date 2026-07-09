from __future__ import annotations

import re
from typing import Dict, Iterable, List, Sequence

from .models import Claim, Severity, TaskContract, VerificationFinding, VerificationReport


def has_section(text: str, section: str) -> bool:
    pattern = re.compile(rf"(^|\n)\s*#+\s*{re.escape(section)}\s*(\n|$)", re.IGNORECASE)
    return bool(pattern.search(text))


def word_present(text: str, phrase: str) -> bool:
    words = [w for w in re.split(r"\W+", phrase.lower()) if len(w) >= 4]
    if not words:
        return True
    lower = text.lower()
    return any(w in lower for w in words)


class BaseVerifier:
    name = "base"

    def verify(self, contract: TaskContract, answer: str, claims: Sequence[Claim], context: Dict[str, object]) -> List[VerificationFinding]:
        raise NotImplementedError


class RequiredSectionsVerifier(BaseVerifier):
    name = "required_sections"

    def verify(self, contract: TaskContract, answer: str, claims: Sequence[Claim], context: Dict[str, object]) -> List[VerificationFinding]:
        findings: List[VerificationFinding] = []
        for section in contract.required_sections:
            if not has_section(answer, section):
                findings.append(VerificationFinding(
                    code="missing_required_section",
                    message=f"Нет обязательной секции: {section}",
                    severity=Severity.HIGH.value,
                    target=section,
                    repair_hint=f"Добавить секцию '{section}' с конкретным содержанием.",
                    verifier=self.name,
                ))
        return findings


class CoverageVerifier(BaseVerifier):
    name = "coverage"

    def verify(self, contract: TaskContract, answer: str, claims: Sequence[Claim], context: Dict[str, object]) -> List[VerificationFinding]:
        findings: List[VerificationFinding] = []
        missing = [criterion for criterion in contract.success_criteria if not word_present(answer, criterion)]
        # Do not require exact criterion coverage; flag if more than half is absent.
        if contract.success_criteria and len(missing) > max(1, len(contract.success_criteria) // 2):
            findings.append(VerificationFinding(
                code="weak_success_criteria_coverage",
                message="Ответ слабо покрывает критерии качества: " + "; ".join(missing[:5]),
                severity=Severity.MEDIUM.value,
                target="success_criteria",
                repair_hint="Добавить явные тезисы под непокрытые критерии качества.",
                verifier=self.name,
            ))
        return findings


class ContradictionVerifier(BaseVerifier):
    name = "contradiction"

    NEG = ["не нужно", "не должен", "нельзя", "запрещено", "не использовать", "не требуется"]
    POS = ["нужно", "должен", "обязательно", "использовать", "требуется"]

    def verify(self, contract: TaskContract, answer: str, claims: Sequence[Claim], context: Dict[str, object]) -> List[VerificationFinding]:
        findings: List[VerificationFinding] = []
        lower = answer.lower()
        # Small heuristic: if the same technical token appears near positive and negative modal language.
        tokens = [t for t in re.split(r"\W+", lower) if len(t) >= 6]
        interesting = sorted({t for t in tokens if t in {"kafka", "outbox", "инвариант", "верификатор", "агентов", "тесты", "источник", "роутер"} or t.endswith("ция")})
        for token in interesting[:80]:
            pos_hit = any(re.search(rf"{p}.{{0,60}}{re.escape(token)}|{re.escape(token)}.{{0,60}}{p}", lower) for p in self.POS)
            neg_hit = any(re.search(rf"{n}.{{0,60}}{re.escape(token)}|{re.escape(token)}.{{0,60}}{n}", lower) for n in self.NEG)
            if pos_hit and neg_hit:
                findings.append(VerificationFinding(
                    code="possible_contradiction",
                    message=f"Возможное противоречие вокруг термина '{token}'.",
                    severity=Severity.MEDIUM.value,
                    target=token,
                    repair_hint="Развести условия: когда это нужно, а когда не нужно.",
                    verifier=self.name,
                ))
                break
        return findings


class ActionabilityVerifier(BaseVerifier):
    name = "actionability"

    def verify(self, contract: TaskContract, answer: str, claims: Sequence[Claim], context: Dict[str, object]) -> List[VerificationFinding]:
        lower = answer.lower()
        action_markers = ["сделать", "добавить", "запустить", "проверить", "реализ", "шаг", "план", "mvp", "тест"]
        if sum(1 for marker in action_markers if marker in lower) < 2:
            return [VerificationFinding(
                code="not_actionable",
                message="Ответ недостаточно операционален: мало конкретных действий.",
                severity=Severity.MEDIUM.value,
                target="answer",
                repair_hint="Добавить план реализации или проверяемые шаги.",
                verifier=self.name,
            )]
        return []


class RiskCoverageVerifier(BaseVerifier):
    name = "risk_coverage"

    def verify(self, contract: TaskContract, answer: str, claims: Sequence[Claim], context: Dict[str, object]) -> List[VerificationFinding]:
        lower = answer.lower()
        risk_markers = ["риск", "огранич", "слаб", "отказ", "ошиб", "не доказ", "может слом"]
        if not any(marker in lower for marker in risk_markers):
            return [VerificationFinding(
                code="missing_risk_analysis",
                message="Не найден явный анализ рисков или ограничений.",
                severity=Severity.HIGH.value,
                target="risks",
                repair_hint="Добавить отдельную секцию с рисками, ограничениями и условиями провала.",
                verifier=self.name,
            )]
        return []


class UnsupportedClaimsVerifier(BaseVerifier):
    name = "unsupported_claims"

    FACT_PATTERN = re.compile(r"\b\d+(?:[.,]\d+)?\s*(?:%|мс|ms|сек|руб|₽|x|раз|дней|лет)?\b|\b(?:исследование|paper|arxiv|закон|норма|стандарт|ГОСТ|ФЗ)\b", re.IGNORECASE)

    def verify(self, contract: TaskContract, answer: str, claims: Sequence[Claim], context: Dict[str, object]) -> List[VerificationFinding]:
        findings: List[VerificationFinding] = []
        evidence = context.get("evidence", []) or []
        has_evidence = bool(evidence)
        unsupported = []
        for claim in claims:
            if claim.origin in {"critic", "counterexample"}:
                continue
            if self.FACT_PATTERN.search(claim.text) and not claim.source_refs and not has_evidence:
                unsupported.append(claim.text)
        if unsupported:
            findings.append(VerificationFinding(
                code="unsupported_critical_claims",
                message="Есть потенциально фактические утверждения без источников: " + " | ".join(unsupported[:3]),
                severity=Severity.MEDIUM.value if contract.risk_level != "high" else Severity.HIGH.value,
                target="claims",
                repair_hint="Пометить как гипотезы или добавить источник/проверку.",
                verifier=self.name,
            ))
        return findings


VERIFIERS = {
    "required_sections": RequiredSectionsVerifier(),
    "coverage": CoverageVerifier(),
    "contradiction": ContradictionVerifier(),
    "actionability": ActionabilityVerifier(),
    "risk_coverage": RiskCoverageVerifier(),
    "unsupported_claims": UnsupportedClaimsVerifier(),
}


class VerifierMesh:
    def __init__(self, verifier_names: Iterable[str]) -> None:
        self.verifiers = [VERIFIERS[name] for name in verifier_names if name in VERIFIERS]

    def verify(self, contract: TaskContract, answer: str, claims: Sequence[Claim], context: Dict[str, object]) -> VerificationReport:
        report = VerificationReport()
        for verifier in self.verifiers:
            for finding in verifier.verify(contract, answer, claims, context):
                report.add(finding)
        report.scores = compute_scores(contract, report, claims, answer)
        return report


def compute_scores(contract: TaskContract, report: VerificationReport, claims: Sequence[Claim], answer: str) -> Dict[str, float]:
    blocking = len(report.blocking_findings)
    total_findings = len(report.findings)
    section_hits = sum(1 for s in contract.required_sections if has_section(answer, s))
    section_score = section_hits / max(1, len(contract.required_sections))
    claim_score = min(1.0, len(claims) / 12.0)
    penalty = min(0.65, blocking * 0.25 + max(0, total_findings - blocking) * 0.08)
    quality = max(0.0, min(1.0, 0.45 * section_score + 0.25 * claim_score + 0.30 * (1.0 - penalty)))
    return {
        "section_coverage": round(section_score, 3),
        "claim_density": round(claim_score, 3),
        "finding_penalty": round(penalty, 3),
        "quality_score": round(quality, 3),
    }
