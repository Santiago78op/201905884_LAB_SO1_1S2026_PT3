# gRPC Client
En ``internal/client/grpc-client.go``, necesitas un struct con:

- Una conexión ``gRPC (*grpc.ClientConn)``
- Un cliente del servicio ``proto (proto.WarReportServiceClient)`` 

## Qué función tiene la librería gRPC
La librería gRPC es un framework de comunicación remota que permite a los clientes y servidores comunicarse de manera eficiente y escalable.

Proporciona una forma sencilla de definir servicios y métodos utilizando archivos de definición de protocolo (protobuf), lo que facilita la generación automática de código para diferentes lenguajes de programación.

Al momento de que un proceso quiere comunicarse con otro proceso que corre en una máquina diferente, (o en otro pod de Kubernetes), necesita establecer una **conexión** entre ambos procesos. La función ``NewClient`` es la encargada de establecer esta conexión utilizando la librería gRPC.

```go
func NewClient( cadena de destino , opciones ... DialOption ) (conn * ClientConn , err error )
```

**Parámetros**:
- ``cadena de destino``: Es la dirección del servidor al que deseas conectarte, por ejemplo, "localhost:50051".
- ``opciones``: Son opciones adicionales para configurar la conexión, como el uso de TLS, tiempo de espera, etc.
    - ``grpc.WithTransportCredentials(insecure.NewCredentials())``: Esta opción indica que la conexión no utilizará TLS, lo que es común en entornos de desarrollo o cuando se confía en la red.
**Retorna**:
- ``conn``: Es la conexión establecida con el servidor gRPC.
- ``err``: Si ocurre algún error durante la conexión, se devuelve un error.

En Kubernetes, el ``go-api-grpc-client`` se comunica con el ``go-api-grpc-server`` a través de esta conexión gRPC, la dirección no será "localhost:50051" sino el **nombre del servicio de Kubernetes**.