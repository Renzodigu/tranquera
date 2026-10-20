"""Control assessors.

* ``HeuristicAssessor`` — offline and deterministic. Decides from document coverage only
  (policy present? evidence present?). Free, reproducible, used for the demo and CI.
* ``ClaudeAssessor`` — asks Claude for an auditor's verdict on each control, forcing a
  structured answer whose citations are then verified against the source text.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Protocol

from .i18n import t
from .ingest import Company
from .models import Action, Assessment, Citation, Control, Verdict
from .retrieval import Hit
from .textutil import squash

DEFAULT_MODEL = os.environ.get("TRANQUERA_MODEL", "claude-sonnet-5-5")


@dataclass
class Context:
    company: Company
    as_of: date
    lang: str

    @property
    def superseded(self) -> set[str]:
        return self.company.superseded_ids


class Assessor(Protocol):
    name: str

    def assess(self, control: Control, hits: list[Hit], ctx: Context) -> Assessment: ...


def _first_sentence(text: str, limit: int = 180) -> str:
    flat = " ".join(line.strip(" -*|") for line in text.splitlines() if line.strip())
    cut = flat.split(". ")[0]
    return (cut[:limit].rsplit(" ", 1)[0] + "…") if len(cut) > limit else cut


# --------------------------------------------------------------------------- heuristic
class HeuristicAssessor:
    name = "heuristic"

    def assess(self, control: Control, hits: list[Hit], ctx: Context) -> Assessment:
        docs = {d.id: d for d in ctx.company.documents}
        usable = [h for h in hits if h.chunk.doc_id not in ctx.superseded]
        policy_hits = [h for h in usable if docs[h.chunk.doc_id].is_policy_like and (h.tagged or h.phrase_match)]
        evidence_hits = [h for h in usable if not docs[h.chunk.doc_id].is_policy_like and h.tagged]

        policies = sorted({h.chunk.doc_id for h in policy_hits})
        evidence = sorted({h.chunk.doc_id for h in evidence_hits})
        lang = ctx.lang

        cited = policy_hits[:2] + evidence_hits[:1]
        citations = [Citation(h.chunk.id, h.chunk.doc_id, _first_sentence(h.chunk.text)) for h in cited]

        if not policies and not evidence:
            verdict, root, action = Verdict.NOT_MET, "missing_control", Action.ADD
            why, action_text = t(lang, "h_none"), t(lang, "h_action_add")
        elif policies and not evidence:
            verdict, root, action = Verdict.PARTIAL, "no_operating_evidence", Action.ADD
            why, action_text = t(lang, "h_policy_only", docs=", ".join(policies)), t(lang, "h_action_evidence")
        elif evidence and not policies:
            verdict, root, action = Verdict.PARTIAL, "no_policy", Action.ADD
            why, action_text = t(lang, "h_evidence_only", docs=", ".join(evidence)), t(lang, "h_action_policy")
        else:
            verdict, root, action, action_text = Verdict.MET, "", None, ""
            why = t(lang, "h_both", policies=", ".join(policies), evidence=", ".join(evidence))

        return Assessment(control.id, verdict, why, citations, action=action, action_text=action_text,
                          assessor=self.name, confidence="low", root_cause=root)


# --------------------------------------------------------------------------- Claude
SYSTEM_PROMPT = """You are a meticulous ISO/IEC 27001:2022 lead auditor performing a documentary gap analysis.

You receive one Annex A control and excerpts from the organization's policies, procedures, evidence and records.
Decide whether the excerpts demonstrate that the control is designed AND operating.

Verdicts:
- met: an approved, current policy or procedure covers the control AND there is evidence it operates as written.
- partial: the control is only designed (no operating evidence), the evidence contradicts the policy, coverage is incomplete, or the supporting document is a draft, expired or superseded.
- not_met: nothing in the excerpts addresses the control.
- undetermined: the excerpts are ambiguous and a human must decide.

