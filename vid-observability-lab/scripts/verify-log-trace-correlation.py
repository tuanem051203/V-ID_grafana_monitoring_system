#!/usr/bin/env python3
"""Verify that an International OTP log resolves to the same trace in Tempo."""

from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.parse
import urllib.request


def get_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=10) as response:
        return json.load(response)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--app-url", default="http://localhost:8000")
    parser.add_argument("--loki-url", default="http://localhost:3100")
    parser.add_argument("--tempo-url", default="http://localhost:3200")
    parser.add_argument("--timeout", type=int, default=60)
    args = parser.parse_args()

    deadline = time.time() + args.timeout
    generate_request = urllib.request.Request(
        f"{args.app_url}/api/international-phone-otp/tracing/generate",
        data=b"",
        method="POST",
    )
    with urllib.request.urlopen(generate_request, timeout=10) as response:
        generated_trace_id = json.load(response)["trace_id"]
    if not generated_trace_id:
        raise AssertionError("simulator did not return a trace_id")

    matched: dict[str, str] | None = None
    while time.time() < deadline:
        now = time.time_ns()
        params = urllib.parse.urlencode(
            {
                "query": '{environment="local",service_name="vid-metrics-simulator"}',
                "start": now - 300_000_000_000,
                "end": now,
                "limit": 200,
                "direction": "backward",
            }
        )
        payload = get_json(f"{args.loki_url}/loki/api/v1/query_range?{params}")
        streams = payload.get("data", {}).get("result", [])
        matched = next(
            (
                stream["stream"]
                for stream in streams
                if stream["stream"].get("event_name") == "otp.journey.completed"
                and stream["stream"].get("trace_id") == generated_trace_id
            ),
            None,
        )
        if matched:
            break
        time.sleep(2)
    if not matched:
        raise AssertionError("Loki has no correlated otp.journey.completed log")

    required = {
        "trace_id",
        "span_id",
        "destination_country",
        "provider",
        "result",
        "duration_ms",
        "service_name",
    }
    missing = required - matched.keys()
    if missing:
        raise AssertionError(f"Loki log is missing structured metadata: {sorted(missing)}")
    forbidden = ("phone", "msisdn", "otp_code", "password", "token", "authorization")
    exposed = [key for key in matched if any(word in key.lower() for word in forbidden)]
    if exposed:
        raise AssertionError(f"sensitive log attributes found: {exposed}")

    trace_id = matched["trace_id"]
    while time.time() < deadline:
        try:
            trace_payload = get_json(f"{args.tempo_url}/api/traces/{trace_id}")
            if trace_payload.get("batches"):
                break
        except urllib.error.HTTPError as exc:
            if exc.code != 404:
                raise
        time.sleep(2)
    else:
        raise AssertionError(f"Loki trace_id {trace_id} was not found in Tempo")

    print(
        "PASS Loki → Tempo correlation: "
        f"trace_id={trace_id} country={matched['destination_country']} "
        f"provider={matched['provider']} result={matched['result']}"
    )


if __name__ == "__main__":
    main()
