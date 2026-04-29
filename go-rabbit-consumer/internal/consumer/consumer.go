package consumer

import (
	"context"
	"encoding/json"
	"strconv"

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

/* Struct Reporte
* Reporte es una estructura que representa un reporte de guerra con información sobre el país, el número de aviones en el aire y el número de barcos en el agua y el tiempo.
 */
type Reporte struct {
	Country         string `json:"country"`
	WarplanesInAir  int32  `json:"warplanesInAir"`
	WarshipsInWater int32  `json:"warshipsInWater"`
	Timestamp       string `json:"timestamp"`
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
func (c *Consumer) Start(ctx context.Context, queueName string) error {
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
			c.processMessage(ctx, msg)
		}
	}()

	return nil
}

/* Método processMessage de Consumer
* processMessage es un método de Consumer que se encarga de procesar un mensaje recibido desde RabbitMQ. Este método utiliza el cliente de Valkey para descifrar el mensaje y luego realiza las operaciones necesarias para manejar el contenido del mensaje.
 */
func (c *Consumer) processMessage(ctx context.Context, msg amqp.Delivery) {
	// Declarar variable req de tipo proto.WarReportRequest
	var req proto.WarReportRequest

	// Usar protojson.Unmarshal para convertir el cuerpo del mensaje (msg.Body) en una instancia de proto.WarReportRequest
	err := protojson.Unmarshal(msg.Body, &req)
	if err != nil {
		// Manejar el error de deserialización
		return
	}

	/*
	*   Grupo 1 — Strings (máximos y mínimos): 4 operaciones
	*	Grupo 2 — Sorted Sets (rankings): 2 operaciones
	*	Grupo 3 — Hash (modas): 2 operaciones
	*	Grupo 4 — List (serie temporal): 1 operación
	*	Grupo 5 — Contador país asignado (CHN): 1 operación
	 */
	// Grupo 1 — Strings (máximos): 4
	c.updateMax(ctx, c.valkeyClient, "max_warplanes_in_air", req.WarplanesInAir)
	c.updateMax(ctx, c.valkeyClient, "max_warships_in_water", req.WarshipsInWater)
	// Grupo 1 — Strings (mínimos): 4
	c.updateMin(ctx, c.valkeyClient, "min_warplanes_in_air", req.WarplanesInAir)
	c.updateMin(ctx, c.valkeyClient, "min_warships_in_water", req.WarshipsInWater)

	// Grupo 2 — Sorted Sets (rankings): 2
	c.updateRanking(ctx, c.valkeyClient, "rss_rank", req.Country.String(), req.WarplanesInAir)
	c.updateRanking(ctx, c.valkeyClient, "cpu_rank", req.Country.String(), req.WarshipsInWater)

	// Grupo 3 — Hash (modas): 2
	c.updateModa(ctx, c.valkeyClient, "warplanes_in_air_moda", req.WarplanesInAir)
	c.updateModa(ctx, c.valkeyClient, "warships_in_water_moda", req.WarshipsInWater)

	// Cada Reporte que llega es una fotografia temporal
	// Grupo 4 — List (serie temporal): 1
	if req.Country == proto.Countries_chn {
		c.updateTimeSeries(ctx, &req)
	}

	// Grupo 5 — Contador país asignado (CHN): 1
	if req.Country == proto.Countries_chn {
		c.valkeyClient.Do(ctx, c.valkeyClient.B().Incr().Key("total_chn").Build())
	}
}

/* Función updateMax
* Grupo 1 — Strings (máximos): 4 operaciones
 */
func (c *Consumer) updateMax(ctx context.Context, client valkey.Client, key string, value int32) error {
	// Obtener el valor actual almacenado en Redis para la clave dada utilizando client.Do con una operación de tipo Get. Convertir el resultado a un entero utilizando result.AsInt64().
	result := client.Do(ctx, client.B().Get().Key(key).Build())
	currentValue, err := result.AsInt64()

	if err != nil {
		// Valida que el error es valkey.Nil
		if valkey.IsValkeyNil(err) {
			return client.Do(ctx, client.B().Set().Key(key).Value(strconv.FormatInt(int64(value), 10)).Build()).Error()
		} else {
			// Manejar el error de obtención del valor actual
			return err
		}
	}

	// Comparar el valor actual con el nuevo valor recibido. Si el nuevo valor es mayor, actualizar el valor almacenado en Redis utilizando client.Do con una operación de tipo Set.
	if currentValue < int64(value) {
		// Actualizar el valor almacenado en Redis utilizando client.Do con una operación de tipo Set. Convertir el nuevo valor a una cadena utilizando strconv.FormatInt.
		return client.Do(ctx, client.B().Set().Key(key).Value(strconv.FormatInt(int64(value), 10)).Build()).Error()
	}

	return nil
}

/* Función updateMin
* Grupo 1 — Strings (mínimos): 4 operaciones
 */
