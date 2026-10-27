---
id: POL-02
title: Política de Control de Acceso
type: policy
owner: Lucía Ferreyra (CISO)
version: "2.1"
status: aprobado
approved: 2026-03-10
next_review: 2027-03-10
controls: ["5.15", "5.16", "5.17", "5.18", "6.5", "8.2", "8.3", "8.5"]
supersedes: [POL-09]
commitments:
  - id: COM-02
    control: "5.18"
    activity: Revisión trimestral de los derechos de acceso a sistemas críticos
    frequency: quarterly
    evidence: EVD-01
rules:
  - id: REG-04
    control: "5.18"
    description: Las cuentas de personas desvinculadas se dan de baja dentro de las 24 horas
    check: absent
    evidence: EVD-09
    column: Usuario
    date: Fecha de baja
    grace_days: 1
    against: EVD-10
    against_column: Usuario
    against_where: {Estado: Activa}
---
# Política de Control de Acceso

## 1. Principios
El acceso a la información se otorga según el mínimo privilegio y la necesidad de saber. Los permisos se asignan por rol (RBAC) y cada rol tiene un responsable que lo aprueba.

## 2. Gestión de identidades
- Cada persona tiene un identificador único; no se permiten cuentas compartidas.
- El alta de usuarios se solicita por ticket y la aprueba el responsable del sistema.
- Ante una desvinculación, Recursos Humanos avisa el mismo día y Sistemas da de baja todos los accesos dentro de las 24 horas.

## 3. Autenticación
- Se usa inicio de sesión único (SSO) con autenticación multifactor (MFA) obligatoria para todo el personal y para todos los accesos a la consola de AWS.
- Las contraseñas tienen al menos 14 caracteres, se guardan en el gestor de contraseñas corporativo y no se rotan periódicamente salvo sospecha de compromiso.

## 4. Accesos privilegiados
Las cuentas de administrador son nominales, se usan solo para tareas administrativas y requieren MFA con llave física. El acceso a producción se otorga por tiempo limitado mediante solicitud aprobada.

## 5. Revisión de accesos
Los responsables de los sistemas críticos revisan los derechos de acceso cada trimestre. Las cuentas sin uso o sin justificación se eliminan en un plazo de 10 días hábiles desde la revisión.

## 6. Documentos reemplazados
Esta política reemplaza a la Política de Contraseñas de 2019 (POL-09).
