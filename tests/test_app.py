"""Smoke test for the Streamlit app (skipped when Streamlit is not installed)."""

from pathlib import Path

import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest  # noqa: E402

APP = str(Path(__file__).parents[1] / "app" / "streamlit_app.py")


def test_app_runs_demo_analysis():
    at = AppTest.from_file(APP, default_timeout=60).run()
    assert not at.exception
    at.sidebar.button[0].click().run()
    assert not at.exception
    labels = {m.label: m.value for m in at.metric}
    assert labels["Aplicables"] == "94"  # 88 Annex A + 6 Ley 25.326
    assert "Ñandú Pagos" in at.subheader[0].value


def test_app_asks_for_key_with_claude():
    at = AppTest.from_file(APP, default_timeout=60).run()
    at.sidebar.radio[2].set_value("claude").run()
    at.sidebar.button[0].click().run()
    assert any("clave" in w.value.lower() for w in at.warning)
