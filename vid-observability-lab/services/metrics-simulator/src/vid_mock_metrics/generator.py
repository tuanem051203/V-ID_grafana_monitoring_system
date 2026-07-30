from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import asdict, dataclass
from datetime import datetime

from vid_mock_metrics.config import Settings
from vid_mock_metrics.events import EventEffects, EventScheduler
from vid_mock_metrics.metrics import (
    APPLICATION_ERRORS,
    AUTH_DURATION,
    AUTH_FAILED,
    AUTH_REQUESTS,
    AUTH_SUCCESS,
    AUTHORIZATION_DECISIONS,
    DATABASE_CONNECTIONS,
    DATABASE_MAX_CONNECTIONS,
    DATABASE_QUERIES,
    DATABASE_QUERY_DURATION,
    HTTP_DURATION,
    HTTP_REQUESTS,
    HTTP_REQUESTS_5XX,
    INFRASTRUCTURE_CPU_USAGE,
    INFRASTRUCTURE_MEMORY_USAGE,
    OTP_DELIVERY_FAILED,
    OTP_DELIVERY_SUCCESS,
    OTP_PROVIDER_STATUS,
    OTP_QUEUE_SIZE,
    OTP_SEND,
    OTP_VERIFY,
    OTP_VERIFY_FAILED,
    OTP_VERIFY_SUCCESS,
    POD_READY,
    SERVICE_HEALTH,
    SIMULATION_EVENT_ACTIVE,
    SIMULATION_TPS,
    TOKEN_DURATION,
    TOKEN_FAILED,
    TOKEN_ISSUE,
    TOKEN_REQUEST,
)
from vid_mock_metrics.random_utils import RandomModel
from vid_mock_metrics.traffic import TrafficGenerator

LOGGER = logging.getLogger(__name__)

ROUTES = (
    ("auth-service", "/authenticate", 0.40),
    ("otp-service", "/otp/send", 0.12),
    ("otp-service", "/otp/verify", 0.10),
    ("token-service", "/token", 0.25),
    ("token-service", "/token/refresh", 0.13),
)


@dataclass(frozen=True)
class SimulationSnapshot:
    profile: str
    simulated_time: str
    current_tps: float
    active_events: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


