---
title: Sesiones Docente — Registro de Progreso
created: 2026-04-14
updated: 2026-04-14
tags: [docente, aprendizaje, go-grpc-server-writer, rabbitmq, grpc]
status: activo
project: pegasus
---

# Sesiones Docente — Registro de Progreso

Registro de sesiones de aprendizaje socrático sobre el proyecto Pegasus.

## Conexiones
- [[contratos-grpc]]
- [[go-grpc-server-writer]]
- [[esquema-mensajes-rabbitmq]]

---

## Sesión 2026-04-14 — go-grpc-server-writer

### Componente trabajado
`go-grpc-server-writer` — servidor gRPC que recibe WarReportRequest y publica a RabbitMQ.

### Temas cubiertos (modo docente socrático)
1. **Interfaces en Go** — el estudiante entiende que una interfaz es un contrato, que el struct es el "candidato", y que Go la satisface implícitamente si el método tiene la firma correcta.
2. **Firma de SendReport** — el estudiante identificó los 4 elementos: context.Context, *WarReportRequest, *WarReportResponse, error. Entiende el propósito de cada uno.
3. **context.Context como señal** — conectado con el concepto de señales de SO1. El estudiante entendió que es el mecanismo que avisa al goroutine cuando el cliente cancela la petición.
4. **Separación de responsabilidades** — el estudiante decidió correctamente que la conexión a RabbitMQ va en el struct, no en el método.
5. **Estructura del proyecto** — se explicó el estándar cmd/app/main.go + internal/server/. Se creó la carpeta internal/server/ en go-grpc-server-writer.
6. **RabbitMQ — teoría básica** — se explicó qué es un message broker, el patrón productor/consumidor distribuido, y por qué existe en el pipeline. Se mencionó la librería amqp091-go y los tipos *amqp.Connection y *amqp.Channel.

### Punto de parada
El estudiante no respondió la pregunta: **¿Guardar Connection, Channel, o ambos en el struct?**

### Próximo paso (cuando retome)
1. Responder la pregunta pendiente sobre Connection vs Channel.
2. Escribir el struct `Server` en `internal/server/grpc-server.go` con los campos correctos.
3. Implementar el método `SendReport` con la firma exacta de la interfaz (sin lógica de negocio todavía).
4. Luego: implementar la lógica de publicación a RabbitMQ dentro de SendReport.

### Estado de archivos
- `go-grpc-server-writer/cmd/app/main.go` — existe, vacío o stub
- `go-grpc-server-writer/go.mod` — existe
- `go-grpc-server-writer/internal/server/` — carpeta creada, sin archivos de código aún

---

## Sesión 2026-04-17 — go-grpc-server-writer (continuación)

### Componente trabajado
`go-grpc-server-writer` — continuación de la sesión anterior.

### Temas cubiertos
1. **Connection vs Channel en amqp** — el estudiante entendió por qué se guardan ambos: Channel puede fallar y necesitas Connection para abrir uno nuevo sin reconectar.
2. **Fail-fast** — el estudiante entendió que inicializar la conexión en `main.go` antes de levantar el servidor gRPC es mejor que fallar dentro de una goroutine activa. Conectado con liveness en Kubernetes.
3. **Struct `Server` implementado** — campos `connection *amqp.Connection` y `channel *amqp.Channel`, campos no exportados (privados al package). Import correcto `amqp091-go`. Dependencia añadida al `go.mod`.

### Punto de parada
El estudiante terminó la sesión mientras se le preguntaba: **¿Cómo sabe Go que `Server` implementa `WarReportServiceServer`?** — no respondió todavía.

### Próximo paso (cuando retome)
1. Responder: en Go no hay `implements` — el compilador lo verifica cuando asignas el struct a una variable del tipo interfaz. El método tiene que existir con la firma exacta.
2. Agregar el import del package proto al `grpc-server.go`.
3. Implementar el método `SendReport` con la firma exacta — sin lógica de negocio todavía, solo que compile.
4. Luego: implementar la lógica de publicación a RabbitMQ dentro de `SendReport`.

### Estado de archivos al cerrar sesión
- `go-grpc-server-writer/internal/server/grpc-server.go` — struct `Server` con campos amqp, compila
- `go-grpc-server-writer/go.mod` — tiene `github.com/rabbitmq/amqp091-go v1.10.0`
- `go-grpc-server-writer/cmd/app/main.go` — sigue siendo stub
