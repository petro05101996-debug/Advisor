from __future__ import annotations

from typing import Dict, List

from .models import Claim, GraphNode, TaskContract, VerificationReport, WorkerResult

SUPPORTED_STATUSES = {"supported_by_input", "source_verified", "test_verified"}


def _verification_cap(proxy_calls_model: bool, supported: int, unsupported: int, provider_name: str) -> tuple[float, str, str]:
    if not proxy_calls_model:
        return 0.45, "heuristic_scaffold", "нет внешней модели: результат полезен как структурированный черновик, не как доказанная истина"
    if supported == 0 and unsupported > 0:
        return 0.62, "model_checked_no_sources", "модель подключена, но фактические claims не подтверждены источниками/тестами"
    if supported > 0:
        return 0.78, "input_supported", "часть claims поддержана входным текстом"
    return 0.68, "model_checked", "модель подключена, но нет полноценной source/test verification"


def build_receipt(
    contract: TaskContract,
    graph: List[GraphNode],
    claims: List[Claim],
    verification: VerificationReport,
    worker_results: Dict[str, WorkerResult],
    provider_name: str,
) -> Dict[str, object]:
    proxy_calls_model = any(r.used_provider for r in worker_results.values())

    claim_types: Dict[str, int] = {}
    claim_statuses: Dict[str, int] = {}
    for claim in claims:
        claim_types[claim.claim_type] = claim_types.get(claim.claim_type, 0) + 1
        claim_statuses[claim.status] = claim_statuses.get(claim.status, 0) + 1

    supported = sum(1 for c in claims if c.status in SUPPORTED_STATUSES)
    unsupported = sum(1 for c in claims if c.status == "unsupported")
    cap, level, cap_reason = _verification_cap(proxy_calls_model, supported, unsupported, provider_name)

    structural_score = verification.scores.get("quality_score", 0.0)
    user_quality_score = min(structural_score, cap)
    if verification.blocking_findings:
        user_quality_score = min(user_quality_score, 0.55)

    if verification.blocking_findings:
        status = f"{level}_with_findings"
    else:
        status = level

    return {
        "status": status,
        "mode": contract.mode,
        "pack": contract.pack_name,
        "provider": provider_name,
        "proxy_calls_model": proxy_calls_model,
        "verification_level": level,
        "graph": {
            "nodes_total": len(graph),
            "nodes_completed": sum(1 for n in graph if n.status == "completed"),
            "nodes_failed": sum(1 for n in graph if n.status == "failed"),
        },
        "quality": {
            "quality_score": round(user_quality_score, 3),
            "structural_score": round(structural_score, 3),
            "max_score_cap": cap,
            "cap_reason": cap_reason,
            **{k: v for k, v in verification.scores.items() if k != "quality_score"},
        },
        "claims": {
            "total": len(claims),
            "supported": supported,
            "unsupported": unsupported,
            "by_type": claim_types,
            "by_status": claim_statuses,
        },
        "findings": {
            "total": len(verification.findings),
            "blocking": len(verification.blocking_findings),
            "codes": [f.code for f in verification.findings],
        },
        "success_criteria": contract.success_criteria,
        "remaining_risks": [
            f.message for f in verification.findings if f.severity in {"medium", "high", "critical"}
        ][:5],
    }
