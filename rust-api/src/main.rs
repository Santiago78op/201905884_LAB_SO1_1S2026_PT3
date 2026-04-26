mod app; // Declare the app module

use actix_web::{App, HttpServer}; // Importar Actix-web para el servidor HTTP
use app::routes::grpc_handler;

#[actix_web::main] // O #[tokio::main] si prefieres usar Tokio
async fn main() -> std::io::Result<()> {
    HttpServer::new(|| {
        App::new()
            .service(grpc_handler) // Registrar el handler gRPC
    })
    .bind("0.0.0.0:8080")? // Escuchar en localhost:8080
    .run()
    .await
}