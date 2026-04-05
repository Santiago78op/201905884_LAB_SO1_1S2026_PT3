---
title: Contratos gRPC — WarReportService
created: 2026-04-05
updated: 2026-04-05
tags: [grpc, proto, contratos]
status: activo
---

# Contratos gRPC

## Definición Proto (propuesta del proyecto)

```proto
syntax = "proto3";
package wartweets;
option go_package = "./proto";

// Enum de países válidos
enum Countries {
  countries_unknown = 0;
  usa = 1;
  rus = 2;
  chn = 3;
  esp = 4;
  gtm = 5;
}

// Mensaje de reporte militar
message WarReportRequest {
  Countries country = 1;
  int32 warplanes_in_air = 2;
  int32 warships_in_water = 3;
  string timestamp = 4;
}

// Respuesta del servidor
message WarReportResponse {
  string status = 1;
}

// Servicio gRPC
service WarReportService {
  rpc SendReport (WarReportRequest) returns (WarReportResponse);
}
```

## Comunicación

- **Caller**: Go Deployment 1 (gRPC Client)
- **Server**: Go Deployments 2 & 3 (gRPC Server + RabbitMQ Writer)
- El cliente invoca `SendReport` con el reporte recibido de Rust
- El servidor escribe el mensaje en RabbitMQ y responde con `status`

## Archivos en el Repositorio

- Definición: `proto/warreport.proto`
- Código generado Go (Go packages necesarios):
  - `google.golang.org/grpc`
  - `google.golang.org/protobuf`

## Generación de Código

```bash
protoc --go_out=. --go-grpc_out=. proto/warreport.proto
```

## Conexiones

- [[grpc-client]]
- [[grpc-server]]
- [[flujo-de-datos]]
