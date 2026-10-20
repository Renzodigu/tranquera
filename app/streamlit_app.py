"""Tranquera web demo (Streamlit). Run with: streamlit run app/streamlit_app.py"""

from __future__ import annotations

import io
import tempfile
import zipfile
from datetime import date
from pathlib import Path, PurePosixPath

import streamlit as st

from tranquera import __version__
from tranquera.assessors import DEFAULT_MODEL, ClaudeAssessor, HeuristicAssessor
from tranquera.cli import demo_path
from tranquera.engine import analyze
from tranquera.i18n import t
from tranquera.ingest import CompanyError, load_company
from tranquera.report import register_rows, render_html, render_json, render_register_csv, summary

UI = {
    "es": {
        "tagline": "Análisis de brechas ISO/IEC 27001:2022 y NIST CSF 2.0 con hallazgos auditables.",
        "source": "Documentos", "demo": "Empresa ficticia de demo (Ñandú Pagos S.A.)", "upload": "Subir un .zip propio",
        "zip_help": "Carpeta con scope.yaml y documentos Markdown con front matter (ver la demo).",
        "assessor": "Evaluador", "heuristic": "Heurístico (gratis, sin conexión)", "claude": "Claude (análisis semántico)",
        "key": "Clave de API de Anthropic", "key_help": "Se usa solo en esta sesión y no se guarda.",
        "lang": "Idioma del informe", "as_of": "Fecha de corte", "run": "Analizar",
        "need_zip": "Subí un .zip para continuar.", "need_key": "Ingresá una clave de API para usar Claude.",
        "running": "Evaluando controles…", "score": "Cumplimiento", "applicable": "Aplicables",
        "high": "Hallazgos altos", "tab_findings": "Hallazgos", "tab_recon": "Conciliación",
        "tab_controls": "Controles", "tab_nist": "NIST CSF 2.0", "severity": "Severidad",
        "download": "Descargar", "fictional": "Todos los datos de la demo son ficticios.",
        "bad_zip": "El .zip contiene rutas inválidas.",
    },
    "en": {
        "tagline": "ISO/IEC 27001:2022 and NIST CSF 2.0 gap analysis with auditable findings.",
        "source": "Documents", "demo": "Fictitious demo company (Ñandú Pagos S.A.)", "upload": "Upload your own .zip",
        "zip_help": "Folder with scope.yaml and Markdown documents with front matter (see the demo).",
        "assessor": "Assessor", "heuristic": "Heuristic (free, offline)", "claude": "Claude (semantic review)",
        "key": "Anthropic API key", "key_help": "Used only for this session and never stored.",
        "lang": "Report language", "as_of": "Assessment date", "run": "Analyze",
        "need_zip": "Upload a .zip to continue.", "need_key": "Enter an API key to use Claude.",
        "running": "Assessing controls…", "score": "Compliance", "applicable": "Applicable",
        "high": "High findings", "tab_findings": "Findings", "tab_recon": "Reconciliation",
        "tab_controls": "Controls", "tab_nist": "NIST CSF 2.0", "severity": "Severity",
        "download": "Download", "fictional": "All demo data is fictitious.",
        "bad_zip": "The .zip contains invalid paths.",
    },
}

st.set_page_config(page_title="Tranquera", page_icon="🚧", layout="wide")

lang = st.sidebar.radio("Idioma / Language", ["es", "en"], horizontal=True)
U = UI[lang]

st.title("Tranquera")
st.caption(f"{U['tagline']} · v{__version__}")

source = st.sidebar.radio(U["source"], ["demo", "upload"], format_func=lambda k: U[k])
upload = st.sidebar.file_uploader(".zip", type="zip", help=U["zip_help"]) if source == "upload" else None
kind = st.sidebar.radio(U["assessor"], ["heuristic", "claude"], format_func=lambda k: U[k])
api_key = st.sidebar.text_input(U["key"], type="password", help=U["key_help"]) if kind == "claude" else ""
model = st.sidebar.text_input("Model", DEFAULT_MODEL) if kind == "claude" else DEFAULT_MODEL
as_of = st.sidebar.date_input(U["as_of"], value=date(2026, 10, 20) if source == "demo" else date.today())


