# Protocol Buffer

## Que es un archivo .proto?
                            
Piénsalo como un contrato entre dos programas. Cuando el servicio Go gRPC Client quiere hablarle al Go gRPC Server,
ambos necesitan hablar el mismo "idioma". El .proto define ese idioma: qué datos se envían, qué tipo son, 
y qué operaciones existen.

**PROTOC:** Es el **compilador de Protobuf**, lee el .proto y genera código en el lenguaje que le indiques, en este caso se configuro en Go.

**Comando:**

```proto
protoc  [qué generar]  [archivo .proto]

// Linux
SRC_DIR=proto
DST_DIR=proto

protoc \
  -I=$SRC_DIR \
  --go_out=. \
  --go-grpc_out=. \
  $SRC_DIR/warreport.proto
```

| Parte                        | Explicación técnica                                |
| ---------------------------- | -------------------------------------------------- |
| `-I=$SRC_DIR`                | Define el **include path** (dónde buscar `.proto`) |
| `--go_out=$DST_DIR`          | Dónde generar el código Go                         |
| `$SRC_DIR/addressbook.proto` | Archivo fuente                                     |


Los flags ``[qué generar]`` le dicen a protoc qué tipo de código producir y dónde dejarlo:

| Flag | Que Genera |
|------|------------|
| ``--go_out=.`` | Los structs ``— WarReportRequest``, ``WarReportResponse``, el enum ``Countries`` |
| ``--go-grpc_out=.`` |  La interfaz del servidor y el cliente gRPC — los métodos para llamar/recibir ``SendReport`` |

El ``.`` en ambos significa "deja los archivos aquí mismo, respetando el path del ``go_package``". Como se armo en option ``go_package = "./proto"``, los archivos van a quedar dentro de ``proto/``.  

![Proto](./img/proto.png)

* ``- warreport.pb.go`` — contiene los structs: WarReportRequest, WarReportResponse y el enum Countries
  
* ``- warreport_grpc.pb.go`` — contiene la interfaz del servidor y el stub del cliente para SendReport

Al Abrir ``warreport.pb.go`` un momento y buscar la struct WarReportRequest. Se vera algo como:                             

```go
type WarReportRequest struct {
	state           protoimpl.MessageState
	Country         Countries
	WarplanesInAir  int32                
	WarshipsInWater int32
	Timestamp       string
	unknownFields   protoimpl.UnknownFields
	sizeCache       protoimpl.SizeCache
}
```                                       
                                         
Algo importante: Es que los nombres cambiaron de ``snake_case`` (como en el proto) a ``CamelCase``. Eso es automático — Go usa CamelCase por convención y protoc hace esa conversión solo.

Abre ``warreport_grpc.pb.go`` y busca la interfaz ``WarReportServiceServer``. Esa interfaz es la que Go gRPC Server va a tener que implementar.

```go
type WarReportServiceServer interface {
	SendReport(context.Context, *WarReportRequest) (*WarReportResponse, error)
	mustEmbedUnimplementedWarReportServiceServer()
}
```

## Que es gRPC

Google Remote Procedure Call, es un framework de código abierto, de alto rendimiento, desarrollado por Google para facilitar la comunicación entre servicios (microservicios) y aplicaciones cliente-servidor. Utiliza HTTP/2 para transporte y Protocol Buffers como lenguaje de definición de interfaz para serializar datos en binario, siendo más rápido y ligero que REST/JSON.

**Que es Implementación de una Interfaz**

![gRPC](./img/grpc.png)