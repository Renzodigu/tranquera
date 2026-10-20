"""Core data structures shared by the engine, the assessors and the reports."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date
from enum import Enum, StrEnum


class Verdict(StrEnum):
    MET = "met"
    PARTIAL = "partial"
    NOT_MET = "not_met"
    UNDETERMINED = "undetermined"
    EXCLUDED = "excluded"


# Lower rank = worse. Used to "cap" a verdict (a control can never look better
# than its weakest piece of supporting evidence).
VERDICT_RANK = {
    Verdict.NOT_MET: 0,
    Verdict.UNDETERMINED: 1,
    Verdict.PARTIAL: 2,
    Verdict.MET: 3,
}


class Severity(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


SEVERITY_ORDER = {Severity.HIGH: 0, Severity.MEDIUM: 1, Severity.LOW: 2}


def lower(sev: Severity) -> Severity:
    """One notch less severe."""
    return {Severity.HIGH: Severity.MEDIUM, Severity.MEDIUM: Severity.LOW}.get(sev, Severity.LOW)


class Action(StrEnum):
    """Corrective action types, the same vocabulary used in a reconciliation audit."""

    ADD = "add"        # something is missing and must be created
    FIX = "fix"        # something exists but is wrong, stale or incomplete
    REMOVE = "remove"  # something exists and should not


@dataclass(frozen=True)
class Control:
    id: str
    theme: str
    criticality: Severity
    title_en: str
    title_es: str
    keywords: tuple[str, ...]
    nist: tuple[str, ...]

    def title(self, lang: str) -> str:
        return self.title_es if lang == "es" else self.title_en


@dataclass(frozen=True)
class Commitment:
    """A periodic activity a policy promises to perform (e.g. quarterly access review)."""

    id: str
    control: str
    activity: str
    frequency: str
    evidence: str | None
    source_doc: str


@dataclass
class Document:
    id: str
    title: str
    type: str  # policy | procedure | evidence | record
    path: str
    body: str
    owner: str = ""
    version: str = ""
    status: str = "aprobado"
    approved: date | None = None
    next_review: date | None = None
    controls: tuple[str, ...] = ()
    supersedes: tuple[str, ...] = ()
    executions: tuple[date, ...] = ()
    commitments: tuple[Commitment, ...] = ()

    @property
    def is_policy_like(self) -> bool:
        return self.type in ("policy", "procedure")

    @property
    def is_draft(self) -> bool:
        return self.status.lower() in ("borrador", "draft")


@dataclass(frozen=True)
class Chunk:
    id: str        # e.g. "POL-02#3"
    doc_id: str
    heading: str
    text: str


@dataclass
class Citation:
    chunk_id: str
    doc_id: str
    quote: str
    verified: bool = True


@dataclass
class Assessment:
    control_id: str
    verdict: Verdict
    rationale: str
    citations: list[Citation] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)
    contradictions: list[str] = field(default_factory=list)
    action: Action | None = None
    action_text: str = ""
    assessor: str = ""
    confidence: str = "low"  # low | medium | high
    notes: list[str] = field(default_factory=list)
    root_cause: str = ""


@dataclass
class Finding:
    id: str
    source: str  # assessment | hygiene | reconciliation | soa | pattern
    root_cause: str
    title: str
    detail: str
    severity: Severity
    action: Action
    action_text: str
    controls: list[str] = field(default_factory=list)
    documents: list[str] = field(default_factory=list)
    owner: str = ""
    due: date | None = None
    status: str = "open"


@dataclass
class ControlResult:
    control: Control
    assessment: Assessment
    final: Verdict
    cap_reasons: list[str] = field(default_factory=list)
    exclusion_reason: str = ""


@dataclass
class NistResult:
    id: str
    function: str
    category: str
    title: str
    status: str  # met | partial | not_met | out_of_scope
    iso_controls: list[str]


@dataclass
class AnalysisResult:
    company: str
    description: str
    as_of: date
    lang: str
    assessor: str
    controls: list[ControlResult]
    findings: list[Finding]
    nist: list[NistResult]
    documents: list[Document]
    reconciliation: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        def conv(o):
            if isinstance(o, Enum):
                return o.value
            if isinstance(o, date):
                return o.isoformat()
            if isinstance(o, dict):
                return {k: conv(v) for k, v in o.items()}
            if isinstance(o, (list, tuple)):
                return [conv(v) for v in o]
            return o

        data = asdict(self)
        for d in data["documents"]:
            d.pop("body", None)
        return conv(data)
