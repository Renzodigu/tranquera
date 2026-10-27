# Tranquera

**Deterministic ISO/IEC 27001:2022, NIST CSF 2.0 and Ley 25.326 gap analysis: policy rules tested against evidence, with findings you can trace to a row or a date, and accuracy measured against expected verdicts.**

Tranquera reads an organization's policies and evidence (Markdown with YAML front matter), assesses
every Annex A control, reconciles what policies *promise* against what evidence *shows*, tests the rules each policy sets
(targets, deadlines, mandatory records, leavers) against the evidence tables, and produces
the outputs a GRC team actually works with: an executive report, a findings register with corrective
actions, owners and due dates, and a Statement of Applicability.

> *Tranquera* is the gate of an Argentine ranch: what gets through and what doesn't.

![CI](https://github.com/Renzodigu/tranquera/actions/workflows/ci.yml/badge.svg)

## Why another compliance tool?

Most "AI compliance" demos ask a model whether a policy is good. An auditor needs something else:
results that are reproducible, explainable and cheap to rerun every month. Tranquera works fully
offline, with no AI and no API key.

- **Policy rules tested row by row.** A policy declares what its evidence must show; Tranquera tests
  it against the evidence tables and lists the exact rows that fail (see [rules](#rules-testing-operation-without-ai)).
- **Designed vs. operating.** A control backed only by a policy is *partial*. It is *met* only when
  linked evidence shows it running.
- **Deterministic reconciliation.** Policies declare periodic commitments (quarterly access reviews,
  restore tests, monthly scans). Tranquera checks each complete calendar period against the evidence
  log and lists exactly which periods are missing, no AI involved.
- **Verdicts can't look better than their weakest evidence.** A control that relies on an expired or
  draft document, or that has a missed commitment, is capped at *partial*.
- **Systemic patterns.** Findings are grouped by root cause; a cause repeated three or more times is
  reported as a process failure, not as isolated errors.
- **One assessment, two frameworks.** Annex A results roll up into the 106 NIST CSF 2.0 subcategories.
- **Argentine privacy law, opt-in.** Six obligations of Ley 25.326 (consent, data subject rights,
  international transfers, database registration...) assessed with the same engine, with their
  articles cited. Legal deadlines become rules: access answered in 10 calendar days, rectification
  or deletion in 5 business days.
- **Measured, not claimed.** `tranquera evaluate` compares the verdicts with an `expected.yaml`
  written from the documents and reports accuracy, missed gaps and false *met* (see
  [accuracy](#accuracy-measured-against-expected-verdicts)).
- **Optional second opinion.** A Claude assessor can review content; every verdict must quote the
  documents verbatim, quotes are checked mechanically and unverified ones are discarded. It is never
  needed for the core analysis.

## Quick start

```bash
pip install "tranquera[app] @ git+https://github.com/Renzodigu/tranquera"
tranquera demo                      # offline, no AI: fictitious fintech, Spanish report
tranquera demo --lang en            # English report
tranquera evaluate                  # demo + accuracy against its expected verdicts (metrics.md)
open tranquera-report/report.html
```

From a clone:

```bash
pip install -e ".[dev,app,claude]"
pytest -q
tranquera analyze path/to/company --out report/
streamlit run app/streamlit_app.py  # web demo
```

### Optional: Claude review

```bash
export ANTHROPIC_API_KEY=...        # never commit it
tranquera analyze path/to/company --assessor claude --controls 5.18,8.13   # try a few controls first
tranquera analyze path/to/company --assessor claude                        # full run: one call per control
```

The model defaults to `claude-sonnet-5-5` and can be changed with `--model` or `TRANQUERA_MODEL`.
Answers are cached in `.tranquera-cache/`, so re-running the same analysis costs nothing.

### Use it in CI

`--fail-on high` exits with code 1 when there is a high-severity finding, so a documentation
repository can block merges that leave, for example, an expired incident policy.

## Demo: Ñandú Pagos S.A.

`src/tranquera/demo/nandu-pagos` is a **fictitious** Buenos Aires payments company (100 % on AWS,
140 employees) with 10 policies, 11 evidence records, a Statement of Applicability and the Ley 25.326
pack enabled. Problems were planted on purpose to check what the tool catches. Deterministic run
(no AI), as of 2026-10-20:

| | |
| --- | --- |
| Applicable controls | 94: 88 Annex A (5 excluded in the SoA) + 6 Ley 25.326 obligations |
| Met / partial / not met | 8 / 54 / 32 |
| Findings | 92 (11 high) in 4 systemic patterns |
| Commitments reconciled | 2 of 6 |
| Policy rules passed | 1 of 7 |
| Accuracy against expected verdicts | 88 % on 42 controls, 3 false *met* |

Sample reports: [`examples/demo-es`](examples/demo-es) and [`examples/demo-en`](examples/demo-en)
(HTML report, findings register CSV, SoA CSV, JSON).

| Planted problem | Caught by | Result |
| --- | --- | --- |
| Quarterly access review done once in 2026 | Reconciliation | High: periods Q4 2025, Q2 2026, Q3 2026 missing |
| Quarterly restore test, last one Nov 2025 | Reconciliation | High: Q1–Q3 2026 missing |
| Monthly vulnerability scan skipped Jul and Aug 2026 | Reconciliation | Medium: 10 of 12 months |
| Annual incident drill, last one in 2024 | Reconciliation | High |
| Incident policy review overdue since 2025-03-01 | Hygiene | High; caps every control it supports at partial |
| 2019 password policy still published, superseded | Hygiene | Remove |
| Supplier policy without owner | Hygiene | Fix |
| Secure development policy still a draft | Hygiene | Fix; caps every control it supports at partial |
| SoA excludes 8.11 without justification | SoA | Fix |
| No business continuity, threat intelligence or DLP | Assessment | Not met |
| Only 62 % of staff completed the annual training | Rule `threshold` | 6.3 capped at partial: 62 vs. target 95 |
| Two critical vulnerabilities open beyond the 7-day SLA | Rule `deadline` | VULN-26-017 and VULN-26-018, open for 41 days |
| High-severity incident closed without post mortem | Rule `required` | INC-2026-02 |
| Three leavers still have an active SSO account | Rule `absent` | mrojas, jcabral, pvillalba (a leaver from yesterday is still inside the 24-hour grace period) |
| Data subject access request answered in 18 days | Rule `deadline` | LPDP-14 capped at partial: SOL-26-04 |
| Deletion requests beyond 5 business days | Rule `deadline` (`business_days`) | SOL-26-03 (9 business days) and SOL-26-06 (open for 7); SOL-26-05 took 7 calendar days but only 5 business days, so it passes |
| Databases never registered with the AAIP | Assessment | LPDP-21 not met |

Every planted problem is caught without AI. Version 0.1 needed Claude for the rule rows; 0.2 turns
them into rules the policy owner can read and the auditor can rerun.

## Accuracy: measured against expected verdicts

A demo where every planted problem is caught says little about the controls where nothing was
planted. `src/tranquera/demo/nandu-pagos/expected.yaml` holds the verdict an auditor would give for
42 controls, and why, written from the documents before running the tool. `tranquera evaluate`
compares them ([sample `metrics.md`](examples/demo-es/metrics.md)):

| Assessor | Accuracy | Real gaps detected | False *met* | Met controls flagged as gaps | Retrieval |
| --- | ---: | ---: | ---: | ---: | ---: |
| Deterministic | 88 % | 92 % | 3 | 0 | 98 % |
| Claude | *not run yet* | | | | |

What the misses show:

- **Evidence that contradicts the policy without a rule.** 5.16, 6.5 and 8.2 come out *met*:
  there is a policy and linked evidence. But the leavers rule only caps 5.18, the control it
  names, and the access review in EVD-01 says in plain text that three former employees still have
  access to the production AWS console. Nothing deterministic reads that sentence.
- **Negation.** POL-10 says there are *no* model contractual clauses for the transfer to AWS
  us-east-1. The phrase matches the LPDP-12 keywords, so the obligation comes out *partial* instead
  of *not met*. The gap is still reported, with the wrong size.
- **Retrieval is measured apart** from judgment, because if the right document never reaches the
  assessor no assessor can get it right: 5.34 did not get the data subject request log.

The expected verdicts were written by the same author as the documents and the catalog, so this is a
regression baseline, not an independent benchmark. `--min-accuracy` turns it into a CI gate.
The method comes from Copiloto GRC, an earlier prototype whose keyword assessor scored 92 % on the
documents its keywords were written from and 12 % on a second company written with other words.

## Rules: testing operation without AI

Policies say things like "critical vulnerabilities are fixed in 7 days". Tranquera lets the policy
state that as a rule, and tests it against the Markdown tables already kept in the evidence records:

```yaml
# POL-08 front matter
rules:
  - id: REG-02
    control: "8.8"
    description: Critical vulnerabilities remediated in 7 days
    check: deadline
    evidence: EVD-03              # the evidence record that holds the table
    where: {Severidad: Crítica}   # rows to test (accent- and case-insensitive)
    start: Detectada
    end: Remediada                # empty = still open, aged until the assessment date
    max_days: 7
```

| Check | Tests | Typical use |
| --- | --- | --- |
| `threshold` | a metric in the evidence front matter against `min` / `max` | training completion, MFA coverage, backup success rate |
| `deadline` | every matching row closed within `max_days` | vulnerability SLAs, incident response, access request approval |
| `required` | every matching row has an accepted value in a column | post mortems, approvals, risk acceptance sign-off |
| `absent` | keys from one table must not appear in another | leavers vs. active accounts, retired assets vs. inventory |

A failed rule becomes a finding that lists the failing rows and caps the control at *partial*. A rule
that cannot be evaluated (missing table, column or record) is reported as a finding too, never ignored.
Full reference: [docs/document-format.md](docs/document-format.md#rules).

## How it works

```mermaid
flowchart LR
  A[scope.yaml + Markdown docs] --> B[Chunking]
  B --> C[Retrieval<br/>BM25 + control tags]
  A --> D[Deterministic checks<br/>hygiene · SoA · reconciliation]
  C --> E{Assessor}
  E -->|deterministic| F[Coverage rules]
  E -->|claude| G[Structured verdict<br/>+ citation verification]
  F --> H[Verdict caps]
  G --> H
  D --> H
  A --> R[Policy rules<br/>threshold · deadline · required · absent]
  R --> H
  H --> I[Findings · patterns · NIST roll-up]
  I --> J[HTML · CSV register · SoA · JSON]
```

1. **Ingest** — documents are split by headings; front matter gives type, owner, status, review date,
   control tags, `supersedes`, commitments and execution dates.
2. **Retrieve** — for each control, the most relevant chunks by BM25 over Spanish and English
   keywords, boosted when the document is tagged with the control.
3. **Check** — review dates, owners, drafts, superseded documents, SoA justifications,
   commitment-by-period reconciliation and policy rules tested against evidence tables.
4. **Assess** — deterministic coverage rules, or (optionally) Claude with a forced structured answer
   (`met / partial / not_met / undetermined`, rationale, verbatim citations, gaps, contradictions,
   one corrective action: add, fix or remove).
5. **Cap and register** — verdicts are capped by deterministic findings; each gap becomes a finding
   with severity (from control criticality), action, owner and due date (30/90/180 days).
6. **Roll up** — Annex A results map onto NIST CSF 2.0 subcategories ([details](docs/mapping.md)).

Document format: [docs/document-format.md](docs/document-format.md).

## Limitations

- Annex A and Ley 25.326 only. Clauses 4 to 10 (risk assessment, internal audit, management review) are not
  assessed yet, so many CSF *Govern* subcategories show as "not mapped".
- The deterministic assessor judges coverage, and rules test only what a policy states as a rule.
  Content quality (is this policy any good?) still needs an auditor or the optional Claude review.
- Claude mode is covered by tests with a fake client; results from a live model still need an
  auditor's review. It supports professional judgment, it does not replace it.
- The ISO ↔ NIST mapping is the author's, indicative, not NIST's official informative reference.
- The Ley 25.326 pack summarizes six obligations; it is not legal advice and does not cover every
  article or AAIP resolution. Business days skip weekends but not Argentine public holidays.

## Copyright and data

ISO/IEC 27001 is copyrighted by ISO/IEC: this repository contains only control identifiers and
short titles written in the author's own words. NIST CSF 2.0 is a U.S. Government work. Ley 25.326 is cited by article with summaries
written by the author. All company
data in the demo is invented.

## Roadmap

- [x] Policy rules tested against evidence tables (0.2)
- [x] Ley 25.326 obligations pack and accuracy against expected verdicts (0.3)
- [ ] A second fictitious company, written without looking at the catalog, for a clean measurement
- [ ] Rules that cap every control their evidence bears on (5.16 and 6.5 next to 5.18)
- [ ] CSV evidence (exports from Jira, the IdP or the scanner) next to Markdown tables
- [ ] Clauses 4–10 as assessable requirements
- [ ] Ingest PDF and DOCX policies
- [ ] BCRA communications for payment service providers
- [ ] Questionnaire mode: answer vendor security questionnaires from the same evidence

## License

MIT. Built by Renzo Di Guglielmo ([LinkedIn](https://www.linkedin.com/in/renzo-di-guglielmo-ciberseguridad-redes/)).
