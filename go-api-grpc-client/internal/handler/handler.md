# Handler
Este directorio contiene los handlers de la aplicación, que son responsables de manejar las solicitudes entrantes y enviar respuestas. Cada handler se encarga de una funcionalidad específica, como crear un nuevo usuario, obtener información de un usuario existente, actualizar datos de un usuario o eliminar un usuario. Los handlers interactúan con el servicio gRPC para realizar las operaciones necesarias y devolver los resultados al cliente.

## Struc Handler Report
Como ``report-handler.go`` es el puente entre el mundo HTTP (lo que llega del Rust API) y el mundo gRPC (lo que envías al servidor Go). Para eso se necesita parsear el JSON del body de la request HTTP.

Para ello Go tiene una forma **nativa** de parsear JSON a través de structs. Entonces, para parsear el JSON del body de la request HTTP, se define un struct que refleje la estructura del JSON esperado. Por ejemplo:

```go
type Report struct {
    UserID    string `json:"user_id"`
    Action    string `json:"action"`
    Timestamp int64  `json:"timestamp"`
}
```

**Ejemplo de JSON**:
```json
{
    "user_id": "12345",
    "action": "login",
    "timestamp": 1627847261
}
```
En este ejemplo, el struct `Report` tiene tres campos: `UserID`, `Action` y `Timestamp`. Las etiquetas JSON (`json:"field_name"`) indican cómo se deben mapear los campos del JSON a los campos del struct. Cuando se recibe una solicitud HTTP con un body JSON, se puede usar la función `json.Unmarshal` para convertir el JSON en una instancia del struct `Report`, lo que facilita el acceso a los datos de la solicitud y su posterior procesamiento.