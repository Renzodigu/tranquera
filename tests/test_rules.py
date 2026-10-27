from datetime import date

from tranquera.engine import analyze
from tranquera.ingest import load_company
from tranquera.models import Rule, Verdict
from tranquera.rules import evaluate_rule, parse_tables, rule_findings

from .conftest import AS_OF, write_doc

TABLE_DOC = """# Registro

Texto previo.

## Casos 2026

| ID | Severidad | Detectada | Cerrada | Revisión |
| --- | :---: | --- | --- | --- |
| A-1 | Crítica | 2026-10-01 | 2026-10-05 | Sí |
| A-2 | critica | 2026-10-01 | | no |
| A-3 | Baja | 01/09/2026 | | |
"""


def _rule(check, evidence="EVD-01", **spec):
    return Rule("R-1", "8.8", check, "", evidence, "POL-01", spec)


def _company(tmp_path, body=TABLE_DOC, front_extra=""):
    write_doc(tmp_path, "pol.md", "id: POL-01\ntype: policy\nowner: CISO")
    write_doc(tmp_path, "evd.md", f"id: EVD-01\ntype: evidence\ncontrols: ['8.8']\n{front_extra}", body)
    return load_company(tmp_path)


def test_parse_tables_keeps_heading_and_pads_rows():
    tables = parse_tables(TABLE_DOC + "\n| x | y |\n| --- | --- |\n| 1 |\n")
    assert [tb.heading for tb in tables] == ["Casos 2026", "Casos 2026"]
    assert tables[0].rows[1]["Cerrada"] == ""
    assert tables[1].rows == [{"x": "1", "y": ""}]


def test_deadline_ages_open_rows_until_as_of_and_ignores_accents(tmp_path):
    res = evaluate_rule(_rule("deadline", where={"Severidad": "Crítica"}, start="Detectada", end="Cerrada",
                              max_days=7), _company(tmp_path), AS_OF, "en")
    assert not res.ok and res.tested == 2
    assert res.failures == ["A-2 (open for 19 days)"]


def test_deadline_reads_day_first_dates(tmp_path):
    res = evaluate_rule(_rule("deadline", where={"Severidad": "Baja"}, start="Detectada", max_days=60),
                        _company(tmp_path), AS_OF, "en")
    assert res.ok and res.tested == 1  # 2026-09-01 → 49 days


def test_required_with_expected_values(tmp_path):
    res = evaluate_rule(_rule("required", where={"Severidad": ["Crítica"]}, column="revisión", expect=["si"]),
                        _company(tmp_path), AS_OF, "en")
    assert res.failures == ["A-2 (Revisión: no)"]


def test_threshold_min_and_max(tmp_path):
    company = _company(tmp_path, front_extra="metrics: {coverage: 80}")
    assert not evaluate_rule(_rule("threshold", metric="coverage", min=90), company, AS_OF, "en").ok
    assert evaluate_rule(_rule("threshold", metric="coverage", max=80), company, AS_OF, "en").ok


def test_absent_respects_grace_period(tmp_path):
    write_doc(tmp_path, "pol.md", "id: POL-01\ntype: policy\nowner: CISO")
    write_doc(tmp_path, "hr.md", "id: HR\ntype: record",
              "| User | Left |\n| --- | --- |\n| ana | 2026-10-01 |\n| bob | 2026-10-19 |\n| eva | 2026-09-01 |")
    write_doc(tmp_path, "idp.md", "id: IDP\ntype: record",
              "| User | Status |\n| --- | --- |\n| ANA | Active |\n| bob | Active |\n| eva | Disabled |")
    rule = _rule("absent", evidence="HR", column="User", date="Left", grace_days=1, against="IDP",
                 against_where={"Status": "Active"})
    res = evaluate_rule(rule, load_company(tmp_path), AS_OF, "en")
    assert res.tested == 2 and res.failures == ["ana (IDP)"]


def test_broken_rule_is_reported_not_raised(tmp_path):
    company = _company(tmp_path)
    for rule in (_rule("deadline", start="Nope", max_days=1), _rule("required", evidence="EVD-99", column="x"),
                 _rule("magic"), _rule("threshold", metric="missing", min=1)):
        res = evaluate_rule(rule, company, AS_OF, "en")
        assert not res.ok and res.error


def test_demo_rules_catch_content_problems(company):
    results, findings = rule_findings(company, AS_OF, "es")
    by_id = {r.rule.id: r for r in results}
    assert by_id["REG-01"].failures == ["completion_rate = 62 (meta >= 95)"]
    assert [f.split(" ")[0] for f in by_id["REG-02"].failures] == ["VULN-26-017", "VULN-26-018"]
    assert by_id["REG-03"].failures == ["INC-2026-02 (Post mortem: No)"]
    assert [f.split(" ")[0] for f in by_id["REG-04"].failures] == ["mrojas", "jcabral", "pvillalba"]
    assert by_id["REG-05"].ok
    assert {f.root_cause for f in findings} == {"operating_deviation"}


def test_failed_rule_caps_verdict(company):
    r = {c.control.id: c for c in analyze(company, as_of=AS_OF, only=["6.3", "5.27"]).controls}
    assert r["6.3"].assessment.verdict == Verdict.MET
    assert r["6.3"].final == Verdict.PARTIAL and any("REG-01" in x for x in r["6.3"].cap_reasons)


def test_rules_are_in_json(company):
    data = analyze(company, as_of=date(2026, 10, 20), only=["8.8"]).to_dict()
    assert {x["rule"] for x in data["rules"]} >= {"REG-02", "REG-05"}
