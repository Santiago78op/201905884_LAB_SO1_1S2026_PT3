// build.rs es ejecutado por Cargo ANTES de compilar src/.
// Su único trabajo aquí es invocar tonic-build para generar
// el código Rust correspondiente a warreport.proto.
//
// El código generado se coloca en $OUT_DIR (una carpeta temporal
// gestionada por Cargo) y se incluye en main.rs con include_proto!().

fn main() -> Result<(), Box<dyn std::error::Error>> {
    tonic::build::compile_protos(
        &["../proto/warreport.proto"],  // archivo(s) .proto a compilar
        &["../proto"],                  // directorios donde buscar imports
    )?;
    Ok(())
}
