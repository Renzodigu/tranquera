---
id: POL-05
title: Política de Seguridad con Proveedores
type: policy
owner: ""
version: "1.0"
status: aprobado
approved: 2026-01-20
next_review: 2027-01-20
controls: ["5.19", "5.20", "5.21", "5.22", "5.23"]
commitments:
  - id: COM-05
    control: "5.22"
    activity: Revisión anual de seguridad de proveedores críticos
    frequency: annual
    evidence: EVD-06
---
# Política de Seguridad con Proveedores

## 1. Clasificación de proveedores
Los proveedores se clasifican como críticos, importantes o estándar según el acceso a datos de clientes y su impacto en la operación.

## 2. Evaluación previa
Antes de contratar un proveedor crítico se completa un cuestionario de seguridad y se solicita su informe SOC 2 tipo II o certificación ISO 27001 vigente.

## 3. Contratos
Los contratos con proveedores críticos incluyen cláusulas de confidencialidad, notificación de incidentes en 48 horas, derecho de auditoría y devolución o destrucción de datos al finalizar.

## 4. Servicios en la nube
AWS es el proveedor de nube principal. El modelo de responsabilidad compartida está documentado y el equipo de Plataforma es responsable de la configuración de las cuentas.

## 5. Seguimiento
Los proveedores críticos se revisan una vez por año.
