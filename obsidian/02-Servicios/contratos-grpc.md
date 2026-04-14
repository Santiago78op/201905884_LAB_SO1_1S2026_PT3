---
title: Contratos gRPC — WarReportService
created: 2026-04-05
updated: 2026-04-14
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

- Definicion: `proto/warreport.proto`
- Codigo generado (disponible desde 2026-04-14):
  - `proto/warreport.pb.go` — structs `WarReportRequest`, `WarReportResponse`, enum `Countries`
  - `proto/warreport_grpc.pb.go` — interfaz `WarReportServiceServer` y stub cliente gRPC
- Go packages requeridos:
  - `google.golang.org/grpc`
  - `google.golang.org/protobuf`

## Generacion de Codigo

Comando verificado y ejecutado exitosamente el 2026-04-14:

```bash
protoc -I=proto --go_out=proto --go-grpc_out=proto warreport.proto
```

Nota: `-I=proto` indica el directorio de busqueda del .proto; `--go_out=proto` deposita los archivos generados dentro de `proto/`.

## Conexiones

- [[grpc-client]]
- [[grpc-server]]
- [[flujo-de-datos]]
