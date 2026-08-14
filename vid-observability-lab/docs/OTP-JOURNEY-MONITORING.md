# International OTP journey monitoring

Architecture source: `../../docs/v-id-intern-docs/docs/architecture/architecture.md`
and `components.md`. This lab models the documented V-ID boundary, not an assumed destination-country
datacenter route:

```text
edge -> Kong -> identity-provider -> Redis -> route selection
     -> Notification Center queue -> GSM submit -> carrier delivery receipt
```

All data and traces are synthetic. A phone country does not prove where compute
runs. Production topology, provider contracts and ownership need approval before
the contract is adopted outside the lab.

## Demo

Render and start the local stack:

```bash
python3 scripts/render-config.py --environment local
GRAFANA_ADMIN_PASSWORD=admin VID_SMTP_APP_PASSWORD=unused \
  docker compose -f generated/local/docker-compose.yml up --build -d
```

Open `http://localhost:3000/d/sso-otp-journey`. Prometheus shows aggregate RED
signals and stage p95. Tempo stores a sampled 10% of journeys. Native histogram
exemplars carry only `trace_id`, allowing Grafana to open the matching waterfall.
Tempo 2.8 also enables the `local-blocks` metrics-generator processor so Grafana
Traces Drilldown can execute TraceQL metrics queries such as `rate()`.

Trigger a carrier bottleneck for Indonesia:

```bash
curl -X POST http://localhost:8000/api/simulation/warnings/otp-journey-degradation \
  -H 'content-type: application/json' \
  -d '{"duration_seconds":420,"destination_region":"id","hop":"carrier_delivery","latency_multiplier":5,"failure_rate":0.15}'
```

Valid stages are `edge_to_kong`, `kong_to_idp`, `redis_challenge`,
`route_selection`, `queue_wait`, `gsm_submit`, and `carrier_delivery`. Clear the
scenario with `DELETE` on the same endpoint.

## Interpretation

- Slow `kong_to_idp` points to the application boundary.
- Slow `redis_challenge` points to challenge persistence.
- Slow `queue_wait` plus high `otp_queue_size` points to backlog.
- Slow `gsm_submit` is provider API submission latency.
- Slow `carrier_delivery` with fast `gsm_submit` means the synchronous request is
  healthy but delivery downstream is delayed.

The documented IdP uses a `RoutingSMSSender`: +84 remains on Notification Center;
allowlisted international destinations may route to GSM, while WhatsApp is a
separate channel/policy. Only a provider delivery report is treated as authoritative delivery. No phone,
OTP, user, challenge, session or request identifier is emitted as a Prometheus
label. Synthetic traces contain bounded country/channel/provider attributes only.

## Production replacement

Replace the simulator with W3C `traceparent` propagation through Kong and every
HTTP/gRPC boundary. Inject/extract context in queue messages and correlate the
provider callback using a privacy-reviewed identifier. Keep the Prometheus label
contract bounded and confirm all route names and thresholds with service/network
owners.
