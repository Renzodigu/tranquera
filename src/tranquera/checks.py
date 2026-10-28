"""Deterministic checks that need no AI: document hygiene, SoA and commitment reconciliation.

The reconciliation compares what policies *promise* (front-matter ``commitments``) with what
evidence records *show* (``executions`` dates), period by period — the same line-by-line
logic as reconciling an internal plan against the documents a client actually received.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta

from .catalog import control_index
from .i18n import t
from .ingest import Company
from .models import Action, Commitment, Finding, Severity, lower

MONTH_NAMES = {
    "es": ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"],
    "en": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
}
PERIOD_MONTHS = {"monthly": 1, "quarterly": 3, "semiannual": 6}


def _finding(source: str, root: str, title: str, detail: str, sev: Severity, action: Action,
             action_text: str, controls=(), documents=(), owner: str = "") -> Finding:
    return Finding(id="", source=source, root_cause=root, title=title, detail=detail, severity=sev,
                   action=action, action_text=action_text, controls=list(controls),
                   documents=list(documents), owner=owner)


# --------------------------------------------------------------------------- hygiene
def hygiene_findings(company: Company, as_of: date, lang: str) -> list[Finding]:
    out: list[Finding] = []
    superseded = company.superseded_ids
    replaced_by = {s: d.id for d in company.documents if not d.is_draft for s in d.supersedes}

    for doc in company.documents:
        label = f"{doc.id} {doc.title}"
        if doc.id in superseded and doc.status.lower() not in ("obsoleto", "obsolete", "retirado"):
            out.append(_finding(
                "hygiene", "obsolete_document", t(lang, "f_obsolete_title", doc=label),
                t(lang, "f_obsolete_detail", by=replaced_by[doc.id], status=doc.status),
                Severity.MEDIUM, Action.REMOVE, t(lang, "f_obsolete_action"), doc.controls, [doc.id], doc.owner))
            continue  # an obsolete document should be removed, not reviewed

        if not doc.is_policy_like and doc.type not in ("evidence", "record"):
            continue

        if doc.is_policy_like and doc.is_draft:
            out.append(_finding(
                "hygiene", "not_approved", t(lang, "f_draft_title", doc=label),
                t(lang, "f_draft_detail", status=doc.status),
                Severity.MEDIUM, Action.FIX, t(lang, "f_draft_action"), doc.controls, [doc.id], doc.owner))
        elif doc.is_policy_like and doc.next_review and doc.next_review < as_of:
            days = (as_of - doc.next_review).days
            out.append(_finding(
                "hygiene", "document_expired", t(lang, "f_expired_title", doc=label),
                t(lang, "f_expired_detail", date=doc.next_review.isoformat(), days=days),
                Severity.HIGH if days > 365 else Severity.MEDIUM, Action.FIX, t(lang, "f_expired_action"),
                doc.controls, [doc.id], doc.owner))

        if doc.is_policy_like and not doc.owner:
            out.append(_finding(
                "hygiene", "no_owner", t(lang, "f_owner_title", doc=label), t(lang, "f_owner_detail"),
                Severity.MEDIUM, Action.FIX, t(lang, "f_owner_action"), doc.controls, [doc.id]))
    return out


# --------------------------------------------------------------------------- SoA
def soa_findings(company: Company, lang: str) -> list[Finding]:
    known = control_index()
    out = []
    for cid, exc in company.exclusions.items():
        if cid not in known:
            out.append(_finding("soa", "soa_unjustified", t(lang, "f_soa_unknown_title", control=cid),
                                t(lang, "f_soa_unknown_detail", control=cid), Severity.LOW, Action.FIX,
                                t(lang, "f_soa_unknown_action")))
        elif not exc.justification:
            sev = Severity.MEDIUM if known[cid].criticality != Severity.LOW else Severity.LOW
            out.append(_finding("soa", "soa_unjustified", t(lang, "f_soa_title", control=cid),
                                t(lang, "f_soa_detail", control=cid), sev, Action.FIX,
                                t(lang, "f_soa_action"), [cid], ["scope.yaml"]))
    return out


# --------------------------------------------------------------------------- reconciliation
@dataclass
class ReconciliationLine:
    commitment: Commitment
    expected: int
    found: int
    missing_periods: list[str]
    last: date | None
    evidence_exists: bool
    # One cell per period judged, oldest first: {"label": ..., "done": bool}. Drawn as a timeline in the report.
    periods: list[dict] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.evidence_exists and not self.missing_periods


def _period_label(index: int, months: int, lang: str) -> str:
    year, m0 = divmod(index * months, 12)
    names = MONTH_NAMES[lang if lang in MONTH_NAMES else "en"]
    if months == 1:
        return f"{names[m0]} {year}"
    if months == 3:
        return f"T{m0 // 3 + 1} {year}" if lang == "es" else f"Q{m0 // 3 + 1} {year}"
    return f"S{m0 // 6 + 1} {year}" if lang == "es" else f"H{m0 // 6 + 1} {year}"


def reconcile_commitment(c: Commitment, company: Company, as_of: date, lang: str) -> ReconciliationLine:
    evidence = company.doc(c.evidence) if c.evidence else None
    executions = [d for d in (evidence.executions if evidence else ()) if d <= as_of]
    last = max(executions) if executions else None

    months = PERIOD_MONTHS.get(c.frequency)
    if months:
        # The last N *complete* calendar periods covering twelve months. The current
        # period is not judged yet: the activity may still happen before it ends.
        current = (as_of.year * 12 + as_of.month - 1) // months
        periods = list(range(current - 12 // months, current))
        done = {(d.year * 12 + d.month - 1) // months for d in executions}
        missing = [_period_label(p, months, lang) for p in periods if p not in done]
        found = sum(1 for p in periods if p in done)
        expected = len(periods)
        cells = [{"label": _period_label(p, months, lang), "done": p in done} for p in periods]
    else:  # annual: rolling twelve months
        window_start = as_of - timedelta(days=365)
        found = sum(1 for d in executions if d > window_start)
        expected = 1
        missing = [] if found else [f"{window_start.isoformat()} → {as_of.isoformat()}"]
        found = min(found, 1)
        cells = [{"label": f"{window_start.isoformat()} → {as_of.isoformat()}", "done": bool(found)}]
    return ReconciliationLine(c, expected, found, missing, last, evidence is not None, cells)


def reconciliation(company: Company, as_of: date, lang: str) -> tuple[list[ReconciliationLine], list[Finding]]:
    known = control_index()
    lines, out = [], []
    excluded = set(company.exclusions)
    for c in company.commitments:
        if c.control in excluded:
            continue
        line = reconcile_commitment(c, company, as_of, lang)
        lines.append(line)
        if line.ok:
            continue
        crit = known[c.control].criticality if c.control in known else Severity.MEDIUM
        source = company.doc(c.source_doc)
        owner = source.owner if source else ""
        freq = t(lang, f"freq_{c.frequency}")
        if not line.evidence_exists:
            out.append(_finding(
                "reconciliation", "commitment_missed", t(lang, "f_noevidence_doc_title", activity=c.activity),
                t(lang, "f_noevidence_doc_detail", doc=c.source_doc, freq=freq, ref=c.evidence or "—"),
                crit, Action.ADD, t(lang, "f_noevidence_doc_action"), [c.control], [c.source_doc], owner))
            continue
        ratio = 1 - line.found / line.expected if line.expected else 1
        sev = crit if (line.found == 0 or ratio >= 0.5) else lower(crit)
        out.append(_finding(
            "reconciliation", "commitment_missed", t(lang, "f_missed_title", activity=c.activity),
            t(lang, "f_missed_detail", doc=c.source_doc, freq=freq, expected=line.expected, ref=c.evidence,
              found=line.found, gaps=", ".join(line.missing_periods),
              last=line.last.isoformat() if line.last else t(lang, "f_never")),
            sev, Action.FIX, t(lang, "f_missed_action"), [c.control], [c.source_doc, c.evidence], owner))
    return lines, out
