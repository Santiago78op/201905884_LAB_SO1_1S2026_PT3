use crate::app::models::WarData; // Importar el modelo WarData

pub async fn forward_report(data: WarData) -> Result<(), Box<dyn std::error::Error>> {
    let resp = reqwest::Client::new()
        .post("http://go-client:8080/grpc-201905884")
        .json(&data)
        .send()
        .await?;
    println!("{resp:#?}");
    Ok(())
}
