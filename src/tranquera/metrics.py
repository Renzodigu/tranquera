"""Measures an analysis against expected verdicts (ground truth) written together with the documents.

A demo where every planted problem is caught says little about the controls nobody planted anything
in. ``expected.yaml`` states the verdict an auditor would give for a set of controls, and why, so
accuracy, missed gaps and gaps that are not real can be counted instead of claimed::

    verdicts:
      "5.18": {verdict: partial, why: "Quarterly review done once in 2026", evidence: [POL-02, EVD-01]}

``evidence`` (optional) lists the documents that hold the answer. If retrieval does not bring them to
the assessor, no assessor can get the control right, so retrieval is measured apart from judgment.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from .i18n import t
from .models import AnalysisResult, Verdict
from .report import LABELS

EXPECTED = ("met", "partial", "not_met")
OBTAINED = ("met", "partial", "not_met", "undetermined", "excluded")


class ExpectedError(ValueError):
    pass


def load_expected(path: str | Path) -> dict[str, dict]:
    path = Path(path)
    if not path.is_file():
        raise ExpectedError(f"Expected-verdicts file not found: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    out = {}
    for cid, item in (data.get("verdicts") or {}).items():
        verdict = str(item.get("verdict", "")).lower()
        if verdict not in EXPECTED:
            raise ExpectedError(f"{cid}: verdict must be one of {', '.join(EXPECTED)}, not '{verdict}'")
        out[str(cid)] = {"verdict": verdict, "why": str(item.get("why", "")),
                         "evidence": [str(d) for d in item.get("evidence") or []]}
    return out


def compare(result: AnalysisResult, expected: dict[str, dict]) -> dict:
    by_id = {c.control.id: c for c in result.controls}
    ids = [cid for cid in expected if cid in by_id]
    obtained = {cid: by_id[cid].final.value for cid in ids}

    matrix = {e: dict.fromkeys(OBTAINED, 0) for e in EXPECTED}
    errors = []
    for cid in ids:
        real, got = expected[cid]["verdict"], obtained[cid]
        matrix[real][got] += 1
        if real != got:
            errors.append({"control": cid, "expected": real, "obtained": got, "why": expected[cid]["why"]})

    # The worst error in GRC: reporting as met something that is not.
    false_met = [e for e in errors if e["obtained"] == Verdict.MET]
    with_gap = [cid for cid in ids if expected[cid]["verdict"] != "met"]
    detected = [cid for cid in with_gap if obtained[cid] != Verdict.MET]
    # The other way round: controls that work but are flagged. They create remediation work nobody
    # needs and cost the report its credibility.
    false_gaps = [e for e in errors if e["expected"] == "met"]

    wanted = {cid: set(expected[cid]["evidence"]) for cid in ids if expected[cid]["evidence"]}
    seen = {cid: {chunk.split("#")[0] for chunk in by_id[cid].retrieved} for cid in wanted}
    total = sum(len(docs) for docs in wanted.values())
    found = sum(len(docs & seen[cid]) for cid, docs in wanted.items())
    missed = [{"control": cid, "missing": sorted(docs - seen[cid])} for cid, docs in wanted.items()
              if docs - seen[cid] and obtained[cid] != Verdict.EXCLUDED]

    return {
        "assessor": result.assessor,
        "compared": len(ids),
        "not_assessed": [cid for cid in expected if cid not in by_id],
        "accuracy": (len(ids) - len(errors)) / len(ids) if ids else 0.0,
        "gap_detection": len(detected) / len(with_gap) if with_gap else 1.0,
        "false_met": false_met,
        "false_gaps": false_gaps,
        "retrieval_recall": found / total if total else None,
        "retrieval_missed": missed,
        "matrix": matrix,
        "errors": errors,
    }


def render_markdown(m: dict, lang: str = "es") -> str:
    L = LABELS[lang if lang in LABELS else "en"]
    out = [f"# {L['metrics_title']} · `{m['assessor']}`", ""]
    out.append(f"- **{L['m_compared']}:** {m['compared']}")
    out.append(f"- **{L['m_accuracy']}:** {m['accuracy']:.0%}")
    out.append(f"- **{L['m_detection']}:** {m['gap_detection']:.0%} {L['m_detection_of']}")
    out.append(f"- **{L['m_false_met']}:** {len(m['false_met'])}")
    out.append(f"- **{L['m_false_gap']}:** {len(m['false_gaps'])}")
    if m["retrieval_recall"] is not None:
        out.append(f"- **{L['m_retrieval']}:** {m['retrieval_recall']:.0%} {L['m_retrieval_of']}")
    if m["not_assessed"]:
        out.append(f"- **{L['m_not_assessed']}:** {', '.join(m['not_assessed'])}")
    cols = [c for c in OBTAINED if any(m["matrix"][e][c] for e in EXPECTED) or c in EXPECTED]
    out += ["", f"## {L['m_matrix']}", ""]
    out.append("| | " + " | ".join(t(lang, c) for c in cols) + " |")
    out.append("| --- |" + " ---: |" * len(cols))
    for e in EXPECTED:
        out.append(f"| **{t(lang, e)}** | " + " | ".join(str(m["matrix"][e][c]) for c in cols) + " |")
    if m["errors"]:
        out += ["", f"## {L['m_diffs']}", "",
                f"| {L['controls']} | {L['m_expected']} | {L['m_obtained']} | {L['m_why']} |", "| --- | --- | --- | --- |"]
        for e in m["errors"]:
            out.append(f"| {e['control']} | {t(lang, e['expected'])} | {t(lang, e['obtained'])} | {e['why']} |")
    if m["retrieval_missed"]:
        out += ["", f"## {L['m_missed_docs']}", "", f"| {L['controls']} | {L['m_missing']} |", "| --- | --- |"]
        for x in m["retrieval_missed"]:
            out.append(f"| {x['control']} | {', '.join(x['missing'])} |")
    out.append("")
    return "\n".join(out)
