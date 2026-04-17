package server

import (
	"encoding/json"
	"context"
	"time"

	proto "201905884_LAB_SO1_1S2026_PT3/proto"
	amqp "github.com/rabbitmq/amqp091-go"
)

/* Server struct 
* Hace referencia a la conexión y canal de RabbitMQ
* connection: es la conexión física con el servidor RabbitMQ
* channel: es el canal virtual que vive dentro de esa conexión
* UnimplementedWarReportServiceServer: es el struct auxiliar 
* 	generado por protoc para implementar la interfaz WarReportServiceServer
*/
type Server struct {
	connection *amqp.Connection
	channel    *amqp.Channel
	proto.UnimplementedWarReportServiceServer // Embed para satisfacer la interfaz
}

/* Metodo de Negocio SendReport 
* Encargado de procesar el reporte militar y publicarlo en RabbitMQ
* Recibe un WarReportRequest y devuelve un WarReportResponse
* Serializa el request y publica en RabbitMQ
* Publicar JSON en RabbitMQ con el channel
* Retorna un WarReportResponse con el status "ok"
*/
func (s *Server) SendReport(ctx context.Context, req *proto.WarReportRequest)(*proto.WarReportResponse, error) {
	// json Marshall
	jsonData, err := json.Marshal(req)

	// Si hay error, fileOnError
	faildOnError(err, "Fail to serealize request")

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	// Publicar en RabbitMQ con el channel
	err = s.channel.PublishWithContext({ctx,
		"warreport_exchange",
		"warreport.process",
		false,
		false,
		amqp.Publishing{
			ContentType: "application/json",
			Body:        jsonData,
		},
	})

	failedToPublish(err, "Failed to publish to RabbitMQ")

	// Retornar respuesta exitosa
	return &proto.WarReportResponse{Status: "ok"}, nil
}

func failedToPublish(err error, message string) {
	if err != nil {
		log.Fatalf("%s: %v", message, err)
	}
}