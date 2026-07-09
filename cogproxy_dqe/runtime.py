from __future__ import annotations

from typing import Dict, List, Optional

from .claims import extract_claims, assign_claim_statuses
from .contract import compile_task_contract
from .models import DQEResult, GraphNode, Mode, TaskContract, WorkerResult
from .planner import build_graph
from .providers import BaseProvider, make_provider
from .receipt import build_receipt
from .reducer import reduce_answer
from .repair import repair_answer
from .verifiers import VerifierMesh
from .workers import WorkerPool


def _node(graph: List[GraphNode], node_id: str) -> GraphNode:
    for n in graph:
        if n.node_id == node_id:
            return n
    raise KeyError(node_id)


def _complete(graph: List[GraphNode], node_id: str, output: Optional[dict] = None) -> None:
    n = _node(graph, node_id)
    n.start()
    n.complete(output or {})


def run_dqe(
    task: str,
    pack_name: Optional[str] = None,
    mode: str = Mode.STANDARD.value,
    provider: Optional[BaseProvider] = None,
    provider_cmd: Optional[str] = None,
    max_workers: int = 4,
    extra_context: Optional[dict] = None,
) -> DQEResult:
    contract = compile_task_contract(task, pack_name=pack_name, mode=mode)
    if extra_context:
        contract.metadata.update(extra_context)
    graph = build_graph(contract.mode)
    provider = provider or make_provider(provider_cmd)
    pool = WorkerPool(provider=provider, max_workers=max_workers)
    worker_results: Dict[str, WorkerResult] = {}

    _complete(graph, "contract", {"contract": contract.to_dict()})

    generated = pool.run_initial(contract)
    decompose = generated["decompose"]
    worker_results["decompose"] = decompose
    _complete(graph, "decompose", decompose.to_dict())

    worker_results.update(generated)
    _complete(graph, "generate", generated["generate"].to_dict())
    if any(n.node_id == "critic" for n in graph):
        _complete(graph, "critic", generated["critic"].to_dict())

    if contract.mode in {Mode.DEEP.value, Mode.AUDIT.value}:
        deep_results = pool.run_deep_workers(contract)
        worker_results.update(deep_results)
        for node_id, result in deep_results.items():
            if any(n.node_id == node_id for n in graph):
                _complete(graph, node_id, result.to_dict())

    claims_input = [worker_results[k] for k in worker_results if k != "decompose"]
    claims = extract_claims(claims_input)

    verifier_context = {}
    if "evidence" in worker_results:
        verifier_context["evidence"] = worker_results["evidence"].artifacts.get("evidence", [])
    if "generate" in worker_results and "bug_evidence" in worker_results["generate"].artifacts:
        verifier_context["evidence"] = worker_results["generate"].artifacts.get("bug_evidence", [])
    provider_called = any(r.used_provider for r in worker_results.values())
    assign_claim_statuses(claims, provider_called=provider_called, evidence_present=bool(verifier_context.get("evidence")))
    _complete(graph, "claims", {"claims_total": len(claims), "claims": [c.to_dict() for c in claims]})

    initial_answer = worker_results["generate"].content
    mesh = VerifierMesh(contract.verification_modes)
    verification = mesh.verify(contract, initial_answer, claims, verifier_context)
    _complete(graph, "verify", verification.to_dict())

    repaired_answer = initial_answer
    if any(n.node_id == "repair" for n in graph):
        repaired_answer = repair_answer(initial_answer, contract, verification.findings)
        # Re-run verifiers after repair. This is the core repair loop; v0.1 performs one bounded repair pass.
        repaired_claims = extract_claims([WorkerResult("repaired", "repair", repaired_answer, confidence=0.7)])
        claims.extend(c for c in repaired_claims if c.claim_id not in {x.claim_id for x in claims})
        assign_claim_statuses(claims, provider_called=provider_called, evidence_present=bool(verifier_context.get("evidence")))
        verification = mesh.verify(contract, repaired_answer, claims, verifier_context)
        _complete(graph, "repair", {"repaired": repaired_answer != initial_answer, "verification_after_repair": verification.to_dict()})

    final_answer = reduce_answer(contract, repaired_answer, worker_results, claims, verification)
    _complete(graph, "reduce", {})
    receipt = build_receipt(contract, graph, claims, verification, worker_results, provider.name)
    _node(graph, "reduce").output = {"receipt": receipt}

    return DQEResult(
        final_answer=final_answer,
        contract=contract,
        graph=graph,
        claims=claims,
        verification=verification,
        receipt=receipt,
        intermediate={
            "workers": {k: v.to_dict() for k, v in worker_results.items()},
            "repaired_answer": repaired_answer,
            "verifier_context": verifier_context,
        },
    )
