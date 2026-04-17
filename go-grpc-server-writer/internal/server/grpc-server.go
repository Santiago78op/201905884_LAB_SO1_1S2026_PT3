package server

import (
	amqp "github.com/rabbitmq/amqp091-go"
)

/* Server struct 
* Hace referencia a la conexión y canal de RabbitMQ
* connection: es la conexión física con el servidor RabbitMQ
* channel: es el canal virtual que vive dentro de esa conexión
*/
type Server struct {
	connection *amqp.Connection
	channel    *amqp.Channel
}