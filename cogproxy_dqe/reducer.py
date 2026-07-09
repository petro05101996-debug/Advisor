from __future__ import annotations

from typing import Dict, Iterable, List

from .models import Claim, TaskContract, VerificationReport, WorkerResult


def _top_claims(claims: Iterable[Claim], claim_type: str, limit: int = 5) -> List[str]:
    selected = [c.text for c in claims if c.claim_type == claim_type]
    return selected[:limit]


def reduce_answer(
    contract: TaskContract,
    repaired_answer: str,
    worker_results: Dict[str, WorkerResult],
    claims: List[Claim],
    verification: VerificationReport,
) -> str:
    findings = verification.findings
    critical = [f for f in findings if f.is_blocking()]
    quality_score = verification.scores.get("quality_score", 0.0)

    header = (
        f"# Ответ DQE\n\n"
        f"**Режим:** {contract.mode}  \n"
        f"**Pack:** {contract.pack_name}  \n"
        f"**Structural score:** {quality_score}  \n"
        f"**Доверие:** см. receipt; offline-режим ограничивает максимальную оценку.\n\n"
    )

    if critical:
        header += (
            "**Статус:** собран ответ с исправлениями, но остались блокирующие замечания. "
            "Используй как черновик, а не как финальное экспертное заключение.\n\n"
        )
    else:
        header += "**Статус:** ядро собрало пользовательский артефакт и проверило структуру без блокирующих замечаний. Это не означает фактическую верификацию всех claims.\n\n"

    evidence_note = ""
    evidence = worker_results.get("evidence")
    if evidence:
        evidence_items = evidence.artifacts.get("evidence", [])
        if evidence_items:
            evidence_note = "\n\n## Опорные фрагменты входа\n" + "\n".join(
                f"- {item['ref']}: {item['text']}" for item in evidence_items[:6]
            )

    verifier_note = "\n\n## Проверка качества\n"
    if not findings:
        verifier_note += "- Существенных замечаний verifier mesh не нашёл."
    else:
        for f in findings[:10]:
            verifier_note += f"\n- [{f.severity}] {f.code}: {f.message}"

    risk_claims = _top_claims(claims, "risk", limit=4)
    if risk_claims:
        verifier_note += "\n\n## Claims риска, найденные ядром\n" + "\n".join(f"- {r}" for r in risk_claims)

    body = repaired_answer.strip()
    if body.startswith("# Ответ DQE"):
        body = body[len("# Ответ DQE"):].lstrip()
    return header + body + evidence_note + verifier_note
