from __future__ import annotations

import logging
import os
import time

LOGGER = logging.getLogger(__name__)

try:
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
except ModuleNotFoundError:  # Tests can run without optional tracing dependencies.
    trace = None


def configure_tracing() -> None:
    if trace is None or os.getenv("OTEL_TRACES_EXPORTER", "otlp") == "none":
        LOGGER.info("Synthetic tracing disabled")
        return
    provider = TracerProvider(
        resource=Resource.create(
            {"service.name": "vid-metrics-simulator", "deployment.synthetic": True}
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
