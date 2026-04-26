// Modulo para los servicios de la aplicación
pub mod war_services; // Re-exports the WarService struct for easier access

// Re-exportar el servicio para facilitar su uso
pub use self::war_services::forward_report; // Make forward_report available at the crate root