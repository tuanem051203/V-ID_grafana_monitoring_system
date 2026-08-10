# Alertmanager environments

| Environment | Configuration | Status |
|---|---|---|
| Local | `alertmanager.local.yml` | Active in local Docker Compose; Gmail test account |
| UAT | `alertmanager.uat.yml` | Template; replace all `example.com` SMTP and email values |
| Production | `alertmanager.production.yml` | Template; replace all `example.com` SMTP and email values |

Every environment expects its SMTP credential at
`/run/secrets/smtp_password`. The deployment platform is responsible for
providing that secret; it must not be stored in these files.

All email receivers use `templates/email.tmpl`. The template provides both an
HTML body and a plain-text fallback with status, severity, environment,
service, affected alerts, dashboard, runbook, Prometheus and Alertmanager
links.

Before deploying UAT or production:

1. Replace the reserved `example.com` SMTP host, sender, username and recipients.
2. Inject the environment-specific SMTP password using the target platform's
   secret manager.
3. Validate the selected file with `amtool check-config`.
4. Test firing and resolved notifications in that environment.

Do not reuse the local Gmail credential in UAT or production.
