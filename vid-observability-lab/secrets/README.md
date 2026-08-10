# Local SMTP secret

Docker Compose creates the `smtp_password` secret from the
`VID_SMTP_APP_PASSWORD` environment variable and mounts it inside Alertmanager
at `/run/secrets/smtp_password`.

From `deployments/local`, enter the 16-character Gmail App Password without
putting it in shell history:

```sh
read -s "VID_SMTP_APP_PASSWORD?Gmail App Password: "
export VID_SMTP_APP_PASSWORD
docker compose up -d --force-recreate alertmanager
unset VID_SMTP_APP_PASSWORD
```

Do not put the credential in `.env`, Compose YAML, or any tracked file. This
Compose secret is suitable for the local environment. Production should use an
orchestrator or external secret manager.
