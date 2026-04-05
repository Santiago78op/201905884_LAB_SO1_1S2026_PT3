# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Pegasus** is a distributed system for processing and visualizing war report data. It is an early-stage project with stub implementations and complete architectural documentation in the `obsidian/` vault.

## Build Commands

**Go services** (all three follow the same pattern):
```bash
cd go-api-grpc-client   && go build ./cmd/app/ && go test ./...
cd go-grpc-server-writer && go build ./cmd/app/ && go test ./...
cd go-rabbit-consumer    && go build ./cmd/app/ && go test ./...
```

**Rust API:**
```bash
cd rust-api && cargo build
cd rust-api && cargo test
cd rust-api && cargo run
```

**Proto code generation** (requires `protoc` + Go gRPC plugins):
```bash
protoc --go_out=. --go-grpc_out=. proto/warreport.proto
```

## Architecture

Data flows through a linear pipeline:

```
Locust → Rust API → Go gRPC Client → Go gRPC Server → RabbitMQ → Go Consumer → Valkey → Grafana
```

| Component | Language | Role |
|---|---|---|
| `rust-api/` | Rust 2024 | Entry point; receives HTTP from Locust, forwards via gRPC |
| `go-api-grpc-client/` | Go 1.26 | gRPC client; sends `WarReportRequest` to the gRPC server |
| `go-grpc-server-writer/` | Go 1.26 | gRPC server; receives reports, publishes to RabbitMQ |
| `go-rabbit-consumer/` | Go 1.26 | Consumes RabbitMQ messages, writes to Valkey |
| `proto/` | Protobuf | Shared service contract (`WarReportService.SendReport`) |
| `locust/` | Python | Load testing |
| `deployments/` | K8s YAML | GKE deployment manifests (not yet implemented) |

## gRPC Contract

Defined in `proto/warreport.proto`. The single RPC:
```proto
service WarReportService {
  rpc SendReport (WarReportRequest) returns (WarReportResponse);
}
```
`WarReportRequest` carries `country`, `warplanes_in_air`, `warships_in_water`, and `timestamp`.

## RabbitMQ Topology

- Exchange: `warreport_exchange`
- Queue: `warreport_queue`
- Routing key: `warreport.process`

## Valkey / Grafana

The consumer writes ranked data to Valkey (Redis-compatible). Grafana reads:
- `ZREVRANGE rss_rank 0 4 WITHSCORES`
- `ZREVRANGE cpu_rank 0 4 WITHSCORES`
- `LRANGE meminfo 0 -1`

## Infrastructure

Targets GKE (Kubernetes) with KubeVirt for VM workloads and Zot as the container image registry. No manifests exist yet — `deployments/` is empty.

## Documentation

All architectural decisions, service specs, and observability setup live in `obsidian/` as a structured Obsidian vault:
- `01-Arquitectura/` — general design, data flow, technical decisions
- `02-Servicios/` — per-service specs and RabbitMQ message schema
- `03-Infraestructura/` — GKE, KubeVirt, Zot setup
- `04-Observabilidad/` — Grafana dashboards
- `05-Pruebas/` — testing strategy
