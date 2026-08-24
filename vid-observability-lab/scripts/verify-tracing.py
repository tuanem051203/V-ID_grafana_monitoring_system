#!/usr/bin/env python3
"""Prove that local/demo stores one root trace for every test HTTP request."""

from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid


def request(url: str, batch: str, expected_status: int) -> None:
    req = urllib.request.Request(url, headers={"x-trace-verification-batch": batch})
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            actual_status = response.status
    except urllib.error.HTTPError as exc:
        actual_status = exc.code
    if actual_status != expected_status:
        raise AssertionError(f"{url}: expected HTTP {expected_status}, got {actual_status}")


def get_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=10) as response:
        return json.load(response)


def value(attribute: dict) -> object:
    return next(iter(attribute["value"].values()))


def verify_trace(tempo_url: str, trace_id: str, batch: str) -> int:
    payload = get_json(f"{tempo_url}/api/traces/{trace_id}")
    matching: list[tuple[dict, dict]] = []
    for resource_spans in payload.get("batches", []):
        resource = {
            attribute["key"]: value(attribute)
            for attribute in resource_spans["resource"].get("attributes", [])
        }
        for scope in resource_spans.get("scopeSpans", []):
            for span in scope.get("spans", []):
                attributes = {
                    attribute["key"]: value(attribute)
                    for attribute in span.get("attributes", [])
                }
                if attributes.get("test.trace_verification_batch") == batch:
                    matching.append((span, resource))
    if len(matching) != 1:
        raise AssertionError(f"{trace_id}: expected one marked server span, found {len(matching)}")
    span, resource = matching[0]
    if span.get("parentSpanId"):
        raise AssertionError(f"{trace_id}: marked HTTP span is not a root span")
    expected_resource = {
        "service.name": "vid-metrics-simulator",
        "service.version": "2.0.0",
        "deployment.environment": "local",
    }
    for key, expected in expected_resource.items():
        if resource.get(key) != expected:
            raise AssertionError(f"{trace_id}: {key}={resource.get(key)!r}, expected {expected!r}")
    attributes = {
        attribute["key"]: value(attribute) for attribute in span.get("attributes", [])
    }
    return int(attributes["http.status_code"])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--app-url", default="http://localhost:8000")
    parser.add_argument("--tempo-url", default="http://localhost:3200")
    parser.add_argument("--timeout", type=int, default=45)
    args = parser.parse_args()

    batch = f"verify-{uuid.uuid4().hex}"
    for _ in range(20):
        request(
            f"{args.app_url}/api/international-phone-otp/tracing/verify/success",
            batch,
            200,
        )
    for _ in range(5):
        request(
            f"{args.app_url}/api/international-phone-otp/tracing/verify/error",
            batch,
            500,
        )

    query = f'{{ span.test.trace_verification_batch = "{batch}" }}'
    search_url = (
        f"{args.tempo_url}/api/search?"
        + urllib.parse.urlencode({"q": query, "limit": 100})
    )
    deadline = time.time() + args.timeout
    traces: list[dict] = []
    while time.time() < deadline:
        traces = get_json(search_url).get("traces", [])
        if len(traces) == 25:
            break
        if len(traces) > 25:
            raise AssertionError(f"expected exactly 25 traces, found {len(traces)}")
        time.sleep(2)

    trace_ids = {trace["traceID"] for trace in traces}
    if len(traces) != 25 or len(trace_ids) != 25:
        raise AssertionError(
            f"expected 25 distinct root traces (20 success + 5 error), found {len(trace_ids)}"
        )

    statuses = [verify_trace(args.tempo_url, trace_id, batch) for trace_id in trace_ids]
    if statuses.count(200) != 20 or statuses.count(500) != 5:
        raise AssertionError(f"unexpected Tempo root-span HTTP statuses: {statuses}")

    print(f"PASS batch={batch}: 20 HTTP 200 + 5 HTTP 500 = {len(trace_ids)} traces")


if __name__ == "__main__":
    main()
