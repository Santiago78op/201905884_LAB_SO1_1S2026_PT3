---
title: Dockerfiles — M.U.M.N.K8s
created: 2026-04-27
updated: 2026-04-27
tags: [docker, build, multi-stage, infraestructura]
status: completo
---

# Dockerfiles del Proyecto

Todos los servicios usan **multi-stage builds** para minimizar el tamaño de imagen final.

## Patrón Go (3 servicios)

Los servicios Go tienen una dependencia local (`proto/`) referenciada con `replace` en `go.mod`. Por eso el build context debe ser la **raíz del repo**, no el directorio del servicio.

```
docker build -f Dockerfile.go-client -t go-client:latest .
docker build -f Dockerfile.go-server -t go-server:latest .
docker build -f Dockerfile.go-consumer -t go-consumer:latest .
```

**Estructura del Dockerfile Go:**
- Etapa builder: `golang:1.26.2`
  - COPY proto/ y el servicio como hermanos en `/app/`
  - WORKDIR al directorio del servicio
  - `go mod download` + `go build -o <bin> ./cmd/app/`
- Etapa runtime: `alpine:3.21`
  - Copia solo el binario desde builder
  - CMD ejecuta el binario

| Dockerfile | Servicio | Binario |
|---|---|---|
| `Dockerfile.go-client` | `go-api-grpc-client` | `go-client` |
| `Dockerfile.go-server` | `go-grpc-server-writer` | `go-server` |
| `Dockerfile.go-consumer` | `go-rabbit-consumer` | `go-consumer` |

## Rust API

Sin dependencias locales externas — build context es `rust-api/`.

```
docker build -f rust-api/Dockerfile -t rust-api:latest rust-api/
```

**Estructura:**
- Etapa builder: `rust:1.95.0`
  - COPY . .
  - `cargo build --release`
  - Binario: `target/release/rust-api`
- Etapa runtime: `debian:bookworm-slim`
  - Razón: Rust linkea glibc dinámicamente; alpine usa musl (incompatible sin recompilación especial)
  - Copia solo el binario

## Configuración en runtime

Las variables de entorno (hosts de RabbitMQ, Valkey, etc.) NO van en el Dockerfile. Se inyectan en los Deployment YAMLs de Kubernetes:

```yaml
env:
  - name: RABBITMQ_HOST
    value: "rabbitmq"
```

## Conexiones

- [[arquitectura-general]]
- [[infra-gke]]
- [[zot-registry]]
