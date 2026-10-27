from datetime import date

import pytest

from tranquera.catalog import ley_controls
from tranquera.engine import analyze
from tranquera.ingest import CompanyError, load_company
from tranquera.models import Verdict
from tranquera.report import render_html, render_soa_csv
from tranquera.rules import _business_days

from .conftest import AS_OF, write_doc


def _by_id(company):
    return {c.control.id: c for c in analyze(company, as_of=AS_OF).controls}


def test_catalog_cites_articles_and_annex_a():
    obligations = ley_controls()
    assert [o.id for o in obligations] == ["LPDP-04", "LPDP-05", "LPDP-09", "LPDP-12", "LPDP-14", "LPDP-21"]
    for o in obligations:
        assert o.refs and o.iso and o.keywords and o.theme == "privacy"


def test_law_pack_is_opt_in(tmp_path):
    write_doc(tmp_path, "pol.md", "id: POL-01\ntype: policy\nowner: CISO")
    ids = {c.control.id for c in analyze(load_company(tmp_path), as_of=AS_OF).controls}
    assert "5.34" in ids and not any(i.startswith("LPDP-") for i in ids)


def test_unknown_framework_is_rejected(tmp_path):
    (tmp_path / "scope.yaml").write_text("frameworks: [iso27001-2022, gdpr]\n", encoding="utf-8")
    write_doc(tmp_path, "pol.md", "id: POL-01\ntype: policy")
    with pytest.raises(CompanyError, match="gdpr"):
        load_company(tmp_path)


def test_rights_deadlines_cap_the_obligation(company):
    r = _by_id(company)["LPDP-14"]
    assert r.assessment.verdict == Verdict.MET and r.final == Verdict.PARTIAL
    reasons = " ".join(r.cap_reasons)
    assert "REG-06" in reasons and "REG-07" in reasons


def test_rights_rules_list_the_late_requests(company):
    rules = {x["rule"]: x for x in analyze(company, as_of=AS_OF).rules}
    assert [f.split(" ")[0] for f in rules["REG-06"]["failures"]] == ["SOL-26-04"]
    # SOL-26-05: 7 calendar days but 5 business days, so it is on time
    assert [f.split(" ")[0] for f in rules["REG-07"]["failures"]] == ["SOL-26-03", "SOL-26-06"]


def test_undocumented_obligations_are_not_met(company):
    r = _by_id(company)
    assert r["LPDP-21"].final == Verdict.NOT_MET


def test_soa_has_only_annex_a(company):
    result = analyze(company, as_of=AS_OF)
    assert "LPDP-" not in render_soa_csv(result)
    html = render_html(result)
    assert "Ley 25.326" in html and "art. 14" in html


@pytest.mark.parametrize(("start", "end", "expected"), [
    ("2026-08-14", "2026-08-21", 5),   # Friday to Friday
    ("2026-10-09", "2026-10-20", 7),   # Friday to Tuesday, one weekend in between
    ("2026-10-17", "2026-10-18", 0),   # Saturday to Sunday
    ("2026-10-20", "2026-10-20", 0),
])
def test_business_days(start, end, expected):
    assert _business_days(date.fromisoformat(start), date.fromisoformat(end)) == expected
