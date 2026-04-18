package main

import (
	"201905884_LAB_SO1_1S2026_PT3/go-grpc-server-writer/internal/server"

	amqp "github.com/rabbitmq/amqp091-go"
)

func main() {
	// Coneccion a RabbitMQ
	conn, err := amqp.Dial("amqp://guest:guest@locatehost:5672/")
	// Si falla importamos Panicf con err
	failMsg := server.OutPutFaildOnError{}
	failMsg.FaildOnError(err, "Fail to connect to RabbitMQ")
	defer conn.Close()

	// Abrir canal
	ch, err := conn.Channel()
	failMsg.FaildOnError(err, "Faild to open a channel")
	defer ch.Close()

	// Creación de server Struct
	srv := server.NewServer(conn, ch)

}
