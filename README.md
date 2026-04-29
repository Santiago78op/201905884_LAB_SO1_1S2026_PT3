# M.U.M.N.K8s — Monitoreo de Unidades Militares en la Nube con Kubernetes

**Curso:** Sistemas Operativos 1 — FIUSAC, Universidad San Carlos de Guatemala
**Carnet:** 201905884
**País asignado:** CHN (último dígito del carnet: 4)

---

## Descripción del Sistema

M.U.M.N.K8s es un sistema distribuido desplegado en Google Kubernetes Engine (GKE) que procesa reportes militares en tiempo real. Locust genera tráfico de carga hacia el clúster, los datos fluyen por una cadena de microservicios, se almacenan en Valkey y se visualizan en Grafana.

---

## Arquitectura del Pipeline

```
[Locust]
   │ POST /grpc-201905884
   ▼
[Kubernetes Gateway API]       ← exposición pública del clúster
   │
   ▼
[Rust REST API]                ← Actix-web, HPA 1–3 réplicas (CPU > 30%)
   │ HTTP forward
   ▼
[Go gRPC Client]               ← HTTP receiver + gRPC client, HPA 1–3 réplicas
   │ gRPC (WarReportService.SendReport)
   ▼
[Go gRPC Server]               ← gRPC server + RabbitMQ publisher
   │ AMQP
   ▼
[RabbitMQ]                     ← broker de mensajería
   │ consume
   ▼
[Go Consumer]                  ← procesa mensajes y escribe en Valkey
   │
   ▼
[Valkey]  ←── KubeVirt VM1    ← almacenamiento de datos procesados
[Grafana] ←── KubeVirt VM2    ← visualización de dashboards
[Zot]     ←── VM GCP externa  ← registro privado de imágenes OCI
```

---

## Estructura del Repositorio

```
.
├── rust-api/               # API REST en Rust (Actix-web)
├── go-api-grpc-client/     # gRPC client en Go
├── go-grpc-server-writer/  # gRPC server + RabbitMQ writer en Go
├── go-rabbit-consumer/     # Consumidor RabbitMQ → Valkey en Go
├── proto/                  # Contrato Protobuf compartido
├── locust/                 # Scripts de prueba de carga
├── deployments/            # Manifiestos Kubernetes
├── Dockerfile.go-client    # Multi-stage build para go-client
├── Dockerfile.go-server    # Multi-stage build para go-server
└── Dockerfile.go-consumer  # Multi-stage build para go-consumer
```

---

## Payload JSON

Estructura exacta que Locust envía al sistema:

```json
{
  "country": "CHN",
  "warplanes_in_air": 42,
  "warships_in_water": 14,
  "timestamp": "2026-03-12T20:15:30Z"
}
```

**Rangos:** `warplanes_in_air`: random(25–100) a random(1000–3200) | `warships_in_water`: igual
**Países válidos:** USA, RUS, CHN, ESP, GTM

---

## Servicios

### Rust REST API (`rust-api/`)

| Campo | Valor |
|---|---|
| Lenguaje | Rust 2024 (Actix-web) |
| Puerto | 8080 |
| Ruta | `POST /grpc-201905884` |
| Variable de entorno | `GRPC_CLIENT_HOST` (default: `go-client:8080`) |
| Réplicas | 1–3 (HPA, CPU > 30%) |

Recibe el payload JSON de Locust y lo reenvía por HTTP al Go gRPC Client. Es el punto de entrada público del sistema.

**Build:**
```bash
cd rust-api && cargo build --release
```

**Dockerfile:** `rust-api/Dockerfile` — multi-stage: `rust:1.95.0` → `debian:bookworm-slim`

---

### Go gRPC Client (`go-api-grpc-client/`)

| Campo | Valor |
|---|---|
| Lenguaje | Go 1.26 |
| Puerto HTTP | 8080 |
| Ruta | `POST /grpc-201905884` |
| Variable de entorno | `GRPC_SERVER_HOST` (default: `localhost:50051`) |
| Réplicas | 1–3 (HPA, CPU > 30%) |

Recibe el reporte del Rust API, construye un `WarReportRequest` protobuf y lo envía por gRPC al Go gRPC Server.

**Build:**
```bash
cd go-api-grpc-client && go build ./cmd/app/
```

**Dockerfile:** `Dockerfile.go-client` — multi-stage: `golang:1.26.2` → `alpine:3.21`

---

### Go gRPC Server (`go-grpc-server-writer/`)

| Campo | Valor |
|---|---|
| Lenguaje | Go 1.26 |
| Puerto gRPC | 50051 |
| Variable de entorno | `RABBITMQ_HOST` (default: `localhost`) |
| Réplicas | 1–2 |

Implementa `WarReportService.SendReport`. Recibe el request gRPC, lo serializa a JSON y lo publica en RabbitMQ con routing key `warreport.process`.

