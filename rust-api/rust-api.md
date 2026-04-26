# Rust API - Punto de entrada del sistema
El punto de entrada del sistema es el archivo `main.rs`, que se encuentra en la raíz del proyecto. Este archivo contiene la función `main`, que es el punto de inicio de la aplicación.

La Rust API es un servidor HTTP que expone **un solo endpoint:** `POST /grpc-201905884`. Su única responsabilidad es recibir el JSON de Locust y reenviarlo — vía HTTP — al Go gRPC Client que corre
en `:8080`.

Es un **proxy HTTP inteligente:** recibe, valida mínimamente, y reenvía.

```
Ubicación en el pipeline:                                                                                                                                                                     
  [Locust] → POST /grpc-201905884
                  ↓                                                                                                                                                                             
            [Rust API]  ← AQUÍ
                  ↓
       [Go gRPC Client :8080] 
```

## Teoría
La Rust API tiene un rol simple pero crítico: recibir un JSON por HTTP y reenviarlo al siguiente servicio. No transforma los datos, no los almacena — es un proxy.

Para construirla necesitas tres capacidades:

1. **Servidor HTTP** — escuchar peticiones en un puerto 

2. **Deserialización JSON** — convertir el body a un struct Rust

3. **Cliente HTTP** — reenviar la petición al Go gRPC Client

En Rust, el framework web más popular para esto es Actix-web.

## El Cargo.toml:

El `Cargo.toml` tiene la sección `[dependencies]` vacía. Antes de se necesitas declarar las dependencias.

Para las tres capacidades, se necesitan estos crates: 

- `actix-web` — servidor HTTP 
- `serde` + `serde_json` — serialización JSON
- `reqwest` — cliente HTTP para reenviar al Go service
- `tokio` — runtime asíncrono (Actix y reqwest lo requieren)

**Nota:** Locust es el productor, y el Go Client es el consumidor — la Rust API es el canal.

## Teoría: async y el problema de la espera

Imagina que tu programa hace una petición HTTP. Mientras espera la respuesta del servidor remoto, ¿qué debería hacer el proceso?

**Opción A — Bloquear**: El hilo se queda parado, sin hacer nada, consumiendo su slot en el scheduler del SO. Si llegan 1,000 requests simultáneos, necesitas 1,000 hilos. Eso es caro en memoria y en cambios de contexto. 

**Opción B — No bloquear (`async`)**: El hilo registra "cuando llegue la respuesta, continúa aquí" y se va a atender otro request. Un solo hilo puede manejar miles de requests concurrentes.

Esto es lo que en SO1 se llama **I/O no bloqueante**. El kernel ofrece mecanismos como `epoll `(Linux) que notifican al proceso cuando un descriptor de archivo tiene datos listos — sin que el proceso tenga que estar esperando activamente.

## Uso de Tokio
                           
En Rust, `async fn` no hace nada por sí sola — solo define una **tarea diferida**. Alguien tiene que ejecutarla, pausarla cuando bloquea, y reanudarla cuando hay datos. Ese "alguien" es el **runtime asíncrono**. 

Tokio es ese runtime: internamente usa un `thread pool + epoll` para manejar miles de tareas concurrentes con pocos hilos del SO. 

El código async  →  Tokio Runtime  →  epoll (kernel)  →  red/disco 

Es el mismo concepto que un **scheduler de procesos**, pero a nivel de tareas dentro de un solo proceso.

El payload que llega a Locust es:

```json
{
      "country": "CHN", 
      "warplanes_in_air": 42,
      "warships_in_water": 14,
      "timestamp": "2026-03-12T20:15:30Z"                       
}
```

Para ello se necesita un **struct** en Rust que represente ese JSON, para que Rust pueda convertir autimáticamente el JSON a ese struct (deserealizar) y **struct** a JSON (serializar), usando los traits derivados de `serde`. 

```rust
#[derive(Serialize, Deserialize)]
struct WarData {
      country: String,
      warplanes_in_air: u32,
      warships_in_water: u32,
      timestamp: String,
}
```

---

## Sesión 6 — Implementación completa (2026-04-26)

### Modularización en Rust

