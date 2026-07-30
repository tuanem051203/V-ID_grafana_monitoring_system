from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager, suppress
from typing import AsyncIterator

from fastapi import FastAPI, HTTPException, Response, status
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from vid_mock_metrics.config import load_settings
from vid_mock_metrics.generator import MetricsGenerator
from vid_mock_metrics.metrics import REGISTRY
from vid_mock_metrics.scenarios import ScenarioManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

settings = load_settings()
scenario_manager = ScenarioManager(settings.scenarios, settings.initial_scenario)
generator = MetricsGenerator(scenario_manager, settings.generation_interval_seconds)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    generator.generate((await scenario_manager.get())[1])
    task = asyncio.create_task(generator.run(), name="metrics-generator")
    try:
        yield
    finally:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task


app = FastAPI(title="V-ID Mock Metrics", version="1.0.0", lifespan=lifespan)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "healthy"}


@app.get("/metrics", include_in_schema=False)
async def metrics() -> Response:
    return Response(generate_latest(REGISTRY), media_type=CONTENT_TYPE_LATEST)


@app.get("/api/scenario")
async def get_scenario() -> dict[str, object]:
    active, _ = await scenario_manager.get()
    return {"active": active, "available": scenario_manager.names}


@app.post("/api/scenario/{scenario_name}")
async def set_scenario(scenario_name: str) -> dict[str, str]:
    try:
        await scenario_manager.set(scenario_name)
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown scenario {scenario_name!r}. Available: {scenario_manager.names}",
        ) from exc
    return {"active": scenario_name}
