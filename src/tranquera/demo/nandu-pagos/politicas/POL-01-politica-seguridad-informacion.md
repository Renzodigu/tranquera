---
id: POL-01
title: Política de Seguridad de la Información
type: policy
owner: Lucía Ferreyra (CISO)
version: "3.0"
status: aprobado
approved: 2026-02-01
next_review: 2027-02-01
controls: ["5.1", "5.2", "5.4", "5.31", "5.36", "6.3", "6.4"]
commitments:
  - id: COM-01
    control: "6.3"
    activity: Capacitación anual de concientización en seguridad para todo el personal
    frequency: annual
    evidence: EVD-04
rules:
  - id: REG-01
    control: "6.3"
    description: Al menos el 95 % del personal completa la capacitación anual
    check: threshold
    evidence: EVD-04
    metric: completion_rate
    min: 95
---
# Política de Seguridad de la Información

## 1. Objetivo
Ñandú Pagos S.A. protege la confidencialidad, integridad y disponibilidad de la información de sus clientes y de la compañía. Esta política fue aprobada por el Directorio el 1 de febrero de 2026 y se revisa una vez al año o ante cambios significativos.

## 2. Alcance
Aplica a todo el personal, contratistas y proveedores con acceso a información o sistemas de la compañía, incluida la plataforma de billetera virtual alojada en AWS.

## 3. Roles y responsabilidades
- **Directorio:** aprueba esta política y asigna los recursos para el programa de seguridad.
- **CISO:** define el programa, mantiene el marco normativo interno y reporta trimestralmente al Comité de Seguridad.
- **Comité de Seguridad:** integrado por el CISO, el CTO, el responsable de Legales y el responsable de Operaciones. Se reúne cada trimestre.
- **Responsables de activos:** cada sistema tiene un responsable que aprueba los accesos y garantiza los controles.
- **Todo el personal:** cumple las políticas y reporta eventos de seguridad.

## 4. Requisitos legales y regulatorios
La compañía identifica y cumple los requisitos aplicables a un proveedor de servicios de pago, la normativa de protección de datos personales (Ley 25.326) y las obligaciones contractuales con clientes y entidades financieras. Legales mantiene un registro de requisitos que se revisa semestralmente.

## 5. Concientización y capacitación
Todo el personal realiza una capacitación anual de concientización en seguridad. La meta es que al menos el 95 % la complete cada año. Los ingresantes la completan durante su primer mes.

## 6. Cumplimiento y sanciones
El CISO verifica el cumplimiento de las políticas mediante revisiones periódicas. Los incumplimientos se tratan según el proceso disciplinario definido por Recursos Humanos. Las excepciones deben aprobarse por escrito y tienen un plazo máximo de seis meses.

## 7. Marco normativo interno
Esta política se complementa con las políticas específicas de control de acceso, gestión de incidentes, respaldos, proveedores, desarrollo seguro, clasificación de la información y el estándar de operaciones de seguridad.
