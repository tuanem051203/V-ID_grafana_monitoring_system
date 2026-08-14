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
  ring:
    kvstore:
      store: inmemory
  processor:
    local_blocks:
      filter_server_spans: false
      flush_to_storage: true

overrides:
  defaults:
    metrics_generator:
      processors:
        - local-blocks
