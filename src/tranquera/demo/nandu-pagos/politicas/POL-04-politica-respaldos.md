---
id: POL-04
title: Política de Respaldos y Recuperación
type: policy
owner: Diego Albornoz (CTO)
version: "2.0"
status: aprobado
approved: 2025-11-03
next_review: 2026-11-03
controls: ["8.13", "8.14"]
commitments:
  - id: COM-04
    control: "8.13"
    activity: Prueba trimestral de restauración de la base de datos transaccional
    frequency: quarterly
    evidence: EVD-02
---
# Política de Respaldos y Recuperación

## 1. Respaldos
- Las bases de datos de producción se respaldan automáticamente todos los días mediante snapshots cifrados con claves de KMS.
- Los respaldos se retienen 35 días y se replican en una segunda región de AWS.
- El acceso a los respaldos está restringido al equipo de Plataforma.

## 2. Redundancia
La base de datos transaccional opera en modo multi zona con conmutación automática (failover).

## 3. Pruebas de restauración
Cada trimestre se restaura la base de datos transaccional en un entorno aislado para verificar la integridad de los datos y el tiempo de recuperación. El objetivo de tiempo de recuperación (RTO) es de 4 horas y el de punto de recuperación (RPO) es de 24 horas.
