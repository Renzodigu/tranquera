from tranquera.checks import hygiene_findings, reconciliation, soa_findings
from tranquera.ingest import load_company
from tranquera.models import Action, Severity

from .conftest import AS_OF, write_doc


def _by_doc(findings):
    out = {}
    for f in findings:
        for d in f.documents:
            out.setdefault(d, []).append(f.root_cause)
    return out


def test_hygiene_detects_planted_issues(company):
    found = _by_doc(hygiene_findings(company, AS_OF, "es"))
    assert found["POL-03"] == ["document_expired"]
    assert found["POL-05"] == ["no_owner"]
    assert found["POL-06"] == ["not_approved"]
    assert found["POL-09"] == ["obsolete_document"]
    assert "POL-01" not in found and "POL-02" not in found


def test_obsolete_document_must_be_removed(company):
    f = next(f for f in hygiene_findings(company, AS_OF, "es") if f.root_cause == "obsolete_document")
    assert f.action == Action.REMOVE


def test_expired_more_than_a_year_is_high(company):
    f = next(f for f in hygiene_findings(company, AS_OF, "es") if f.root_cause == "document_expired")
    assert f.severity == Severity.HIGH  # due 2025-03-01, 598 days late


def test_soa_flags_unjustified_exclusion(company):
    findings = soa_findings(company, "es")
    assert [f.controls for f in findings] == [["8.11"]]


def test_reconciliation_periods(company):
    lines, findings = reconciliation(company, AS_OF, "es")
    by = {ln.commitment.id: ln for ln in lines}
    assert by["COM-02"].missing_periods == ["T4 2025", "T2 2026", "T3 2026"]  # access reviews
    assert by["COM-04"].missing_periods == ["T1 2026", "T2 2026", "T3 2026"]  # restore tests
    assert by["COM-06"].missing_periods == ["jul 2026", "ago 2026"]          # monthly scans
    assert by["COM-06"].expected == 12 and by["COM-06"].found == 10
    assert by["COM-03"].found == 0                                           # tabletop: 2024
    assert by["COM-01"].ok and by["COM-05"].ok
    assert len(findings) == 4


def test_reconciliation_severity(company):
    _, findings = reconciliation(company, AS_OF, "es")
    sev = {f.controls[0]: f.severity for f in findings}
    assert sev["5.18"] == Severity.HIGH    # 1 of 4 quarters
    assert sev["8.8"] == Severity.MEDIUM   # 10 of 12 months: one notch below criticality


def test_current_period_is_not_judged_yet(company):
    lines, _ = reconciliation(company, AS_OF, "en")
    by = {ln.commitment.id: ln for ln in lines}
    assert "Q4 2026" not in by["COM-02"].missing_periods
    assert "Oct 2026" not in by["COM-06"].missing_periods


def test_commitment_without_evidence_record(tmp_path):
    write_doc(tmp_path, "p.md", """
id: P1
type: policy
owner: Ana
commitments:
  - {id: C1, control: "8.13", activity: Restore test, frequency: quarterly, evidence: MISSING}
""")
    _, findings = reconciliation(load_company(tmp_path), AS_OF, "en")
    assert len(findings) == 1 and findings[0].action == Action.ADD
