"""Hostile or sloppy input: what a real document folder brings that the demo does not."""

import csv
import io

import pytest

from tranquera.engine import analyze
from tranquera.ingest import CompanyError, load_company, parse_document
from tranquera.metrics import load_expected
from tranquera.report import render_html, render_register_csv
from tranquera.rules import parse_tables

from .conftest import AS_OF, write_doc


def test_unquoted_control_ids_keep_their_trailing_zero(tmp_path):
    (tmp_path / "scope.yaml").write_text("company: X\nexclusions:\n  - {control: 7.10, justification: Sin medios}\n",
                                         encoding="utf-8")
    write_doc(tmp_path, "p.md", """
id: POL-1
controls: [5.10, 8.20, 5.18]
commitments:
  - {id: C1, control: 8.30, activity: Revisión, frequency: annual, evidence: EVD-1}
""")
    c = load_company(tmp_path)
    assert c.doc("POL-1").controls == ("5.10", "8.20", "5.18")
    assert c.commitments[0].control == "8.30"
    assert list(c.exclusions) == ["7.10"]


def test_byte_order_mark_does_not_hide_the_front_matter(tmp_path):
    path = tmp_path / "e.md"
    path.write_bytes("﻿---\nid: EVD-1\ntype: evidence\n---\n# Registro\n".encode())
    d = parse_document(path)
    assert d.id == "EVD-1" and d.type == "evidence"


def test_unknown_frequency_is_an_error_not_an_annual_check(tmp_path):
    write_doc(tmp_path, "p.md", """
id: POL-1
commitments:
  - {id: C1, control: "5.18", activity: Revisión, frequency: quaterly, evidence: EVD-1}
""")
    with pytest.raises(CompanyError, match="quaterly"):
        load_company(tmp_path)


@pytest.mark.parametrize("front", ["id: POL-1\nnext_review: 2027-02-30", "id: POL-1\nexecutions: [hola]",
                                   "id: [sin cerrar"])
def test_bad_front_matter_names_the_file(tmp_path, front):
    write_doc(tmp_path, "roto.md", front)
    with pytest.raises(CompanyError, match="roto.md"):
        load_company(tmp_path)


def test_html_report_escapes_document_content(tmp_path):
    (tmp_path / "scope.yaml").write_text('company: "<script>alert(1)</script>"\n', encoding="utf-8")
    write_doc(tmp_path, "p.md", 'id: POL-1\ntitle: "<img src=x onerror=alert(1)>"\nnext_review: 2020-01-01')
    html = render_html(analyze(tmp_path, as_of=AS_OF, only=["5.1"]))
    assert "<script>alert(1)" not in html and "<img src=x" not in html
    assert "&lt;script&gt;alert(1)" in html


def test_csv_register_neutralizes_formulas(tmp_path):
    write_doc(tmp_path, "p.md", 'id: POL-1\nowner: "=HYPERLINK(\\"http://x\\")"\nnext_review: 2020-01-01')
    rows = list(csv.DictReader(io.StringIO(render_register_csv(analyze(tmp_path, as_of=AS_OF, only=["5.1"])))))
    owners = {r["owner"] for r in rows}
    assert "'=HYPERLINK(\"http://x\")" in owners
    assert not any(v.startswith(("=", "+", "-", "@")) for r in rows for v in r.values() if v)


def test_tables_inside_code_blocks_are_not_evidence():
    md = "# Ejemplo\n\n```\n| Id | Fecha |\n|---|---|\n| FALSO | 2020-01-01 |\n```\n\n| Id | Fecha |\n|---|---|\n| R1 | 2026-01-01 |\n"
    tables = parse_tables(md)
    assert len(tables) == 1 and tables[0].rows[0]["Id"] == "R1"


def test_expected_verdicts_accept_unquoted_ids(tmp_path):
    path = tmp_path / "expected.yaml"
    path.write_text("verdicts:\n  5.10: {verdict: met}\n  8.20: {verdict: partial}\n", encoding="utf-8")
    assert list(load_expected(path)) == ["5.10", "8.20"]


def test_csv_files_have_one_line_break_per_row(tmp_path, company):
    from tranquera.report import write_reports

    files = write_reports(analyze(company, as_of=AS_OF, only=["5.18"]), tmp_path)
    data = files["register"].read_bytes()
    assert b"\r\r\n" not in data and data.count(b"\r\n") >= 2
