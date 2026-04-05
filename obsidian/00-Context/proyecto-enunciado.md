---
title: Proyecto #3 - M.U.M.N.K8s
created: 2026-04-05
updated: 2026-04-05
tags: [proyecto, contexto, mumk8s]
status: activo
---

# M.U.M.N.K8s — Monitoreo de Unidades Militares en la Nube con Kubernetes

**Curso:** Sistemas Operativos 1 — FIUSAC, Universidad San Carlos de Guatemala
**Ponderación:** 50 pts | **Tiempo estimado:** 60 hrs
**Entrega:** 30/04/2026 | **Calificación:** 02/05/2026 – 04/05/2026

## Objetivo

Implementar una arquitectura de sistema distribuido y escalable en GCP que procese reportes militares en tiempo real usando GKE, Rust, Go, RabbitMQ, Valkey y Grafana. El sistema debe soportar alta carga mediante HPA (1-3 réplicas, CPU > 30%) y visualizar el 100% de las métricas requeridas en Grafana.

## Descripción del Problema

Simular un escenario de monitoreo bélico donde se generan reportes militares continuamente desde distintos países. Cada reporte representa el estado parcial de recursos bélicos (aviones en el aire, barcos en el mar, país de origen, timestamp).

## Payload JSON (estructura exacta del proyecto)

```json
{
  "country": "ESP",
  "warplanes_in_air": 42,
  "warships_in_water": 14,
  "timestamp": "2026-03-12T20:15:30Z"
}
```

**Rangos:** `warplanes_in_air`: 0–50 | `warships_in_water`: 0–30
**Países válidos (enum proto):** usa=1, rus=2, chn=3, esp=4, gtm=5

## País Asignado (último dígito del carnet)

| Dígito | País |
|--------|------|
| 0, 1   | USA  |
| 2, 3   | RUS  |
| 4, 5   | CHN  |
| 6, 7   | ESP  |
| 8, 9   | GTM  |

## Rutas Gateway API

- `/grpc-#carnet` → flujo principal (obligatorio)
- `/dapr-#carnet` → flujo alternativo con Dapr (opcional / punteo extra en clase magistral, solo si nota >= 90)

## Entregables

1. Código en GitHub privado — **misma repo del Proyecto 1**, carpeta `proyecto3`
   - Colaboradores: `@roldyoran`, `@JoseLorenzana272`, `@KINGR0X`
2. Manual técnico en **formato Markdown** dentro del repo (obligatorio para nota ≠ 0)
3. Capturas de prueba y evidencia funcional
4. Entrega en **UEDI** (obligatorio para nota ≠ 0)

## Requisitos Mínimos (sin estos = sin calificación)

- Clúster Kubernetes en GCP (GKE)
- Locust para generación de carga
- RabbitMQ como broker
- KubeVirt para Valkey y Grafana

## Penalizaciones sobre la nota final

| Elemento faltante         | Penalización |
|---------------------------|-------------|
| No usar GKE               | -80%        |
| No usar Grafana/KubeVirt  | -60%        |
| No usar RabbitMQ          | -30%        |
| No usar Valkey/KubeVirt   | -15%        |
| No usar Locust            | -10%        |
| No usar Zot               | -5%         |

## Distribución de Puntos

| Criterio                              | Pts |
|---------------------------------------|-----|
| Gateway API (Kubernetes)              | 5   |
| API REST en Rust (+ HPA)             | 5   |
| Servicios Go (gRPC Client + Server)   | 10  |
| Despliegue en Zot                     | 10  |
| RabbitMQ + Consumer                   | 15  |
| Valkey en KubeVirt                    | 20  |
| Grafana en KubeVirt                   | 25  |
| Pruebas de carga HPA (Locust)         | 5   |
| Manual técnico                        | 2   |
| Respuestas a preguntas                | 3   |
| **TOTAL**                             | **100** |

## Conexiones

- [[arquitectura-general]]
- [[flujo-de-datos]]
- [[contratos-grpc]]
- [[esquema-mensajes-rabbitmq]]
- [[dashboards-grafana]]
