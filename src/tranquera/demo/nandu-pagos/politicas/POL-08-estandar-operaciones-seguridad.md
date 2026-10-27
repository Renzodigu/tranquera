---
id: POL-08
title: Estándar de Operaciones de Seguridad
type: procedure
owner: Martín Quiroga (Líder de Operaciones de Seguridad)
version: "1.4"
status: aprobado
approved: 2026-04-02
next_review: 2027-04-02
controls: ["8.1", "8.7", "8.8", "8.9", "8.15", "8.16", "8.20", "8.22", "8.24"]
commitments:
  - id: COM-06
    control: "8.8"
    activity: Escaneo mensual de vulnerabilidades de la infraestructura productiva
    frequency: monthly
    evidence: EVD-03
rules:
  - id: REG-02
    control: "8.8"
    description: Vulnerabilidades críticas remediadas en 7 días
    check: deadline
    evidence: EVD-03
    where: {Severidad: Crítica}
    start: Detectada
    end: Remediada
    max_days: 7
  - id: REG-05
    control: "8.8"
    description: Vulnerabilidades altas remediadas en 30 días
    check: deadline
    evidence: EVD-03
    where: {Severidad: Alta}
    start: Detectada
    end: Remediada
    max_days: 30
---
# Estándar de Operaciones de Seguridad

## 1. Dispositivos
Las notebooks corporativas se gestionan con MDM, tienen el disco cifrado, bloqueo de pantalla a los 5 minutos y EDR instalado.

## 2. Vulnerabilidades
La infraestructura productiva se escanea todos los meses. Plazos de remediación: críticas en 7 días, altas en 30 días, medias en 90 días.

## 3. Configuración
La infraestructura se define como código (Terraform) y se valida contra una línea base de configuración segura.

## 4. Registro y monitoreo
CloudTrail y los logs de aplicación se centralizan en el SIEM y se retienen 12 meses. Las alertas de severidad alta se atienden en menos de 30 minutos.

## 5. Redes
Producción está en una VPC propia con subredes privadas. Los grupos de seguridad siguen el principio de denegar por defecto.

## 6. Cifrado
Los datos en tránsito usan TLS 1.2 o superior. Los datos en reposo se cifran con claves administradas en KMS que rotan cada año.
