## Consumer
Es el consumidor de mensajes de RabbitMQ, se encarga de recibir los mensajes enviados por el productor y procesarlos.

El Consumer se conecta a RabbitMQ, escucha los mensajes de la cola `warreport_queue`, y por cada mensaje recibido, deserializa el JSON y escribe los datos en Valkey.

```
[Locust] → [Gateway] → [Rust API] → HTTP
                                        ↓
                                 [main.go] ← AQUÍ
                                 crea todo y arranca
                                        ↓
                                [HTTPServer] → [Handler] → [GRPCClient]
                                        ↓
                                 [Go gRPC Server]
```

**Campos del Struct**

- connection: conexión a RabbitMQ
- channel: canal de comunicación con RabbitMQ
- valkeyClient: cliente para escribir en Valkey

## Tabla cmdline valkey
| Visualización           | Estructura Valkey                 | Operación                          |
|------------------------|----------------------------------|------------------------------------|
| Max aviones            | `SET max_warplanes <valor>`      | Actualizar si el nuevo es mayor     |
| Min aviones            | `SET min_warplanes <valor>`      | Actualizar si el nuevo es menor     |
| Max barcos             | `SET max_warships <valor>`       | Igual                               |
| Min barcos             | `SET min_warships <valor>`       | Igual                               |
| Top países aviones     | `ZADD rss_rank <score> <country>`| Sorted set                          |
| Top países barcos      | `ZADD cpu_rank <score> <country>`| Sorted set                          |
| Moda aviones           | `HINCRBY moda_warplanes <valor> 1` | Hash — contar frecuencias        |
| Moda barcos            | `HINCRBY moda_warships <valor> 1` | Hash — contar frecuencias        |
| Serie temporal         | `LPUSH meminfo <json>`           | Lista                               |
| País asignado          | `constante "CHN"`                | No necesita Valkey                  |
| Total reportes país    | `INCR total_chn`                 | Contador                            |