**RabbitMQ topology:**
- Exchange: `warreport_exchange` (direct, durable)
- Queue: `warreport_queue` (durable)
- Routing key: `warreport.process`

**Build:**
```bash
cd go-grpc-server-writer && go build ./cmd/app/
```

**Dockerfile:** `Dockerfile.go-server` — multi-stage: `golang:1.26.2` → `alpine:3.21`

---

### Go Consumer (`go-rabbit-consumer/`)

| Campo | Valor |
|---|---|
| Lenguaje | Go 1.26 |
| Variable de entorno | `RABBITMQ_HOST` (default: `localhost`) |
| Variable de entorno | `VALKEY_HOST` (default: `localhost`) |
| Réplicas | 1–2 |

Consume mensajes de `warreport_queue` y escribe los datos procesados en Valkey. No expone ningún puerto (worker puro).

**Build:**
```bash
cd go-rabbit-consumer && go build ./cmd/app/
```

**Dockerfile:** `Dockerfile.go-consumer` — multi-stage: `golang:1.26.2` → `alpine:3.21`

---

## Contrato gRPC

Definido en `proto/warreport.proto`:

```proto
syntax = "proto3";

enum Countries {
  countries_unknown = 0;
  usa = 1;
  rus = 2;
  chn = 3;
  esp = 4;
  gtm = 5;
}

message WarReportRequest {
  Countries country         = 1;
  int32 warplanes_in_air    = 2;
  int32 warships_in_water   = 3;
  string timestamp          = 4;
}

message WarReportResponse {
  string status = 1;
}

service WarReportService {
  rpc SendReport (WarReportRequest) returns (WarReportResponse);
}
```

**Generar código Go:**
```bash
protoc --go_out=. --go-grpc_out=. proto/warreport.proto
```

---

## Infraestructura Kubernetes

### Namespaces

| Namespace | Servicios |
|---|---|
| `military-pipeline` | Rust API, Go gRPC Client, Go gRPC Server, Gateway, HTTPRoute |
| `messaging` | RabbitMQ, Go Consumer, Valkey VM, Grafana VM |

```bash
kubectl apply -f deployments/namespaces.yaml
```

### Gateway API

Expone el sistema hacia internet. Locust apunta a la IP del Gateway.

| Recurso | Descripción |
|---|---|
| `GatewayClass` | Controlador GKE L7 global external managed |
| `Gateway` | Listener HTTP en puerto 80 |
| `HTTPRoute` | `PathPrefix /grpc-201905884` → `rust-api:8080` |

```bash
kubectl apply -f deployments/gateway.yaml
```

### HPA — Horizontal Pod Autoscaler

| Servicio | Min | Max | Umbral CPU |
|---|---|---|---|
| `rust-api` | 1 | 3 | 30% |
| `go-client` | 1 | 3 | 30% |

El HPA calcula: `(uso actual / requests.cpu) × 100`. Configurado con `requests.cpu: 100m` en ambos Deployments.

### Aplicar todos los manifiestos

```bash
kubectl apply -f deployments/namespaces.yaml
kubectl apply -f deployments/rabbitmq.yaml
kubectl apply -f deployments/go-services.yaml
kubectl apply -f deployments/rust-api.yaml
kubectl apply -f deployments/gateway.yaml
kubectl apply -f deployments/kubevirt.yaml
```

### Variables de entorno por servicio

| Servicio | Variable | Valor en K8s |
|---|---|---|
| `rust-api` | `GRPC_CLIENT_HOST` | `go-client:8080` |
| `go-client` | `GRPC_SERVER_HOST` | `go-server:50051` |
| `go-server` | `RABBITMQ_HOST` | `rabbitmq.messaging.svc.cluster.local` |
| `go-consumer` | `RABBITMQ_HOST` | `rabbitmq` |
| `go-consumer` | `VALKEY_HOST` | `valkey-service` |

---

## KubeVirt — VMs dentro del clúster

KubeVirt extiende Kubernetes para correr máquinas virtuales completas. Valkey y Grafana corren como `VirtualMachine` dentro del clúster GKE.

### VM1 — Valkey

| Campo | Valor |
|---|---|
| Nombre | `valkey-vm` |
| Namespace | `messaging` |
| Imagen base | `quay.io/containerdisks/ubuntu:22.04` |
| Puerto | 6379 |
| Service | `valkey-service` |

Valkey es compatible con Redis. El `go-consumer` escribe en él usando el cliente `valkey-go`.

### VM2 — Grafana

| Campo | Valor |
|---|---|
| Nombre | `grafana-vm` |
| Namespace | `messaging` |
| Imagen base | `quay.io/containerdisks/ubuntu:22.04` |
| Puerto | 3000 |
| Service | `grafana-service` |

Grafana se conecta a Valkey como data source (plugin Redis/Valkey compatible) y muestra los dashboards de monitoreo.

```bash
kubectl apply -f deployments/kubevirt.yaml
```

