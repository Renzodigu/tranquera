"""Reads a company folder: the Statement of Applicability plus Markdown documents.

Expected layout (see examples/nandu-pagos)::

    company/
      scope.yaml          # company name, as_of date, SoA exclusions
      **/*.md             # policies, procedures, evidence and records with YAML front matter
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import yaml

from .models import Chunk, Commitment, Document, Rule

_FRONT_MATTER = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_HEADING = re.compile(r"^(#{1,3})\s+(.*)$", re.MULTILINE)
MAX_CHUNK_CHARS = 1400


class CompanyError(ValueError):
    pass


@dataclass
class Exclusion:
    control: str
    justification: str


@dataclass
class Company:
    name: str
    description: str
    as_of: date | None
    root: Path
    exclusions: dict[str, Exclusion] = field(default_factory=dict)
    documents: list[Document] = field(default_factory=list)
    chunks: list[Chunk] = field(default_factory=list)

    def doc(self, doc_id: str) -> Document | None:
        return next((d for d in self.documents if d.id == doc_id), None)

    @property
    def commitments(self) -> list[Commitment]:
        return [c for d in self.documents for c in d.commitments]

    @property
    def rules(self) -> list[Rule]:
        return [r for d in self.documents for r in d.rules]

    @property
    def superseded_ids(self) -> set[str]:
        return {s for d in self.documents if not d.is_draft for s in d.supersedes}


def _as_date(value) -> date | None:
    if value in (None, "", "null"):
        return None
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def _as_str_tuple(value) -> tuple[str, ...]:
    if not value:
        return ()
    if isinstance(value, (str, int, float)):
        value = [value]
    return tuple(str(v) for v in value)


def parse_document(path: Path, text: str | None = None) -> Document:
    text = path.read_text(encoding="utf-8") if text is None else text
    m = _FRONT_MATTER.match(text)
    meta: dict = yaml.safe_load(m.group(1)) if m else {}
    meta = meta or {}
    body = text[m.end():] if m else text
    doc_id = str(meta.get("id") or path.stem)
    commitments = tuple(
        Commitment(
            id=str(c.get("id", f"{doc_id}-C{i + 1}")),
            control=str(c["control"]),
            activity=str(c.get("activity", "")),
            frequency=str(c.get("frequency", "annual")).lower(),
            evidence=str(c["evidence"]) if c.get("evidence") else None,
            source_doc=doc_id,
        )
        for i, c in enumerate(meta.get("commitments") or [])
    )
    rules = tuple(
        Rule(
            id=str(r.get("id", f"{doc_id}-R{i + 1}")),
            control=str(r["control"]),
            check=str(r.get("check", "")).lower(),
            description=str(r.get("description", "")),
            evidence=str(r["evidence"]) if r.get("evidence") else None,
            source_doc=doc_id,
            spec={k: v for k, v in r.items() if k not in ("id", "control", "check", "description", "evidence")},
        )
        for i, r in enumerate(meta.get("rules") or [])
    )
    return Document(
        id=doc_id,
        title=str(meta.get("title") or path.stem),
        type=str(meta.get("type") or "policy").lower(),
        path=str(path),
        body=body.strip(),
        owner=str(meta.get("owner") or "").strip(),
        version=str(meta.get("version") or ""),
        status=str(meta.get("status") or "aprobado"),
        approved=_as_date(meta.get("approved")),
        next_review=_as_date(meta.get("next_review")),
        controls=_as_str_tuple(meta.get("controls")),
        supersedes=_as_str_tuple(meta.get("supersedes")),
        executions=tuple(sorted(d for d in (_as_date(x) for x in meta.get("executions") or []) if d)),
        commitments=commitments,
        rules=rules,
        metrics={str(k): v for k, v in (meta.get("metrics") or {}).items()},
    )


def chunk_document(doc: Document) -> list[Chunk]:
    """Split by Markdown headings; long sections are split again by paragraphs."""
    sections: list[tuple[str, str]] = []
    matches = list(_HEADING.finditer(doc.body))
    if not matches:
        sections.append((doc.title, doc.body))
    else:
        if matches[0].start() > 0:
            sections.append((doc.title, doc.body[: matches[0].start()]))
        for i, m in enumerate(matches):
            end = matches[i + 1].start() if i + 1 < len(matches) else len(doc.body)
            sections.append((m.group(2).strip(), doc.body[m.end():end]))

    chunks: list[Chunk] = []
    for heading, text in sections:
        text = text.strip()
        if not text:
            continue
        parts = [text]
        if len(text) > MAX_CHUNK_CHARS:
            parts, buf = [], ""
            for para in re.split(r"\n\s*\n", text):
                if buf and len(buf) + len(para) > MAX_CHUNK_CHARS:
                    parts.append(buf)
                    buf = ""
                buf = f"{buf}\n\n{para}" if buf else para
            if buf:
                parts.append(buf)
        for part in parts:
            chunks.append(Chunk(f"{doc.id}#{len(chunks) + 1}", doc.id, heading, part.strip()))
    return chunks


def load_company(root: str | Path) -> Company:
    root = Path(root)
    if not root.is_dir():
        raise CompanyError(f"Not a folder: {root}")
    scope_path = root / "scope.yaml"
    scope = yaml.safe_load(scope_path.read_text(encoding="utf-8")) if scope_path.exists() else {}
    scope = scope or {}

    exclusions: dict[str, Exclusion] = {}
    for item in scope.get("exclusions") or []:
        cid = str(item.get("control", "")).strip()
        if cid:
            exclusions[cid] = Exclusion(cid, str(item.get("justification") or "").strip())

    company = Company(
        name=str(scope.get("company") or root.name),
        description=str(scope.get("description") or ""),
        as_of=_as_date(scope.get("as_of")),
        root=root,
        exclusions=exclusions,
    )
    seen: set[str] = set()
    for path in sorted(root.rglob("*.md")):
        if path.name.lower() == "readme.md":
            continue
        doc = parse_document(path)
        if doc.id in seen:
            raise CompanyError(f"Duplicate document id {doc.id} ({path})")
        seen.add(doc.id)
        company.documents.append(doc)
        company.chunks.extend(chunk_document(doc))
    if not company.documents:
        raise CompanyError(f"No Markdown documents found in {root}")
    return company
