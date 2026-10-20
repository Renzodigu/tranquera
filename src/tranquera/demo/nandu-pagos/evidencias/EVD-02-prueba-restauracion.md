---
id: EVD-02
title: Informe de prueba de restauración de base de datos
type: evidence
owner: Diego Albornoz (CTO)
controls: ["8.13"]
executions: [2025-11-18]
---
# Prueba de restauración — 18/11/2025

- **Alcance:** base de datos transaccional, snapshot del 17/11/2025.
- **Entorno:** cuenta aislada de recuperación.
- **Resultado:** restauración completa en 3 horas 10 minutos. Integridad verificada con sumas de control sobre las tablas de transacciones.
- **Desvío:** ninguno respecto al RTO de 4 horas.
- **Próxima prueba:** febrero 2026.
