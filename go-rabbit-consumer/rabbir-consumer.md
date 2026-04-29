# Rabbit Consumer
Es el consumidor de mensajes de RabbitMQ, se encarga de recibir los mensajes enviados por el productor y procesarlos.

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

## Qué es este componente?
Es el **consumidor** del patrón productor-consumidor, se encarga de recibir los mensajes enviados por el productor y procesarlos.

Qué se trabaja aquí:
- Conexión a RabbitMQ
- Escucha de mensajes de warreport_queue
- Por cada mensaje: deserialización del mensaje JSON y escribir datos en Valkey.

## Patron Procuctor-Consumidor
Este es el patrón clásico aplicado a sistemas distribuidos:

[Go gRPC Server] = Productor → publica en RabbitMQ (buffer compartido)

[Go Consumer]    = Consumidor → lee del buffer y procesa

RabbitMQ actúa como el buffer sincronizado entre procesos — equivalente a una cola bloqueante, pero entre procesos distribuidos en red.

## Qué es Valkey?
Valkey es un almacén clave-valor en memoria (fork de Redis). El Consumer escribe ahí los datos procesados que Grafana luego lee.

Los datos que Grafana necesita leer son:

- ZREVRANGE rss_rank  0 4 WITHSCORES  → top 5 países por RSS
- ZREVRANGE cpu_rank  0 4 WITHSCORES  → top 5 países por CPU
- LRANGE    meminfo   0 -1            → lista de memoria

Esto significa que el Consumer debe escribir en sorted sets (ZADD) y listas (RPUSH).

El mensaje que llega de RabbitMQ es el JSON que serializó el Go gRPC Server.

Entonces el Consumer hace por cada mensaje:

ZADD rss_rank  <warships_in_water>  <country>

ZADD cpu_rank  <warplanes_in_air>   <country>  
