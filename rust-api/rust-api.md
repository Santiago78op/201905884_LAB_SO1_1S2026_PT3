# Rust API - Punto de entrada del sistema
El punto de entrada del sistema es el archivo `main.rs`, que se encuentra en la raíz del proyecto. Este archivo contiene la función `main`, que es el punto de inicio de la aplicación.

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