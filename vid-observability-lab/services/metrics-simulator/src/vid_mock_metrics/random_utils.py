from __future__ import annotations

import math
import random


class RandomModel:
    """Seeded stochastic model with bounded, autocorrelated noise."""

    def __init__(self, seed: int) -> None:
        self._random = random.Random(seed)
        self._noise: dict[str, float] = {}

    def smooth_noise(self, key: str, limit: float, persistence: float = 0.82) -> float:
        previous = self._noise.get(key, 0.0)
        innovation = self._random.gauss(0.0, limit / 2)
        value = (
            persistence * previous
            + math.sqrt(1 - persistence**2) * innovation
        )
        value = max(-limit, min(limit, value))
        self._noise[key] = value
        return value

    def bounded_rate(self, low: float, high: float, key: str) -> float:
        midpoint = (low + high) / 2
        spread = (high - low) / 2
        return max(low, min(high, midpoint + self.smooth_noise(key, spread)))

    def event_count(self, expected: float) -> int:
        """Sample a stable integer count without bias at low traffic."""
        if expected <= 0:
            return 0
        base = math.floor(expected)
        return base + int(self._random.random() < expected - base)

    def split(self, total: int, weights: tuple[float, ...]) -> tuple[int, ...]:
        if total <= 0:
            return tuple(0 for _ in weights)
        remaining = total
        remaining_weight = sum(weights)
        values: list[int] = []
        for weight in weights[:-1]:
            probability = 0.0 if remaining_weight == 0 else weight / remaining_weight
            count = sum(self._random.random() < probability for _ in range(remaining))
            values.append(count)
            remaining -= count
            remaining_weight -= weight
        values.append(remaining)
        return tuple(values)

    def lognormal_latency(self, median: float, sigma: float, multiplier: float) -> float:
        return max(0.001, self._random.lognormvariate(math.log(median), sigma) * multiplier)
