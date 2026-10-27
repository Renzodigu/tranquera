---
id: POL-03
title: Política de Gestión de Incidentes de Seguridad
type: policy
owner: Martín Quiroga (Líder de Operaciones de Seguridad)
version: "1.2"
status: aprobado
approved: 2024-03-01
next_review: 2025-03-01
controls: ["5.5", "5.24", "5.25", "5.26", "5.27", "5.28", "6.8"]
commitments:
  - id: COM-03
    control: "5.24"
    activity: Simulacro anual de respuesta a incidentes (ejercicio de mesa)
    frequency: annual
    evidence: EVD-05
rules:
  - id: REG-03
    control: "5.27"
    description: Todo incidente de severidad alta o crítica cerrado tiene post mortem
    check: required
    evidence: EVD-07
    where: {Severidad: [Alta, Crítica], Estado: Cerrado}
    column: Post mortem
    expect: [Sí]
---
# Política de Gestión de Incidentes de Seguridad

## 1. Reporte
Cualquier persona que detecte un evento de seguridad lo reporta en el canal #seguridad o por correo a seguridad@nandupagos.example. El equipo de Operaciones de Seguridad confirma la recepción en menos de una hora hábil.

## 2. Clasificación
Los eventos se evalúan y, si corresponde, se declaran incidentes con severidad baja, media, alta o crítica según el impacto en clientes, datos personales y disponibilidad de la plataforma.

## 3. Respuesta
El líder de Operaciones de Seguridad coordina la contención, erradicación y recuperación. Los incidentes de severidad alta o crítica se escalan al CISO y al CTO de inmediato.

## 4. Notificación
Legales evalúa la obligación de notificar a reguladores, a la autoridad de protección de datos y a los clientes afectados.

## 5. Evidencia
Durante la respuesta se preservan los registros y la evidencia relevante, documentando quién accedió a ella.

## 6. Lecciones aprendidas
Cada incidente de severidad alta o crítica termina con un análisis post mortem dentro de los 10 días hábiles, con causa raíz y acciones de mejora.

## 7. Simulacros
Una vez por año se realiza un ejercicio de mesa con los equipos de Operaciones de Seguridad, Ingeniería, Legales y Atención al Cliente.
