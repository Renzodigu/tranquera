from tranquera.engine import analyze
from tranquera.models import Verdict

from .conftest import AS_OF


def _result(company, **kw):
    return analyze(company, as_of=AS_OF, **kw)


def test_excluded_controls_are_not_assessed(company):
    r = _result(company)
    excluded = {c.control.id for c in r.controls if c.final == Verdict.EXCLUDED}
    assert excluded == {"7.8", "7.11", "7.12", "8.11", "8.30"}


def test_missed_commitment_caps_met_to_partial(company):
    r = {c.control.id: c for c in _result(company).controls}
    assert r["5.18"].assessment.verdict == Verdict.MET
    assert r["5.18"].final == Verdict.PARTIAL
    assert any("COM-02" in reason for reason in r["5.18"].cap_reasons)


def test_expired_and_draft_documents_cap_verdicts(company):
    r = {c.control.id: c for c in _result(company).controls}
    assert r["5.26"].final == Verdict.PARTIAL and "POL-03" in " ".join(r["5.26"].cap_reasons)
    assert "POL-06" in " ".join(r["8.28"].cap_reasons)


def test_clean_control_stays_met(company):
    r = {c.control.id: c for c in _result(company).controls}
    assert r["6.3"].final == Verdict.MET  # policy + training record, commitment reconciled


def test_missing_topics_are_not_met(company):
    r = {c.control.id: c for c in _result(company).controls}
    for cid in ("5.7", "5.29", "8.12"):
        assert r[cid].final == Verdict.NOT_MET, cid


def test_superseded_document_never_counts_as_coverage(company):
    r = {c.control.id: c for c in _result(company).controls}
    assert all(q.doc_id != "POL-09" for q in r["5.17"].assessment.citations)


def test_findings_are_numbered_dated_and_unique(company):
    r = _result(company)
    ids = [f.id for f in r.findings]
    assert len(ids) == len(set(ids))
    assert all(f.due and f.due > AS_OF for f in r.findings)
    first = [f for f in r.findings if f.source != "pattern"][0]
    assert first.id == "TQ-001" and first.severity.value == "high"


def test_systemic_patterns(company):
    r = _result(company)
    patterns = {f.root_cause: f for f in r.findings if f.source == "pattern"}
    assert "commitment_missed" in patterns
    members = [f for f in r.findings if f.root_cause == "commitment_missed" and f.source != "pattern"]
    assert all(m.id in patterns["commitment_missed"].detail for m in members)


def test_nist_rollup(company):
    r = _result(company)
    by = {n.id: n for n in r.nist}
    assert len(by) == 106
    assert by["PR.DS-11"].status == "partial"         # backups: restore tests missed
    assert by["ID.RA-02"].status == "not_met"         # threat intelligence missing
    assert by["GV.RM-01"].status == "out_of_scope"    # clause-level, not Annex A
    assert by["PR.AT-01"].status == "met"


def test_subset_and_english(company):
    r = _result(company, only=["5.18", "8.13"], lang="en")
    assert [c.control.id for c in r.controls] == ["5.18", "8.13"]
    assert any(f.title.startswith("Commitment missed") for f in r.findings)
