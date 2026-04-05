package main

import (
	"context"
	"fmt"
	"log"
	"net"

	// Importamos el paquete "proto" generado por protoc.
	// El alias "pb" es convención para paquetes proto en Go.
	pb "pegasus/go-grpc-server-writer/proto"

	"google.golang.org/grpc"
)

// ── PASO 1: Definir el servidor ──────────────────────────────────────────────
//
// "server" es nuestra implementación del servicio gRPC.
// Embeder UnimplementedWarReportServiceServer es OBLIGATORIO en gRPC-Go moderno:
// garantiza que si el .proto agrega nuevos RPCs en el futuro, tu servidor
// no falle en compilación por métodos faltantes.
type server struct {
	pb.UnimplementedWarReportServiceServer
}

// ── PASO 2: Implementar el RPC ───────────────────────────────────────────────
//
// SendReport se llama cada vez que el cliente Rust invoca
// WarReportService.SendReport(). El framework gRPC inyecta el contexto
// y el request deserializado automáticamente.
func (s *server) SendReport(ctx context.Context, req *pb.WarReportRequest) (*pb.WarReportResponse, error) {
	// En el MVP solo logueamos. Aquí irá la publicación a RabbitMQ más adelante.
	log.Printf("[REPORTE RECIBIDO] país=%-5s | aviones=%d | barcos=%d | ts=%s",
		req.Country,
		req.WarplanesInAir,
		req.WarshipsInWater,
		req.Timestamp,
	)

	return &pb.WarReportResponse{Status: "OK"}, nil
}

// ── PASO 3: Arrancar el servidor ─────────────────────────────────────────────
func main() {
	const port = ":50051"

	// net.Listen abre el socket TCP. gRPC funciona sobre TCP.
	lis, err := net.Listen("tcp", port)
	if err != nil {
		log.Fatalf("Error al abrir socket: %v", err)
	}

	// grpc.NewServer() crea el servidor. Aquí puedes inyectar
	// interceptores (logging, auth, métricas) en el futuro.
	s := grpc.NewServer()

	// Registramos nuestra implementación en el servidor.
	// Esto conecta la interfaz generada por protoc con nuestro código.
	pb.RegisterWarReportServiceServer(s, &server{})

	fmt.Printf("✓ gRPC Server escuchando en %s\n", port)

	// Serve() bloquea: acepta conexiones hasta que el proceso termine.
	if err := s.Serve(lis); err != nil {
		log.Fatalf("Error al servir: %v", err)
	}
}
