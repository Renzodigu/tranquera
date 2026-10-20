# Example outputs

Generated with `tranquera demo` (Spanish) and `tranquera demo --lang en` on the fictitious company
Ñandú Pagos S.A., heuristic assessor, as of 2026-10-20. Regenerate with:

```bash
tranquera demo --out examples/demo-es
tranquera demo --lang en --out examples/demo-en
```

| File | Content |
| --- | --- |
| `report.html` | Executive report: KPIs, coverage by theme and CSF function, patterns, reconciliation, register, control detail, SoA |
| `findings-register.csv` | One row per finding: severity, root cause, controls, action (add / fix / remove), owner, due date, status |
| `statement-of-applicability.csv` | Every Annex A control with applicability, justification, status and NIST mapping |
| `results.json` | Full machine-readable result |