---

## Estructura de Datos en Valkey

El `go-consumer` escribe las siguientes keys:

| Key | Tipo | Descripción |
|---|---|---|
| `max_warplanes_in_air` | String | Máximo global de aviones en aire |
| `min_warplanes_in_air` | String | Mínimo global de aviones en aire |
| `max_warships_in_water` | String | Máximo global de barcos en agua |
| `min_warships_in_water` | String | Mínimo global de barcos en agua |
| `rss_rank` | Sorted Set | Ranking acumulado de países por warplanes (ZINCRBY) |
| `cpu_rank` | Sorted Set | Ranking acumulado de países por warships (ZINCRBY) |
| `warplanes_in_air_moda` | Hash | Distribución de frecuencias de warplanes |
| `warplanes_in_air_moda_winner` | String | Valor de moda actual de warplanes |
| `warplanes_in_air_moda_winner_count` | String | Conteo del valor ganador de warplanes |
| `warships_in_water_moda` | Hash | Distribución de frecuencias de warships |
| `warships_in_water_moda_winner` | String | Valor de moda actual de warships |
| `warships_in_water_moda_winner_count` | String | Conteo del valor ganador de warships |
| `meminfo` | List | Serie temporal de reportes CHN (JSON) |
| `total_chn` | String (counter) | Total de reportes del país asignado (CHN) |

---

## Grafana — Dashboards

11 paneles obligatorios configurados con Valkey como data source:

| # | Panel | Visualización | Key Valkey | Comando |
|---|---|---|---|---|
| 1 | Max Warplanes in Air | Stat | `max_warplanes_in_air` | GET |
| 2 | Min Warplanes in Air | Stat | `min_warplanes_in_air` | GET |
| 3 | Max Warships in Water | Stat | `max_warships_in_water` | GET |
| 4 | Min Warships in Water | Stat | `min_warships_in_water` | GET |
| 5 | Top Countries — Warplanes | Bar chart | `rss_rank` | ZRANGE Index 0 -1 |
| 6 | Top Countries — Warships | Bar chart | `cpu_rank` | ZRANGE Index 0 -1 |
| 7 | Mode Warplanes in Air | Stat | `warplanes_in_air_moda_winner` | GET |
| 8 | Mode Warships in Water | Stat | `warships_in_water_moda_winner` | GET |
| 9 | País asignado (CHN) | Text | — | Texto fijo |
| 10 | Total Reports CHN | Stat | `total_chn` | GET |
| 11 | Time Series CHN | Time series | `meminfo` | LRANGE 0 99 + Extract fields JSON |

---

## Zot — Registro Privado de Imágenes

Zot corre en una VM de GCP **fuera del clúster** como registro OCI privado.

**Push de imágenes:**
```bash
# Build desde la raíz del repo
docker build -f Dockerfile.go-client   -t zot-registry:5000/go-client:latest .
docker build -f Dockerfile.go-server   -t zot-registry:5000/go-server:latest .
docker build -f Dockerfile.go-consumer -t zot-registry:5000/go-consumer:latest .
docker build -f rust-api/Dockerfile    -t zot-registry:5000/rust-api:latest rust-api/

# Push
docker push zot-registry:5000/go-client:latest
docker push zot-registry:5000/go-server:latest
docker push zot-registry:5000/go-consumer:latest
docker push zot-registry:5000/rust-api:latest
```

> Reemplazar `zot-registry` con la IP externa de la VM de GCP donde corre Zot.

---

## Pruebas de Carga — Locust

Locust simula usuarios que envían reportes militares aleatorios.

**Ejecutar:**
```bash
cd locust
locust -f locustfile.py --host=http://<GATEWAY_IP>
```

Acceder a la UI de Locust en `http://localhost:8089` y configurar:
- **Number of users:** 100 (recomendado para activar HPA)
- **Spawn rate:** 10 usuarios/segundo

El script genera payloads con país aleatorio (USA, RUS, CHN, ESP, GTM), warplanes y warships con rango `random(25–100)` a `random(1000–3200)`, y timestamp ISO 8601.

---

## Comandos de Verificación

```bash
# Ver pods en todos los namespaces
kubectl get pods -A

# Ver estado del HPA
kubectl get hpa -n military-pipeline

# Ver VMs de KubeVirt
kubectl get vm -n messaging

# Ver Gateway y su IP pública
kubectl get gateway -n military-pipeline

# Ver logs del consumer
kubectl logs -l app=go-consumer -n messaging -f

# Ver logs del go-server
kubectl logs -l app=go-server -n military-pipeline -f
```

---

## Penalizaciones del Proyecto

| Elemento | Penalización |
|---|---|
| No usar GKE | -80% |
| No usar Grafana/KubeVirt | -60% |
| No usar RabbitMQ | -30% |
| No usar Valkey/KubeVirt | -15% |
| No usar Locust | -10% |
| No usar Zot | -5% |
