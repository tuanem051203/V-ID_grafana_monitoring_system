server:
  http_listen_port: 3200
distributor:
  receivers:
    otlp:
      protocols:
        grpc:
          endpoint: 0.0.0.0:4317
        http:
          endpoint: 0.0.0.0:4318
storage:
  trace:
    backend: local
    local:
      path: /var/tempo/traces
    wal:
      path: /var/tempo/wal
compactor:
  compaction:
    block_retention: 24h

# Tempo 2.8 TraceQL metrics (for Grafana Traces Drilldown queries such as
# `{ ... } | rate()`). A trace search works without this component, but range
# metrics queries require a metrics-generator registered in the ring and the
# local-blocks processor enabled for the tenant.
metrics_generator:
  storage:
    # Tempo 2.x disables the metrics-generator when this WAL path is absent,
    # even when it is used only for TraceQL local-blocks queries.
    path: /var/tempo/generator/wal
  ring:
    kvstore:
      store: inmemory
    # The distroless container may not resolve a usable interface automatically.
    # Advertise the in-process gRPC listener so monolithic Tempo joins its own ring.
    instance_addr: 127.0.0.1
    instance_port: 9095
  processor:
    local_blocks:
      filter_server_spans: false
      flush_to_storage: true

overrides:
  defaults:
    metrics_generator:
      processors:
        - local-blocks
