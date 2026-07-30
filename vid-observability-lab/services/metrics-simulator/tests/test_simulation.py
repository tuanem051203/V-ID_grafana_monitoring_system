from __future__ import annotations

import statistics
import unittest

from vid_mock_metrics.config import (
    EventDefinition,
    LoadProfile,
    ServiceBaseline,
    Settings,
    TrafficPoint,
)
from vid_mock_metrics.events import EventScheduler
from vid_mock_metrics.random_utils import RandomModel
from vid_mock_metrics.traffic import TrafficGenerator


class TrafficGeneratorTest(unittest.TestCase):
    def setUp(self) -> None:
        self.traffic = TrafficGenerator(
            peak_tps=500,
            schedule=(
                TrafficPoint(0, 0.01),
                TrafficPoint(480, 0.20),
                TrafficPoint(540, 1.00),
                TrafficPoint(1440, 0.10),
            ),
            noise_ratio=0,
            random_model=RandomModel(42),
        )

    def test_profile_reaches_configured_peak(self) -> None:
        self.assertAlmostEqual(self.traffic.tps_at(540), 500)

    def test_cosine_interpolation_does_not_jump_at_boundary(self) -> None:
        before = self.traffic.tps_at(479.9)
        boundary = self.traffic.tps_at(480)
        after = self.traffic.tps_at(480.1)
        self.assertLess(abs(boundary - before), 0.01)
        self.assertLess(abs(after - boundary), 0.01)


class EventSchedulerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.scheduler = EventScheduler(
            (
                EventDefinition(
                    name="database_slow",
                    start_minute=9 * 60 + 20,
                    duration_seconds=600,
                    auth_success_penalty=0.02,
                    auth_latency_multiplier=2.5,
                ),
            )
        )

    def test_event_activates_and_recovers_without_restart(self) -> None:
        before = self.scheduler.active_at((9 * 60 + 19) * 60)
        active = self.scheduler.active_at((9 * 60 + 20) * 60)
        recovered = self.scheduler.active_at((9 * 60 + 30) * 60)
        self.assertEqual(before.names, ())
        self.assertEqual(active.names, ("database_slow",))
        self.assertEqual(active.auth_latency_multiplier, 2.5)
        self.assertEqual(recovered.names, ())
        self.assertEqual(recovered.auth_latency_multiplier, 1.0)

    def test_traffic_event_can_ramp_in_and_out_smoothly(self) -> None:
        scheduler = EventScheduler(
            (
                EventDefinition(
                    "morning_peak",
                    480,
                    3600,
                    ramp_seconds=300,
                    traffic_multiplier=1.35,
                ),
            )
        )
        start = scheduler.active_at(480 * 60)
        mid_ramp = scheduler.active_at(480 * 60 + 150)
        peak = scheduler.active_at(480 * 60 + 300)
        recovery_ramp = scheduler.active_at(480 * 60 + 3600 - 150)
        self.assertEqual(start.traffic_multiplier, 1.0)
        self.assertAlmostEqual(mid_ramp.traffic_multiplier, 1.175)
        self.assertEqual(peak.traffic_multiplier, 1.35)
        self.assertAlmostEqual(recovery_ramp.traffic_multiplier, 1.175)


class RandomModelTest(unittest.TestCase):
    def test_lognormal_auth_latency_matches_production_shape(self) -> None:
        model = RandomModel(20250730)
        samples = sorted(
            model.lognormal_latency(0.12, 0.64, 1.0) for _ in range(20_000)
        )

        def percentile(value: float) -> float:
            return samples[round((len(samples) - 1) * value)]

        self.assertAlmostEqual(statistics.median(samples), 0.12, delta=0.01)
        self.assertGreaterEqual(percentile(0.95), 0.30)
        self.assertLessEqual(percentile(0.95), 0.45)
        self.assertGreaterEqual(percentile(0.99), 0.50)
        self.assertLessEqual(percentile(0.99), 0.70)


class MetricsGeneratorTest(unittest.TestCase):
    def test_raw_counter_invariants_and_event_recovery(self) -> None:
        try:
            from prometheus_client import generate_latest
        except ModuleNotFoundError:
            self.skipTest("prometheus-client is not installed")

        from vid_mock_metrics.generator import MetricsGenerator
        from vid_mock_metrics.metrics import REGISTRY

        settings = Settings(
            generation_interval_seconds=5,
            simulation_day_seconds=86400,
            random_seed=42,
            noise_ratio=0,
            load_profile=LoadProfile("test", 100),
            traffic_schedule=(
                TrafficPoint(0, 1),
                TrafficPoint(1440, 1),
            ),
            events=(
                EventDefinition(
                    "database_slow",
                    560,
                    600,
                    auth_success_penalty=0.12,
                    auth_latency_multiplier=2.4,
                ),
            ),
            baseline=ServiceBaseline(
                auth_success_min=0.999,
                auth_success_max=0.9999,
                otp_delivery_min=0.98,
                otp_delivery_max=0.99,
                otp_verification_min=0.85,
                otp_verification_max=0.95,
                token_success_rate=0.9995,
                http_5xx_rate=0.0001,
                auth_latency_p50_seconds=0.12,
                auth_latency_sigma=0.64,
                token_latency_p50_seconds=0.08,
            ),
        )
        generator = MetricsGenerator(settings)
        before = generator.generate_at(559 * 60)
        healthy_exposition = generate_latest(REGISTRY).decode()
        self.assertIn(
            'application_errors_total{error_type="database_dependency",'
            'service="auth-service",severity="critical"} 0.0',
            healthy_exposition,
        )
        active = generator.generate_at(560 * 60)
        recovered = generator.generate_at(570 * 60)
        self.assertEqual(before.active_events, ())
        self.assertEqual(active.active_events, ("database_slow",))
        self.assertEqual(recovered.active_events, ())

        exposition = generate_latest(REGISTRY).decode()

        def counter_total(name: str) -> float:
            total = 0.0
            prefix = f"{name}"
            for line in exposition.splitlines():
                if line.startswith(prefix + "{") or line.startswith(prefix + " "):
                    total += float(line.rsplit(" ", maxsplit=1)[1])
            return total

        self.assertEqual(
            counter_total("auth_requests_total"),
            counter_total("auth_success_total") + counter_total("auth_failed_total"),
        )
        self.assertEqual(
            counter_total("otp_send_total"),
            counter_total("otp_delivery_success_total")
            + counter_total("otp_delivery_failed_total"),
        )
        self.assertGreater(counter_total("otp_verify_total"), 0)
        self.assertEqual(
            counter_total("otp_verify_total"),
            counter_total("otp_verify_success_total")
            + counter_total("otp_verify_failed_total"),
        )
        self.assertEqual(
            counter_total("token_request_total"),
            counter_total("token_issue_total") + counter_total("token_failed_total"),
        )
        self.assertLessEqual(
            counter_total("http_requests_5xx_total"),
            counter_total("http_requests_total"),
        )


if __name__ == "__main__":
    unittest.main()
