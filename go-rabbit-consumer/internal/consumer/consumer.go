package consumer

import (
	amqp "github.com/rabbitmq/amqp091-go"
	"github.com/valkey-io/valkey-go"
	"google.golang.org/protobuf/encoding/protojson"

	"201905884_LAB_SO1_1S2026_PT3/proto"
)

/* Struct Consumer
* Consumer es la estructura que representa a un consumidor de mensajes en RabbitMQ.
 */
type Consumer struct {
	connection   *amqp.Connection
	channel      *amqp.Channel
	valkeyClient valkey.Client
}

/* Función NewConsumer
* NewConsumer es el constructor de Consumer. Recibe una conexión a RabbitMQ y un cliente de Valkey, y devuelve una nueva instancia de Consumer con la conexión, el canal y el cliente de Valkey configurados.
*
* Parámetros:
* 	- connection: Es una conexión a RabbitMQ que se utiliza para establecer la comunicación con el servidor RabbitMQ.
* 	- valkeyClient: Es un cliente de Valkey que se utiliza para realizar operaciones de cifrado y descifrado en los mensajes recibidos.
*
* Retorna:
* 	- *Consumer: Una nueva instancia de Consumer con la conexión, el canal y el cliente de Valkey configurados.
 */
func NewConsumer(connection *amqp.Connection, valkeyClient valkey.Client) (*Consumer, error) {
	channel, err := connection.Channel()
	if err != nil {
		return nil, err
	}

	return &Consumer{
		connection:   connection,
		channel:      channel,
		valkeyClient: valkeyClient,
	}, nil
}

/* Método Start de Consumer
* Start es un método de Consumer que inicia el proceso de consumo de mensajes desde RabbitMQ. Este método se encarga de configurar la cola, consumir los mensajes y procesarlos utilizando el cliente de Valkey para descifrar los mensajes recibidos.
 */
func (c *Consumer) Start(queueName string) error {
	// Suscribirse a la cola warreport_queue con channel.Consume
	msgs, err := c.channel.Consume(
		queueName, // queue
		"",        // consumer
		true,      // auto-ack
		false,     // exclusive
		false,     // no-local
		false,     // no-wait
		nil,       // args
	)
	if err != nil {
		return err
	}

	// Entrar en un loop que reciba los mensajes de la cola y los procese con la función processMessage
	go func() {
		for msg := range msgs {
			c.processMessage(msg)
		}
	}()

	return nil
}

/* Método processMessage de Consumer
* processMessage es un método de Consumer que se encarga de procesar un mensaje recibido desde RabbitMQ. Este método utiliza el cliente de Valkey para descifrar el mensaje y luego realiza las operaciones necesarias para manejar el contenido del mensaje.
 */
func (c *Consumer) processMessage(msg amqp.Delivery) {
	// Declarar variable req de tipo proto.WarReportRequest
	var req proto.WarReportRequest

	// Usar protojson.Unmarshal para convertir el cuerpo del mensaje (msg.Body) en una instancia de proto.WarReportRequest
	err := protojson.Unmarshal(msg.Body, &req)
	if err != nil {
		// Manejar el error de deserialización
		return
	}

	//imprimir el contenido del mensaje recibido
	println("Mensaje recibido:")
	println("Country:", req.Country)
	println("Warplanes in Air:", req.WarplanesInAir)
	println("Warships in Water:", req.WarshipsInWater)
	println("Timestamp:", req.Timestamp)

	// Falta agregar la lógica adicional para manejar el mensaje, como almacenar los datos en una base de datos o realizar otras operaciones necesarias.
}
