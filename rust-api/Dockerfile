# =========================
# Build stage
# =========================
FROM --platform=$BUILDPLATFORM rust:1.95.0 AS builder

WORKDIR /app
RUN apt-get update && apt-get install -y gcc-x86-64-linux-gnu
RUN rustup target add x86_64-unknown-linux-gnu

COPY . .

RUN CARGO_TARGET_X86_64_UNKNOWN_LINUX_GNU_LINKER=x86_64-linux-gnu-gcc \
    cargo build --release --target x86_64-unknown-linux-gnu

# =========================
# Runtime stage
# =========================
FROM debian:bookworm-slim AS runtime

WORKDIR /app

COPY --from=builder /app/target/x86_64-unknown-linux-gnu/release/rust-api ./rust-api

CMD ["./rust-api"]