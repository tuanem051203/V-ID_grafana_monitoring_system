# Alertmanager environments

Alertmanager configuration is generated from `deployments/config.json` and
`deployments/templates/alertmanager.yml.tpl`. The rendered artifact is written
to `generated/<environment>/alertmanager/alertmanager.yml`.

Every environment expects its SMTP credential at
`/run/secrets/smtp_password`. The deployment platform is responsible for
providing that secret; it must not be stored in deployment JSON or templates.

All email receivers use `templates/email.tmpl`. The template provides both an
HTML body and a plain-text fallback with status, severity, environment,
service, affected alerts, dashboard, runbook, Prometheus and Alertmanager
links.

Before deploying UAT or production:

1. Replace the reserved `example.com` values in `deployments/config.json`.
2. Inject the environment-specific SMTP password using the target platform's
   secret manager.
3. Render the environment and validate the generated file with `amtool check-config`.
4. Test firing and resolved notifications in that environment.

Do not reuse the local Gmail credential in UAT or production.
