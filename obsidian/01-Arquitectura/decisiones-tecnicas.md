---
title: Decisiones Técnicas
created: 2026-04-05
updated: 2026-04-28
tags: [arquitectura, decisiones, tecnologia]
status: activo
---

# Decisiones Técnicas

## Stack Obligatorio

| Tecnología | Decisión | Justificación |
|---|---|---|
| **GKE** | Clúster con instancias `n2-standard-4` (x86/AMD64) en GCP | Requisito del proyecto (-80% sin GKE). N4A ARM64 descartado — GCP no expone FEAT_NV en ARM64, sin nested virt no hay /dev/kvm y KubeVirt no funciona. |
| **Kubernetes Gateway API** | Reemplaza Ingress Controller | Requisito explícito del enunciado |
| **Rust** | API REST (Actix-Web o Axum) | Alto rendimiento, manejo de alta concurrencia |
| **Go** | 3 Deployments (gRPC Client + 2x Server/Writer) | Concurrencia nativa, ecosistema gRPC maduro |
| **gRPC + Protocol Buffers** | Comunicación interna eficiente entre servicios Go | Tipado fuerte, serialización eficiente |
| **RabbitMQ** | Broker de mensajería principal | Desacopla procesamiento, garantiza entrega (-30% sin él) |
| **Valkey** | Almacenamiento en VM KubeVirt | Baja latencia, compatible Redis, KubeVirt obligatorio (-15%) |
| **Grafana** | Visualización en VM KubeVirt separada | Dashboards requeridos, KubeVirt obligatorio (-60%) |
| **Zot** | Container Registry en VM GCP externa | Todas las imágenes Docker deben pasar por Zot (-5%) |
| **Locust** | Generación de carga | Pruebas de rendimiento obligatorias (-10%) |
| **KubeVirt** | VMs dentro del clúster K8s | Para Valkey (VM1) y Grafana (VM2) |

## Decisiones de Escalado

- **HPA en Rust**: 1–3 réplicas, umbral CPU > 30%
- **HPA en Go Dep 1**: 1–3 réplicas
- **Go Dep 2 & 3**: análisis comparativo con 1 y 2 réplicas
- **Consumer**: análisis comparativo con 1 y 2 réplicas

## Decisión sobre Dapr (Opcional)

- Implementar SOLO si se obtiene >= 90 puntos en el resto del proyecto
- Ruta alternativa: `/dapr-#carnet`
- Coexiste con flujo principal para comparación de arquitecturas
- Punteo neto sobre la clase magistral, no sobre el proyecto

## OCI Artifact en Zot

- Se debe publicar al menos un archivo de entrada como OCI Artifact en Zot
- Documentar qué archivo se publica y cómo los deployments lo consumen al inicio

## Recomendaciones del Enunciado

- Usar `requests` y `limits` en todos los Deployments (estabilidad)
- Configurar TTL en Valkey para evitar saturación de memoria
- Usar namespaces para organización lógica

## Conexiones

- [[arquitectura-general]]
- [[deployment-k8s]]
- [[kubevirt]]
- [[zot]]
- [[proyecto-enunciado]]
