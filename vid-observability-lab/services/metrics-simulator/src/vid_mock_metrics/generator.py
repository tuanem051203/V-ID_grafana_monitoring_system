from __future__ import annotations

import asyncio
import logging
from collections.abc import Sequence

from vid_mock_metrics.config import Scenario
from vid_mock_metrics.metrics import (
    AUTH_DURATION,
    AUTH_IN_PROGRESS,
    AUTH_REQUESTS,
    HTTP_REQUESTS,
    OTP_PROVIDER_STATUS,
    OTP_QUEUE_SIZE,
    OTP_SEND_ATTEMPTS,
    OTP_VERIFICATION_ATTEMPTS,
    TOKEN_IN_PROGRESS,
    TOKEN_REQUESTS,
)
from vid_mock_metrics.scenarios import ScenarioManager

LOGGER = logging.getLogger(__name__)


def _split(total: int, weights: Sequence[float]) -> list[int]:
    """Deterministically allocate total events while preserving the total."""
    raw = [total * weight / sum(weights) for weight in weights]
    values = [int(value) for value in raw]
    for index in sorted(
        range(len(raw)), key=lambda item: raw[item] - values[item], reverse=True
    )[: total - sum(values)]:
        values[index] += 1
    return values


class MetricsGenerator:
    def __init__(self, manager: ScenarioManager, interval: float) -> None:
        self._manager = manager
        self._interval = interval
        self._tick = 0

    async def run(self) -> None:
        while True:
            try:
                name, scenario = await self._manager.get()
                self.generate(scenario)
                LOGGER.info("Generated metric batch", extra={"scenario": name})
            except asyncio.CancelledError:
                raise
            except Exception:
                LOGGER.exception("Failed to generate metric batch")
            await asyncio.sleep(self._interval)

    def generate(self, profile: Scenario) -> None:
        self._tick += 1
        wave = (-1, 0, 1, 0)[self._tick % 4]

        auth_success, auth_failed = _split(
            profile.auth_requests, [profile.auth_success_rate, 1 - profile.auth_success_rate]
        )
        for client, count in zip(
            ("terminal", "mobile", "web"), _split(auth_success, (0.25, 0.5, 0.25))
        ):
            AUTH_REQUESTS.labels("success", "true", client, "none").inc(count)
        for reason, count in zip(
            ("invalid_credential", "locked", "expired", "system_error"),
            _split(auth_failed, (0.55, 0.15, 0.15, 0.15)),
        ):
            AUTH_REQUESTS.labels("failed", "false", "mobile", reason).inc(count)

        fast, slow = _split(
            profile.auth_requests,
            [profile.auth_under_500ms_rate, 1 - profile.auth_under_500ms_rate],
        )
        for index in range(fast):
            AUTH_DURATION.labels("success", "mobile", "none").observe(
                (0.08, 0.14, 0.24, 0.42)[(index + self._tick) % 4]
            )
        for index in range(slow):
            AUTH_DURATION.labels("success", "mobile", "none").observe(
                (0.65, 0.9, 1.4, 2.4)[(index + self._tick) % 4]
            )

        delivered, failed, pending = _split(
            profile.otp_requests,
            [
                profile.otp_delivery_rate,
                max(0.0, 1 - profile.otp_delivery_rate - profile.otp_pending_rate),
                profile.otp_pending_rate,
            ],
        )
        for provider, count in zip(
            ("viettel", "vnpt", "mock"), _split(delivered, (0.45, 0.4, 0.15))
        ):
            OTP_SEND_ATTEMPTS.labels("delivered", provider, "sms", "none").inc(count)
        for reason, count in zip(
            ("provider_error", "invalid_destination", "timeout", "rate_limited"),
            _split(failed, (0.45, 0.15, 0.25, 0.15)),
        ):
            OTP_SEND_ATTEMPTS.labels("failed", "viettel", "sms", reason).inc(count)
        OTP_SEND_ATTEMPTS.labels("pending", "vnpt", "sms", "none").inc(pending)

        verified, verify_failed = _split(
            profile.otp_requests,
            [profile.otp_verification_rate, 1 - profile.otp_verification_rate],
        )
        OTP_VERIFICATION_ATTEMPTS.labels("success", "true", "sms", "none").inc(verified)
        for reason, count in zip(
            ("wrong_otp", "expired_otp", "max_attempts", "system_error"),
            _split(verify_failed, (0.6, 0.2, 0.15, 0.05)),
        ):
            OTP_VERIFICATION_ATTEMPTS.labels("failed", "false", "sms", reason).inc(count)

        issued, token_failed = _split(
            profile.token_requests,
            [profile.token_success_rate, 1 - profile.token_success_rate],
        )
        token_types = ("access_token", "refresh_token", "id_token")
        grants = ("authorization_code", "refresh_token", "client_credentials")
        for index, count in enumerate(_split(issued, (0.55, 0.3, 0.15))):
            TOKEN_REQUESTS.labels("issued", "true", token_types[index], grants[index], "none").inc(
                count
            )
        for reason, count in zip(
            ("invalid_grant", "signing_error", "storage_error", "system_error"),
            _split(token_failed, (0.45, 0.2, 0.15, 0.2)),
        ):
            TOKEN_REQUESTS.labels(
                "failed", "false", "access_token", "authorization_code", reason
            ).inc(count)

        available, unavailable = _split(
            profile.platform_requests,
            [profile.platform_availability_rate, 1 - profile.platform_availability_rate],
        )
        routes = (
            ("auth-service", "/authenticate"),
            ("otp-service", "/otp/send"),
            ("otp-service", "/otp/verify"),
            ("token-service", "/token"),
            ("token-service", "/token/refresh"),
        )
        for (service, endpoint), count in zip(routes, _split(available, (3, 1, 1, 2, 1))):
            HTTP_REQUESTS.labels(service, endpoint, "POST", "200", "true").inc(count)
        for (service, endpoint), count in zip(routes, _split(unavailable, (3, 1, 1, 2, 1))):
            HTTP_REQUESTS.labels(service, endpoint, "POST", "503", "true").inc(count)

        AUTH_IN_PROGRESS.set(max(0, round(profile.auth_requests / 20) + wave))
        TOKEN_IN_PROGRESS.set(max(0, round(profile.token_requests / 20) - wave))
        OTP_QUEUE_SIZE.set(max(0, profile.otp_queue_size + wave * 2))
        for provider in ("viettel", "vnpt"):
            OTP_PROVIDER_STATUS.labels(provider).set(profile.otp_provider_up)
        OTP_PROVIDER_STATUS.labels("mock").set(1)
