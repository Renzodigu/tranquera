"""Orchestrates a gap analysis: retrieval → assessment → deterministic checks → findings."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Iterable
from datetime import date, timedelta
from pathlib import Path

from .assessors import Assessor, Context, HeuristicAssessor
from .catalog import controls_for, nist_catalog
from .checks import hygiene_findings, reconciliation, soa_findings
from .i18n import t
from .ingest import Company, load_company
from .models import (
    SEVERITY_ORDER,
    VERDICT_RANK,
    Action,
    AnalysisResult,
    Assessment,
    ControlResult,
    Finding,
    NistResult,
    Severity,
    Verdict,
    lower,
)
from .retrieval import Retriever
from .rules import rule_findings

DUE_DAYS = {Severity.HIGH: 30, Severity.MEDIUM: 90, Severity.LOW: 180}
SOURCE_ORDER = {"pattern": 0, "reconciliation": 1, "rule": 2, "soa": 3, "hygiene": 4, "assessment": 5}
PATTERN_THRESHOLD = 3


def _cap(verdict: Verdict, ceiling: Verdict) -> Verdict:
    return ceiling if VERDICT_RANK.get(verdict, 0) > VERDICT_RANK[ceiling] else verdict


def analyze(
    company: Company | str | Path,
    assessor: Assessor | None = None,
    as_of: date | None = None,
    lang: str = "es",
    only: Iterable[str] | None = None,
    progress: Callable[[int, int, str], None] | None = None,
) -> AnalysisResult:
    if not isinstance(company, Company):
        company = load_company(company)
    assessor = assessor or HeuristicAssessor()
    as_of = as_of or company.as_of or date.today()
    ctx = Context(company, as_of, lang)
    retriever = Retriever(company)
    docs = {d.id: d for d in company.documents}
    superseded = company.superseded_ids

    controls = [c for c in controls_for(company.frameworks) if not only or c.id in set(only)]

    # 1) deterministic checks first: their results cap the AI/heuristic verdicts
    recon_lines, recon_findings = reconciliation(company, as_of, lang)
    rule_results, rule_breaches = rule_findings(company, as_of, lang)
    deterministic = (hygiene_findings(company, as_of, lang) + soa_findings(company, lang) + recon_findings
                     + rule_breaches)
    missed_by_control: dict[str, list[str]] = defaultdict(list)
    for line in recon_lines:
        if not line.ok:
            missed_by_control[line.commitment.control].append(line.commitment.id)
    broken_by_control: dict[str, list[str]] = defaultdict(list)
    for res in rule_results:
        if not res.ok and not res.error:
            broken_by_control[res.rule.control].append(res.rule.id)

    # 2) per-control assessment
    results: list[ControlResult] = []
    for i, control in enumerate(controls, 1):
        if progress:
            progress(i, len(controls), control.id)
        if control.id in company.exclusions:
            exc = company.exclusions[control.id]
            a = Assessment(control.id, Verdict.EXCLUDED, exc.justification, assessor="soa")
            results.append(ControlResult(control, a, Verdict.EXCLUDED, exclusion_reason=exc.justification))
            continue

        hits = retriever.search(control)
        assessment = assessor.assess(control, hits, ctx)
        final, reasons = assessment.verdict, []

        covering = {d.id for d in company.documents if control.id in d.controls}
        covering |= {c.doc_id for c in assessment.citations}
        for doc_id in sorted(covering - superseded):
            d = docs.get(doc_id)
            if not d or not d.is_policy_like:
                continue
            if d.is_draft:
                reasons.append(t(lang, "cap_draft", doc=doc_id))
            elif d.next_review and d.next_review < as_of:
                reasons.append(t(lang, "cap_expired", doc=doc_id))
        for cid in missed_by_control.get(control.id, []):
            reasons.append(t(lang, "cap_missed", commitment=cid))
        for rid in broken_by_control.get(control.id, []):
            reasons.append(t(lang, "cap_rule", rule=rid))
        if reasons:
            final = _cap(final, Verdict.PARTIAL)
        results.append(ControlResult(control, assessment, final, reasons, retrieved=[h.chunk.id for h in hits]))

    # 3) findings from assessments (only where the assessor itself saw a gap)
    findings = list(deterministic)
    for r in results:
        a = r.assessment
        if r.final == Verdict.EXCLUDED or a.verdict == Verdict.MET:
            continue  # met-but-capped controls are already explained by a deterministic finding
        crit = r.control.criticality
        sev = crit if a.verdict == Verdict.NOT_MET else lower(crit)
        if a.contradictions and sev != crit:
            sev = crit  # a contradiction is worse than a simple gap
        owner = next((docs[c.doc_id].owner for c in a.citations
                      if c.doc_id in docs and docs[c.doc_id].is_policy_like and docs[c.doc_id].owner), "")
        detail = a.rationale
        if a.gaps:
            detail += " " + " ".join(f"• {g}" for g in a.gaps)
        if a.contradictions:
            detail += " " + " ".join(f"⚠ {c}" for c in a.contradictions)
        findings.append(Finding(
            id="", source="assessment", root_cause=a.root_cause or "insufficient_evidence",
            title=t(lang, "f_assess_title", verdict=t(lang, a.verdict.value), control=r.control.id,
                    title=r.control.title(lang)),
            detail=detail.strip(), severity=sev, action=a.action or Action.ADD,
            action_text=a.action_text or t(lang, "h_action_add"), controls=[r.control.id],
            documents=sorted({c.doc_id for c in a.citations}), owner=owner,
        ))

    # 4) order, number, due dates
    findings.sort(key=lambda f: (SEVERITY_ORDER[f.severity], SOURCE_ORDER[f.source],
                                 _control_sort_key(f.controls[0]) if f.controls else (99, 0), f.title))
    for n, f in enumerate(findings, 1):
        f.id = f"TQ-{n:03d}"
        f.due = as_of + timedelta(days=DUE_DAYS[f.severity])

    # 5) systemic patterns: the same root cause repeated across findings
    by_cause: dict[str, list[Finding]] = defaultdict(list)
    for f in findings:
        by_cause[f.root_cause].append(f)
    patterns = []
    ranked = sorted(by_cause.items(),
                    key=lambda kv: (min(SEVERITY_ORDER[m.severity] for m in kv[1]), -len(kv[1])))
    for cause, members in ranked:
        if len(members) < PATTERN_THRESHOLD:
            continue
        sev = min((m.severity for m in members), key=SEVERITY_ORDER.get)
        patterns.append(Finding(
            id=f"TQ-P{len(patterns) + 1:02d}", source="pattern", root_cause=cause,
            title=t(lang, "f_pattern_title", cause=t(lang, f"rc_{cause}")),
            detail=t(lang, "f_pattern_detail", n=len(members), ids=", ".join(m.id for m in members)),
            severity=sev, action=Action.FIX, action_text=t(lang, "f_pattern_action"),
            controls=sorted({c for m in members for c in m.controls}, key=_control_sort_key),
            documents=sorted({d for m in members for d in m.documents}),
            due=as_of + timedelta(days=DUE_DAYS[sev]),
        ))

    return AnalysisResult(
        company=company.name, description=company.description, as_of=as_of, lang=lang,
        assessor=getattr(assessor, "name", "custom"), controls=results, frameworks=list(company.frameworks),
        findings=patterns + findings, nist=_nist_rollup(results, lang), documents=company.documents,
        reconciliation=[{
            "commitment": ln.commitment.id, "control": ln.commitment.control,
            "activity": ln.commitment.activity, "frequency": ln.commitment.frequency,
            "source": ln.commitment.source_doc, "evidence": ln.commitment.evidence,
            "expected": ln.expected, "found": ln.found, "missing": ln.missing_periods,
            "last": ln.last, "ok": ln.ok, "periods": ln.periods,
        } for ln in recon_lines],
        rules=[{
            "rule": res.rule.id, "control": res.rule.control, "check": res.rule.check,
            "description": res.rule.description, "source": res.rule.source_doc, "evidence": res.rule.evidence,
            "tested": res.tested, "failed": len(res.failures), "summary": res.summary,
            "failures": res.failures, "ok": res.ok, "error": res.error,
        } for res in rule_results],
    )


def _control_sort_key(cid: str) -> tuple[int, int]:
    try:
        if cid.startswith("LPDP-"):
            return 100, int(cid[5:])  # Ley 25.326 obligations after Annex A
        a, b = cid.split(".")
        return int(a), int(b)
    except ValueError:
        return 99, 0


def _nist_rollup(results: list[ControlResult], lang: str) -> list[NistResult]:
    nist = nist_catalog()
    mapped: dict[str, list[ControlResult]] = defaultdict(list)
    for r in results:
        for sub in r.control.nist:
            mapped[sub].append(r)
    out = []
    for sub_id, desc in nist.subcategories.items():
        rs = [r for r in mapped.get(sub_id, []) if r.final != Verdict.EXCLUDED]
        if not rs:
            status = "out_of_scope"
        elif all(r.final == Verdict.MET for r in rs):
            status = "met"
        elif all(r.final == Verdict.NOT_MET for r in rs):
            status = "not_met"
        else:
            status = "partial"
        out.append(NistResult(
            id=sub_id, function=nist.function_of(sub_id), category=nist.category_of(sub_id),
            title=desc["es"] if lang == "es" else desc["en"], status=status,
            iso_controls=[r.control.id for r in mapped.get(sub_id, [])],
        ))
    return out
