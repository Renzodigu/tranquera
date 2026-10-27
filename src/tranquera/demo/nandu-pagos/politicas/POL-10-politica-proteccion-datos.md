---
id: POL-10
title: Política de Protección de Datos Personales
type: policy
owner: Carla Medina (Legales y Privacidad)
version: "1.0"
status: aprobado
approved: 2026-03-03
next_review: 2027-03-03
controls: ["5.34", "LPDP-04", "LPDP-05", "LPDP-09", "LPDP-14"]
rules:
  - id: REG-06
    control: LPDP-14
    description: Pedidos de acceso respondidos en 10 días corridos (Ley 25.326, art. 14)
    check: deadline
    evidence: EVD-11
    where: {Tipo: Acceso}
    start: Recibido
    end: Respondido
    max_days: 10
  - id: REG-07
    control: LPDP-14
    description: Rectificación y supresión resueltas en 5 días hábiles (Ley 25.326, art. 16)
    check: deadline
    evidence: EVD-11
    where: {Tipo: [Rectificación, Supresión]}
    start: Recibido
    end: Respondido
    max_days: 5
    business_days: true
---
# Política de Protección de Datos Personales

## 1. Objetivo
Establecer cómo Ñandú Pagos trata los datos personales de clientes, comercios y empleados, en el marco de la Ley 25.326 de Protección de los Datos Personales.

## 2. Datos que tratamos
Tratamos datos de identificación (nombre, DNI, CUIT/CUIL), de contacto y de las operaciones de la billetera. Solo se piden los datos necesarios para abrir y operar la cuenta: no se recolectan datos excesivos para esa finalidad. Los datos de clientes dados de baja se eliminan o anonimizan al vencer el plazo legal de conservación.

## 3. Consentimiento e información al titular
Al registrarse en la aplicación, el cliente acepta la política de privacidad, que le informa la finalidad del tratamiento, quiénes pueden recibir sus datos y cómo ejercer sus derechos. El consentimiento queda registrado con fecha y hora.

## 4. Derechos de los titulares
Los titulares pueden pedir acceso, rectificación o supresión de sus datos escribiendo a privacidad@nandupagos.example. Los pedidos de acceso se responden en 10 días corridos y los de rectificación o supresión en 5 días hábiles. Cada pedido queda en el registro de solicitudes de titulares (EVD-11).

## 5. Seguridad y confidencialidad
Las bases de datos con datos personales se cifran en reposo y el acceso se rige por la POL-02. Todo el personal firma un acuerdo de confidencialidad al ingresar, que sigue vigente después de la desvinculación.

## 6. Dónde se alojan los datos
La plataforma corre en AWS, región us-east-1 (Estados Unidos). Todavía no se analizó si esa transferencia cumple el artículo 12 de la ley y no hay cláusulas contractuales modelo firmadas con el proveedor.
