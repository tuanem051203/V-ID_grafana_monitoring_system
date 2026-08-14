# V-ID observability runbook

## First response

1. Confirm environment, time, affected client/realm and flow.
2. Decide whether the flow is IdP native/transition, Hydra browser OIDC, token,
   AuthZ, or international OTP.
3. Check Overview, then the matching detail dashboard.
4. Identify the first degraded service/stage, then open a Tempo exemplar.
5. Correlate deployment/config changes and dependency/provider health.
6. Mitigate only within owner-approved procedures; verify recovery and record it.

## Authentication

- Native transition: Kong → `identity-provider` challenge/verify/login.
- Browser: client → Hydra → `identity-provider` login/consent → Hydra.
- Check Redis/Postgres, App Check rejection classification, session state and the
  issuer boundary. Do not treat invalid credential as platform outage.

## Token

Filter by issuer/grant. Current architecture may contain Hydra and IdP-issued
tokens while ADR-0007 migration is incomplete; `oauth2-token` is transitioning to
a Hydra front. Escalate issuer/claim-shape drift separately from latency/outage.

## International OTP

Use **V-ID SSO — OTP Journey**:

- `kong_to_idp`: gateway/application boundary.
- `redis_challenge`: OTP challenge persistence.
- `route_selection`: Notification Center vs GSM/WhatsApp policy.
- `queue_wait`: Notification Center backlog.
- `gsm_submit`: provider API acceptance.
- `carrier_delivery`: asynchronous delivery receipt.

Fast submit plus slow delivery means the synchronous V-ID path is healthy and the
downstream provider/carrier is delayed. Missing receipt requires checking callback
contract, not merely retrying sends. Never paste phone, OTP or token into tickets.

## Authorization

`organization` is organization source of truth; `authz` evaluates RBAC. Separate
expected policy denial from `authz` timeout/system error and from cross-account
connectivity where applicable.

## Synthetic cross-region

Use only for lab demonstration. It does not prove V-ID has a route/datacenter in
the destination country and must not drive production escalation.

## Recovery criteria

User-journey SLI returns to baseline, affected stage/error series recover, alert
resolves, traffic is non-zero and representative, and no retry/backlog wave remains.
