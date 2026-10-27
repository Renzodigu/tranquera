import json

from tranquera.cli import main
from tranquera.engine import analyze
from tranquera.report import render_html, render_register_csv, write_reports

from .conftest import AS_OF


def test_reports_are_written(company, tmp_path):
    r = analyze(company, as_of=AS_OF)
    files = write_reports(r, tmp_path, fictional=True)
    html = files["html"].read_text(encoding="utf-8")
    assert "Ñandú Pagos S.A." in html and "TQ-001" in html and "Datos ficticios" in html
    data = json.loads(files["json"].read_text(encoding="utf-8"))
    assert data["summary"]["applicable"] == 94 and data["tool"]["name"] == "tranquera"
    raw = files["register"].read_bytes()
    assert raw.startswith(b"\xef\xbb\xbf")  # BOM: accents survive Excel
    header = raw.decode("utf-8-sig").splitlines()[0]
    assert header.startswith("id,severity,source,root_cause,title")


def test_register_has_one_row_per_finding(company):
    r = analyze(company, as_of=AS_OF)
    assert render_register_csv(r).count("\nTQ-") == len(r.findings)


def test_english_report(company):
    html = render_html(analyze(company, as_of=AS_OF, lang="en"))
    assert "Security gap analysis" in html and "Findings register" in html


def test_cli_demo(tmp_path, capsys):
    assert main(["demo", "--out", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "94 applicable" in out and (tmp_path / "report.html").exists()


def test_cli_fail_on_high(tmp_path):
    assert main(["demo", "--out", str(tmp_path), "--fail-on", "high"]) == 1


def test_cli_claude_requires_key(tmp_path, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert main(["demo", "--assessor", "claude", "--out", str(tmp_path)]) == 2


def test_cli_bad_folder(tmp_path):
    assert main(["analyze", str(tmp_path / "missing"), "--out", str(tmp_path)]) == 2
