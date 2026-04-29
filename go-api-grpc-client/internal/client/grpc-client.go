package client

import (
	"201905884_LAB_SO1_1S2026_PT3/proto"
	"log"

	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"
)

/* Struct GRPCClient
* Esta estructura representa un cliente gRPC que se conecta al servidor * de informes de guerra.
*
* Parámetros:
* 	- conn: Es una conexión gRPC que se utiliza para comunicarse con el servidor.
* 	- client: Es un cliente gRPC generado a partir del archivo proto que define el servicio WarReportService. Este cliente se utiliza para realizar llamadas al servidor y obtener respuestas.
*	- Close(): Es un método que se utiliza para cerrar la conexión gRPC cuando ya no se necesita. Esto es importante para liberar recursos y evitar fugas de memoria.
 */
type GRPCClient struct {
	Conn   *grpc.ClientConn
	Client proto.WarReportServiceClient
}

/* Método NewClient
* Método constructora crea una nueva instancia de GRPCClient.
*
* 1. Llama a grpc.NewClient
* 2. Crea el cliente  con proto.NewWarReportServiceClient utilizando la conexión establecida.
* 3. Retorna el struct GRPCClient con la conexión y el cliente gRPC configurados.
* Parámetros:
* 	- address: Es la dirección del servidor gRPC al que se desea conectar, por ejemplo, "localhost:50051".
*
* Retorna:
* 	- *GRPCClient: Una instancia de GRPCClient con la conexión y el cliente gRPC configurados.
* 	- error: Un error si ocurre algún problema al establecer la conexión o crear el cliente gRPC.
 */
func NewClient(address string) (*GRPCClient, error) {
	// Establecer la conexión gRPC con el servidor
	conn, err := grpc.NewClient(address, grpc.WithTransportCredentials(insecure.NewCredentials()))

	if err != nil {
		log.Fatalf("Failed to connect to gRPC server: %v", err)
	}

	// Crea un nuevo cliente gRPC utilizando la conexión establecida
	client := proto.NewWarReportServiceClient(conn)

	// Retorna el struct GRPCClient con la conexión y el cliente gRPC configurados
	return &GRPCClient{
		Conn:   conn,
		Client: client,
	}, nil
}

/* Método Close
* Método para cerrar la conexión gRPC cuando ya no se necesita. Esto es importante para liberar recursos y evitar fugas de memoria.
*
* Comportamiento:
* 	- Llama al método Close() de la conexión gRPC para cerrar la conexión con el servidor.
 */
func (c *GRPCClient) Close() {
	if c.Conn != nil {
		c.Conn.Close()
	}
}
