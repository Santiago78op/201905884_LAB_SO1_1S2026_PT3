---
title: Deployments K8s — Plan de Manifiestos
created: 2026-04-27
updated: 2026-04-27
tags: [kubernetes, deployments, gke, manifiestos]
status: en-progreso
---

# Manifiestos Kubernetes — M.U.M.N.K8s

Carpeta real: `../../deployments/`

## Estado

Teoría iniciada (2026-04-27). YAMLs pendientes de escritura.

## Orden de implementación

1. **Namespaces** — base de todo lo demás
2. **RabbitMQ** — Deployment + Service (sin él, go-server no puede publicar)
3. **Go Services** — go-server, go-client, go-consumer (Deployments + Services)
4. **Rust API** — Deployment + Service + HPA
5. **Go Client HPA** — autoscaling
6. **Gateway API** — GatewayClass + Gateway + HTTPRoute
7. **KubeVirt VMs** — Valkey (VM1) + Grafana (VM2)

## Namespaces

- `military-pipeline` — Rust API, Go Client, Go Server
- `messaging` — RabbitMQ, Go Consumer

## HPA Targets

| Servicio | Min | Max | Trigger |
|---|---|---|---|
| Rust API | 1 | 3 | CPU > 30% |
| Go Client | 1 | 3 | CPU > 30% |
| Go Server | 1 | 2 | manual |
| Consumer | 1 | 2 | manual |

## Puertos de servicios

| Servicio | Puerto |
|---|---|
| go-client (HTTP) | 8080 |
| go-server (gRPC) | 50051 |
| RabbitMQ (AMQP) | 5672 |
| RabbitMQ (UI) | 15672 |
| Rust API (HTTP) | 8080 |

## Gateway API

- Ruta principal: `/grpc-201905884` → Rust API Service
- Recursos: GatewayClass + Gateway + HTTPRoute

## KubeVirt

- VM1: Valkey — redis-compatible, puerto 6379
- VM2: Grafana — dashboards, puerto 3000
- Ambas dentro del clúster GKE

## Conexiones

- [[arquitectura-general]]
- [[kubevirt]]
- [[gke]]
