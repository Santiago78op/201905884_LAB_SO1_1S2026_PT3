# Zot

Registro de imágenes OCI privado usado por servicios desplegados en [[GKE]].

---

## Configuración

| Parámetro | Valor |
|---|---|
| VM GCP | `zot-registry` |
| Zona | `us-central1-a` (independiente del clúster) |
| Machine type | `n1-standard-1` (x86_64) |
| IP | `34.68.174.65` |
| Puerto | `5000` (HTTP inseguro) |
| Imagen Docker | `ghcr.io/project-zot/zot-linux-amd64:latest` |

## Imágenes almacenadas (sesión 12 — 2026-04-28)

| Imagen | Arquitectura | Estado |
|---|---|---|
| `go-client:latest` | linux/amd64 | En Zot, compatible con n2-standard-4 |
| `go-server:latest` | linux/amd64 | En Zot, compatible con n2-standard-4 |
| `go-consumer:latest` | linux/amd64 | En Zot, compatible con n2-standard-4 |
| `rust-api:latest` | linux/amd64 | En Zot, compatible con n2-standard-4 |

Las imágenes son `linux/amd64` — compatibles directamente con los nodos `n2-standard-4` (x86/AMD64) activos desde sesión 12. No se requiere reconstruir.

## Consideración de arquitectura

Zot corre en una VM x86_64 (`n1-standard-1`, `us-central1-a`). Al haber migrado el clúster GKE de ARM64 (N4A) a AMD64 (N2), las imágenes existentes en Zot ya son del tipo correcto — no se necesita reconstrucción.

## Comandos

```bash
# Verificar contenido
curl http://34.68.174.65:5000/v2/_catalog

# Push de imagen AMD64 (formato usado en el proyecto)
docker build -f rust-api/Dockerfile \
  -t 34.68.174.65:5000/rust-api:latest rust-api/
docker push 34.68.174.65:5000/rust-api:latest
```

## Ver también

- [[gke]] — clúster que consume las imágenes
- [[deployments/setup-guide.md]] — Paso 6 y 7 con comandos completos
