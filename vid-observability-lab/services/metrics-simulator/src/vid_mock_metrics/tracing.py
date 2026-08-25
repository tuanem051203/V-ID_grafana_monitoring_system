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
    from opentelemetry._logs import set_logger_provider
    from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
    from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
except ModuleNotFoundError:  # Tests can run without optional tracing dependencies.
    trace = None
    FastAPIInstrumentor = None

OTP_LOGGER = logging.getLogger("vid.otp.journey")
OTP_LOGGER.propagate = False


def _resource() -> Any:
    service_name = os.getenv("OTEL_SERVICE_NAME", "vid-metrics-simulator")
    environment = os.getenv("OTEL_DEPLOYMENT_ENVIRONMENT", os.getenv("APP_ENV", "local"))
    service_version = os.getenv("OTEL_SERVICE_VERSION", "2.0.0")
    return Resource.create(
        {
            "service.name": service_name,
            "service.version": service_version,
            "deployment.environment": environment,
            "deployment.environment.name": environment,
            "deployment.synthetic": True,
        }
    )


def _log_resource() -> Any:
    """Use a small, stable Loki label set; request IDs remain log metadata."""
    return Resource.create(
        {
            "service.name": os.getenv("OTEL_SERVICE_NAME", "vid-metrics-simulator"),
            "service.version": os.getenv("OTEL_SERVICE_VERSION", "2.0.0"),
            "environment": os.getenv(
                "OTEL_DEPLOYMENT_ENVIRONMENT", os.getenv("APP_ENV", "local")
            ),
            "deployment.synthetic": True,
        }
    )


def configure_tracing() -> None:
    if trace is None or os.getenv("OTEL_TRACES_EXPORTER", "otlp") == "none":
        LOGGER.info("Synthetic tracing disabled")
        return
    service_name = os.getenv("OTEL_SERVICE_NAME", "vid-metrics-simulator")
    environment = os.getenv("OTEL_DEPLOYMENT_ENVIRONMENT", os.getenv("APP_ENV", "local"))
    service_version = os.getenv("OTEL_SERVICE_VERSION", "2.0.0")
    resource = _resource()
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(
        BatchSpanProcessor(
            OTLPSpanExporter(
                endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel-collector:4317"),
                insecure=True,
            )
        )
    )
    trace.set_tracer_provider(provider)
    if os.getenv("OTEL_LOGS_EXPORTER", "otlp") != "none":
        logger_provider = LoggerProvider(resource=_log_resource())
        logger_provider.add_log_record_processor(
            BatchLogRecordProcessor(
                OTLPLogExporter(
                    endpoint=os.getenv(
                        "OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel-collector:4317"
                    ),
                    insecure=True,
                )
            )
        )
        set_logger_provider(logger_provider)
        OTP_LOGGER.handlers.clear()
        OTP_LOGGER.addHandler(LoggingHandler(level=logging.INFO, logger_provider=logger_provider))
        OTP_LOGGER.setLevel(logging.INFO)
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
    trace_id = f"{root.get_span_context().trace_id:032x}"
    cursor = start_ns
    with trace.use_span(root, end_on_exit=False):
        _otp_log(
            logging.INFO,
            "international OTP challenge accepted",
            start_ns,
            {
                **attributes,
                "event.name": "otp.journey.accepted",
                "otp.journey_id": trace_id,
                "http.request.method": "POST",
                "url.path": "/v1/auth/challenge",
            },
        )
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
            with trace.use_span(child, end_on_exit=False):
                level = logging.WARNING if stage_result == "failure" else logging.INFO
                stage_attributes: dict[str, Any] = {
                    **attributes,
                    "event.name": "otp.stage.completed",
                    "otp.journey_id": trace_id,
                    "otp.stage": name,
                    "otp.result": stage_result,
                    "service.target": service,
                    "duration_ms": round(duration * 1000, 3),
                }
                if stage_result == "failure":
                    stage_attributes["error.type"] = "dependency_timeout"
                _otp_log(
                    level,
                    f"OTP stage {name} {stage_result}",
                    child_end,
                    stage_attributes,
                )
            child.end(end_time=child_end)
            cursor = child_end
        root.set_attribute("otp.result", result)
        _otp_log(
            logging.ERROR if result == "failure" else logging.INFO,
            f"international OTP journey {result}",
            end_ns,
            {
                **attributes,
                "event.name": "otp.journey.completed",
                "otp.journey_id": trace_id,
                "otp.result": result,
                "duration_ms": round(total * 1000, 3),
            },
        )
    context = root.get_span_context()
    root.end(end_time=end_ns)
    return f"{context.trace_id:032x}" if context.is_valid else None


def _otp_log(level: int, message: str, timestamp_ns: int, attributes: dict[str, Any]) -> None:
    """Emit a backdated structured log while the matching trace/span is current."""
    if not OTP_LOGGER.handlers:
        return
    canonical_names = {
        "event.name": "event_name",
        "otp.journey_id": "journey_id",
        "otp.destination_country": "destination_country",
        "otp.channel": "channel",
        "otp.provider": "provider",
        "otp.stage": "stage",
        "otp.result": "result",
        "service.target": "service",
        "error.type": "error_type",
        "http.request.method": "http_method",
        "url.path": "url_path",
        "simulation.synthetic": "simulation_synthetic",
    }
    canonical_attributes = {
        canonical_names.get(key, key): value for key, value in attributes.items()
    }
    record = OTP_LOGGER.makeRecord(
        OTP_LOGGER.name,
        level,
        __file__,
        0,
        message,
        (),
        None,
        extra=canonical_attributes,
    )
    record.created = timestamp_ns / 1_000_000_000
    OTP_LOGGER.handle(record)
