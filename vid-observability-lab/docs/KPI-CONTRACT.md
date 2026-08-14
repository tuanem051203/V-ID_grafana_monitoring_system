# V-ID KPI contract for the lab

Status: proposed for UAT review. Architecture source:
`../../docs/v-id-intern-docs/docs/architecture/`.

| Signal | Production boundary | Lab target |
|---|---|---|
| Authentication success | IdP terminal auth or Hydra web completion | 99.9% / 30d |
| Authentication latency | same selected flow boundary | 95% < 500 ms / 30d |
| OTP provider submission | Notification Center/GSM client result | baseline first |
| OTP delivery | authoritative delivery receipt | 95% / 24h and 30d |
| OTP verification | IdP terminal verify result | baseline; no SLO alert |
| Token issuance | issuer-specific Hydra/IdP transition event | 99.9% / 30d |
| Platform availability | valid critical Kong/service request | 99.9% / 30d |

ADR-0007 targets Hydra as sole issuer. Until migration completes, token metrics
must preserve `issuer`/operation boundaries and must not silently combine unlike
flows. Native V-App auth is a deprecated transition flow.

Provider acceptance does not mean device delivery. Retry counts attempts, not
unique journeys. Wrong/expired OTP, invalid credential and AuthZ policy denial are
business outcomes unless owner explicitly includes them in an SLI.

Allowed labels are bounded environment/cluster/service/operation/result/reason,
client class, realm, issuer/grant, channel/provider/country/stage. PII, secrets and
all correlation identifiers are forbidden as Prometheus labels.

Before UAT, owners must approve the exact boundary, exclusions, minimum traffic,
target/window and notification route for every row.
