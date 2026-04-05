use actix_web::{web, App, HttpResponse, HttpServer};
use serde::{Deserialize, Serialize};
use tonic::transport::Channel;

// ── PASO 1: Incluir el código generado por tonic-build ───────────────────────
//
// include_proto!("wartweets") busca en $OUT_DIR el archivo generado
// a partir del package "wartweets" del .proto.
// Esto nos da:
//   - WarReportRequest, WarReportResponse  (structs de los mensajes)
//   - WarReportServiceClient               (el cliente gRPC listo para usar)
pub mod warreport {
    tonic::include_proto!("wartweets");
}

use warreport::war_report_service_client::WarReportServiceClient;
use warreport::WarReportRequest as GrpcRequest;

// ── PASO 2: Definir el payload HTTP ─────────────────────────────────────────
//
// Esta struct representa el JSON que llega por POST /reports.
// #[derive(Deserialize)] le enseña a actix-web a leer el cuerpo JSON
// y mapearlo aquí automáticamente.
#[derive(Deserialize)]
struct ReportPayload {
    country: String,
    warplanes_in_air: i32,
    warships_in_water: i32,
    timestamp: String,
}

// La respuesta JSON que devolvemos al cliente HTTP.
#[derive(Serialize)]
struct ApiResponse {
    status: String,
    message: String,
}

// ── PASO 3: Estado compartido de la aplicación ───────────────────────────────
//
// AppState vive durante toda la vida del servidor.
// Lo compartimos entre todos los workers de actix-web con web::Data<>.
//
// WarReportServiceClient<Channel> es clonable y thread-safe:
// internamente usa un connection pool, por lo que clonar es barato.
#[derive(Clone)]
struct AppState {
    grpc_client: WarReportServiceClient<Channel>,
}

// ── PASO 4: Handler del endpoint POST /reports ───────────────────────────────
//
// actix-web inyecta automáticamente los parámetros por tipo:
//   - web::Data<AppState>        → estado compartido
//   - web::Json<ReportPayload>   → body JSON deserializado
async fn post_report(
    state: web::Data<AppState>,
    body: web::Json<ReportPayload>,
) -> HttpResponse {
    // ── 4a. Validación del payload ───────────────────────────────────────────
    //
    // Validamos aquí y no en el servidor gRPC porque la API REST es el
    // punto de entrada público. Fallar rápido ahorra recursos.
    let valid_countries = ["usa", "rus", "chn", "esp", "gtm"];
    let country_lower = body.country.to_lowercase();

    if !valid_countries.contains(&country_lower.as_str()) {
        return HttpResponse::BadRequest().json(ApiResponse {
            status: "error".into(),
            message: format!(
                "País inválido: '{}'. Valores aceptados: usa, rus, chn, esp, gtm",
                body.country
            ),
        });
    }

    if !(0..=50).contains(&body.warplanes_in_air) {
        return HttpResponse::BadRequest().json(ApiResponse {
            status: "error".into(),
            message: "warplanes_in_air debe estar entre 0 y 50".into(),
        });
    }

    if !(0..=30).contains(&body.warships_in_water) {
        return HttpResponse::BadRequest().json(ApiResponse {
            status: "error".into(),
            message: "warships_in_water debe estar entre 0 y 30".into(),
        });
    }

    if body.timestamp.trim().is_empty() {
        return HttpResponse::BadRequest().json(ApiResponse {
            status: "error".into(),
            message: "timestamp no puede estar vacío".into(),
        });
    }

    // ── 4b. Llamada gRPC al servidor Go ──────────────────────────────────────
    //
    // Clonamos el cliente (barato: comparte el Channel subyacente).
    // Lo declaramos mut porque send_report requiere &mut self.
    let mut client = state.grpc_client.clone();

    // Construimos el mensaje proto con los datos validados.
    let grpc_request = tonic::Request::new(GrpcRequest {
        country: country_lower,
        warplanes_in_air: body.warplanes_in_air,
        warships_in_water: body.warships_in_water,
        timestamp: body.timestamp.clone(),
    });

    match client.send_report(grpc_request).await {
        Ok(response) => {
            let grpc_status = response.into_inner().status;
            println!(
                "[OK] Reporte enviado → país={} aviones={} barcos={} | gRPC status={}",
                body.country, body.warplanes_in_air, body.warships_in_water, grpc_status
            );
            HttpResponse::Ok().json(ApiResponse {
                status: "success".into(),
                message: format!("Reporte procesado. Servidor gRPC respondió: {}", grpc_status),
            })
        }
        Err(e) => {
            eprintln!("[ERROR] Fallo al contactar gRPC server: {}", e);
            HttpResponse::InternalServerError().json(ApiResponse {
                status: "error".into(),
                message: format!("No se pudo contactar el servidor gRPC: {}", e),
            })
        }
    }
}

// ── PASO 5: Arrancar todo ────────────────────────────────────────────────────
//
// #[tokio::main] convierte main() en una función async.
// actix-web y tonic requieren un runtime async; tokio es el estándar.
#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let grpc_addr = "http://127.0.0.1:50051";
    let http_port = "0.0.0.0:8080";

    println!("Conectando al gRPC server en {}...", grpc_addr);

    // Channel::from_static abre la conexión TCP al servidor Go.
    // Si Go no está corriendo, esto fallará aquí con un error claro.
    let channel = Channel::from_static("http://127.0.0.1:50051")
        .connect()
        .await?;

    let grpc_client = WarReportServiceClient::new(channel);

    let state = AppState { grpc_client };

    println!("✓ Rust REST API escuchando en http://{}", http_port);
    println!("  Endpoint: POST /reports");

    HttpServer::new(move || {
        App::new()
            // web::Data envuelve el estado en un Arc internamente.
            // Todos los workers de actix-web comparten el mismo AppState.
            .app_data(web::Data::new(state.clone()))
            .route("/reports", web::post().to(post_report))
    })
    .bind(http_port)?
    .run()
    .await?;

    Ok(())
}
