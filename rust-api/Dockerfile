# =========================
# Build stage
# =========================
FROM --platform=linux/amd64 rust:1.95 AS builder

WORKDIR /app

COPY . .

# Build the application for release
RUN cargo build --release

# =========================
# Runtime stage
# =========================
# Stage 2: Runtime stage
# Use a slim Debian or Distroless image for the smallest footprint
FROM --platform=linux/amd64 debian:bookworm-slim AS runtime

WORKDIR /app

# Install necessary runtime dependencies (e.g., SSL for web apps)
RUN apt-get update && apt-get install -y ca-certificates && rm -rf /var/lib/apt/lists/*

# Copy the binary from the builder stage
COPY --from=builder /app/target/release/rust-api ./rust-api

CMD ["./rust-api"]