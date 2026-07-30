from __future__ import annotations

import asyncio

from vid_mock_metrics.config import Scenario


class ScenarioManager:
    """Stores the active scenario without mutating metric state."""

    def __init__(self, scenarios: dict[str, Scenario], initial: str) -> None:
        self._scenarios = scenarios
        self._active = initial
        self._lock = asyncio.Lock()

    @property
    def names(self) -> list[str]:
        return list(self._scenarios)

    async def get(self) -> tuple[str, Scenario]:
        async with self._lock:
            return self._active, self._scenarios[self._active]

    async def set(self, name: str) -> Scenario:
        async with self._lock:
            if name not in self._scenarios:
                raise KeyError(name)
            self._active = name
            return self._scenarios[name]
