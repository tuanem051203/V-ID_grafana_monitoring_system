from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from vid_mock_metrics.config import EventDefinition


@dataclass(frozen=True)
class EventEffects:
    names: tuple[str, ...] = ()
    traffic_multiplier: float = 1.0
    auth_success_penalty: float = 0.0
    auth_latency_multiplier: float = 1.0
    otp_delivery_penalty: float = 0.0
    token_success_penalty: float = 0.0
    token_latency_multiplier: float = 1.0
    http_5xx_rate: float | None = None
    database_latency_multiplier: float = 1.0
    database_error_rate: float | None = None
    unavailable_pods: int = 0


class EventScheduler:
    def __init__(self, definitions: tuple[EventDefinition, ...]) -> None:
        self._definitions = definitions

    def active_at(self, second_of_day: float) -> EventEffects:
        active = tuple(
            (event, event_weight(event, second_of_day))
            for event in self._definitions
            if event.start_minute * 60
            <= second_of_day
            < event.start_minute * 60 + event.duration_seconds
        )
        if not active:
            return EventEffects()
        http_rates = [
            event.http_5xx_rate
            for event, _ in active
            if event.http_5xx_rate is not None
        ]
        database_rates = [
            event.database_error_rate
            for event, _ in active
            if event.database_error_rate is not None
        ]
        return EventEffects(
            names=tuple(event.name for event, _ in active),
            traffic_multiplier=math_product(
                1 + (event.traffic_multiplier - 1) * weight
                for event, weight in active
            ),
            auth_success_penalty=sum(
                event.auth_success_penalty * weight for event, weight in active
            ),
            auth_latency_multiplier=math_product(
                1 + (event.auth_latency_multiplier - 1) * weight
                for event, weight in active
            ),
            otp_delivery_penalty=sum(
                event.otp_delivery_penalty * weight for event, weight in active
            ),
            token_success_penalty=sum(
                event.token_success_penalty * weight for event, weight in active
            ),
            token_latency_multiplier=math_product(
                1 + (event.token_latency_multiplier - 1) * weight
                for event, weight in active
            ),
            http_5xx_rate=max(http_rates) if http_rates else None,
            database_latency_multiplier=math_product(
                1 + (event.database_latency_multiplier - 1) * weight
                for event, weight in active
            ),
            database_error_rate=max(database_rates) if database_rates else None,
            unavailable_pods=max(
                round(event.unavailable_pods * weight) for event, weight in active
            ),
        )


def math_product(values: Iterable[float]) -> float:
    result = 1.0
    for value in values:
        result *= value
    return result


def event_weight(event: EventDefinition, second_of_day: float) -> float:
    if event.ramp_seconds <= 0:
        return 1.0
    elapsed = second_of_day - event.start_minute * 60
    remaining = event.duration_seconds - elapsed
    return max(0.0, min(1.0, elapsed / event.ramp_seconds, remaining / event.ramp_seconds))
