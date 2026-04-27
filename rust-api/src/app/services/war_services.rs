use crate::app::models::WarData; // Importar el modelo WarData
use std::env;

pub async fn forward_report(data: WarData) -> Result<(), Box<dyn std::error::Error>> {
    let grpc_client_host = env::var("GRPC_CLIENT_HOST").unwrap_or_else(|_| "go-client:8080".into());
    let resp = reqwest::Client::new()
        .post(format!("http://{}/grpc-201905884", grpc_client_host))
        .json(&data)
        .send()
        .await?;
    println!("{resp:#?}");
    Ok(())
}
