from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class Scenario:
    """A bounded traffic profile used by the deterministic generator."""

    auth_requests: int
    auth_success_rate: float
    auth_under_500ms_rate: float
    otp_requests: int
    otp_delivery_rate: float
    otp_pending_rate: float
    otp_verification_rate: float
    token_requests: int
    token_success_rate: float
    platform_requests: int
    platform_availability_rate: float
    otp_provider_up: float
    otp_queue_size: int


@dataclass(frozen=True)
class Settings:
    generation_interval_seconds: float
    initial_scenario: str
    scenarios: dict[str, Scenario]


def _rate(value: Any, key: str) -> float:
    number = float(value)
    if not 0.0 <= number <= 1.0:
        raise ValueError(f"{key} must be between 0 and 1")
    return number


def load_settings() -> Settings:
    default_path = Path(__file__).resolve().parents[2] / "config" / "scenarios.yaml"
    path = Path(os.getenv("VID_SCENARIOS_FILE", str(default_path)))
    with path.open(encoding="utf-8") as stream:
        raw = yaml.safe_load(stream)

    if not isinstance(raw, dict) or not isinstance(raw.get("scenarios"), dict):
        raise ValueError(f"Invalid scenarios configuration: {path}")

    scenarios: dict[str, Scenario] = {}
    for name, values in raw["scenarios"].items():
        if not isinstance(values, dict):
            raise ValueError(f"Scenario {name!r} must be a mapping")
        scenarios[name] = Scenario(
            auth_requests=int(values["auth_requests"]),
            auth_success_rate=_rate(values["auth_success_rate"], "auth_success_rate"),
            auth_under_500ms_rate=_rate(
                values["auth_under_500ms_rate"], "auth_under_500ms_rate"
            ),
            otp_requests=int(values["otp_requests"]),
            otp_delivery_rate=_rate(values["otp_delivery_rate"], "otp_delivery_rate"),
            otp_pending_rate=_rate(values["otp_pending_rate"], "otp_pending_rate"),
            otp_verification_rate=_rate(
                values["otp_verification_rate"], "otp_verification_rate"
            ),
            token_requests=int(values["token_requests"]),
            token_success_rate=_rate(values["token_success_rate"], "token_success_rate"),
            platform_requests=int(values["platform_requests"]),
            platform_availability_rate=_rate(
                values["platform_availability_rate"], "platform_availability_rate"
            ),
            otp_provider_up=_rate(values["otp_provider_up"], "otp_provider_up"),
            otp_queue_size=max(0, int(values["otp_queue_size"])),
        )

    interval = float(os.getenv("VID_GENERATION_INTERVAL_SECONDS", "5"))
    initial = os.getenv("VID_INITIAL_SCENARIO", "normal")
    if interval <= 0:
        raise ValueError("VID_GENERATION_INTERVAL_SECONDS must be positive")
    if initial not in scenarios:
        raise ValueError(f"Unknown initial scenario: {initial}")
    return Settings(interval, initial, scenarios)
