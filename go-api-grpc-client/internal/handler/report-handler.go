package handler

import (
	"201905884_LAB_SO1_1S2026_PT3/go-api-grpc-client/internal/client"
	"201905884_LAB_SO1_1S2026_PT3/proto"
	"encoding/json"
	"net/http"
)

/* Struct WarReport */
type WarReport struct {
	Country           string `json:"country"`
	Warplanes_in_air  int32  `json:"warplanes_in_air"`
	Warships_in_water int32  `json:"warships_in_water"`
	Timestamp         string `json:"timestamp"`
}

/* Struct Handler
* Esta estructura representa un manejador HTTP que se encarga de procesar las solicitudes entrantes y comunicarse con el cliente gRPC para enviar los informes de guerra al servidor gRPC.
*
* Parámetros:
* 	- GRPCClient: Es una instancia del cliente gRPC que se utiliza para enviar solicitudes al servidor gRPC. Este cliente se configura para comunicarse con el servicio de informes de guerra definido en el archivo proto.
 */
type Handler struct {
	GRPCClient *client.GRPCClient
}

/* Función NewHandler
* NewHandler es el constructor de Handler. Recibe una instancia del cliente gRPC y devuelve una nueva instancia de Handler con el cliente gRPC configurado.
*
* Parámetros:
* 	- grpcClient: Es una instancia del cliente gRPC que se utiliza para enviar solicitudes al servidor gRPC. Este cliente se configura para comunicarse con el servicio de informes de guerra definido en el archivo proto.
*
* Retorna:
* 	- *Handler: Una nueva instancia de Handler con el cliente gRPC configurado.
 */
func NewHandler(grpcClient *client.GRPCClient) *Handler {
	return &Handler{
		GRPCClient: grpcClient,
	}
}

/* ServeHTTP
* Mapeo de campos del struct WarReport a los campos del mensaje gRPC WarReportRequest para enviar la solicitud al servidor gRPC.
 */
func (h *Handler) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	// Decodificar body de la solicitud HTTP en una instancia de WarReport
	var report WarReport
	err := json.NewDecoder(r.Body).Decode(&report)
	if err != nil {
		http.Error(w, "Invalid request body", http.StatusBadRequest)
		return
	}

	// Conversion de datos string country to enum proto.Countries_especific_country
	pais := mapCountryToEnum(report.Country)

	// Construir WarReportRequest a partir de los datos recibidos en la solicitud HTTP
	req := &proto.WarReportRequest{
		Country:         pais,
		WarplanesInAir:  report.Warplanes_in_air,
		WarshipsInWater: report.Warships_in_water,
		Timestamp:       report.Timestamp,
	}

	// Llamar al método SendReport del cliente gRPC para enviar la solicitud al servidor gRPC
	resp, err := h.GRPCClient.Client.SendReport(r.Context(), req)
	if err != nil {
		http.Error(w, "Failed to report war", http.StatusInternalServerError)
		return
	}

	// Codificar la respuesta del servidor gRPC en formato JSON y enviarla como respuesta HTTP
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(resp)
}

/* Mapear el campo Country del struct WarReport a un valor del enum proto.Countries
* Este mapeo se realiza para convertir el valor de country recibido en la solicitud HTTP a un valor compatible con el enum definido en el archivo proto.
* El enum proto.Countries define los países específicos que pueden ser reportados en el servicio gRPC.
* El mapeo se realiza utilizando una estructura de control de flujo (switch o if-else) para asignar el valor correcto del enum según el valor de country recibido.
 */
func mapCountryToEnum(country string) proto.Countries {
	switch country {
	case "USA":
		return proto.Countries_usa
	case "RUS":
		return proto.Countries_rus
	case "CHN":
		return proto.Countries_chn
	case "ESP":
		return proto.Countries_esp
	case "GTM":
		return proto.Countries_gtm
	default:
		return proto.Countries_countries_unknown
	}
}
