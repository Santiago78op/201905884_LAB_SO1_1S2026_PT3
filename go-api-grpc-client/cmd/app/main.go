package main

import (
	"201905884_LAB_SO1_1S2026_PT3/go-api-grpc-client/internal/client"
	"201905884_LAB_SO1_1S2026_PT3/go-api-grpc-client/internal/handler"
	"201905884_LAB_SO1_1S2026_PT3/go-api-grpc-client/internal/server"
	"fmt"
	"os"
)

func main() {
	// Leer variables de entorno para gRPC server
	grpcServerHost := os.Getenv("GRPC_SERVER_HOST")
	if grpcServerHost == "" {
		grpcServerHost = "localhost:50051"
	}

	// Crear el gRPC client
	grpcClient, err := client.NewClient(grpcServerHost)
	if err != nil {
		fmt.Printf("Error creating gRPC client: %v\n", err)
		return
	}
	defer grpcClient.Close()

	// Crear el handler HTTP
	h := handler.NewHandler(grpcClient)

	// Crear el servidor HTTP
	httpServer := server.NewHTTPServer(":8080", h)

	// Iniciar el servidor HTTP
	if err := httpServer.Start(); err != nil {
		fmt.Printf("Error starting HTTP server: %v\n", err)
	}
}
