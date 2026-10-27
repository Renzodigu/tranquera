import pytest

from tranquera.cli import main
from tranquera.engine import analyze
from tranquera.metrics import ExpectedError, compare, load_expected, render_markdown


@pytest.fixture()
def metrics(company, demo_dir):
    return compare(analyze(company), load_expected(demo_dir / "expected.yaml"))


def test_demo_is_measured_against_its_expected_verdicts(metrics):
    assert metrics["compared"] == 42 and not metrics["not_assessed"]
    assert sum(sum(row.values()) for row in metrics["matrix"].values()) == 42
    assert 0 < metrics["accuracy"] < 1


def test_false_met_are_reported(metrics):
    # The leavers rule caps 5.18 only; the same evidence also breaks 5.16, 6.5 and 8.2.
    assert {e["control"] for e in metrics["false_met"]} == {"5.16", "6.5", "8.2"}


def test_retrieval_is_measured_apart(metrics):
    assert metrics["retrieval_recall"] is not None
    assert {"control": "5.34", "missing": ["EVD-11"]} in metrics["retrieval_missed"]


def test_markdown_lists_every_difference(metrics):
    md = render_markdown(metrics, "es")
    assert md.count("\n| LPDP-12 |") == 1 and "Matriz de confusión" in md
    assert "Confusion matrix" in render_markdown(metrics, "en")


def test_invalid_expected_verdict(tmp_path):
    p = tmp_path / "expected.yaml"
    p.write_text('verdicts:\n  "5.1": {verdict: cubierto}\n', encoding="utf-8")
    with pytest.raises(ExpectedError, match="cubierto"):
        load_expected(p)


def test_cli_evaluate(tmp_path):
    assert main(["evaluate", "--out", str(tmp_path)]) == 0
    assert (tmp_path / "metrics.md").exists()
    assert main(["evaluate", "--out", str(tmp_path), "--min-accuracy", "99"]) == 1
    assert main(["evaluate", "--expected", str(tmp_path / "missing.yaml"), "--out", str(tmp_path)]) == 2
