global:
  scrape_interval: @@PROMETHEUS_SCRAPE_INTERVAL@@
  evaluation_interval: @@PROMETHEUS_EVALUATION_INTERVAL@@

alerting:
  alertmanagers:
    - static_configs:
        - targets:
            - @@TARGETS_ALERTMANAGER@@

rule_files:
  - /etc/prometheus/rules/*.yml

scrape_configs:
  - job_name: prometheus
    static_configs:
      - targets:
          - localhost:9090
        labels:
          environment: @@ENVIRONMENT@@
          cluster: @@CLUSTER@@

  - job_name: vid-metrics-simulator
    metrics_path: /metrics
    static_configs:
      - targets:
          - @@TARGETS_METRICS_SIMULATOR@@
        labels:
          environment: @@ENVIRONMENT@@
          cluster: @@CLUSTER@@
