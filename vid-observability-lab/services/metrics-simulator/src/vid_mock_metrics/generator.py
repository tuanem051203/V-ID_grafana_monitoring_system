from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import asdict, dataclass, replace
from datetime import datetime

from vid_mock_metrics.config import CrossRegionHop, Settings
from vid_mock_metrics.events import EventEffects, EventScheduler
from vid_mock_metrics.metrics import (
    APPLICATION_ERRORS,
    AUTH_DURATION,
    AUTH_FAILED,
    AUTH_REQUESTS,
    AUTH_SUCCESS,
    AUTHORIZATION_DECISIONS,
    CROSS_REGION_DURATION,
    CROSS_REGION_FAILURES,
    CROSS_REGION_HOP_DURATION,
    CROSS_REGION_HOP_REQUESTS,
    CROSS_REGION_REQUESTS,
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
    OTP_DELIVERY_DURATION,
    OTP_DELIVERY_REPORTS,
    OTP_DELIVERY_SUCCESS,
    OTP_JOURNEY_DURATION,
    OTP_JOURNEY_FAILURES,
    OTP_JOURNEY_REQUESTS,
    OTP_PROVIDER_STATUS,
    OTP_QUEUE_SIZE,
    OTP_QUEUE_WAIT_DURATION,
    OTP_SEND,
    OTP_STAGE_DURATION,
    OTP_STAGE_REQUESTS,
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
from vid_mock_metrics.tracing import emit_otp_trace
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
OTP_JOURNEY_STAGES = {
    "edge_to_kong",
    "kong_to_idp",
    "redis_challenge",
    "route_selection",
    "queue_wait",
    "gsm_submit",
    "carrier_delivery",
}


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
        self._manual_otp_queue_deadline = 0.0
        self._manual_otp_queue_size = 0
        self._manual_cross_region_deadline = 0.0
        self._manual_cross_region_destination = "id"
        self._manual_cross_region_hop = "carrier_delivery"
        self._manual_cross_region_latency_multiplier = 1.0
        self._manual_cross_region_failure_rate = 0.0
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

    def activate_otp_queue_warning(
        self, duration_seconds: int, queue_size: int
    ) -> dict[str, object]:
        self._manual_otp_queue_deadline = time.monotonic() + duration_seconds
        self._manual_otp_queue_size = queue_size
        return self.otp_queue_warning_state()

    def clear_otp_queue_warning(self) -> dict[str, object]:
        self._manual_otp_queue_deadline = 0.0
        self._manual_otp_queue_size = 0
        return self.otp_queue_warning_state()

    def otp_queue_warning_state(self) -> dict[str, object]:
        remaining = max(0.0, self._manual_otp_queue_deadline - time.monotonic())
        active = remaining > 0
        return {
            "scenario": "otp_queue_backlog",
            "active": active,
            "queue_size": self._manual_otp_queue_size if active else 0,
            "remaining_seconds": round(remaining, 1),
        }

    def activate_cross_region_degradation(
        self,
        duration_seconds: int,
        destination_region: str,
        hop: str,
        latency_multiplier: float,
        failure_rate: float,
    ) -> dict[str, object]:
        destinations = {
            item.destination_region: item for item in self._settings.cross_region.destinations
        }
        if destination_region not in destinations:
            raise ValueError(f"Unknown cross-region destination {destination_region!r}")
        allowed_hops = {item.name for item in destinations[destination_region].hops}
        allowed_hops.update(OTP_JOURNEY_STAGES)
        if hop not in allowed_hops:
            raise ValueError(f"Unknown cross-region hop {hop!r}")
        self._manual_cross_region_deadline = time.monotonic() + duration_seconds
        self._manual_cross_region_destination = destination_region
        self._manual_cross_region_hop = hop
        self._manual_cross_region_latency_multiplier = latency_multiplier
        self._manual_cross_region_failure_rate = failure_rate
        return self.cross_region_degradation_state()

    def clear_cross_region_degradation(self) -> dict[str, object]:
        self._manual_cross_region_deadline = 0.0
        return self.cross_region_degradation_state()

    def cross_region_degradation_state(self) -> dict[str, object]:
        remaining = max(0.0, self._manual_cross_region_deadline - time.monotonic())
        active = remaining > 0
        return {
            "scenario": "cross_region_degradation",
            "active": active,
            "destination_region": self._manual_cross_region_destination,
            "hop": self._manual_cross_region_hop,
            "latency_multiplier": self._manual_cross_region_latency_multiplier,
            "failure_rate": self._manual_cross_region_failure_rate,
            "remaining_seconds": round(remaining, 1),
        }

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
        manual_warning_active = self._manual_otp_queue_deadline > time.monotonic()
        manual_cross_region_active = self._manual_cross_region_deadline > time.monotonic()
        if manual_cross_region_active:
            effects = replace(
                effects,
                cross_region_affected_hop=self._manual_cross_region_hop,
                cross_region_affected_destination=self._manual_cross_region_destination,
                cross_region_latency_multiplier=self._manual_cross_region_latency_multiplier,
                cross_region_failure_rate=self._manual_cross_region_failure_rate,
            )
        baseline_tps = self._traffic.tps_at(second_of_day / 60)
        tps = baseline_tps * effects.traffic_multiplier
        count = self._random.event_count(tps * self._settings.generation_interval_seconds)

        self._generate_authentication(count, tps, effects)
        self._generate_otp(count, effects)
        self._generate_otp_journeys(count, effects)
        self._generate_token(count, effects)
        self._generate_platform(count, tps, effects)
        self._generate_supporting_metrics(count, tps, effects, manual_warning_active)
        self._set_simulation_state(
            tps, effects, manual_warning_active, manual_cross_region_active
        )

        hour = int(second_of_day // 3600)
        minute = int(second_of_day % 3600 // 60)
        second = int(second_of_day % 60)
        self._snapshot = SimulationSnapshot(
            self._settings.load_profile.name,
            f"{hour:02d}:{minute:02d}:{second:02d}",
            round(tps, 2),
            effects.names
            + (("manual_otp_queue_backlog",) if manual_warning_active else ())
            + (("manual_cross_region_degradation",) if manual_cross_region_active else ()),
        )
        LOGGER.info(
            "Generated production-like metric batch",
            extra=self._snapshot.as_dict(),
        )
        return self._snapshot

    def _generate_authentication(self, count: int, tps: float, effects: EventEffects) -> None:
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
        for provider, sent in zip(providers, send_providers):
            success, provider_failed = self._random.split(sent, (delivery_rate, 1 - delivery_rate))
            OTP_SEND.labels(provider, "sms").inc(sent)
            OTP_DELIVERY_SUCCESS.labels(provider, "sms").inc(success)
            delivered += success
            failed_reasons = self._random.split(provider_failed, (0.60, 0.25, 0.15))
            for reason, value in zip(
                ("provider_error", "timeout", "invalid_destination"), failed_reasons
            ):
                OTP_DELIVERY_FAILED.labels(provider, "sms", reason).inc(value)

        verify_count = self._random.event_count(delivered * 0.92)
        verify_rate = self._random.bounded_rate(
            baseline.otp_verification_min,
            baseline.otp_verification_max,
            "otp_verification",
        )
        verified, verify_failed = self._random.split(verify_count, (verify_rate, 1 - verify_rate))
        OTP_VERIFY.labels("sms").inc(verify_count)
        OTP_VERIFY_SUCCESS.labels("sms").inc(verified)
        for reason, value in zip(
            ("wrong_otp", "expired_otp", "max_attempts"),
            self._random.split(verify_failed, (0.65, 0.25, 0.10)),
        ):
            OTP_VERIFY_FAILED.labels("sms", reason).inc(value)

    def _generate_otp_journeys(self, auth_count: int, effects: EventEffects) -> None:
        """Generate correlated stage metrics and sampled synthetic traces."""
        total = self._random.event_count(auth_count * 0.10)
        countries = ("us", "dk", "id", "ph", "la", "in", "kz", "ru", "nl")
        weights = (0.20, 0.06, 0.18, 0.15, 0.10, 0.15, 0.05, 0.06, 0.05)
        stages = (
            ("edge_to_kong", "kong", 0.018, 0.001),
            ("kong_to_idp", "identity-provider", 0.035, 0.001),
            ("redis_challenge", "redis", 0.008, 0.001),
            ("route_selection", "identity-provider", 0.003, 0.0005),
            ("queue_wait", "notification-center", 0.040, 0.002),
            ("gsm_submit", "gsm-gateway", 0.280, 0.006),
            ("carrier_delivery", "sms-provider", 3.500, 0.012),
        )
        for country, count in zip(countries, self._random.split(total, weights)):
            provider = "gsm"
            for _ in range(count):
                observed: list[tuple[str, str, float, str]] = []
                terminal_result = "success"
                end_to_end = 0.0
                for stage, service, p50, baseline_failure in stages:
                    affected = (
                        effects.cross_region_affected_destination == country
                        and effects.cross_region_affected_hop == stage
                    )
                    multiplier = effects.cross_region_latency_multiplier if affected else 1.0
                    failure_rate = (
                        effects.cross_region_failure_rate
                        if affected and effects.cross_region_failure_rate is not None
                        else baseline_failure
                    )
                    duration = self._random.lognormal_latency(p50, 0.45, multiplier)
                    failed = self._random.split(1, (1 - failure_rate, failure_rate))[1] == 1
                    stage_result = "failure" if failed else "success"
                    observed.append((stage, service, duration, stage_result))
                    end_to_end += duration
                    OTP_STAGE_REQUESTS.labels(
                        country, "sms", provider, stage, service, stage_result
                    ).inc()
                    OTP_STAGE_DURATION.labels(
                        country, "sms", provider, stage, service, stage_result
                    ).observe(duration)
                    if stage == "queue_wait":
                        OTP_QUEUE_WAIT_DURATION.labels(provider, stage_result).observe(duration)
                    if stage == "carrier_delivery":
                        OTP_DELIVERY_REPORTS.labels(
                            country, "sms", provider, stage_result
                        ).inc()
                        OTP_DELIVERY_DURATION.labels(
                            country, "sms", provider, stage_result
                        ).observe(duration)
                    if failed:
                        terminal_result = "failure"
                        OTP_JOURNEY_FAILURES.labels(
                            country,
                            "sms",
                            provider,
                            stage,
                            service,
                            "timeout" if affected else "dependency_error",
                        ).inc()
                        break
                trace_value = None
                if self._random.split(1, (0.90, 0.10))[1] == 1:
                    trace_value = emit_otp_trace(
                        {
                            "otp.destination_country": country,
                            "otp.channel": "sms",
                            "otp.provider": provider,
                            "simulation.synthetic": "true",
                        },
                        observed,
                        terminal_result,
                    )
                exemplar = {"trace_id": trace_value} if trace_value else None
                OTP_JOURNEY_REQUESTS.labels(
                    "vn", country, "sms", provider, terminal_result
                ).inc(exemplar=exemplar)
                OTP_JOURNEY_DURATION.labels(
                    "vn", country, "sms", provider, terminal_result
                ).observe(end_to_end, exemplar=exemplar)

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
            TOKEN_FAILED.labels("access_token", "authorization_code", reason).inc(value)
            for _ in range(value):
                TOKEN_DURATION.labels("access_token", "authorization_code", "failed").observe(
                    self._random.lognormal_latency(
                        baseline.token_latency_p50_seconds,
                        0.55,
                        effects.token_latency_multiplier * 1.2,
                    )
                )

    def _generate_platform(self, auth_count: int, tps: float, effects: EventEffects) -> None:
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
        route_counts = self._random.split(request_count, tuple(route[2] for route in ROUTES))
        error_counts = self._random.split(errors, tuple(route[2] for route in ROUTES))
        utilization = min(2.0, tps / self._settings.load_profile.peak_tps)
        latency_multiplier = 1 + 0.30 * utilization**2
        for (service, endpoint, _), total, failed in zip(ROUTES, route_counts, error_counts):
            HTTP_REQUESTS.labels(service, endpoint, "POST", "true").inc(total)
            HTTP_REQUESTS_5XX.labels(service, endpoint, "POST", "true", "503").inc(failed)
            for _ in range(total):
                HTTP_DURATION.labels(service, endpoint, "POST").observe(
                    self._random.lognormal_latency(0.10, 0.62, latency_multiplier)
                )
        self._generate_cross_region(route_counts, effects)

    def _generate_cross_region(
        self, route_counts: tuple[int, ...], effects: EventEffects
    ) -> None:
        """Generate bounded RED metrics for the configured multi-hop route."""
        route = self._settings.cross_region
        if not route.enabled:
            return
        for (service, endpoint, _), platform_total in zip(ROUTES, route_counts):
            total = self._random.event_count(platform_total * route.traffic_ratio)
            operation = endpoint.strip("/").replace("/", "_")
            destination_counts = self._random.split(
                total,
                tuple(item.traffic_weight for item in route.destinations),
            )
            for destination, destination_total in zip(
                route.destinations, destination_counts
            ):
                self._generate_cross_region_destination(
                    route.source_region,
                    destination.destination_region,
                    destination.hops,
                    destination_total,
                    service,
                    operation,
                    effects,
                )

    def _generate_cross_region_destination(
        self,
        source_region: str,
        destination_region: str,
        hops: tuple[CrossRegionHop, ...],
        total: int,
        service: str,
        operation: str,
        effects: EventEffects,
    ) -> None:
        route = self._settings.cross_region
        for _ in range(total):
            end_to_end_duration = 0.0
            terminal_result = "success"
            for hop in hops:
                affected = (
                    effects.cross_region_affected_destination == destination_region
                    and effects.cross_region_affected_hop == hop.name
                )
                multiplier = effects.cross_region_latency_multiplier if affected else 1.0
                failure_rate = (
                    effects.cross_region_failure_rate
                    if affected and effects.cross_region_failure_rate is not None
                    else hop.failure_rate
                )
                duration = self._random.lognormal_latency(
                    hop.latency_p50_seconds, route.latency_sigma, multiplier
                )
                failed = self._random.split(1, (1 - failure_rate, failure_rate))[1] == 1
                result = "failure" if failed else "success"
                CROSS_REGION_HOP_REQUESTS.labels(
                    source_region, destination_region, hop.name, service, result
                ).inc()
                CROSS_REGION_HOP_DURATION.labels(
                    source_region, destination_region, hop.name, service, result
                ).observe(duration)
                end_to_end_duration += duration
                if failed:
                    terminal_result = "failure"
                    CROSS_REGION_FAILURES.labels(
                        source_region,
                        destination_region,
                        service,
                        hop.name,
                        "timeout" if affected else "connection_error",
                    ).inc()
                    break
            CROSS_REGION_REQUESTS.labels(
                source_region, destination_region, service, operation, terminal_result
            ).inc()
            CROSS_REGION_DURATION.labels(
                source_region, destination_region, service, operation, terminal_result
            ).observe(end_to_end_duration)

    def _generate_supporting_metrics(
        self,
        auth_count: int,
        tps: float,
        effects: EventEffects,
        manual_otp_queue_warning: bool = False,
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
        AUTHORIZATION_DECISIONS.labels("identity", "deny", "insufficient_scope").inc(denied)

        database_count = self._random.event_count(auth_count * 0.70)
        database_error_rate = (
            effects.database_error_rate if effects.database_error_rate is not None else 0.001
        )
        database_errors = self._random.event_count(database_count * database_error_rate)
        database_success = max(0, database_count - database_errors)
        operations = ("select", "insert", "update")
        operation_counts = self._random.split(database_success, (0.70, 0.15, 0.15))
        for operation, operation_count in zip(operations, operation_counts):
            for _ in range(operation_count):
                DATABASE_QUERY_DURATION.labels("identity-db", operation, "success").observe(
                    self._random.lognormal_latency(0.025, 0.70, effects.database_latency_multiplier)
                )
            DATABASE_QUERIES.labels("identity-db", operation, "success").inc(operation_count)
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
        if manual_otp_queue_warning:
            queue_size = max(queue_size, self._manual_otp_queue_size)
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
            APPLICATION_ERRORS.labels("auth-service", "database_dependency", "critical").inc(
                max(1, database_errors)
            )
        if effects.otp_delivery_penalty:
            APPLICATION_ERRORS.labels("otp-service", "provider_error", "critical").inc(
                max(1, round(auth_count * 0.01))
            )
        if effects.token_success_penalty:
            APPLICATION_ERRORS.labels("token-service", "cache_dependency", "critical").inc(
                max(1, round(auth_count * 0.01))
            )

    def _set_simulation_state(
        self,
        tps: float,
        effects: EventEffects,
        manual_otp_queue_warning: bool,
        manual_cross_region_degradation: bool,
    ) -> None:
        SIMULATION_TPS.labels(self._settings.load_profile.name).set(tps)
        active_names = set(effects.names)
        for definition in self._settings.events:
            SIMULATION_EVENT_ACTIVE.labels(definition.name).set(definition.name in active_names)
        SIMULATION_EVENT_ACTIVE.labels("manual_otp_queue_backlog").set(
            manual_otp_queue_warning
        )
        SIMULATION_EVENT_ACTIVE.labels("manual_cross_region_degradation").set(
            manual_cross_region_degradation
        )
