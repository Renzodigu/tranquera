# Example outputs

Generated with `tranquera evaluate` (Spanish) and `tranquera evaluate --lang en` on the fictitious company
Ñandú Pagos S.A., deterministic assessor (no AI), as of 2026-10-20. Regenerate with:

```bash
tranquera evaluate --out examples/demo-es
tranquera evaluate --lang en --out examples/demo-en
```

| File | Content |
| --- | --- |
| `report.html` | Executive report: KPIs, coverage by theme and CSF function, patterns, reconciliation, rule tests, register, control detail, SoA |
| `findings-register.csv` | One row per finding: severity, root cause, controls, action (add / fix / remove), owner, due date, status |
| `statement-of-applicability.csv` | Every Annex A control with applicability, justification, status and NIST mapping |
| `results.json` | Full machine-readable result |
| `metrics.md` | Accuracy against the demo's expected verdicts: confusion matrix, false *met*, missed retrieval |
