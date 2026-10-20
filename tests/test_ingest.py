import pytest

from tranquera.ingest import CompanyError, chunk_document, load_company, parse_document

from .conftest import write_doc


def test_demo_company_loads(company):
    assert company.name == "Ñandú Pagos S.A."
    assert len(company.documents) == 17
    assert "8.11" in company.exclusions and company.exclusions["8.11"].justification == ""
    assert company.superseded_ids == {"POL-09"}
    assert len(company.commitments) == 6


def test_front_matter_is_parsed(tmp_path):
    p = write_doc(tmp_path, "a.md", """
id: POL-X
title: Política X
type: policy
owner: Ana
approved: 2026-01-01
next_review: 2027-01-01
controls: [5.1, "5.2"]
commitments:
  - {id: C1, control: "5.18", activity: Revisión, frequency: quarterly, evidence: EVD-X}
""")
    d = parse_document(p)
    assert d.id == "POL-X" and d.owner == "Ana" and d.controls == ("5.1", "5.2")
    assert d.commitments[0].frequency == "quarterly" and d.commitments[0].source_doc == "POL-X"


def test_chunks_follow_headings(tmp_path):
    p = write_doc(tmp_path, "b.md", "id: D1", "# T\n\nIntro\n\n## Uno\n\nA\n\n## Dos\n\nB")
    chunks = chunk_document(parse_document(p))
    assert [c.heading for c in chunks] == ["T", "Uno", "Dos"]
    assert [c.id for c in chunks] == ["D1#1", "D1#2", "D1#3"]


def test_duplicate_ids_are_rejected(tmp_path):
    write_doc(tmp_path, "a.md", "id: DUP")
    write_doc(tmp_path, "b.md", "id: DUP")
    with pytest.raises(CompanyError):
        load_company(tmp_path)


def test_empty_or_missing_folder(tmp_path):
    with pytest.raises(CompanyError):
        load_company(tmp_path)
    with pytest.raises(CompanyError):
        load_company(tmp_path / "nope")