def _extract(data: bytes) -> Path:
    target = Path(tempfile.mkdtemp(prefix="tranquera-"))
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        for name in zf.namelist():
            p = PurePosixPath(name)
            if p.is_absolute() or ".." in p.parts:
                raise CompanyError(U["bad_zip"])
        zf.extractall(target)
    scopes = sorted(target.rglob("scope.yaml"), key=lambda p: len(p.parts))
    return scopes[0].parent if scopes else target


if st.sidebar.button(U["run"], type="primary", use_container_width=True):
    try:
        if source == "upload":
            if upload is None:
                st.warning(U["need_zip"])
                st.stop()
            folder = _extract(upload.getvalue())
        else:
            folder = demo_path()
        if kind == "claude":
            if not api_key:
                st.warning(U["need_key"])
                st.stop()
            import anthropic

            assessor = ClaudeAssessor(model=model, client=anthropic.Anthropic(api_key=api_key), cache_dir=None)
        else:
            assessor = HeuristicAssessor()
        company = load_company(folder)
        bar = st.progress(0.0, text=U["running"])
        result = analyze(company, assessor, as_of=as_of, lang=lang,
                         progress=lambda i, n, cid: bar.progress(i / n, text=f"{U['running']} {cid}"))
        bar.empty()
        st.session_state["result"] = result
        st.session_state["fictional"] = source == "demo"
    except (CompanyError, zipfile.BadZipFile) as exc:
        st.error(str(exc))

result = st.session_state.get("result")
if result is None:
    st.info(U["tagline"])
    st.stop()

s = summary(result)
st.subheader(f"{result.company} · {result.as_of}")
if st.session_state.get("fictional"):
    st.caption(U["fictional"])
cols = st.columns(5)
cols[0].metric(U["score"], f"{s['score']}%")
cols[1].metric(U["applicable"], s["applicable"])
cols[2].metric(t(lang, "met"), s["counts"]["met"])
cols[3].metric(t(lang, "not_met"), s["counts"]["not_met"])
cols[4].metric(U["high"], s["high"])

d1, d2, d3 = st.columns(3)
d1.download_button(f"{U['download']} HTML", render_html(result, st.session_state.get("fictional", False)),
                   "report.html", "text/html", use_container_width=True)
d2.download_button(f"{U['download']} CSV", render_register_csv(result).encode("utf-8-sig"),
                   "findings-register.csv", "text/csv", use_container_width=True)
d3.download_button(f"{U['download']} JSON", render_json(result), "results.json", "application/json",
                   use_container_width=True)

tab_f, tab_r, tab_c, tab_n = st.tabs([U["tab_findings"], U["tab_recon"], U["tab_controls"], U["tab_nist"]])
with tab_f:
    sevs = [t(lang, x) for x in ("high", "medium", "low")]
    chosen = st.multiselect(U["severity"], sevs, default=sevs)
    rows = [r for r in register_rows(result) if r["severity"] in chosen]
    st.dataframe(rows, use_container_width=True, hide_index=True,
                 column_order=["id", "severity", "title", "controls", "action", "action_text", "owner", "due"])
with tab_r:
    st.dataframe([{**ln, "missing": ", ".join(ln["missing"]), "ok": "✓" if ln["ok"] else "✗"}
                  for ln in result.reconciliation], use_container_width=True, hide_index=True)
with tab_c:
    for c in result.controls:
        with st.expander(f"{c.control.id} · {c.control.title(lang)} — {t(lang, c.final.value)}"):
            st.write(c.assessment.rationale or c.exclusion_reason)
            for reason in c.cap_reasons:
                st.caption(f"↓ {reason}")
            for q in c.assessment.citations:
                st.markdown(f"> `{q.chunk_id}` {q.quote}")
with tab_n:
    st.dataframe([{"id": n.id, "status": t(lang, n.status), "title": n.title, "iso": " ".join(n.iso_controls)}
                  for n in result.nist], use_container_width=True, hide_index=True)
