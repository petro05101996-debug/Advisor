from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional
import hashlib
import json
import time


class Mode(str, Enum):
    FAST = "fast"
    STANDARD = "standard"
    DEEP = "deep"
    AUDIT = "audit"


class Severity(str, Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class NodeStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


def stable_id(prefix: str, text: str, length: int = 12) -> str:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:length]
    return f"{prefix}_{digest}"


@dataclass
class TaskContract:
    goal: str
    task_type: str
    pack_name: str
    mode: str
    risk_level: str
    output_type: str
    quality_dimensions: List[str]
    required_sections: List[str]
    success_criteria: List[str]
    verification_modes: List[str]
    constraints: List[str] = field(default_factory=list)
    source_text: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class GraphNode:
    node_id: str
    kind: str
    description: str
    depends_on: List[str] = field(default_factory=list)
    status: str = NodeStatus.PENDING.value
    output: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    started_at: Optional[float] = None
    finished_at: Optional[float] = None

    def start(self) -> None:
        self.status = NodeStatus.RUNNING.value
        self.started_at = time.time()

    def complete(self, output: Optional[Dict[str, Any]] = None) -> None:
        self.status = NodeStatus.COMPLETED.value
        self.output = output or {}
        self.finished_at = time.time()

    def fail(self, error: str) -> None:
        self.status = NodeStatus.FAILED.value
        self.error = error
        self.finished_at = time.time()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class WorkerResult:
    worker_name: str
    role: str
    content: str
    artifacts: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.5
    used_provider: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Claim:
    claim_id: str
    text: str
    claim_type: str
    origin: str
    confidence: float = 0.5
    status: str = "unverified"
    source_refs: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class VerificationFinding:
    code: str
    message: str
    severity: str
    target: str = "answer"
    repair_hint: str = ""
    verifier: str = "unknown"

    def is_blocking(self) -> bool:
        return self.severity in {Severity.HIGH.value, Severity.CRITICAL.value}

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class VerificationReport:
    findings: List[VerificationFinding] = field(default_factory=list)
    scores: Dict[str, float] = field(default_factory=dict)

    @property
    def blocking_findings(self) -> List[VerificationFinding]:
        return [f for f in self.findings if f.is_blocking()]

    @property
    def status(self) -> str:
        return "failed" if self.blocking_findings else "passed"

    def add(self, finding: VerificationFinding) -> None:
        self.findings.append(finding)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "findings": [f.to_dict() for f in self.findings],
            "scores": self.scores,
        }


@dataclass
class DQEResult:
    final_answer: str
    contract: TaskContract
    graph: List[GraphNode]
    claims: List[Claim]
    verification: VerificationReport
    receipt: Dict[str, Any]
    intermediate: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "final_answer": self.final_answer,
            "contract": self.contract.to_dict(),
            "graph": [n.to_dict() for n in self.graph],
            "claims": [c.to_dict() for c in self.claims],
            "verification": self.verification.to_dict(),
            "receipt": self.receipt,
            "intermediate": self.intermediate,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
