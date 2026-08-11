name: @@PROJECT_NAME@@

services:
  metrics-simulator:
    build:
      context: ../../services/metrics-simulator
    environment:
      APP_ENV: @@ENVIRONMENT@@
      CONFIG_FILE: /app/config/runtime.json
      LOG_LEVEL: ${LOG_LEVEL:-INFO}
    volumes:
      - ../../services/metrics-simulator/config/runtime.json:/app/config/runtime.json:ro
    ports:
      - "@@PORTS_METRICS_SIMULATOR@@:8000"
    restart: unless-stopped

  alertmanager:
    image: @@IMAGES_ALERTMANAGER@@
    working_dir: /etc/alertmanager
    command:
      - --config.file=/etc/alertmanager/alertmanager.yml
      - --storage.path=/alertmanager
    volumes:
      - ./alertmanager:/etc/alertmanager:ro
      - alertmanager-data:/alertmanager
    secrets:
      - smtp_password
    ports:
      - "@@PORTS_ALERTMANAGER@@:9093"
    restart: unless-stopped

  prometheus:
    image: @@IMAGES_PROMETHEUS@@
    command:
      - --config.file=/etc/prometheus/prometheus.yml
    volumes:
      - ./prometheus:/etc/prometheus:ro
      - prometheus-data:/prometheus
    ports:
      - "@@PORTS_PROMETHEUS@@:9090"
    depends_on:
      - metrics-simulator
      - alertmanager
    restart: unless-stopped

  grafana:
    image: @@IMAGES_GRAFANA@@
    environment:
      GF_SECURITY_ADMIN_USER: @@GRAFANA_ADMIN_USER@@
      GF_SECURITY_ADMIN_PASSWORD__FILE: /run/secrets/grafana_admin_password
    secrets:
      - grafana_admin_password
    volumes:
      - grafana-data:/var/lib/grafana
      - ../../observability/grafana/provisioning/dashboards:/etc/grafana/provisioning/dashboards:ro
      - ./grafana/prometheus.yml:/etc/grafana/provisioning/datasources/prometheus.yml:ro
      - ../../observability/grafana/dashboards:/var/lib/grafana/dashboards:ro
    ports:
      - "@@PORTS_GRAFANA@@:3000"
    depends_on:
      - prometheus
    restart: unless-stopped

volumes:
  prometheus-data:
  grafana-data:
  alertmanager-data:

secrets:
  smtp_password:
    environment: VID_SMTP_APP_PASSWORD
  grafana_admin_password:
    environment: GRAFANA_ADMIN_PASSWORD
