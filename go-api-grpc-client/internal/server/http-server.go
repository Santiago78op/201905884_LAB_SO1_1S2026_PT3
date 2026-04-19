package server

import (
	"201905884_LAB_SO1_1S2026_PT3/go-api-grpc-client/internal/handler"
	"errors"
	"net/http"
)

/* Struct HTTPServer
* HTTPServer es el servidor HTTP que recibe las solicitudes de Locust y las reenvía al Go gRPC Client. Es el punto de entrada del sistema y se encarga de manejar la comunicación con el mundo exterior.
 */
type HTTPServer struct {
	Direccion string
	Handler   *handler.Handler
}

/* Funcion NewHTTPServer
* NewHTTPServer es el constructor de HTTPServer. Recibe la dirección en la que se va a ejecutar el servidor y el handler que se encargará de procesar las solicitudes. Devuelve una instancia de HTTPServer lista para ser utilizada.
 */
func NewHTTPServer(direccion string, handler *handler.Handler) *HTTPServer {
	return &HTTPServer{
		Direccion: direccion,
		Handler:   handler,
	}
}

/* Metodo Start
* Start es el método que inicia el servidor HTTP. Se encarga de configurar las rutas y de escuchar las solicitudes entrantes. Es el punto de partida para que el servidor comience a funcionar.
 */
func (s *HTTPServer) Start() error {
	// Creacion del mux
	mux := http.NewServeMux()

	// Registra la ruta apuntando al handler
	mux.HandleFunc("/grpc-201905884", s.Handler.ServeHTTP)

	// Creacion del servidor HTTP
	httpServer := &http.Server{
		Addr:    s.Direccion,
		Handler: mux,
	}

	// llamada a ListenAndServe para iniciar el servidor HTTP
	if err := httpServer.ListenAndServe(); err != nil {
		if errors.Is(err, http.ErrServerClosed) {
			return nil // El servidor se cerró correctamente
		}
		return err // Error al iniciar el servidor
	}

	return nil
}
