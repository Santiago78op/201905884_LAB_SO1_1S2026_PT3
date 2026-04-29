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

El patrón del builder en valkey-go siempre es el mismo: `client.B().<Comando>().<Opciones>().Build()`.

## Cliente Redis/Valkey
El cliente de Valkey se encarga de escribir los datos procesados en Valkey utilizando comandos específicos para cada tipo de operación (SET, ZADD, HINCRBY, LPUSH, INCR).

```go
cliente.Set(ctx, "key", "value", 0) // método directo
```

**valkey-go funciona diferente**. Usa un patrón de **builder + executor**:

```go
client.Do(ctx,  client.B().Set().Key("key").Value("value").Build())
```

| Parte | ¿Qué hace? |
|------|------------|
| `client.B()` | Inicia la construcción de un comando. |
| `.Set().Key(...).Value(...).Build()` | Define qué comando es y cuáles son sus parámetros. |
| `client.Do(ctx, ...)` | Ejecuta el comando construido en Valkey. |

El  builder garantiza en **tiempo de compilación** que el comando esté bien formado, evitando errores comunes como olvidar un campo obligatorio o usar un tipo de dato incorrecto. Si olvidas `.key(...)`. el código no compilará, lo que es una gran ventaja para la seguridad y robustez de la aplicación. Con el patrón de metodo directo, los errores se detectan en runtime.

## Estructura

```
SET:     client.B().Set().Key("k").Value("v").Build()
ZADD:    client.B().Zadd().Key("k").ScoreMember().ScoreMember(score, "member").Build()                                                            
HINCRBY: client.B().Hincrby().Key("k").Field("f").Increment(1).Build()                                                        LPUSH:   client.B().Lpush().Key("k").Element("v").Build()                                                            INCR:    client.B().Incr().Key("k").Build()                                                            GET:     client.B().Get().Key("k").Build()
```

## Una cosa importante

`Do` retorna un `valkey.ValkeyResult`. Para leer el valor (cuando haces GET), usas `.ToString()` o `.AsInt64()` sobre el resultado.

Este retorno es de tipo **wraper** no es un valor directamente, es un contenedor que puede tener el valor o un error.

```go
resultado.ToString() // devuelve el valor como string o un error si no se pudo obtener
resultado.AsInt64() // devuelve el valor como int64 o un error si no se pudo obtener
resultado.AsFloat64() // devuelve el valor como float64 o un error si no se pudo obtener
```

Cuando `valkey.Nil`. No es un error de conexión es la señal de "key no encontrada".

## LPUSH y la serie temporal
El tipo **List** en Valkey es una lista enlazada. El comando `LPUSH` inserta al **frente** de la lista (Left Push). Esto significa que el elemento más reciente siempre queda en la posición 0 — útil para series temporales donde lo más nuevo es lo más importante.

**Comando Valkey**

- `LRANGE key 0 -1`: devuelve todos los elementos de la lista desde el más nuevo 0 hasta el más viejo (-1).
- `LLEN key`: devuelve la longitud de la lista, útil para saber cuántos elementos hay en la serie temporal.
- `LTRIM key 0 N`: mantiene solo los N elementos más recientes, eliminando el resto para evitar que la lista crezca indefinidamente.