func (c *Consumer) updateMin(ctx context.Context, client valkey.Client, key string, value int32) error {
	// Obtener el valor actual almacenado en Redis para la clave dada utilizando client.Do con una operación de tipo Get. Convertir el resultado a un entero utilizando result.AsInt64().
	result := client.Do(ctx, client.B().Get().Key(key).Build())
	currentValue, err := result.AsInt64()

	if err != nil {
		// Valida que el error es valkey.Nil
		if valkey.IsValkeyNil(err) {
			return client.Do(ctx, client.B().Set().Key(key).Value(strconv.FormatInt(int64(value), 10)).Build()).Error()
		} else {
			// Manejar el error de obtención del valor actual
			return err
		}
	}

	// Comparar el valor actual con el nuevo valor recibido. Si el nuevo valor es menor, actualizar el valor almacenado en Redis utilizando client.Do con una operación de tipo Set.
	if currentValue > int64(value) {
		// Actualizar el valor almacenado en Redis utilizando client.Do con una operación de tipo Set. Convertir el nuevo valor a una cadena utilizando strconv.FormatInt.
		return client.Do(ctx, client.B().Set().Key(key).Value(strconv.FormatInt(int64(value), 10)).Build()).Error()
	}

	return nil
}

/* Función updateRanking
* Grupo 2 — Sorted Sets (rankings): 2 operaciones
 */
func (c *Consumer) updateRanking(ctx context.Context, client valkey.Client, key string, member string, score int32) error {
	// ZADD lo que hace es que guarda el ultimo score, pero necesito la suma total de los scores
	// Para ello uso ZINCRBY que incrementa el score de un miembro en el sorted set.
	return client.Do(ctx, client.B().Zincrby().Key(key).Increment(float64(score)).Member(member).Build()).Error()
}

/* Función updateModa
* Grupo 3 — Hash (modas): 2 operaciones
* Para implementar la función updateModa, se puede utilizar el comando HINCRBY de Redis para incrementar el contador de cada valor recibido. El campo del hash será el valor numérico convertido a una cadena, y el valor del campo será el contador que se incrementa cada vez que se recibe ese valor.
 */
func (c *Consumer) updateModa(ctx context.Context, client valkey.Client, key string, value int32) error {
	// Convertir el valor numérico a una cadena utilizando strconv.FormatInt.
	valueStr := strconv.FormatInt(int64(value), 10)

	// Incrementar el contador del valor recibido
	valueIncremente := client.Do(ctx, client.B().Hincrby().Key(key).Field(valueStr).Increment(1).Build())

	// Validar si hay error
	if valueIncremente.Error() != nil {
		return valueIncremente.Error()
	}

	// Obtener el conteo actual de ese valor después del incremento
	currentCount, err := valueIncremente.AsInt64()
	if err != nil {
		return err
	}

	// Comparar con el conteo alamacenado en la key ganadora
	winnerCountResult := client.Do(ctx, client.B().Get().Key(key+"_winner_count").Build())
	winnerCount, err := winnerCountResult.AsInt64()
	if err != nil && !valkey.IsValkeyNil(err) {
		return err
	}

	// Si el nuevo conteo es mayor, procedo a actualizar la key ganadora con el nuevo valor y su conteo
	if currentCount > winnerCount {
		// Actualizar la key ganadora con el nuevo valor y su conteo
		err := client.Do(ctx, client.B().Set().Key(key+"_winner").Value(valueStr).Build()).Error()
		if err != nil {
			return err
		}
		err = client.Do(ctx, client.B().Set().Key(key+"_winner_count").Value(strconv.FormatInt(currentCount, 10)).Build()).Error()
		if err != nil {
			return err
		}
	}

	return nil
}

/* Función updateTimeSeries
* Grupo 4 — List (serie temporal): 1 operación
* Se usa el struct Reporte para almacenar la información de cada reporte recibido. Cada vez que se recibe un nuevo reporte, se convierte a JSON y se inserta al frente de la lista utilizando LPUSH.
 */
func (c *Consumer) updateTimeSeries(ctx context.Context, req *proto.WarReportRequest) error {
	// Crear una instancia de Reporte con la información del reporte recibido
	reporte := Reporte{
		Country:         req.Country.String(), // País asignado
		WarplanesInAir:  req.WarplanesInAir,   // Número de aviones en el aire
		WarshipsInWater: req.WarshipsInWater,  // Número de barcos en el agua (puede ser ajustado según la información disponible)
		Timestamp:       req.Timestamp,        // Timestamp actual (puede ser ajustado según la información disponible)
	}

	// Convertir el reporte a JSON
	reporteJSON, err := json.Marshal(reporte)
	if err != nil {
		return err
	}

	// Insertar el reporte al frente de la lista utilizando LPUSH
	// El consumer tiene acceso a Valkey a través de c, y la key siempre es "meminfo"
	return c.valkeyClient.Do(ctx, c.valkeyClient.B().Lpush().Key("meminfo").Element(string(reporteJSON)).Build()).Error()
}
