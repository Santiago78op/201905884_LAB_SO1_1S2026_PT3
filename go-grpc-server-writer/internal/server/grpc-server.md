# Server

**Ubicación en el pipeline:**

```
  [Go gRPC Server] ── publica →  [RabbitMQ]  ── consume → [Go Consumer]
```

## ¿Qué es RabbitMQ? 

Un *message broker* es un sistema intermediario que recibe, almacena y distribuye mensajes entre productores y consumidores.

Es el patrón productor/consumidor que estudiaste, pero entre procesos distribuidos en red. En lugar de un buffer en      
memoria compartida, el buffer es RabbitMQ corriendo en otro proceso (o máquina).

```
  Productor          Buffer           Consumidor
  [Tu servidor] → [RabbitMQ queue] → [Go Consumer]
```

![RabbitMQ](./img/BabbitMQ.png)

## ¿Por qué existe en este pipeline?

El servidor gRPC puede recibir miles de reportes por segundo. El consumer que escribe a Valkey puede ser más lento. RabbitMQ actúa como amortiguador — acumula los mensajes y los entrega al ritmo que el consumer puede procesar.

Sin RabbitMQ, si el consumer es lento, tu servidor gRPC se bloquea. Con RabbitMQ, el servidor publica y sigue adelante.

## La librería en Go                         
                   
Para hablar con RabbitMQ desde Go se usa amqp091-go. Cuando te conectas exitosamente, la librería te devuelve dos cosas:

1. Una *amqp.Connection — la conexión TCP al servidor RabbitMQ
                                                           
2. Un *amqp.Channel — el canal por donde publicas mensajes

Pregunta: ¿Cuál de los dos guardarías en tu struct — la Connection, el Channel, o ambos? ¿Por qué?