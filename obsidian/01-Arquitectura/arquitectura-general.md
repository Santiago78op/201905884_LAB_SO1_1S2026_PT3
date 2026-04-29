---
title: Arquitectura General — M.U.M.N.K8s
created: 2026-04-05
updated: 2026-04-05
tags: [arquitectura, gke, kubernetes]
status: activo
---

# Arquitectura General

## Diagrama de Flujo

```
[Locust]
   │ POST /grpc-#carnet  (JSON: country, warplanes_in_air, warships_in_water, timestamp)
   ▼
[Kubernetes Gateway API]   ← exposición pública del clúster (reemplaza Ingress)
   │
   ▼
[Rust REST API]            ← Deployment, HPA 1–3 réplicas (CPU > 30%)
   │ gRPC
   ▼
[Go Deployment 1]          ← API REST receiver + gRPC Client (HPA 1–3 réplicas)
   │ gRPC (WarReportService.SendReport)
   ▼
[Go Deployments 2 & 3]     ← gRPC Server + RabbitMQ Writer (1–2 réplicas para análisis)
   │ AMQP
   ▼
[RabbitMQ]                 ← broker de mensajería principal
   │ consume
   ▼
[Go Consumer]              ← Deployment, procesa y almacena
   │
   ▼
[Valkey]  ←── KubeVirt VM1 (dentro del clúster GKE)
               ↑
[Grafana] ←── KubeVirt VM2 (dentro del clúster GKE, VM independiente)

[Zot Registry] ←── VM en GCP FUERA del clúster (todas las imágenes Docker)
```

## Componentes y Roles

| Componente | Tecnología | Rol | Réplicas |
|---|---|---|---|
| Locust | Python | Generador de tráfico → Gateway | N/A |
| Gateway API | K8s Gateway API | Exposición pública, enrutamiento | N/A |
| Rust REST API | Rust (Actix/Axum) | Recibe de Locust, reenvía a Go Dep 1 | 1–3 (HPA) |
| Go Deployment 1 | Go | REST receiver + gRPC Client | 1–3 (HPA) |
| Go Deployment 2 | Go | gRPC Server + RabbitMQ Writer | 1–2 |
| Go Deployment 3 | Go | gRPC Server + RabbitMQ Writer | 1–2 |
| RabbitMQ | RabbitMQ | Broker principal de mensajería | 1 |
| Go Consumer | Go | Consume RabbitMQ → escribe en Valkey | 1–2 |
| Valkey | Valkey (Redis) | Almacenamiento procesado, fuente Grafana | KubeVirt VM1 |
| Grafana | Grafana | Visualización de dashboards | KubeVirt VM2 |
| Zot | Zot | Container Registry (OCI) | VM GCP ext. |

## Infraestructura GCP

- **GKE**: Clúster con instancias **N1**
- **KubeVirt**: Instalado dentro del clúster GKE para correr VMs
  - VM1: Valkey (dedicada a almacenamiento)
  - VM2: Grafana (dedicada a visualización)
- **Zot VM**: VM de GCP **fuera del clúster**, almacena todas las imágenes Docker como OCI artifacts

## Namespaces sugeridos

- `military-pipeline` — Rust, Go deployments
- `messaging` — RabbitMQ, Consumer
- `monitoring` — referencias a VMs KubeVirt

## Estado del Sistema (2026-04-29 sesión 14)

Todo el pipeline E2E está RUNNING. Gateway IP: `34.102.175.55`.
- Locust instalado (pipx v2.43.4) — corre desde máquina local contra Gateway
- HPA verificado: CPU 15%→43% con 200 usuarios, réplicas 1→2
- 11 paneles Grafana creados — ver `dashboards-grafana.md` para estado detallado
- Locust rangos en ajuste (evitar min=0)
- Pendiente: fixes Grafana + evidencia final + entrega (deadline 30/04/2026)

## Conexiones

- [[flujo-de-datos]]
- [[decisiones-tecnicas]]
- [[contratos-grpc]]
- [[deployment-k8s]]
- [[kubevirt]]
- [[zot]]
- [[proyecto-enunciado]]
