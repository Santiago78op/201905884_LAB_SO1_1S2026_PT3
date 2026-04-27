# =========================
# Build stage
# =========================
FROM rust:1.95.0 AS builder

WORKDIR /app

COPY . .

RUN cargo build --release


# =========================
# Runtime stage
# =========================
FROM debian:bookworm-slim AS runtime

WORKDIR /app

COPY --from=builder /app/target/release/rust-api ./rust-api

CMD ["./rust-api"]