Rules:
1. Use ONLY the excerpts provided. Never assume a practice exists because it is common.
2. Every claim must be backed by a citation whose `quote` is copied VERBATIM from the excerpt identified by `chunk_id` (max 30 words). Citations are verified mechanically; paraphrased quotes are discarded.
3. Look actively for contradictions: evidence that shows less than the policy promises (frequency, coverage, deadlines), open issues past their deadline, and older documents with conflicting rules.
4. Excerpts marked SUPERSEDED or DRAFT never make a control `met` on their own.
5. Recommend exactly one corrective action: `add` (create something missing), `fix` (correct or complete something that exists) or `remove` (withdraw something that should not exist).
6. Write `rationale`, `gaps`, `contradictions` and `action_text` in {language}. Be concrete and brief, like an audit working paper.
"""

ASSESSMENT_TOOL = {
    "name": "record_assessment",
    "description": "Record the audit verdict for one control.",
    "input_schema": {
        "type": "object",
        "properties": {
            "verdict": {"type": "string", "enum": ["met", "partial", "not_met", "undetermined"]},
            "rationale": {"type": "string", "description": "Two or three sentences explaining the verdict."},
            "citations": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "chunk_id": {"type": "string"},
                        "quote": {"type": "string", "description": "Verbatim text from that excerpt."},
                    },
                    "required": ["chunk_id", "quote"],
                },
            },
            "gaps": {"type": "array", "items": {"type": "string"}},
            "contradictions": {"type": "array", "items": {"type": "string"}},
            "action": {"type": "string", "enum": ["add", "fix", "remove", "none"]},
            "action_text": {"type": "string"},
            "confidence": {"type": "string", "enum": ["low", "medium", "high"]},
        },
        "required": ["verdict", "rationale", "citations", "action", "action_text", "confidence"],
    },
}


def build_user_prompt(control: Control, hits: list[Hit], ctx: Context) -> str:
    docs = {d.id: d for d in ctx.company.documents}
    lines = [
        f"Assessment date: {ctx.as_of.isoformat()}",
        f"Organization: {ctx.company.name}. {ctx.company.description}".strip(),
        "",
        f"CONTROL {control.id} — {control.title_en} / {control.title_es}",
        f"Theme: {control.theme}. Typical topics: {', '.join(control.keywords)}.",
        "",
        "EXCERPTS:",
    ]
    if not hits:
        lines.append("(no relevant excerpts were found)")
    for h in hits:
        d = docs[h.chunk.doc_id]
        flags = []
        if d.id in ctx.superseded:
            flags.append("SUPERSEDED")
        if d.is_draft:
            flags.append("DRAFT")
        if d.next_review and d.next_review < ctx.as_of:
            flags.append(f"REVIEW OVERDUE since {d.next_review.isoformat()}")
        meta = f"{d.type}, status={d.status}, approved={d.approved}, next_review={d.next_review}"
        if d.executions:
            meta += f", executions={[x.isoformat() for x in d.executions]}"
        lines += [
            f'<excerpt chunk_id="{h.chunk.id}" document="{d.id} {d.title}" {meta}{" " + " ".join(flags) if flags else ""}>',
            f"## {h.chunk.heading}",
            h.chunk.text,
            "</excerpt>",
        ]
    return "\n".join(lines)


def verify_citations(raw: list[dict], hits: list[Hit], lang: str) -> tuple[list[Citation], list[str]]:
    """Keep only citations whose quote really appears in the excerpt they point to."""
    by_id = {h.chunk.id: h.chunk for h in hits}
    good, notes = [], []
    for c in raw or []:
        chunk = by_id.get(str(c.get("chunk_id", "")))
        quote = str(c.get("quote", "")).strip()
        if chunk and quote and squash(quote) in squash(chunk.text):
            good.append(Citation(chunk.id, chunk.doc_id, quote))
        else:
            notes.append(t(lang, "unverified_citation", chunk=c.get("chunk_id", "?")))
    return good, notes


class ClaudeAssessor:
    name = "claude"

    def __init__(self, model: str = DEFAULT_MODEL, client=None, cache_dir: str | Path | None = ".tranquera-cache",
                 max_tokens: int = 1500):
        self.model = model
        self._client = client
        self.max_tokens = max_tokens
        self.cache_dir = Path(cache_dir) if cache_dir else None
        self.calls = 0

    @property
    def client(self):
        if self._client is None:
            try:
                import anthropic
            except ImportError as exc:  # pragma: no cover - depends on the environment
                raise RuntimeError("Install the Claude extra: pip install 'tranquera[claude]'") from exc
            self._client = anthropic.Anthropic()
        return self._client

    def _call(self, system: str, user: str) -> dict:
        key = hashlib.sha256(f"{self.model}\n{system}\n{user}".encode()).hexdigest()[:24]
        path = self.cache_dir / f"{key}.json" if self.cache_dir else None
        if path and path.exists():
            return json.loads(path.read_text(encoding="utf-8"))

        response = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
            tools=[ASSESSMENT_TOOL],
            tool_choice={"type": "tool", "name": ASSESSMENT_TOOL["name"]},
            messages=[{"role": "user", "content": user}],
        )
        self.calls += 1
        block = next((b for b in response.content if getattr(b, "type", "") == "tool_use"), None)
        if block is None:
            raise RuntimeError("Claude did not return a structured assessment")
        data = dict(block.input)
        if path:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return data

    def assess(self, control: Control, hits: list[Hit], ctx: Context) -> Assessment:
        language = "Spanish (Rioplatense, neutral professional tone)" if ctx.lang == "es" else "English"
        data = self._call(SYSTEM_PROMPT.replace("{language}", language), build_user_prompt(control, hits, ctx))

        try:
            verdict = Verdict(data.get("verdict", "undetermined"))
        except ValueError:
            verdict = Verdict.UNDETERMINED
        citations, notes = verify_citations(data.get("citations", []), hits, ctx.lang)
        # Anti-hallucination guard: a positive verdict must rest on verified text.
        if verdict in (Verdict.MET, Verdict.PARTIAL) and not citations:
            verdict = Verdict.UNDETERMINED
            notes.append(t(ctx.lang, "no_valid_citations"))

        raw_action = data.get("action", "none")
        action = Action(raw_action) if raw_action in ("add", "fix", "remove") else None
        return Assessment(
            control_id=control.id,
            verdict=verdict,
            rationale=str(data.get("rationale", "")),
            citations=citations,
            gaps=[str(g) for g in data.get("gaps", [])],
            contradictions=[str(c) for c in data.get("contradictions", [])],
            action=action,
            action_text=str(data.get("action_text", "")),
            assessor=f"claude:{self.model}",
            confidence=str(data.get("confidence", "medium")),
            notes=notes,
            root_cause=("contradiction" if data.get("contradictions") else
                        "missing_control" if verdict == Verdict.NOT_MET else "insufficient_evidence"),
        )
