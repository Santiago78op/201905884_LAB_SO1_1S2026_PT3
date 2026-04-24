package main

import (
	"201905884_LAB_SO1_1S2026_PT3/go-rabbit-consumer/internal/consumer"
	"context"
	"fmt"
	"log"
	"os"

	amqp "github.com/rabbitmq/amqp091-go"
	"github.com/valkey-io/valkey-go"
)

func main() {
	// Leer variables de entorno para RabbitMQ
	host := os.Getenv("RABBITMQ_HOST")
	if host == "" {
		host = "localhost"
	}

	// Coneccion a RabbitMQ
	conn, err := amqp.Dial(fmt.Sprintf("amqp://guest:guest@%s:5672/", host))
	if err != nil {
		log.Fatalf("Failed to connect to RabbitMQ: %v", err)
	}
	defer conn.Close()

	// Leer variables de entorno para Valkey
	hostValkey := os.Getenv("VALKEY_HOST")
	if hostValkey == "" {
		hostValkey = "localhost"
	}

	// Valkey ClientOption Redis/Valkeyy convencion InitAddress Incializacion del cliente de Valkey.
	client, err := valkey.NewClient(valkey.ClientOption{
		InitAddress: []string{fmt.Sprintf("%s:6379", hostValkey)},
	})

	if err != nil {
		log.Fatalf("Failed to create Valkey client: %v", err)
	}

	// Crear nuevo consumidor
	consumer, err := consumer.NewConsumer(conn, client)
	if err != nil {
		log.Fatalf("Failed to create consumer: %v", err)
	}

	// Iniciar el consumidor
	if err := consumer.Start(context.Background(), "warreport_queue"); err != nil {
		log.Fatalf("Failed to start consumer: %v", err)
	}

	// Bloquear el proceso
	select {}

}
