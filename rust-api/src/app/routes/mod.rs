// Modulo para las rutas de la aplicación
pub mod war_routes;

// Re-exportar las rutas para facilitar su uso
pub use self::war_routes::grpc_handler; // Re-exportar grpc_handler para que esté disponible en main.rs