class MetricsGenerator:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._random = RandomModel(settings.random_seed)
        self._traffic = TrafficGenerator(
            settings.load_profile.peak_tps,
            settings.traffic_schedule,
            settings.noise_ratio,
            self._random,
        )
        self._scheduler = EventScheduler(settings.events)
        now = datetime.now().astimezone()
        self._anchor_second = now.hour * 3600 + now.minute * 60 + now.second
        self._anchor_monotonic = time.monotonic()
        self._snapshot = SimulationSnapshot(
            settings.load_profile.name,
            now.strftime("%H:%M:%S"),
            0.0,
            (),
        )

    @property
    def snapshot(self) -> SimulationSnapshot:
        return self._snapshot

    def simulated_second_of_day(self) -> float:
        elapsed = time.monotonic() - self._anchor_monotonic
        speed = 86400 / self._settings.simulation_day_seconds
        return (self._anchor_second + elapsed * speed) % 86400

    async def run(self) -> None:
        while True:
            started = time.monotonic()
            try:
                self.generate_at(self.simulated_second_of_day())
            except asyncio.CancelledError:
                raise
            except Exception:
                LOGGER.exception("Failed to generate metric batch")
            elapsed = time.monotonic() - started
            await asyncio.sleep(max(0, self._settings.generation_interval_seconds - elapsed))

    def generate_at(self, second_of_day: float) -> SimulationSnapshot:
        effects = self._scheduler.active_at(second_of_day)
        baseline_tps = self._traffic.tps_at(second_of_day / 60)
        tps = baseline_tps * effects.traffic_multiplier
        count = self._random.event_count(tps * self._settings.generation_interval_seconds)

        self._generate_authentication(count, tps, effects)
        self._generate_otp(count, effects)
        self._generate_token(count, effects)
        self._generate_platform(count, tps, effects)
        self._generate_supporting_metrics(count, tps, effects)
        self._set_simulation_state(tps, effects)

        hour = int(second_of_day // 3600)
        minute = int(second_of_day % 3600 // 60)
        second = int(second_of_day % 60)
        self._snapshot = SimulationSnapshot(
            self._settings.load_profile.name,
            f"{hour:02d}:{minute:02d}:{second:02d}",
            round(tps, 2),
            effects.names,
        )
        LOGGER.info(
            "Generated production-like metric batch",
            extra=self._snapshot.as_dict(),
        )
        return self._snapshot

    def _generate_authentication(
        self, count: int, tps: float, effects: EventEffects
    ) -> None:
        baseline = self._settings.baseline
        success_rate = self._random.bounded_rate(
            baseline.auth_success_min,
            baseline.auth_success_max,
            "auth_success",
        )
        success_rate = max(0, success_rate - effects.auth_success_penalty)
        client_counts = self._random.split(count, (0.50, 0.30, 0.20))
        clients = ("mobile", "web", "terminal")
        utilization = min(2.0, tps / self._settings.load_profile.peak_tps)
        latency_multiplier = (1 + 0.25 * utilization**2) * effects.auth_latency_multiplier

        for client, total in zip(clients, client_counts):
            good, bad = self._random.split(total, (success_rate, 1 - success_rate))
            AUTH_REQUESTS.labels(client).inc(total)
            AUTH_SUCCESS.labels(client).inc(good)
            for _ in range(good):
                AUTH_DURATION.labels("success", client).observe(
                    self._random.lognormal_latency(
                        baseline.auth_latency_p50_seconds,
                        baseline.auth_latency_sigma,
                        latency_multiplier,
                    )
                )
            reason_counts = self._random.split(bad, (0.25, 0.20, 0.15, 0.40))
            for reason, reason_count in zip(
                ("invalid_credential", "locked", "expired", "system_error"),
                reason_counts,
            ):
                AUTH_FAILED.labels(client, reason).inc(reason_count)
                for _ in range(reason_count):
                    AUTH_DURATION.labels("failed", client).observe(
                        self._random.lognormal_latency(
                            baseline.auth_latency_p50_seconds,
                            baseline.auth_latency_sigma,
                            latency_multiplier * 1.15,
                        )
                    )

    def _generate_otp(self, auth_count: int, effects: EventEffects) -> None:
        baseline = self._settings.baseline
        send_count = self._random.event_count(auth_count * 0.28)
        delivery_rate = self._random.bounded_rate(
            baseline.otp_delivery_min,
            baseline.otp_delivery_max,
            "otp_delivery",
        )
        delivery_rate = max(0, delivery_rate - effects.otp_delivery_penalty)
        providers = ("viettel", "vnpt", "mock")
        send_providers = self._random.split(send_count, (0.45, 0.40, 0.15))
        delivered = 0
        failed = 0
        for provider, sent in zip(providers, send_providers):
            success, provider_failed = self._random.split(
                sent, (delivery_rate, 1 - delivery_rate)
            )
            OTP_SEND.labels(provider, "sms").inc(sent)
            OTP_DELIVERY_SUCCESS.labels(provider, "sms").inc(success)
            delivered += success
            failed += provider_failed
        failed_reasons = self._random.split(failed, (0.60, 0.25, 0.15))
        for reason, value in zip(
            ("provider_error", "timeout", "invalid_destination"), failed_reasons
        ):
            OTP_DELIVERY_FAILED.labels("viettel", "sms", reason).inc(value)

        verify_count = self._random.event_count(delivered * 0.92)
        verify_rate = self._random.bounded_rate(
            baseline.otp_verification_min,
            baseline.otp_verification_max,
            "otp_verification",
        )
        verified, verify_failed = self._random.split(
            verify_count, (verify_rate, 1 - verify_rate)
        )
        OTP_VERIFY.labels("sms").inc(verify_count)
        OTP_VERIFY_SUCCESS.labels("sms").inc(verified)
        for reason, value in zip(
            ("wrong_otp", "expired_otp", "max_attempts"),
            self._random.split(verify_failed, (0.65, 0.25, 0.10)),
        ):
            OTP_VERIFY_FAILED.labels("sms", reason).inc(value)

    def _generate_token(self, auth_count: int, effects: EventEffects) -> None:
        baseline = self._settings.baseline
        request_count = self._random.event_count(auth_count * 0.80)
        success_rate = max(
            0,
            baseline.token_success_rate
            + self._random.smooth_noise("token_success", 0.0003)
            - effects.token_success_penalty,
        )
        token_types = ("access_token", "refresh_token", "id_token")
        grants = ("authorization_code", "refresh_token", "client_credentials")
        request_types = self._random.split(request_count, (0.55, 0.30, 0.15))
        failed = 0
        for token_type, grant, requested in zip(token_types, grants, request_types):
            successful, type_failed = self._random.split(
                requested, (success_rate, 1 - success_rate)
            )
            TOKEN_REQUEST.labels(token_type, grant).inc(requested)
            TOKEN_ISSUE.labels(token_type, grant).inc(successful)
            failed += type_failed
            for _ in range(successful):
                TOKEN_DURATION.labels(token_type, grant, "success").observe(
                    self._random.lognormal_latency(
                        baseline.token_latency_p50_seconds,
                        0.55,
                        effects.token_latency_multiplier,
                    )
                )
        for reason, value in zip(
            ("signing_error", "storage_error", "system_error"),
            self._random.split(failed, (0.30, 0.30, 0.40)),
        ):
            TOKEN_FAILED.labels(
                "access_token", "authorization_code", reason
            ).inc(value)
            for _ in range(value):
                TOKEN_DURATION.labels(
                    "access_token", "authorization_code", "failed"
                ).observe(
                    self._random.lognormal_latency(
                        baseline.token_latency_p50_seconds,
                        0.55,
                        effects.token_latency_multiplier * 1.2,
                    )
                )

    def _generate_platform(
        self, auth_count: int, tps: float, effects: EventEffects
    ) -> None:
        request_count = self._random.event_count(auth_count * 1.20)
        error_rate = (
            effects.http_5xx_rate
            if effects.http_5xx_rate is not None
            else max(
                0,
                self._settings.baseline.http_5xx_rate
                + self._random.smooth_noise("http_5xx", 0.00005),
            )
        )
        errors = self._random.event_count(request_count * error_rate)
        route_counts = self._random.split(
            request_count, tuple(route[2] for route in ROUTES)
        )
        error_counts = self._random.split(errors, tuple(route[2] for route in ROUTES))
        utilization = min(2.0, tps / self._settings.load_profile.peak_tps)
        latency_multiplier = 1 + 0.30 * utilization**2
        for (service, endpoint, _), total, failed in zip(
            ROUTES, route_counts, error_counts
        ):
            HTTP_REQUESTS.labels(service, endpoint, "POST", "true").inc(total)
            HTTP_REQUESTS_5XX.labels(
                service, endpoint, "POST", "true", "503"
            ).inc(failed)
            for _ in range(total):
                HTTP_DURATION.labels(service, endpoint, "POST").observe(
                    self._random.lognormal_latency(0.10, 0.62, latency_multiplier)
                )

    def _generate_supporting_metrics(
        self, auth_count: int, tps: float, effects: EventEffects
    ) -> None:
        # Pre-create every bounded error series so Grafana shows a healthy zero
        # instead of "No data" before the first scheduled incident.
        application_error_series = (
            ("auth-service", "database_dependency", "critical"),
            ("otp-service", "provider_error", "critical"),
            ("token-service", "cache_dependency", "critical"),
        )
        for service, error_type, severity in application_error_series:
            APPLICATION_ERRORS.labels(service, error_type, severity).inc(0)

        allowed, denied = self._random.split(auth_count, (0.985, 0.015))
        AUTHORIZATION_DECISIONS.labels("identity", "allow", "policy_match").inc(allowed)
        AUTHORIZATION_DECISIONS.labels(
            "identity", "deny", "insufficient_scope"
        ).inc(denied)

        database_count = self._random.event_count(auth_count * 0.70)
        database_error_rate = (
            effects.database_error_rate
            if effects.database_error_rate is not None
            else 0.001
        )
        database_errors = self._random.event_count(database_count * database_error_rate)
        database_success = max(0, database_count - database_errors)
        operations = ("select", "insert", "update")
        operation_counts = self._random.split(database_success, (0.70, 0.15, 0.15))
        for operation, operation_count in zip(operations, operation_counts):
            for _ in range(operation_count):
                DATABASE_QUERY_DURATION.labels(
                    "identity-db", operation, "success"
                ).observe(
                    self._random.lognormal_latency(
                        0.025, 0.70, effects.database_latency_multiplier
                    )
                )
            DATABASE_QUERIES.labels(
                "identity-db", operation, "success"
            ).inc(operation_count)
        DATABASE_QUERIES.labels("identity-db", "select", "error").inc(database_errors)

        utilization = min(1.0, tps / self._settings.load_profile.peak_tps)
        for index, node in enumerate(("node-a", "node-b")):
            node_offset = index * 0.03
            INFRASTRUCTURE_CPU_USAGE.labels(node).set(
                min(1, 0.25 + utilization * 0.60 + node_offset)
            )
            INFRASTRUCTURE_MEMORY_USAGE.labels(node).set(
                min(1, 0.45 + utilization * 0.35 + node_offset)
            )
        pods = tuple(
            (service, f"{service.removesuffix('-service')}-{replica}")
            for service in ("auth-service", "otp-service", "token-service")
            for replica in (0, 1)
        )
        for index, (service, pod) in enumerate(pods):
            POD_READY.labels(service, pod).set(index >= effects.unavailable_pods)

        active_connections = round(20 + utilization * 65)
        DATABASE_MAX_CONNECTIONS.labels("identity-db").set(100)
        DATABASE_CONNECTIONS.labels("identity-db", "active").set(active_connections)
        DATABASE_CONNECTIONS.labels("identity-db", "idle").set(100 - active_connections)
        queue_size = (
            round(auth_count * effects.otp_delivery_penalty * 0.28)
            if effects.otp_delivery_penalty
            else max(0, round(utilization * 8))
        )
        OTP_QUEUE_SIZE.set(queue_size)
        sms_down = effects.otp_delivery_penalty >= 0.2
        for provider in ("viettel", "vnpt"):
            OTP_PROVIDER_STATUS.labels(provider).set(not sms_down)
        OTP_PROVIDER_STATUS.labels("mock").set(1)
        for service in (
            "auth-service",
            "otp-service",
            "token-service",
            "authorization-service",
        ):
            SERVICE_HEALTH.labels(service).set(
                not effects.http_5xx_rate or effects.http_5xx_rate < 0.05
            )
        if effects.auth_success_penalty:
            APPLICATION_ERRORS.labels(
                "auth-service", "database_dependency", "critical"
            ).inc(max(1, database_errors))
        if effects.otp_delivery_penalty:
            APPLICATION_ERRORS.labels(
                "otp-service", "provider_error", "critical"
            ).inc(max(1, round(auth_count * 0.01)))
        if effects.token_success_penalty:
            APPLICATION_ERRORS.labels(
                "token-service", "cache_dependency", "critical"
            ).inc(max(1, round(auth_count * 0.01)))

    def _set_simulation_state(self, tps: float, effects: EventEffects) -> None:
        SIMULATION_TPS.labels(self._settings.load_profile.name).set(tps)
        active_names = set(effects.names)
        for definition in self._settings.events:
            SIMULATION_EVENT_ACTIVE.labels(definition.name).set(
                definition.name in active_names
            )
