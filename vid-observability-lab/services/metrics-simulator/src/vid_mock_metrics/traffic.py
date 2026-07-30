from __future__ import annotations

import math

from vid_mock_metrics.config import TrafficPoint
from vid_mock_metrics.random_utils import RandomModel


class TrafficGenerator:
    def __init__(
        self,
        peak_tps: float,
        schedule: tuple[TrafficPoint, ...],
        noise_ratio: float,
        random_model: RandomModel,
    ) -> None:
        self._peak_tps = peak_tps
        self._schedule = schedule
        self._noise_ratio = noise_ratio
        self._random = random_model

    def tps_at(self, minute_of_day: float) -> float:
        minute = minute_of_day % 1440
        left, right = self._schedule[0], self._schedule[-1]
        for candidate_left, candidate_right in zip(
            self._schedule, self._schedule[1:]
        ):
            if candidate_left.minute <= minute <= candidate_right.minute:
                left, right = candidate_left, candidate_right
                break
        progress = (minute - left.minute) / max(1, right.minute - left.minute)
        eased = (1 - math.cos(math.pi * progress)) / 2
        multiplier = left.multiplier + (right.multiplier - left.multiplier) * eased
        noise = self._random.smooth_noise("traffic", self._noise_ratio)
        return max(0.1, self._peak_tps * multiplier * (1 + noise))
