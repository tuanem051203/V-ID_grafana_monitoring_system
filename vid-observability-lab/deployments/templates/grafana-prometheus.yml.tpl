apiVersion: 1

datasources:
  - name: Prometheus
    uid: prometheus
    type: prometheus
    access: proxy
    url: @@GRAFANA_DATASOURCE_URL@@
    isDefault: true
    editable: false
    jsonData:
      timeInterval: @@GRAFANA_DATASOURCE_INTERVAL@@
