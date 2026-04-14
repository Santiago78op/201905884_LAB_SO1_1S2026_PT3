# Server struct y el método.

El struct no es la base de la interfaz. La interfaz existe independientemente — la generó protoc y no le importa quién la implemente.

El struct es simplemente el candidato que aplica al contrato. Go verifica automáticamente si califica cuando intentas registrarlo en el servidor gRPC.

## Firma que protoc exige

```go
SendReport(context.Context, *WarReportReques)(*WarReportResponse, error)
```

Hay cuatro elementos en esa firma:

### ¿Qué representa cada uno de esos cuatro elementos y por qué crees que están ahí?

- ``*WarReportReques``
- ``*WarReportResponse``
- ``error``
- ``context.Context``

## *WarReportReques

Es un puntero a una estructura generada por Protobuf que representa el mensaje de entrada enviado por el cliente gRPC.

Características técnicas:

- Serializado/deserializado automáticamente por gRPC
- Contiene los datos del request
- Se pasa como puntero para evitar copias en memoria

Interpretación:

Es el payload de entrada de tu operación remota (RPC).

## *WarReportResponse

Es un puntero a una estructura generada por Protobuf que representa el mensaje de salida que tu servidor devuelve al cliente.

Características técnicas:

- Construido por tu lógica de negocio
- Serializado automáticamente por gRPC al enviarlo
- También se maneja como puntero por eficiencia

Interpretación:
Es el resultado de la ejecución de tu método remoto.

## Error

Es una interfaz nativa de Go que representa el estado de fallo o error de una operación.

```go
type error interface {
    Error() string
}
```

**Propósito:**

- Indicar si la ejecución falló
- Transportar información del fallo

**En gRPC:**

- Si ``error != nil → gRPC`` responde con estado de error
- Si ``error == nil → respuesta`` exitosa

Interpretación:

Es el canal formal de fallos del método.

## context.Context

El servidor gRPC puede estar atendiendo cientos de peticiones simultáneas. Cada una viene de un cliente diferente, en un goroutine diferente.

Ahora imagina este escenario:

*El cliente envía un ``SendReport``. Medio segundo después, el cliente cancela la petición — se cayó la red, o el usuario cerró la aplicación.*

*El servidor ya recibió el request y está a punto de publicar a RabbitMQ.*

```
  Aquí está el problema real:

  Cliente ──cancela──→  [red]  ──→  tu método SendReport
                                        │
                                        │ ← ¿esto sabe algo?
                                        │
                                   publica a RabbitMQ
```

**Goroutine:**
Una goroutine es una unidad de ejecución ligera gestionada por el runtime de Go, que permite ejecutar funciones de forma concurrente.

Tu método está corriendo en un goroutine. El cliente se cayó. ¿Qué mecanismo le avisa a tu goroutine que eso pasó?

### Señales (Signals) → el mecanismo principal

Las señales son la forma estándar en UNIX/Linux para notificar eventos entre procesos.

- Caso: padre termina
    - Cuando un padre muere:

- El kernel envía a los hijos:
    - SIGHUP (Hangup) o en algunos casos SIGTERM

```context.Context`` es el equivalente en Go de una señal entre goroutines. Cuando el cliente cancela, el framework gRPC cierra un canal interno dentro del contexto. Tu método puede escuchar ese canal y reaccionar.

Sin context.Context, tu goroutine correría a ciegas — publicaría a RabbitMQ, esperaría, consumiría recursos — sin saber que nadie está al otro lado.

## recurso compartido vs proceso

La diferencia entre un **recurso compartido** (la conexión, que existe una vez) y un **proceso que lo usa** (el método, que se ejecuta muchas veces concurrentemente).

**Ver la estructura de tus directorios**

```bash
find go-grpc-server-writer -type f
```