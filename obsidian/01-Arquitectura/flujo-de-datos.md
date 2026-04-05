---
title: Flujo de Datos Completo
created: 2026-04-05
updated: 2026-04-05
tags: [arquitectura, flujo, pipeline]
status: activo
---

# Flujo de Datos Completo

## Paso a Paso

### 1. Generación de Tráfico — Locust
- Locust genera peticiones HTTP POST al endpoint público del Kubernetes Gateway API
- Ruta: `/grpc-#carnet`
- Payload:
```json
{
  "country": "ESP",
  "warplanes_in_air": 42,
  "warships_in_water": 14,
  "timestamp": "2026-03-12T20:15:30Z"
}
```
- `warplanes_in_air`: aleatorio 0–50
- `warships_in_water`: aleatorio 0–30
- `country`: uno de usa, rus, chn, esp, gtm (basado en carnet para asignación del dashboard)

### 2. Enrutamiento — Kubernetes Gateway API
- Recurso `Gateway` + `HTTPRoute` exponen el sistema
- **NO se usa Ingress Controller** (reemplazado por Gateway API)
- Rutas configuradas:
  - `/grpc-#carnet` → Rust REST API
  - `/dapr-#carnet` → flujo Dapr (opcional)

### 3. Recepción y Reenvío — Rust REST API
- Recibe el JSON de Locust
- Escala automáticamente con HPA: 1–3 réplicas, umbral CPU > 30%
- Reenvía la información al **Go Deployment 1** (ya sea REST o gRPC interno)

### 4. Cliente gRPC — Go Deployment 1
- Actúa como API REST receiver (recibe de Rust) + gRPC Client
- Invoca `WarReportService.SendReport` en Go Deployment 2/3
- Escala con HPA: 1–3 réplicas

### 5. Servidor gRPC + Publicador RabbitMQ — Go Deployments 2 & 3
- Recibe el `WarReportRequest` por gRPC
- Publica el mensaje en RabbitMQ
  - Exchange: `warreport_exchange`
  - Routing key: `warreport.process`
- Se evalúa rendimiento con 1 y 2 réplicas

### 6. Broker — RabbitMQ
- Exchange: `warreport_exchange` (direct)
- Queue: `warreport_queue`
- Routing key: `warreport.process`
- Desacopla el escritor del consumidor

### 7. Consumidor — Go Consumer
- Deployment que consume mensajes de `warreport_queue`
- Procesa los datos y los almacena en **Valkey**
- Se analiza rendimiento con 1 y 2 réplicas

### 8. Almacenamiento — Valkey (KubeVirt VM1)
- Redis-compatible, desplegado dentro de una VM administrada por KubeVirt
- El Consumer se conecta a la VM a través de la red interna del clúster
- Configurar TTL/políticas de expiración para evitar saturación

### 9. Visualización — Grafana (KubeVirt VM2)
- VM independiente dentro del clúster, administrada por KubeVirt
- Se conecta a Valkey como fuente de datos
- Muestra el dashboard requerido

## Flujo Alternativo (Dapr — Opcional)

```
Locust → /dapr-#carnet → Go Dep 1 → [Dapr Sidecar] → Go Dep 2/3 → RabbitMQ → ...
```

Coexiste con el flujo principal para comparación de rendimiento.

## Conexiones

- [[arquitectura-general]]
- [[contratos-grpc]]
- [[esquema-mensajes-rabbitmq]]
- [[valkey]]
- [[dashboards-grafana]]
