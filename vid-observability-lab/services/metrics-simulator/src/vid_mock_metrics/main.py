from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager, suppress
from typing import AsyncIterator

from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel, Field
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from vid_mock_metrics.config import load_settings
from vid_mock_metrics.generator import MetricsGenerator
from vid_mock_metrics.metrics import REGISTRY
from vid_mock_metrics.tracing import configure_tracing, emit_otp_trace, instrument_fastapi

log_level_name = os.getenv("LOG_LEVEL", "INFO").upper()
log_level = getattr(logging, log_level_name, None)
if not isinstance(log_level, int):
    raise ValueError(f"Invalid LOG_LEVEL {log_level_name!r}")

logging.basicConfig(
    level=log_level,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

settings = load_settings()
configure_tracing()
generator = MetricsGenerator(settings)


class OTPQueueWarningRequest(BaseModel):
    duration_seconds: int = Field(default=420, ge=310, le=3600)
    queue_size: int = Field(default=150, ge=101, le=100_000)


class CrossRegionDegradationRequest(BaseModel):
    duration_seconds: int = Field(default=420, ge=60, le=3600)
    destination_region: str = Field(default="id", pattern=r"^[a-z]{2}$")
    hop: str = Field(default="carrier_delivery", pattern=r"^[a-z][a-z0-9_]*$")
    latency_multiplier: float = Field(default=4.0, ge=1.0, le=20.0)
    failure_rate: float = Field(default=0.20, ge=0.0, le=1.0)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    task = asyncio.create_task(generator.run(), name="metrics-generator")
    try:
        yield
    finally:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task


app = FastAPI(title="V-ID Production-like Metrics Simulator", version="2.0.0", lifespan=lifespan)
instrument_fastapi(app)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "healthy"}


@app.get("/api/international-phone-otp/tracing/verify/success")
async def tracing_verify_success() -> dict[str, str]:
    """Stable HTTP 200 route used by the local all-traces verification."""
    return {"status": "ok"}


@app.get("/api/international-phone-otp/tracing/verify/error")
async def tracing_verify_error() -> None:
    """Stable HTTP 500 route used by the local all-traces verification."""
    raise HTTPException(status_code=500, detail="synthetic tracing verification error")


@app.post("/api/international-phone-otp/tracing/generate")
async def tracing_generate_otp_journey() -> dict[str, str | None]:
    """Create one deterministic, non-PII journey for log/trace correlation checks."""
    trace_id = emit_otp_trace(
        {
            "otp.destination_country": "id",
            "otp.channel": "sms",
            "otp.provider": "gsm",
            "simulation.synthetic": "true",
        },
        [
            ("edge_to_kong", "kong", 0.018, "success"),
            ("kong_to_idp", "identity-provider", 0.042, "success"),
            ("redis_challenge", "redis", 0.009, "success"),
            ("route_selection", "identity-provider", 0.004, "success"),
            ("queue_wait", "notification-center", 0.075, "success"),
            ("gsm_submit", "gsm-gateway", 0.280, "success"),
            ("carrier_delivery", "sms-provider", 2.400, "success"),
        ],
        "success",
    )
    return {"trace_id": trace_id}


@app.get("/metrics", include_in_schema=False)
async def metrics() -> Response:
    return Response(generate_latest(REGISTRY), media_type=CONTENT_TYPE_LATEST)


@app.get("/api/simulation")
async def simulation() -> dict[str, object]:
    return {
        **generator.snapshot.as_dict(),
        "manual_warning": generator.otp_queue_warning_state(),
        "cross_region": {
            "enabled": settings.cross_region.enabled,
            "source_region": settings.cross_region.source_region,
            "traffic_ratio": settings.cross_region.traffic_ratio,
            "destinations": [
                {
                    "destination_region": destination.destination_region,
                    "traffic_weight": destination.traffic_weight,
                    "hops": [hop.name for hop in destination.hops],
                }
                for destination in settings.cross_region.destinations
            ],
            "manual_degradation": generator.cross_region_degradation_state(),
        },
    }


@app.post("/api/simulation/warnings/otp-queue-backlog")
async def activate_otp_queue_warning(request: OTPQueueWarningRequest) -> dict[str, object]:
    return generator.activate_otp_queue_warning(request.duration_seconds, request.queue_size)


@app.delete("/api/simulation/warnings/otp-queue-backlog")
async def clear_otp_queue_warning() -> dict[str, object]:
    return generator.clear_otp_queue_warning()


@app.post("/api/simulation/warnings/cross-region-degradation")
async def activate_cross_region_degradation(
    request: CrossRegionDegradationRequest,
) -> dict[str, object]:
    return generator.activate_cross_region_degradation(
        request.duration_seconds,
        request.destination_region,
        request.hop,
        request.latency_multiplier,
        request.failure_rate,
    )


@app.delete("/api/simulation/warnings/cross-region-degradation")
async def clear_cross_region_degradation() -> dict[str, object]:
    return generator.clear_cross_region_degradation()


@app.post("/api/simulation/warnings/otp-journey-degradation")
async def activate_otp_journey_degradation(
    request: CrossRegionDegradationRequest,
) -> dict[str, object]:
    return generator.activate_cross_region_degradation(
        request.duration_seconds,
        request.destination_region,
        request.hop,
        request.latency_multiplier,
        request.failure_rate,
    )


@app.delete("/api/simulation/warnings/otp-journey-degradation")
async def clear_otp_journey_degradation() -> dict[str, object]:
    return generator.clear_cross_region_degradation()
