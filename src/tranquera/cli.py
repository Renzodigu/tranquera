"""Command line interface: ``tranquera analyze <folder>``, ``tranquera demo`` and ``tranquera evaluate``."""

from __future__ import annotations

import argparse
import os
import sys
from datetime import date
from importlib import resources
from pathlib import Path

from . import __version__
from .assessors import DEFAULT_MODEL, ClaudeAssessor, HeuristicAssessor
from .engine import analyze
from .ingest import CompanyError
from .metrics import ExpectedError, compare, load_expected, render_markdown
from .models import SEVERITY_ORDER, Severity
from .report import summary, write_reports


def demo_path() -> Path:
    return Path(str(resources.files("tranquera").joinpath("demo", "nandu-pagos")))


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="tranquera", description="Deterministic ISO 27001 / NIST CSF 2.0 gap analysis (Claude optional).")
    p.add_argument("--version", action="version", version=f"tranquera {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    def common(sp):
        sp.add_argument("--assessor", choices=["heuristic", "claude"], default="heuristic",
                        help="heuristic: deterministic, offline and free (default). claude: optional semantic review, needs ANTHROPIC_API_KEY.")
        sp.add_argument("--model", default=DEFAULT_MODEL, help=f"Claude model (default: {DEFAULT_MODEL}).")
        sp.add_argument("--lang", choices=["es", "en"], default="es", help="Report language (default: es).")
        sp.add_argument("--as-of", type=date.fromisoformat, help="Assessment date YYYY-MM-DD (default: scope.yaml or today).")
        sp.add_argument("--controls", help="Comma-separated subset of Annex A controls, e.g. 5.18,8.13.")
        sp.add_argument("--out", default="tranquera-report", help="Output folder (default: tranquera-report).")
        sp.add_argument("--no-cache", action="store_true", help="Do not reuse cached Claude answers.")
        sp.add_argument("--fail-on", choices=["high", "medium", "low"],
                        help="Exit with code 1 if there is a finding of this severity or worse (for CI).")

    a = sub.add_parser("analyze", help="Analyze a folder of policies and evidence.")
    a.add_argument("path", help="Company folder with scope.yaml and Markdown documents.")
    common(a)
    d = sub.add_parser("demo", help="Run on the bundled fictitious company (Ñandú Pagos S.A.).")
    common(d)
    e = sub.add_parser("evaluate", help="Measure the analysis against expected verdicts (expected.yaml).")
    e.add_argument("path", nargs="?", help="Company folder (default: the bundled demo).")
    e.add_argument("--expected", help="Expected verdicts file (default: <path>/expected.yaml).")
    e.add_argument("--min-accuracy", type=float, metavar="PCT",
                   help="Exit with code 1 if verdict accuracy is below this percentage (for CI).")
    common(e)
    return p


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        # Redirected output on Windows uses cp1252: a company name with an emoji must not crash the run.
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="replace")
    args = _build_parser().parse_args(argv)
    path = Path(args.path) if getattr(args, "path", None) else demo_path()
    expected = None
    if args.command == "evaluate":
        try:
            expected = load_expected(args.expected or path / "expected.yaml")
        except ExpectedError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2

    if args.assessor == "claude":
        if not os.environ.get("ANTHROPIC_API_KEY"):
            print("error: --assessor claude needs the ANTHROPIC_API_KEY environment variable.", file=sys.stderr)
            return 2
        assessor = ClaudeAssessor(model=args.model, cache_dir=None if args.no_cache else ".tranquera-cache")
    else:
        assessor = HeuristicAssessor()

    only = [c.strip() for c in args.controls.split(",")] if args.controls else None

    def progress(i: int, n: int, cid: str) -> None:
        if sys.stderr.isatty():
            print(f"\r  evaluating {cid:<6} {i}/{n}", end="", file=sys.stderr, flush=True)

    try:
        result = analyze(path, assessor, as_of=args.as_of, lang=args.lang, only=only, progress=progress)
    except CompanyError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if sys.stderr.isatty():
        print(file=sys.stderr)

    files = write_reports(result, args.out, fictional=path == demo_path())
    s = summary(result)
    print(f"{result.company} · {result.as_of} · assessor={result.assessor}")
    print(f"  controls: {s['applicable']} applicable, {s['excluded']} excluded · score {s['score']}%")
    print(f"  met {s['counts']['met']} · partial {s['counts']['partial']} · not met {s['counts']['not_met']}"
          f" · needs review {s['counts']['undetermined']}")
    sev = s["by_severity"]
    print(f"  findings: {s['findings']} (high {sev.get('high', 0)}, medium {sev.get('medium', 0)}, low {sev.get('low', 0)})"
          f" · patterns {sum(1 for f in result.findings if f.source == 'pattern')}")
    if getattr(assessor, "calls", 0):
        print(f"  Claude API calls: {assessor.calls}")
    for kind, f in files.items():
        print(f"  {kind:<9} {f}")

    if expected is not None:
        m = compare(result, expected)
        out = Path(args.out) / "metrics.md"
        out.write_text(render_markdown(m, args.lang), encoding="utf-8")
        recall = f" · retrieval {m['retrieval_recall']:.0%}" if m["retrieval_recall"] is not None else ""
        print(f"  accuracy {m['accuracy']:.0%} on {m['compared']} controls · gaps detected {m['gap_detection']:.0%}"
              f" · false met {len(m['false_met'])} · false gaps {len(m['false_gaps'])}{recall}")
        print(f"  {'metrics':<9} {out}")
        if args.min_accuracy is not None and 100 * m["accuracy"] < args.min_accuracy:
            return 1

    if args.fail_on:
        limit = SEVERITY_ORDER[Severity(args.fail_on)]
        if any(SEVERITY_ORDER[f.severity] <= limit for f in result.findings):
            return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
