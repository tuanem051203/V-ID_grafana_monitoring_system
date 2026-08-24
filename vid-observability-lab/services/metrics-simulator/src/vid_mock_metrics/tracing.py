from __future__ import annotations

import logging
import os
import time
from typing import Any

LOGGER = logging.getLogger(__name__)

# The simulator exposes health, Prometheus and scenario-control endpoints, but
# only requests under this business prefix belong in the International OTP view.
NON_INTERNATIONAL_OTP_HTTP_URLS = r"^(?!.*\/api\/international-phone-otp(?:\/|$)).*$"

try:
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
except ModuleNotFoundError:  # Tests can run without optional tracing dependencies.
    trace = None
    FastAPIInstrumentor = None


def configure_tracing() -> None:
    if trace is None or os.getenv("OTEL_TRACES_EXPORTER", "otlp") == "none":
        LOGGER.info("Synthetic tracing disabled")
        return
    service_name = os.getenv("OTEL_SERVICE_NAME", "vid-metrics-simulator")
    environment = os.getenv("OTEL_DEPLOYMENT_ENVIRONMENT", os.getenv("APP_ENV", "local"))
    service_version = os.getenv("OTEL_SERVICE_VERSION", "2.0.0")
    provider = TracerProvider(
        resource=Resource.create(
            {
                "service.name": service_name,
                "service.version": service_version,
                # Keep the requested attribute and the current semantic-convention name.
                "deployment.environment": environment,
                "deployment.environment.name": environment,
                "deployment.synthetic": True,
            }
        )
    )
    provider.add_span_processor(
        BatchSpanProcessor(
            OTLPSpanExporter(
                endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel-collector:4317"),
                insecure=True,
            )
        )
    )
    trace.set_tracer_provider(provider)
    LOGGER.info(
        "Tracing configured",
        extra={
            "service_name": service_name,
            "service_version": service_version,
            "deployment_environment": environment,
            "traces_sampler": os.getenv("OTEL_TRACES_SAMPLER", "parentbased_always_on"),
        },
    )


def _verification_batch(scope: dict[str, Any]) -> str | None:
    """Read one explicitly allowlisted, non-sensitive local verification header."""
    for raw_name, raw_value in scope.get("headers", ()):
        if raw_name.lower() == b"x-trace-verification-batch":
            value = raw_value.decode("ascii", errors="ignore")[:64]
            return value if value.replace("-", "").replace("_", "").isalnum() else None
    return None


def instrument_fastapi(app: Any) -> None:
    """Trace every inbound FastAPI request without capturing headers or bodies."""
    if trace is None or FastAPIInstrumentor is None:
        LOGGER.info("FastAPI tracing instrumentation disabled")
        return

    def server_request_hook(span: Any, scope: dict[str, Any]) -> None:
        if not span or not span.is_recording():
            return
        batch = _verification_batch(scope)
        if batch:
            span.set_attribute("test.trace_verification_batch", batch)

    FastAPIInstrumentor.instrument_app(
        app,
        excluded_urls=NON_INTERNATIONAL_OTP_HTTP_URLS,
        server_request_hook=server_request_hook,
        # Request/response headers and bodies are deliberately not captured.
        http_capture_headers_server_request=None,
        http_capture_headers_server_response=None,
    )


def emit_otp_trace(
    attributes: dict[str, str], stages: list[tuple[str, str, float, str]], result: str
) -> str | None:
    if trace is None:
        return None
    tracer = trace.get_tracer("vid.synthetic.otp")
    total = sum(duration for _, _, duration, _ in stages)
    end_ns = time.time_ns()
    start_ns = end_ns - int(total * 1_000_000_000)
    root = tracer.start_span("POST /v1/auth/challenge", attributes=attributes, start_time=start_ns)
    cursor = start_ns
    with trace.use_span(root, end_on_exit=False):
        for name, service, duration, stage_result in stages:
            child_end = cursor + int(duration * 1_000_000_000)
            child = tracer.start_span(
                name,
                attributes={
                    **attributes,
                    "service.target": service,
                    "otp.stage": name,
                    "otp.result": stage_result,
                },
                start_time=cursor,
            )
            child.end(end_time=child_end)
            cursor = child_end
    root.set_attribute("otp.result", result)
    context = root.get_span_context()
    root.end(end_time=end_ns)
    return f"{context.trace_id:032x}" if context.is_valid else None
