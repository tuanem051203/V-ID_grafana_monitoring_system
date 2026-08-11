# Cross-region request monitoring

## Scope

This capability monitors every simulated V-ID request routed between regions; it
is not specific to OTP. The synthetic path is repeated for nine destinations:

```text
VN entry -> VN/DC gateway -> inter-region link -> destination gateway -> target service
```

Destinations are `us`, `dk`, `id`, `ph`, `la`, `in`, `kz`, `ru` and `nl` (US,
Denmark, Indonesia, Philippines, Laos, India, Kazakhstan, Russia and the
Netherlands). These routes are a test contract, not proof of production topology
or geographic location inferred from a phone number. Network and service owners
must confirm the actual ingress, gateways, routing policy and ownership before
UAT instrumentation is promoted.

## RED contract

End-to-end counters and histograms expose rate, errors and duration. Hop metrics
localize degradation to `vn_to_dc`, `dc_to_destination` or
`destination_to_service`, while `destination_region` identifies the country.

| Metric | Purpose |
|---|---|
| `cross_region_requests_total` | End-to-end attempts and terminal result |
| `cross_region_request_duration_seconds` | End-to-end latency histogram |
| `cross_region_hop_requests_total` | Attempt/result at each reached hop |
| `cross_region_hop_duration_seconds` | Per-hop latency histogram |
| `cross_region_failures_total` | Terminal failure stage and bounded reason |

Allowed dimensions are region, hop, service, operation, result, stage and a
bounded reason taxonomy. Phone number, user/session/request/trace IDs, token,
OTP and raw URL are prohibited as Prometheus labels. Request correlation belongs
in privacy-reviewed logs and distributed traces.

## Simulation

Ten percent of generated platform requests use a synthetic cross-region route
and are split across the nine destinations with bounded traffic weights.
Authentication, OTP and token operations are all included. At 19:30 simulated
time, `indonesia_route_degradation` increases latency on Indonesia's
`dc_to_destination` hop by 4x and sets its failure rate to 20%. Compress the day
to one hour for a demo:

```bash
VID_SIMULATION_DAY_SECONDS=3600 \
  docker compose -f deployments/local/docker-compose.yml up --build -d
```

Open **V-ID SSO — Cross-region Requests**. The first row gives global health;
the second compares traffic, success and p95 across countries; the lower panels
drill into hop latency, hop errors and terminal failures using dashboard filters.

The degradation can also be activated immediately for a demo:

```bash
curl -X POST http://localhost:8000/api/simulation/warnings/cross-region-degradation \
  -H 'content-type: application/json' \
  -d '{"duration_seconds":420,"destination_region":"id","hop":"dc_to_destination","latency_multiplier":4,"failure_rate":0.2}'
```

Clear it with `DELETE` on the same endpoint.

## Production instrumentation

Instrument both the caller and server boundary with OpenTelemetry-compatible
HTTP/RPC middleware. Propagate trace context across gateways, but aggregate only
bounded labels into Prometheus. Compare both sides of a hop to distinguish an
exporter gap from packet loss or timeout. Provider/carrier delivery remains a
separate downstream contract and requires an authoritative delivery report.

Before production, owners must approve the real route list, traffic thresholds,
latency/error objectives, low-traffic behavior and alert notification route.
