from __future__ import annotations

from typing import List

from .models import GraphNode, Mode


def build_graph(mode: str) -> List[GraphNode]:
    mode = mode.lower()
    nodes: List[GraphNode] = [
        GraphNode("contract", "contract", "Compile task contract"),
        GraphNode("decompose", "decompose", "Decompose task into quality-relevant parts", depends_on=["contract"]),
    ]

    if mode == Mode.FAST.value:
        nodes.extend([
            GraphNode("generate", "worker", "Generate a structured candidate answer", depends_on=["decompose"]),
            GraphNode("claims", "claims", "Extract claims from candidate answer", depends_on=["generate"]),
            GraphNode("verify", "verify", "Run verifier mesh", depends_on=["claims"]),
            GraphNode("reduce", "reduce", "Build final answer and receipt", depends_on=["verify"]),
        ])
        return nodes

    nodes.extend([
        GraphNode("generate", "worker", "Generate a structured candidate answer", depends_on=["decompose"]),
        GraphNode("critic", "worker", "Critique candidate answer", depends_on=["generate"]),
    ])

    if mode in {Mode.DEEP.value, Mode.AUDIT.value}:
        nodes.extend([
            GraphNode("counterexample", "worker", "Search for counterexamples and failure modes", depends_on=["decompose"]),
            GraphNode("evidence", "worker", "Extract evidence and explicit source-like facts", depends_on=["decompose"]),
        ])

    nodes.extend([
        GraphNode("claims", "claims", "Extract and normalize claims", depends_on=["generate", "critic"]),
        GraphNode("verify", "verify", "Run verifier mesh", depends_on=["claims"]),
        GraphNode("repair", "repair", "Repair failed sections only", depends_on=["verify"]),
        GraphNode("reduce", "reduce", "Build final answer and receipt", depends_on=["repair"]),
    ])
    return nodes
