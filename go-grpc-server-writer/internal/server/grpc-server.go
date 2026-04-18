package server

import (
	"context"
	"encoding/json"
	"fmt"
	"time"

	proto "201905884_LAB_SO1_1S2026_PT3/proto"

	amqp "github.com/rabbitmq/amqp091-go"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/status"
)

type Server struct {
	connection *amqp.Connection
	channel    *amqp.Channel
	proto.UnimplementedWarReportServiceServer
}

func (s *Server) SendReport(ctx context.Context, req *proto.WarReportRequest) (*proto.WarReportResponse, error) {
	jsonData, err := json.Marshal(req)

	if err != nil {
		return nil, status.Error(codes.InvalidArgument, "Json Data null")
	}
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	err = s.channel.PublishWithContext(ctx,
		"warreport_exchange",
		"warreport.process",
		false,
		false,
		amqp.Publishing{
			ContentType: "application/json",
			Body:        jsonData,
		},
	)

	if err != nil {
		return nil, status.Error(codes.Internal, "Failed to publish to RabbitMQ")
	}

	return &proto.WarReportResponse{Status: "ok"}, nil
}

/* NewServer Struct
* Función para crear un nuevo servidor gRPC con conexión a RabbitMQ
 */
func NewServer(conn *amqp.Connection, ch *amqp.Channel) *Server {
	// Llamar a la función setupRabbitMQ para configurar RabbitMQ
	setupRabbitMQ(ch)

	// Retornar un nuevo servidor gRPC con la conexión a RabbitMQ
	return &Server{
		connection: conn,
		channel:    ch,
	}
}

/* setupRabbitMQ */
func setupRabbitMQ(ch *amqp.Channel) error {
	// Declarar el exchange
	err := ch.ExchangeDeclare(
		"warreport_exchange",
		"direct",
		true,
		false,
		false,
		false,
		nil,
	)
	// Manejar errores
	if err != nil {
		return fmt.Errorf("Failed to declare exchange: %s", err)
	}

	// Declarar la Queue
	_, err = ch.QueueDeclare(
		"warreport_queue",
		true,
		false,
		false,
		false,
		nil,
	)
	if err != nil {
		return fmt.Errorf("Failed to declare queue: %s", err)
	}

	// Binding con routing key: warreport.process
	err = ch.QueueBind(
		"warreport_queue",
		"warreport.process",
		"warreport_exchange",
		false,
		nil,
	)

	if err != nil {
		return fmt.Errorf("Failed to bind queue: %s", err)
	}

	return nil
}
