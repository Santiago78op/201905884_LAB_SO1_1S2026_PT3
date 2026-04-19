# HTTP Server para gRPC Client
Este componente es un servidor HTTP que se encarga de recibir las solicitudes entrantes desde la Rust API, procesarlas y luego utilizar el cliente gRPC para enviar los datos al servidor gRPC. El servidor HTTP actúa como un intermediario entre la Rust API y el cliente gRPC, permitiendo que las solicitudes HTTP sean traducidas a llamadas gRPC y viceversa.

## Secuencia de funcionamiento
1. **Escuchar** en un puerto TCP esperar solicitudes HTTP entrantes.
2. **Resgistrar** un handler específico para la ruta que se encargará de procesar las solicitudes relacionadas con los informes de guerra.
3. **Arrancar** el servidor HTTP para que esté listo para recibir solicitudes.

## El Rust API en el Pipeline

```
[Locust]        
     ↓  HTTP POST /grpc-201905884                                                                                                                                                
  [Gateway API]   
     ↓  HTTP
  [Rust REST API]  ← AQUÍ                                                                                                                                                        
     ↓  HTTP POST (JSON)
  [Go gRPC Client]
```

## ¿Qué es el Rust API?
En el **punto de entrada del sistema**. Es el único servicio expuesto al mundo exterior a través del Gatway API. Todo el tráfico de **Locust** llega aquí primero.

El trabajo es **exactamente uno:** recibir el payload HTTP de Locust y reenviarlo al siguiente eslabón de la cadena - el Go gRPC Client.

## ¿Por qué Rust y no Go directamente?

```
El Rust API no sabe nada de gRPC, ni siquiera de Go. Solo sabe cómo recibir solicitudes HTTP y enviar respuestas HTTP. Es un servicio muy simple que actúa como un puente entre el mundo HTTP y el mundo gRPC.
```

El sistema tiene una **capa de traducción** entre el mundo HTTP y el mundo gRPC. El Rust API es esa capa de traducción. No tiene que preocuparse por los detalles de gRPC, solo tiene que preocuparse por recibir solicitudes HTTP y enviar respuestas HTTP.

Esta traducción es responsabilidad del Go gRPC Client. Rust hace lo suyo (HTTP) y Go hace lo suyo (gRPC). Es una separación de responsabilidades que hace que el sistema sea más modular y fácil de mantener.

## ¿Modelo productor-consumidor de Sistemas Operativos?

```                            
  Locust (productor de requests)
    → Rust API (buffer / frontera)
      → Go Client (transporte interno)
        → Go Server (consumidor + re-productor para RabbitMQ)
```                                                                      

Cada nodo produce para el siguiente. El Rust API es el primer buffer del pipeline.                                                                                     
## ¿Qué hace Rust internamente?
En términos de implementación, el Rust API necesita:

1. Levantar un servidor HTTP (Actix-Web en este proyecto)

2. Recibir ``POST /grpc-201905884`` con el JSON del reporte                                                   

3. Hacer un ``POST`` HTTP al Go gRPC Client con ese mismo JSON 

4. Devolver la respuesta a Locust

Nada más. Es un **relay HTTP → HTTP** con la lógica de entrada.

## Que pasa si Rust API se rompe y sus mensajes enviados antes de su caida?

Los mensajes que ya cruzaron hacia el Go **Server** siguen su cmaino - RabbitMQ los recibió, el Consumer los procesó, Valkey los guardó. El pipeline downstream no se enteró de que Rust cayó. Eso es la fortaleza del desacoplamiento por colas.

El punto de entrada al sistema queda inaccesible. Locust ya no puede enviar nada. El Go Client está vivo y esperando, pero nadie le habla.

Es como si el proceso servidor muriera en SO1 — el socket existe, pero nadie acepta conexiones nuevas.

## Servidor HTTP

Es conceptualmente un **proceso servidor esperando en un socket**. Cuando llega una conexión, Go internamente hace algo similar al modelo de:

```
Por cada request → una goroutine (hilo ligero del runtime de Go) la maneja de forma concurrente.
```

## Requerimientos
Se necesita **exportar** una función o struct que levante el servidor HTTP y lo conecte al **Handler** que se encargará de procesar las solicitudes entrantes.

- Necesitas un ``http.ServeMux`` — el enrutador.
- Necesitas registrar una ruta (``/grpc-201905884``) apuntando a tu ``Handler``
- Necesitas un ``http.Server`` con una dirección y ese mux
- Necesitas un método para iniciar el servidor

## Qué es un Mux?

**Mux o Multiplexer:** El nombre viene de electrónica/telecomunicaciones.

En redes, un multiplexor es un dispositivo que toma múltiples señales de entrada y las combina en una sola señal de salida. En el contexto de servidores HTTP, un Mux es un componente que recibe solicitudes HTTP y las enruta al handler correcto basado en la URL o el método HTTP.

En un servidor HTTP:

```
  Requests entrantes:
    POST /grpc-201905884  ──┐
    GET  /health          ──┤  [Mux]  ──→ Handler correcto
    POST /otra-ruta       ──┘
```

El **Mux** es el **despachador de tráfico**. Cuando llega un request, el Mux pregunta: "¿A qué handler debo enviar esta solicitud?" y luego la envía al handler registrado para esa ruta.

Go tiene una librería estándar que incluye un Mux básico llamado ``http.ServeMux``, pero también hay frameworks como Gorilla Mux o Chi que ofrecen funcionalidades más avanzadas para el enrutamiento.

- Crea mux
- Registra "ruta X" y "handler A"
- Registra "ruta Y" y "handler B"
- Servidor HTTP usa ese mux para manejar requests entrantes

Entonces cuando llega un request a "/grpc-201905884", el Mux lo envía al handler que registraste para esa ruta, y ese handler es el que se encarga de procesar la solicitud y enviar la respuesta.

La ruta que necesita registrar es "/grpc-201905884" porque es la ruta que el Rust API va a usar para enviar los datos al Go Client. El handler registrado en esa ruta será el encargado de recibir el JSON del reporte, procesarlo y luego enviarlo al servidor gRPC.


| Función | Descripción |
|---------|-------------|
| `status.Error` | Errores gRPC — lleva código de estado gRPC (codes.Internal, etc.) |
| `http.Error` | Errores HTTP — escribe una respuesta HTTP con status code al cliente |
| `fmt.Errorf` | Errores genéricos — formatea un mensaje de error, pero no tiene código de estado específico |
| `errors.Is` | Verificación de errores — se usa para comparar errores, especialmente con `fmt.Errorf` y `status.Error` |
  