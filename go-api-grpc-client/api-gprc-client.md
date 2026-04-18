# ¿Qué es este componente?
Este componente es un cliente gRPC que se conecta a un servidor gRPC para realizar llamadas a métodos definidos en el servidor. El cliente gRPC se utiliza para consumir servicios gRPC expuestos por el servidor, lo que permite la comunicación eficiente y de alto rendimiento entre aplicaciones distribuidas.

El **Go gRPC Client** es el intermediario entre la Rust API y el servidor gRPC. Recibe una petición HTTP de Rust y la **reenvía como llamada gRPC** al servidor. Luego, recibe la respuesta del servidor gRPC y la devuelve a Rust en formato HTTP.

## Por qué existe?
Rust habla **HTTP REST**. El pipline interno habla gRPC. Este componente hace la **traducción** entre ambos protocolos, permitiendo que Rust pueda comunicarse con el servidor gRPC sin necesidad de implementar un cliente gRPC directamente en Rust.

## Implementación

1. Un **servidor HTTP** que recibe el payload de Rust
2. Un **cliente gRPC** que se conecta al Go Server
3. Un **handler** que traduce HTTP → gRPC y responde 

```
  Estructura propuesta:
                    
  go-api-grpc-client/                       
  ├── cmd/app/main.go          ← orquesta el arranque
  └── internal/                                    
      ├── server/
      │   └── http-server.go   ← servidor HTTP (recibe de Rust)                                                                                                                                 
      ├── client/ 
      │   └── grpc-client.go   ← cliente gRPC (habla con Go Server)                                                                                                                             
      └── handler/
          └── report-handler.go ← traduce HTTP → gRPC 
```

- **Server** = "abre la puerta y recibe"
- **Handler** = "decide qué hacer con lo que llegó" 
- **gRPC Client** = "herramienta que usa el Handler para llamar al servidor"
