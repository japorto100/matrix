// Phase 20 stub — Rust Compute Service config
//
// When rust_core becomes a standalone Tonic gRPC service (Phase 20),
// this module will expose a Config struct loaded via the `config` crate.
//
// Planned fields:
//   grpc_port:          RUST_COMPUTE_GRPC_PORT   (default: 9094)
//   nats_url:           NATS_URL                 (default: nats://127.0.0.1:4222)
//   go_gateway_url:     GO_GATEWAY_BASE_URL      (default: http://127.0.0.1:9060)
//   otel_enabled:       OTEL_ENABLED             (default: false)
//
// TODO(P20): add `config` crate to Cargo.toml, implement Config::from_env().