Un proyecto Rust puede organizarse en módulos usando archivos y subdirectorios. Cada carpeta que contiene módulos necesita un archivo `mod.rs` que actúe como raíz de ese módulo.

**Regla:** el nombre de cada archivo `.rs` es el nombre del módulo. Los nombres deben usar `snake_case` — los guiones (`-`) no son válidos como identificadores.

La estructura final de la rust-api:

```
src/
  main.rs                  ← punto de entrada, orquesta el servidor
  app/
    mod.rs                 ← declara los tres submódulos
    models/
      mod.rs               ← re-exporta WarData
      war_data.rs          ← define el struct WarData
    routes/
      mod.rs               ← re-exporta grpc_handler
      war_routes.rs        ← define el endpoint POST
    services/
      mod.rs               ← re-exporta forward_report
      war_services.rs      ← lógica de reenvío HTTP
```

**Separación de responsabilidades:**
- `models` — representa los datos del dominio
- `routes` — define qué URLs expone el servidor y qué función las atiende
- `services` — contiene la lógica de negocio (el reenvío al Go Client)

### El sistema de módulos de Rust

| Keyword | Propósito |
|---|---|
| `mod nombre;` | Registra un archivo como módulo (sin esto, Rust lo ignora) |
| `pub mod nombre;` | Lo registra y lo hace visible desde fuera |
| `use ruta::Tipo;` | Atajo para no escribir la ruta completa |
| `pub use ruta::Tipo;` | Re-exporta un símbolo (lo hace accesible desde el módulo actual) |

**Regla de rutas dentro de módulos:** desde `main.rs` puedes escribir `app::models::WarData`. Desde cualquier submódulo debes usar `crate::` para subir a la raíz: `crate::app::models::WarData`.

### El struct WarData

```rust
use serde::{Deserialize, Serialize};

#[derive(Serialize, Deserialize, Debug)]
pub struct WarData {
    country: String,
    warplanes_in_air: u32,
    warships_in_water: u32,
    timestamp: String,
}
```

- `pub struct` — visible desde otros módulos
- `Serialize` — Rust puede convertir el struct a JSON
- `Deserialize` — Actix puede convertir el JSON del body al struct automáticamente
- `Debug` — permite usar `{:?}` en `println!`

### El endpoint en war_routes.rs

```rust
#[post("/grpc-201905884")]
async fn grpc_handler(data: web::Json<WarData>) -> impl Responder {
    match forward_report(data.into_inner()).await {
        Ok(_) => "Report forwarded successfully",
        Err(e) => {
            eprintln!("Error forwarding report: {e}");
            "Failed to forward report"
        }
    }
}
```

- `web::Json<WarData>` — Actix deserializa el body automáticamente al struct
- `.into_inner()` — extrae el `WarData` del wrapper `web::Json`
- `match` en lugar de `.unwrap()` — si el Go Client no está disponible, el servidor no hace panic; devuelve un error controlado

### El servicio en war_services.rs

```rust
pub async fn forward_report(data: WarData) -> Result<(), Box<dyn std::error::Error>> {
    let resp = reqwest::Client::new()
        .post("http://go-client:8080/grpc-201905884")
        .json(&data)
        .send()
        .await?;
    println!("{resp:#?}");
    Ok(())
}
```

- `reqwest::Client::new()` — crea un cliente HTTP
- `.post(url).json(&data).send()` — hace POST con el body JSON
- `.await?` — espera la respuesta de forma no bloqueante; si falla, propaga el error
- `Ok(())` — retorna éxito sin valor

**Por qué `reqwest::get` no sirve aquí:** `get` es para peticiones sin body. Para enviar datos se necesita `client.post(url).json(&data).send()`.

### El main.rs

```rust
#[actix_web::main]
async fn main() -> std::io::Result<()> {
    HttpServer::new(|| {
        App::new()
            .service(grpc_handler)
    })
    .bind("0.0.0.0:8080")?
    .run()
    .await
}
```

- `#[actix_web::main]` — convierte `main` en una función async usando Tokio internamente
- `0.0.0.0:8080` — escucha en todas las interfaces; necesario en Kubernetes para recibir tráfico externo
- `127.0.0.1` solo acepta conexiones del mismo host — inútil en un Pod