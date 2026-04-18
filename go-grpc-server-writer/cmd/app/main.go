package main

import (
	"201905884_LAB_SO1_1S2026_PT3/go-grpc-server-writer/internal/server"
	"201905884_LAB_SO1_1S2026_PT3/proto"
	"net"

	amqp "github.com/rabbitmq/amqp091-go"
	"google.golang.org/grpc"
)

/*
* Primero se entabla la conexión a RabbitMQ, luego se crea un nuevo servidor gRPC con la conexión a RabbitMQ, se abre un puerto TCP para gRPC, se registra el servicio gRPC y finalmente se arranca el servidor gRPC.

* Esto porque si el puerto se abre antes de establecer la conexión a RabbitMQ, el servidor gRPC no podrá manejar las solicitudes entrantes correctamente, ya que no tendrá acceso a RabbitMQ para procesar los mensajes.
 */
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

	// Abrir puerto TCP para gRPC
	netListener, err := net.Listen("tcp", ":50051")
	failMsg.FaildOnError(err, "Faild to listen on port 50051")
	defer netListener.Close()

	// Crear gRPC server
	grpcServer := grpc.NewServer()

	// Registrar el servicio gRPC
	proto.RegisterWarReportServiceServer(grpcServer, srv)

	// Arrancar el servidor gRPC
	failMsg.FaildOnError(grpcServer.Serve(netListener), "Failed to serve gRPC server")

}
