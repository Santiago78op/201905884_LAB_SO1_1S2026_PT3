---
title: Esquema de Mensajes — RabbitMQ
created: 2026-04-05
updated: 2026-04-05
tags: [rabbitmq, mensajes, broker]
status: activo
---

# Esquema de Mensajes — RabbitMQ

## Topología

| Parámetro    | Valor                |
|--------------|----------------------|
| Exchange     | `warreport_exchange` |
| Tipo         | `direct`             |
| Queue        | `warreport_queue`    |
| Routing Key  | `warreport.process`  |

## Payload del Mensaje

El mensaje publicado por el gRPC Server corresponde al reporte militar procesado:

```json
{
  "country": "ESP",
  "warplanes_in_air": 42,
  "warships_in_water": 14,
  "timestamp": "2026-03-12T20:15:30Z"
}
```

> El esquema debe ser coherente con el `WarReportRequest` del contrato gRPC.

## Flujo

1. **Publisher**: Go Deployment 2/3 (gRPC Server) publica en `warreport_exchange` con routing key `warreport.process`
2. **Queue**: `warreport_queue` recibe los mensajes
3. **Consumer**: Go Consumer hace `consume` de `warreport_queue` y escribe en Valkey

## Recomendaciones

- Configurar `durable: true` en exchange y queue para persistencia
- Usar `prefetch_count` en el consumer para controlar concurrencia
- Configurar TTL en Valkey para evitar saturación de memoria

## Conexiones

- [[grpc-server]]
- [[consumer]]
- [[valkey]]
- [[rabbitmq]]
