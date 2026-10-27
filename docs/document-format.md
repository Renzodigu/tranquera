# Document format

Tranquera reads a folder that contains a `scope.yaml` file and any number of Markdown documents
(subfolders are fine). Each document starts with YAML front matter.

## `scope.yaml` — Statement of Applicability

```yaml
company: Ñandú Pagos S.A.
description: One line about the organization (sent to Claude as context).
as_of: 2026-10-20          # optional; default for --as-of
exclusions:                # Annex A controls out of scope
  - control: "7.11"
    justification: No own data center; utilities are the cloud provider's responsibility.
```

An exclusion without a justification is reported as a finding.

## Policies and procedures

```yaml
---
id: POL-02                  # unique id, used in citations and findings
title: Access Control Policy
type: policy                # policy | procedure
owner: Lucía Ferreyra (CISO)
version: "2.1"
status: aprobado            # aprobado/approved | borrador/draft | obsoleto/obsolete
approved: 2026-03-10
next_review: 2027-03-10
controls: ["5.15", "5.18"]  # optional hint: Annex A controls this document covers
supersedes: [POL-09]        # optional: documents this one replaces
commitments:                # optional: periodic activities the policy promises
  - id: COM-02
    control: "5.18"
    activity: Quarterly review of access rights to critical systems
    frequency: quarterly    # monthly | quarterly | semiannual | annual
    evidence: EVD-01        # id of the evidence record that proves each execution
---
```

## Evidence and records

```yaml
---
id: EVD-01
title: Access review log
type: evidence              # evidence | record
owner: Lucía Ferreyra (CISO)
controls: ["5.18"]          # evidence must be linked to the controls it proves
executions: [2026-02-12]    # one date per execution of the committed activity
---
```

## What the deterministic checks do with this

| Check | Rule | Action |
| --- | --- | --- |
| Review overdue | policy `next_review` is before the assessment date | Fix |
| No owner | policy `owner` is empty | Fix |
| Draft | policy `status` is a draft | Fix |
| Obsolete document | another approved document `supersedes` it and it is not marked obsolete | Remove |
| Unjustified exclusion | SoA exclusion without `justification` | Fix |
| Missing evidence record | a commitment points to an evidence id that does not exist | Add |
| Commitment missed | a complete calendar period (month, quarter, half) has no execution; for annual activities, nothing in the last 365 days | Fix |
| Rule not met | a policy rule fails against its evidence (see below) | Fix |
| Rule cannot be verified | the evidence, table, column or metric a rule needs does not exist | Fix |

The current period is never judged: a quarterly review can still happen before the quarter ends.

## Rules

A policy can declare `rules`: testable requirements checked against its evidence. Evidence keeps its
data in ordinary Markdown tables (any table in the body; `table:` picks one by heading text) or in a
`metrics` map in its front matter. Column names and values are compared without case or accents, so
`Crítica`, `critica` and `CRITICA` match. Dates can be `YYYY-MM-DD` or `DD/MM/YYYY`. The first column
identifies each row in the findings unless `key:` names another one.

```yaml
rules:
  - id: REG-01                     # threshold: a metric against a target
    control: "6.3"
    description: At least 95 % of staff complete the annual training
    check: threshold
    evidence: EVD-04               # EVD-04 front matter has: metrics: {completion_rate: 62}
    metric: completion_rate
    min: 95                        # and/or max:

  - id: REG-02                     # deadline: rows closed within N days
    control: "8.8"
    check: deadline
    evidence: EVD-03
    where: {Severidad: Crítica}    # a value or a list of accepted values per column
    start: Detectada
    end: Remediada                 # optional; an empty cell means open, aged until the assessment date
    max_days: 7

  - id: REG-03                     # required: rows must have an accepted value
    control: "5.27"
    check: required
    evidence: EVD-07
    where: {Severidad: [Alta, Crítica], Estado: Cerrado}
    column: Post mortem
    expect: [Sí]                   # optional; without it, empty, "-" and "no" fail

  - id: REG-04                     # absent: keys from one table missing from another
    control: "5.18"
    check: absent
    evidence: EVD-09               # leavers
    column: Usuario
    date: Fecha de baja            # optional: only rows older than grace_days are tested
    grace_days: 1
    against: EVD-10                # identity provider export
    against_column: Usuario
    against_where: {Estado: Activa}
```

A failed rule caps its control at *partial* and produces a finding with root cause *control operates
outside what the policy requires*, listing up to six failing rows.
