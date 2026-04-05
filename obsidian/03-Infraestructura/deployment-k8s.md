---
title: Deployments Kubernetes — M.U.M.N.K8s
created: 2026-04-05
updated: 2026-04-05
tags: [kubernetes, deployment, gke, hpa]
status: activo
---

# Deployments Kubernetes

## Resumen de Deployments

| Deployment | Réplicas | HPA | Notas |
|---|---|---|---|
| Rust REST API | 1–3 | Sí (CPU > 30%) | Recibe de Gateway API |
| Go Deployment 1 | 1–3 | Sí (CPU > 30%) | REST receiver + gRPC Client |
| Go Deployment 2 | 1–2 | No (análisis manual) | gRPC Server + RabbitMQ Writer |
| Go Deployment 3 | 1–2 | No (análisis manual) | gRPC Server + RabbitMQ Writer |
| RabbitMQ | 1 | No | Broker central |
| Go Consumer | 1–2 | No (análisis manual) | Consume RabbitMQ → Valkey |
| Valkey | VM (KubeVirt) | N/A | Dentro del clúster, VM1 |
| Grafana | VM (KubeVirt) | N/A | Dentro del clúster, VM2 |

## Gateway API

```yaml
# GatewayClass + Gateway + HTTPRoute
# Rutas:
#   /grpc-{CARNET}  → Rust REST API service
#   /dapr-{CARNET}  → Go Dep 1 (flujo Dapr, opcional)
```

**Importante:** Usar `GatewayClass`, `Gateway`, y `HTTPRoute` — NO `Ingress`.

## HPA para Rust

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: rust-api-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: rust-api
  minReplicas: 1
  maxReplicas: 3
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 30
```

## Namespaces

- `military-pipeline` — Rust, Go deployments
- `messaging` — RabbitMQ, Consumer
- (Valkey y Grafana viven como VMs KubeVirt dentro del clúster)

## Zot (fuera del clúster)

- VM de GCP separada, no dentro del clúster K8s
- Todas las imágenes Docker se publican en Zot antes de deployar
- Los manifests K8s referencian la URL del registry Zot
- Se publica también un OCI Artifact (archivo de configuración)

## Buenas Prácticas

- Definir `resources.requests` y `resources.limits` en todos los containers
- Usar variables de entorno para IPs, credenciales, puertos
- Imágenes con tags específicos (nunca `latest`)
- Builds multi-stage en Docker para reducir tamaño

## Análisis de Rendimiento Requerido

Documentar y comparar:
1. Go Deployment 2/3 con **1 réplica** vs **2 réplicas**
2. Consumer con **1 réplica** vs **2 réplicas**
3. Locust como generador de carga con métricas de latencia y throughput

## Conexiones

- [[arquitectura-general]]
- [[gke]]
- [[kubevirt]]
- [[zot]]
- [[decisiones-tecnicas]]
