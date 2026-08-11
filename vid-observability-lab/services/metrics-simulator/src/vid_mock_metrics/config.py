from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast


@dataclass(frozen=True)
class TrafficPoint:
    minute: int
    multiplier: float


@dataclass(frozen=True)
class LoadProfile:
    name: str
    peak_tps: float


@dataclass(frozen=True)
class EventDefinition:
    name: str
    start_minute: int
    duration_seconds: int
    ramp_seconds: int = 0
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


@dataclass(frozen=True)
class ServiceBaseline:
    auth_success_min: float
    auth_success_max: float
    otp_delivery_min: float
    otp_delivery_max: float
    otp_verification_min: float
    otp_verification_max: float
    token_success_rate: float
    http_5xx_rate: float
    auth_latency_p50_seconds: float
    auth_latency_sigma: float
    token_latency_p50_seconds: float


@dataclass(frozen=True)
class Settings:
    generation_interval_seconds: float
    simulation_day_seconds: float
    random_seed: int
    noise_ratio: float
    load_profile: LoadProfile
    traffic_schedule: tuple[TrafficPoint, ...]
    events: tuple[EventDefinition, ...]
    baseline: ServiceBaseline


def _clock_minute(value: Any) -> int:
    hour, minute = (int(part) for part in str(value).split(":", maxsplit=1))
    if not 0 <= hour <= 24 or not 0 <= minute < 60 or (hour == 24 and minute != 0):
        raise ValueError(f"Invalid clock time: {value}")
    return hour * 60 + minute


def _rate(value: Any, key: str) -> float:
    number = float(value)
    if not 0.0 <= number <= 1.0:
        raise ValueError(f"{key} must be between 0 and 1")
    return number


def _mapping(value: object, key: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{key} must be a mapping")
    return cast(dict[str, Any], value)


def _mapping_list(value: object, key: str) -> tuple[dict[str, Any], ...]:
    if not isinstance(value, list):
        raise ValueError(f"{key} must be a list")
    items = cast(list[object], value)
    return tuple(_mapping(item, f"{key} item") for item in items)


def load_settings() -> Settings:
    default_path = Path(__file__).resolve().parents[2] / "config" / "runtime.json"
    path = Path(os.getenv("CONFIG_FILE", str(default_path)))
    with path.open(encoding="utf-8") as stream:
        loaded = cast(object, json.load(stream))
    if not isinstance(loaded, dict):
        raise ValueError(f"Invalid simulation configuration: {path}")
    raw = cast(dict[str, Any], loaded)
    if raw.get("version") != 1:
        raise ValueError(f"Unsupported configuration version in {path}")

    environment = os.getenv("APP_ENV", "local")
    raw_environments = _mapping(raw.get("environments"), "environments")
    if environment not in raw_environments:
        raise ValueError(f"Unknown APP_ENV {environment!r}")
    environment_config = _mapping(
        raw_environments[environment], f"environments.{environment}"
    )
    profile_name = str(environment_config["load_profile"])
    raw_profiles = _mapping(raw.get("load_profiles"), "load_profiles")
    if profile_name not in raw_profiles:
        raise ValueError(
            f"Unknown load profile {profile_name!r} for environment {environment!r}"
        )
    raw_profile = _mapping(raw_profiles[profile_name], f"load_profiles.{profile_name}")
    profile = LoadProfile(profile_name, float(raw_profile["peak_tps"]))
    if profile.peak_tps <= 0:
        raise ValueError("peak_tps must be positive")

    schedule = tuple(
        TrafficPoint(_clock_minute(item["time"]), float(item["multiplier"]))
        for item in _mapping_list(raw.get("traffic_schedule"), "traffic_schedule")
    )
    if len(schedule) < 2 or tuple(sorted(point.minute for point in schedule)) != tuple(
        point.minute for point in schedule
    ):
        raise ValueError("traffic_schedule must contain ordered points")
    if schedule[0].minute != 0 or schedule[-1].minute != 1440:
        raise ValueError("traffic_schedule must cover 00:00 through 24:00")

    events = tuple(
        EventDefinition(
            name=str(item["name"]),
            start_minute=_clock_minute(item["start"]),
            duration_seconds=int(item["duration_seconds"]),
            **{
                key: value
                for key, value in _mapping(item.get("effects", {}), "event effects").items()
                if key in EventDefinition.__dataclass_fields__
            },
        )
        for item in _mapping_list(raw.get("events"), "events")
    )

    values = _mapping(raw.get("baseline"), "baseline")
    baseline = ServiceBaseline(
        auth_success_min=_rate(values["auth_success_min"], "auth_success_min"),
        auth_success_max=_rate(values["auth_success_max"], "auth_success_max"),
        otp_delivery_min=_rate(values["otp_delivery_min"], "otp_delivery_min"),
        otp_delivery_max=_rate(values["otp_delivery_max"], "otp_delivery_max"),
        otp_verification_min=_rate(values["otp_verification_min"], "otp_verification_min"),
        otp_verification_max=_rate(values["otp_verification_max"], "otp_verification_max"),
        token_success_rate=_rate(values["token_success_rate"], "token_success_rate"),
        http_5xx_rate=_rate(values["http_5xx_rate"], "http_5xx_rate"),
        auth_latency_p50_seconds=float(values["auth_latency_p50_seconds"]),
        auth_latency_sigma=float(values["auth_latency_sigma"]),
        token_latency_p50_seconds=float(values["token_latency_p50_seconds"]),
    )
    if baseline.auth_success_min > baseline.auth_success_max:
        raise ValueError("auth success range is inverted")

    interval = float(environment_config["generation_interval_seconds"])
    day_seconds = float(environment_config["simulation_day_seconds"])
    seed = int(environment_config["random_seed"])
    noise_ratio = float(raw.get("noise_ratio", 0.05))
    if interval <= 0 or day_seconds <= 0:
        raise ValueError("generation interval and simulation day must be positive")
    if not 0 <= noise_ratio <= 0.2:
        raise ValueError("noise_ratio must be between 0 and 0.2")
    return Settings(
        interval,
        day_seconds,
        seed,
        noise_ratio,
        profile,
        schedule,
        events,
        baseline,
    )
