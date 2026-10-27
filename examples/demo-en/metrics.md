# Accuracy against the expected verdicts · `heuristic`

- **Controls compared:** 42
- **Verdict accuracy:** 88%
- **Gaps detected:** 92% of the controls with a real gap
- **False 'met' (a real gap reported as met):** 3
- **Controls that are met but were flagged with a gap:** 0
- **Evidence retrieval:** 98% of the documents holding the answer reached the assessor

## Confusion matrix (rows: expected · columns: obtained)

| | Met | Partial | Not met |
| --- | ---: | ---: | ---: |
| **Met** | 5 | 0 | 0 |
| **Partial** | 3 | 26 | 0 |
| **Not met** | 0 | 2 | 6 |

## Differences

| Controls | Expected | Obtained | Why it was expected |
| --- | --- | --- | --- |
| 5.16 | Partial | Met | POL-02 §2 exige baja en 24 h, pero EVD-10 muestra cuentas de exempleados activas. |
| 5.30 | Not met | Partial | No hay plan de continuidad TIC; solo RTO/RPO de una base en POL-04. |
| 6.5 | Partial | Met | POL-02 exige baja en 24 h y EVD-09/EVD-10 muestran tres exempleados activos. |
| 8.2 | Partial | Met | POL-02 §4 está bien, pero EVD-01 encontró 3 cuentas de exempleados activas en la consola de AWS de producción. |
| LPDP-12 | Not met | Partial | Datos en AWS us-east-1 y POL-10 §6 admite que no hay garantías. La frase «cláusulas contractuales modelo» está negada (trampa). |

## Documents retrieval did not bring

| Controls | Missing |
| --- | --- |
| 5.34 | EVD-11 |
