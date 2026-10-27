# Exactitud contra los veredictos esperados · `heuristic`

- **Controles comparados:** 42
- **Exactitud del veredicto:** 88%
- **Brechas detectadas:** 92% de los controles con brecha real
- **Falsos «cumple» (brecha real dada por cumplida):** 3
- **Controles que cumplen y se marcaron con brecha:** 0
- **Búsqueda de evidencia:** 98% de los documentos con la respuesta llegaron al evaluador

## Matriz de confusión (filas: esperado · columnas: obtenido)

| | Cumple | Parcial | No cumple |
| --- | ---: | ---: | ---: |
| **Cumple** | 5 | 0 | 0 |
| **Parcial** | 3 | 26 | 0 |
| **No cumple** | 0 | 2 | 6 |

## Diferencias

| Controles | Esperado | Obtenido | Por qué se esperaba |
| --- | --- | --- | --- |
| 5.16 | Parcial | Cumple | POL-02 §2 exige baja en 24 h, pero EVD-10 muestra cuentas de exempleados activas. |
| 5.30 | No cumple | Parcial | No hay plan de continuidad TIC; solo RTO/RPO de una base en POL-04. |
| 6.5 | Parcial | Cumple | POL-02 exige baja en 24 h y EVD-09/EVD-10 muestran tres exempleados activos. |
| 8.2 | Parcial | Cumple | POL-02 §4 está bien, pero EVD-01 encontró 3 cuentas de exempleados activas en la consola de AWS de producción. |
| LPDP-12 | No cumple | Parcial | Datos en AWS us-east-1 y POL-10 §6 admite que no hay garantías. La frase «cláusulas contractuales modelo» está negada (trampa). |

## Documentos que la búsqueda no trajo

| Controles | Faltó |
| --- | --- |
| 5.34 | EVD-11 |
