# Rust API

**Estado:** COMPLETO — compila sin errores ni warnings (2026-04-26)

Entrada: [[Gateway API]]
Salida: [[Go gRPC Client]]
Código: `../../rust-api/`

---

## Rol en el pipeline

Proxy HTTP inteligente. Recibe el JSON de Locust y lo reenvía al Go gRPC Client. No transforma ni almacena datos.

```
[Locust] → POST /grpc-201905884 → [Rust API] → HTTP POST → [Go Client :8080]
```

## Estructura de módulos

```
src/
  main.rs                  ← servidor Actix, bind 0.0.0.0:8080
  app/
    mod.rs                 ← declara models, routes, services
    models/
      mod.rs               ← re-exporta WarData
      war_data.rs          ← pub struct WarData
    routes/
      mod.rs               ← re-exporta grpc_handler
      war_routes.rs        ← #[post("/grpc-201905884")]
    services/
      mod.rs               ← re-exporta forward_report
      war_services.rs      ← reqwest POST a go-client:8080
```

## Dependencias (Cargo.toml)

```toml
actix-web = "4.13.0"
reqwest = { version = "0.13.2", default-features = false, features = ["json"] }
serde = { version = "1.0.228", features = ["derive"] }
serde_json = "1.0.149"
tokio = { version = "1.52.1", features = ["full"] }
```

## Decisiones técnicas

- `0.0.0.0:8080` — bind en todas las interfaces; necesario para recibir tráfico en Kubernetes
- `web::Json<WarData>` — Actix deserializa el body automáticamente al struct tipado
- `match` en lugar de `.unwrap()` — si el Go Client no responde, el servidor no hace panic
- `crate::app::...` — rutas absolutas dentro de submódulos (no `app::...`)
- `data.into_inner()` — extrae `WarData` del wrapper `web::Json<T>`
- Función `forward_report` en `services` separada del handler — bajo acoplamiento

## URL de reenvío

```
http://go-client:8080/grpc-201905884
```

En Kubernetes: `go-client` resuelve al Service del Go gRPC Client deployment.

## Próximo paso

- Prueba local: `cargo run` + `curl -X POST http://localhost:8080/grpc-201905884 -H "Content-Type: application/json" -d '{"country":"CHN","warplanes_in_air":42,"warships_in_water":14,"timestamp":"2026-03-12T20:15:30Z"}'`
- Dockerfile para construir la imagen
