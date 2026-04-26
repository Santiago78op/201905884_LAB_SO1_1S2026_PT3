use actix_web::{post, web, Responder};
use crate::app::models::WarData; // Importar el modelo WarData
use crate::app::services::forward_report; // Importar los servicios de guerra

// Usa WarData para web, para que JSON valide la estructura de los datos
#[post("/grpc-201905884")]
async fn grpc_handler(data: web::Json<WarData>) -> impl Responder {
    // llamada forward_report con los datos recibidos
    match forward_report(data.into_inner()).await {
        Ok(_) => "Report forwarded successfully",
        Err(e) => {
            eprintln!("Error forwarding report: {e}");
            "Failed to forward report"
        }
    }
}