---
id: POL-06
title: Política de Desarrollo Seguro
type: policy
owner: Diego Albornoz (CTO)
version: "0.3"
status: borrador
approved: null
next_review: null
controls: ["8.4", "8.25", "8.26", "8.28", "8.29", "8.31", "8.32", "8.33"]
---
# Política de Desarrollo Seguro (BORRADOR)

## 1. Ciclo de vida
Todo cambio de código pasa por un pull request con al menos una revisión aprobada antes de fusionarse en la rama principal, que está protegida.

## 2. Análisis automático
El pipeline de integración continua ejecuta análisis estático (SAST) y análisis de dependencias. Los hallazgos críticos bloquean el despliegue.

## 3. Entornos
Desarrollo, staging y producción están en cuentas de AWS separadas. Está prohibido usar datos productivos en desarrollo o staging.

## 4. Pruebas de penetración
Se realiza un test de penetración externo antes de cada lanzamiento mayor.

## 5. Gestión de cambios
Los despliegues a producción requieren la aprobación del líder técnico y quedan registrados en el sistema de tickets.
