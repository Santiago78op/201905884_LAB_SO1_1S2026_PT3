# HTTP Server para gRPC Client
Este componente es un servidor HTTP que se encarga de recibir las solicitudes entrantes desde la Rust API, procesarlas y luego utilizar el cliente gRPC para enviar los datos al servidor gRPC. El servidor HTTP actúa como un intermediario entre la Rust API y el cliente gRPC, permitiendo que las solicitudes HTTP sean traducidas a llamadas gRPC y viceversa.

## Secuencia de funcionamiento
1. **Escuchar** en un puerto TCP esperar solicitudes HTTP entrantes.
2. **Resgistrar** un handler específico para la ruta que se encargará de procesar las solicitudes relacionadas con los informes de guerra.
3. **Arrancar** el servidor HTTP para que esté listo para recibir solicitudes.