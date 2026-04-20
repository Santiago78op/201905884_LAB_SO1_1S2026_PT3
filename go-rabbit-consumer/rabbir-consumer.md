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

●​ Alcance obligatorio:
o​ Locust: Generación de tráfico con la estructura JSON especificada hacia el
endpoint público expuesto mediante Kubernetes Gateway API.
Los datos enviados deberán simular reportes militares con valores aleatorios
dentro de rangos definidos.
o​ Gateway API: Exposición del sistema utilizando Kubernetes Gateway API en
sustitución del uso de Ingress Controller.
El sistema deberá contar con las rutas para:
▪​ /grpc-#carnet
▪​ /dapr-#carnet (parte opcional con Dapr)
o​ Deployments de Rust: API REST que recibe peticiones de Locust, envía a
un Deployment de Go, soporta alta carga y escala con HPA (1-3 réplicas,
CPU > 30%).
o​ Deployments de Go:
▪​ Deployment 1 (API REST y gRPC Client): Recibe de Rust, actúa
como cliente gRPC, invoca funciones para publicar en RabbitMQ.
▪​ Deployments 2 y 3 (gRPC Server y Writer RabbitMQ): recibe
solicitudes gRPC y publica mensajes en RabbitMQ. Deben realizarse
pruebas con 1 y 2 réplicas en los componentes que la cátedra defina
para análisis de rendimiento.
o​ RabbitMQ: Broker principal de mensajería del proyecto. Será el único
sistema de colas obligatorio utilizado para el flujo principal.
o​ RabbitMQ Client (Consumer) (Deployment): Deployment encargado de
consumir los mensajes de RabbitMQ, procesarlos y almacenar la información
resultante en Valkey.
o​ Valkey en KubeVirt: Valkey deberá ejecutarse dentro de una máquina virtual
administrada por KubeVirt, desplegada dentro del clúster de Kubernetes.
Esta VM deberá ser independiente y dedicada al almacenamiento de datos
procesados. Se debe asegurar persistencia y conectividad entre los
consumers y la VM.
o​ Grafana en KubeVirt: Grafana deberá ejecutarse dentro de una máquina
virtual distinta, también administrada por KubeVirt dentro del clúster. Esta VM
deberá conectarse a la fuente de datos correspondiente para construir y
mostrar los dashboards requeridos.
o​ Zot: Implementado en una VM de GCP fuera del clúster K8s. Todas las
imágenes Docker de los componentes se publican y se descargan desde Zot.
o​ OCI Artifact: Descarga de archivo de entrada desde el registry como un OCI
Artifact (se debe especificar qué archivo y cómo se usa en la documentación)
o​ Infraestructura en GCP: Todo el proyecto debe desplegarse en Google
Cloud Platform, utilizando instancias N1.
o​ Documentación: El manual técnico deberá explicar:
▪​ arquitectura general,
▪​ flujo completo de datos,
▪​ configuración de Gateway API,
▪​ comunicación REST y gRPC,
▪​ uso de RabbitMQ,
▪​ despliegue de Valkey y Grafana sobre KubeVirt,
▪​ configuración de HPA,
▪​ publicación/consumo de imágenes desde Zot,
▪​ pruebas realizadas y conclusiones.
El manual técnico deberá ser entregado exclusivamente en formato
Markdown.
o​ Sugerencias Generales: Uso de namespaces, Gateway API, creación
propia de imágenes Docker.
o​ Requisitos Mínimos para tener derecho a calificación:
▪​ Clúster de Kubernetes en GCP
▪​ Uso obligatorio de Locust
▪​ Uso obligatorio de GKE
▪​ Uso obligatorio de RabbitMQ
▪​ Uso obligatorio de KubeVirt para Valkey y Grafana
o​ Restricciones: Proyecto individual, uso obligatorio de Locust y GKE