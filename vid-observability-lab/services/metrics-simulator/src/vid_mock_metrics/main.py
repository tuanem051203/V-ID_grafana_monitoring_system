from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager, suppress
from typing import AsyncIterator

from fastapi import FastAPI, Response
from pydantic import BaseModel, Field
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from vid_mock_metrics.config import load_settings
from vid_mock_metrics.generator import MetricsGenerator
from vid_mock_metrics.metrics import REGISTRY

log_level_name = os.getenv("LOG_LEVEL", "INFO").upper()
log_level = getattr(logging, log_level_name, None)
if not isinstance(log_level, int):
    raise ValueError(f"Invalid LOG_LEVEL {log_level_name!r}")

logging.basicConfig(
    level=log_level,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

settings = load_settings()
generator = MetricsGenerator(settings)


class OTPQueueWarningRequest(BaseModel):
    duration_seconds: int = Field(default=420, ge=310, le=3600)
    queue_size: int = Field(default=150, ge=101, le=100_000)


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
    }


@app.post("/api/simulation/warnings/otp-queue-backlog")
async def activate_otp_queue_warning(request: OTPQueueWarningRequest) -> dict[str, object]:
    return generator.activate_otp_queue_warning(request.duration_seconds, request.queue_size)


@app.delete("/api/simulation/warnings/otp-queue-backlog")
async def clear_otp_queue_warning() -> dict[str, object]:
    return generator.clear_otp_queue_warning()
