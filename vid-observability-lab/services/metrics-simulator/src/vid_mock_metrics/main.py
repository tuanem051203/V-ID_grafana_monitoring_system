from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager, suppress
from typing import AsyncIterator

from fastapi import FastAPI, Response
from pydantic import BaseModel, Field
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from vid_mock_metrics.config import load_settings
from vid_mock_metrics.generator import MetricsGenerator
from vid_mock_metrics.metrics import REGISTRY

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

settings = load_settings()
generator = MetricsGenerator(settings)


class OTPQueueWarningRequest(BaseModel):
    duration_seconds: int = Field(default=420, ge=310, le=3600)
    queue_size: int = Field(default=150, ge=101, le=100_000)


class CrossRegionDegradationRequest(BaseModel):
    duration_seconds: int = Field(default=420, ge=60, le=3600)
    destination_region: str = Field(default="id", pattern=r"^[a-z]{2}$")
    hop: str = Field(default="dc_to_destination", pattern=r"^[a-z][a-z0-9_]*$")
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


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "healthy"}


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
