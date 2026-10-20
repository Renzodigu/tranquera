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

The current period is never judged: a quarterly review can still happen before the quarter ends.
