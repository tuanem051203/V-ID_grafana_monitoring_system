global:
  resolve_timeout: @@ALERTMANAGER_RESOLVE_TIMEOUT@@
  smtp_smarthost: "@@ALERTMANAGER_SMTP_SMARTHOST@@"
  smtp_from: "@@ALERTMANAGER_SMTP_FROM@@"
  smtp_auth_username: "@@ALERTMANAGER_SMTP_USERNAME@@"
  smtp_auth_password_file: "@@ALERTMANAGER_SMTP_PASSWORD_FILE@@"
  smtp_require_tls: @@ALERTMANAGER_SMTP_REQUIRE_TLS@@

templates:
  - "templates/*.tmpl"

route:
  receiver: @@ENVIRONMENT@@-warning-email
  group_by: [@@ALERTMANAGER_GROUP_BY@@]
  group_wait: @@ALERTMANAGER_GROUP_WAIT@@
  group_interval: @@ALERTMANAGER_GROUP_INTERVAL@@
  repeat_interval: @@ALERTMANAGER_REPEAT_INTERVAL@@
  routes:
    - receiver: @@ENVIRONMENT@@-critical-email
      matchers:
        - 'severity="critical"'
      repeat_interval: @@ALERTMANAGER_CRITICAL_REPEAT_INTERVAL@@

receivers:
  - name: @@ENVIRONMENT@@-warning-email
    email_configs:
      - to: "@@ALERTMANAGER_WARNING_RECIPIENTS@@"
        send_resolved: true
        html: '{{ template "vid.email.html" . }}'
        text: '{{ template "vid.email.text" . }}'
        headers:
          Subject: '[V-ID][@@ENVIRONMENT@@][WARNING][{{ .Status }}] {{ .CommonLabels.alertname }}'

  - name: @@ENVIRONMENT@@-critical-email
    email_configs:
      - to: "@@ALERTMANAGER_CRITICAL_RECIPIENTS@@"
        send_resolved: true
        html: '{{ template "vid.email.html" . }}'
        text: '{{ template "vid.email.text" . }}'
        headers:
          Subject: '[V-ID][@@ENVIRONMENT@@][CRITICAL][{{ .Status }}] {{ .CommonLabels.alertname }}'

inhibit_rules:
  - source_matchers:
      - 'severity="critical"'
    target_matchers:
      - 'severity="warning"'
    equal:
      - environment
      - cluster
      - service
