---
title: Go gRPC Server Writer
created: 2026-04-14
updated: 2026-04-14
tags: [grpc, go, rabbitmq, servidor]
status: pendiente-implementacion
service: go-grpc-server-writer
---

# Go gRPC Server Writer

Servicio central del pipeline. Recibe reportes de guerra via gRPC desde el cliente y los publica en RabbitMQ.

## Resumen

- **Entrada**: mensajes `WarReportRequest` desde [[grpc-client]] via gRPC
- **Salida**: mensajes publicados en [[rabbitmq]] (exchange `warreport_exchange`, routing key `warreport.process`)
- **Codigo**: `go-grpc-server-writer/`

## Responsabilidad

1. Implementar la interfaz `WarReportServiceServer` generada por protoc
2. Recibir `SendReport(WarReportRequest)` y publicar el payload en RabbitMQ
3. Responder con `WarReportResponse{status: "ok"}` al cliente

## Interfaz a Implementar

Generada en `proto/warreport_grpc.pb.go` (disponible desde 2026-04-14):

```go
type WarReportServiceServer interface {
    SendReport(context.Context, *WarReportRequest) (*WarReportResponse, error)
    mustEmbedUnimplementedWarReportServiceServer()
}
```

El struct servidor debe embeber `UnimplementedWarReportServiceServer` y sobreescribir `SendReport`.

## Estado de Implementacion

| Componente | Estado |
|---|---|
| `proto/warreport.proto` | Finalizado |
| `proto/warreport.pb.go` | Generado |
| `proto/warreport_grpc.pb.go` | Generado |
| Struct servidor + implementacion | Pendiente |
| Conexion RabbitMQ | Pendiente |

## Proximos Pasos

1. Crear struct `server` que embedee `UnimplementedWarReportServiceServer`
2. Implementar metodo `SendReport`: serializar el request y publicar en RabbitMQ
3. Conectar con el broker usando el esquema definido en [[esquema-mensajes-rabbitmq]]
4. Levantar el servidor gRPC en el `main.go`

## Conexiones

- [[contratos-grpc]]
- [[grpc-client]]
- [[rabbitmq]]
- [[esquema-mensajes-rabbitmq]]
- [[progreso-sesiones]]
