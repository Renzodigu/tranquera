"""Policy rules tested against evidence tables: the deterministic answer to "does it operate as written?".

A policy declares in its front matter what its evidence must show; evidence records keep their data in
ordinary Markdown tables (or in a ``metrics`` map). Four kinds of test cover most audit procedures:

* ``threshold`` — a metric reaches a target (training completion >= 95 %).
* ``deadline``  — every matching row is closed within N days (calendar or business days); open rows age
  until the assessment date (critical vulnerabilities remediated in 7 days).
* ``required``  — every matching row has an accepted value in a column (high incidents have a post mortem).
* ``absent``    — keys from one table must not appear in another (leavers with an active account).

No AI involved: each failure lists the exact rows that break the rule.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime

from .catalog import control_index
from .i18n import t
from .ingest import Company
from .models import Action, Document, Finding, Rule, Severity
from .textutil import fold

CHECKS = ("threshold", "deadline", "required", "absent")
_HEADING = re.compile(r"^#{1,6}\s+(.*)$")
_SEPARATOR = re.compile(r"^\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?$")
MAX_LISTED = 6


class RuleError(ValueError):
    """The rule cannot be evaluated (missing evidence, table or column)."""


@dataclass
class Table:
    heading: str
    columns: list[str]
    rows: list[dict[str, str]]


@dataclass
class RuleResult:
    rule: Rule
    ok: bool
    tested: int = 0
    failures: list[str] = field(default_factory=list)
    summary: str = ""
    error: str = ""


def norm(value) -> str:
    return re.sub(r"\s+", " ", fold(str(value))).strip()


def parse_tables(markdown: str) -> list[Table]:
    """Every pipe table in the document, with the heading it sits under."""
    tables, heading, block = [], "", []

    def flush():
        if len(block) >= 2 and _SEPARATOR.match(block[1].strip()):
            cells = [_cells(line) for line in block]
            columns = cells[0]
            rows = [dict(zip(columns, r + [""] * (len(columns) - len(r)), strict=False)) for r in cells[2:]]
            tables.append(Table(heading, columns, rows))
        block.clear()

    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped.startswith("|"):
            block.append(stripped)
            continue
        flush()
        if m := _HEADING.match(stripped):
            heading = m.group(1).strip()
    flush()
    return tables


def _cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def parse_date(value: str) -> date | None:
    value = value.strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def _col(table: Table, name: str) -> str:
    wanted = norm(name)
    for c in table.columns:
        if norm(c) == wanted:
            return c
    raise RuleError(f"column '{name}' not found")


def find_table(doc: Document, spec: dict, needed: list[str]) -> Table:
    tables = parse_tables(doc.body)
    if spec.get("table"):
        tables = [tb for tb in tables if norm(spec["table"]) in norm(tb.heading)]
    for tb in tables:
        try:
            for name in needed:
                _col(tb, name)
            return tb
        except RuleError:
            continue
    raise RuleError(f"no table in {doc.id} with columns {', '.join(needed)}")


def _matches(row: dict[str, str], table: Table, where: dict) -> bool:
    for name, accepted in (where or {}).items():
        values = accepted if isinstance(accepted, list) else [accepted]
        if norm(row[_col(table, name)]) not in {norm(v) for v in values}:
            return False
    return True


def _key(row: dict[str, str], table: Table, spec: dict) -> str:
    return row[_col(table, spec["key"])] if spec.get("key") else row[table.columns[0]]


def _evidence(company: Company, ref: str | None) -> Document:
    doc = company.doc(ref) if ref else None
    if doc is None:
        raise RuleError(f"evidence record '{ref or '—'}' does not exist")
    return doc


# --------------------------------------------------------------------------- checks
def _threshold(rule: Rule, company: Company, as_of: date, lang: str) -> RuleResult:
    doc, spec = _evidence(company, rule.evidence), rule.spec
    metric = str(spec.get("metric", ""))
    if metric not in doc.metrics:
        raise RuleError(f"metric '{metric}' not found in {doc.id}")
    value = float(doc.metrics[metric])
    low, high = spec.get("min"), spec.get("max")
    ok = (low is None or value >= float(low)) and (high is None or value <= float(high))
    target = f">= {low}" if low is not None else f"<= {high}"
    summary = t(lang, "r_threshold", metric=metric, value=f"{value:g}", target=target)
    return RuleResult(rule, ok, 1, [] if ok else [summary], summary)


def _deadline(rule: Rule, company: Company, as_of: date, lang: str) -> RuleResult:
    doc, spec = _evidence(company, rule.evidence), rule.spec
    max_days = int(spec["max_days"])
    business = bool(spec.get("business_days"))
    table = find_table(doc, spec, [spec["start"]] + ([spec["end"]] if spec.get("end") else []))
    start_col = _col(table, spec["start"])
    end_col = _col(table, spec["end"]) if spec.get("end") else None
    rows = [r for r in table.rows if _matches(r, table, spec.get("where"))]
    failures = []
    for r in rows:
        start = parse_date(r[start_col])
        if start is None:
            failures.append(t(lang, "r_no_date", key=_key(r, table, spec), column=start_col))
            continue
        end = parse_date(r[end_col]) if end_col else None
        days = _business_days(start, end or as_of) if business else ((end or as_of) - start).days
        if days > max_days:
            suffix = "_business" if business else ""
            state = t(lang, f"r_closed_in{suffix}" if end else f"r_open_for{suffix}", days=days)
            failures.append(f"{_key(r, table, spec)} ({state})")
    summary = t(lang, "r_deadline_business" if business else "r_deadline", bad=len(failures), n=len(rows),
                days=max_days)
    return RuleResult(rule, not failures, len(rows), failures, summary)


def _business_days(start: date, end: date) -> int:
    """Monday-to-Friday days after ``start`` up to ``end``. Public holidays are not counted out."""
    if end <= start:
        return 0
    days = (end - start).days
    weeks, rest = divmod(days, 7)
    extra = sum(1 for i in range(1, rest + 1) if (start.weekday() + i) % 7 < 5)
    return weeks * 5 + extra


def _required(rule: Rule, company: Company, as_of: date, lang: str) -> RuleResult:
    doc, spec = _evidence(company, rule.evidence), rule.spec
    table = find_table(doc, spec, [spec["column"]])
    column = _col(table, spec["column"])
    expect = spec.get("expect")
    accepted = {norm(v) for v in (expect if isinstance(expect, list) else [expect])} if expect else None
    rows = [r for r in table.rows if _matches(r, table, spec.get("where"))]
    failures = []
    for r in rows:
        value = norm(r[column])
        if (accepted is None and value in ("", "-", "—", "no")) or (accepted is not None and value not in accepted):
            failures.append(f"{_key(r, table, spec)} ({column}: {r[column] or '—'})")
    summary = t(lang, "r_required", bad=len(failures), n=len(rows), column=column)
    return RuleResult(rule, not failures, len(rows), failures, summary)


def _absent(rule: Rule, company: Company, as_of: date, lang: str) -> RuleResult:
    spec = rule.spec
    source = _evidence(company, rule.evidence)
    target = _evidence(company, spec.get("against"))
    src_table = find_table(source, spec, [spec["column"]] + ([spec["date"]] if spec.get("date") else []))
    against_spec = {"table": spec.get("against_table")}
    tgt_table = find_table(target, against_spec, [spec.get("against_column", spec["column"])])
    src_col = _col(src_table, spec["column"])
    tgt_col = _col(tgt_table, spec.get("against_column", spec["column"]))

    present = {norm(r[tgt_col]): r for r in tgt_table.rows if _matches(r, tgt_table, spec.get("against_where"))}
    grace = int(spec.get("grace_days", 0))
    rows = []
    for r in src_table.rows:
        if not _matches(r, src_table, spec.get("where")):
            continue
        if spec.get("date"):
            when = parse_date(r[_col(src_table, spec["date"])])
            if when is None or (as_of - when).days <= grace:
                continue  # still inside the grace period
        rows.append(r)
    failures = [f"{r[src_col]} ({target.id})" for r in rows if norm(r[src_col]) in present]
    summary = t(lang, "r_absent", bad=len(failures), n=len(rows), source=source.id, target=target.id)
    return RuleResult(rule, not failures, len(rows), failures, summary)


_RUNNERS = {"threshold": _threshold, "deadline": _deadline, "required": _required, "absent": _absent}


def evaluate_rule(rule: Rule, company: Company, as_of: date, lang: str) -> RuleResult:
    runner = _RUNNERS.get(rule.check)
    try:
        if runner is None:
            raise RuleError(f"unknown check '{rule.check}' (use one of: {', '.join(CHECKS)})")
        return runner(rule, company, as_of, lang)
    except (RuleError, KeyError, ValueError, TypeError) as exc:
        msg = str(exc) if isinstance(exc, RuleError) else f"invalid rule definition ({exc!r})"
        return RuleResult(rule, False, error=msg, summary=msg)


# --------------------------------------------------------------------------- findings
def rule_findings(company: Company, as_of: date, lang: str) -> tuple[list[RuleResult], list[Finding]]:
    known = control_index()
    excluded = set(company.exclusions)
    results, out = [], []
    for rule in company.rules:
        if rule.control in excluded:
            continue
        res = evaluate_rule(rule, company, as_of, lang)
        results.append(res)
        if res.ok:
            continue
        source = company.doc(rule.source_doc)
        owner = source.owner if source else ""
        docs = [rule.source_doc] + [d for d in (rule.evidence, rule.spec.get("against")) if d]
        label = rule.description or rule.id
        if res.error:
            out.append(Finding(
                id="", source="rule", root_cause="rule_unverifiable", title=t(lang, "f_rule_error_title", rule=label),
                detail=t(lang, "f_rule_error_detail", id=rule.id, doc=rule.source_doc, error=res.error),
                severity=Severity.LOW, action=Action.FIX, action_text=t(lang, "f_rule_error_action"),
                controls=[rule.control], documents=docs, owner=owner))
            continue
        listed = res.failures[:MAX_LISTED]
        more = len(res.failures) - len(listed)
        items = "; ".join(listed) + (t(lang, "r_more", n=more) if more > 0 else "")
        sev = known[rule.control].criticality if rule.control in known else Severity.MEDIUM
        out.append(Finding(
            id="", source="rule", root_cause="operating_deviation", title=t(lang, "f_rule_title", rule=label),
            detail=t(lang, "f_rule_detail", doc=rule.source_doc, id=rule.id, summary=res.summary, items=items),
            severity=sev, action=Action.FIX, action_text=t(lang, "f_rule_action"),
            controls=[rule.control], documents=docs, owner=owner))
    return results, out
