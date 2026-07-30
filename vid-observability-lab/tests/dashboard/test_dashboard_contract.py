from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DASHBOARDS = ROOT / "observability" / "grafana" / "dashboards"
EXTERNAL_LABELS = {"environment", "cluster", "job", "alertstate", "__name__"}
RAW_METRIC_LABELS = {
    "auth_requests_total": {"client_type"},
    "auth_success_total": {"client_type"},
    "auth_failed_total": {"client_type", "reason"},
    "auth_request_duration_seconds_bucket": {"result", "client_type", "le"},
    "otp_send_total": {"provider", "channel"},
    "otp_delivery_success_total": {"provider", "channel"},
    "otp_delivery_failed_total": {"provider", "channel", "reason"},
    "otp_verify_total": {"channel"},
    "otp_verify_success_total": {"channel"},
    "otp_verify_failed_total": {"channel", "reason"},
    "token_request_total": {"token_type", "grant_type"},
    "token_issue_total": {"token_type", "grant_type"},
    "token_failed_total": {"token_type", "grant_type", "reason"},
    "token_request_duration_seconds_bucket": {
        "token_type",
        "grant_type",
        "result",
        "le",
    },
    "http_requests_total": {"service", "endpoint", "method", "critical"},
    "http_requests_5xx_total": {
        "service",
        "endpoint",
        "method",
        "critical",
        "status_code",
    },
    "http_request_duration_seconds_bucket": {
        "service",
        "endpoint",
        "method",
        "le",
    },
    "authorization_decisions_total": {"resource", "decision", "reason"},
    "application_errors_total": {"service", "error_type", "severity"},
    "database_query_duration_seconds_bucket": {
        "database",
        "operation",
        "result",
        "le",
    },
    "database_connections": {"database", "state"},
    "database_max_connections": {"database"},
    "database_queries_total": {"database", "operation", "result"},
    "infrastructure_cpu_usage_ratio": {"node"},
    "infrastructure_memory_usage_ratio": {"node"},
    "pod_ready": {"service", "pod"},
    "otp_queue_size": set(),
    "otp_provider_status": {"provider"},
    "simulation_event_active": {"event"},
}


class DashboardContractTest(unittest.TestCase):
    def dashboards(self) -> list[tuple[Path, dict[str, object]]]:
        return [
            (path, json.loads(path.read_text()))
            for path in sorted(DASHBOARDS.glob("*.json"))
        ]

    def test_every_panel_has_description_and_unique_id(self) -> None:
        for path, dashboard in self.dashboards():
            panels = dashboard["panels"]
            ids = [panel["id"] for panel in panels]
            self.assertEqual(len(ids), len(set(ids)), path.name)
            for panel in panels:
                self.assertTrue(panel.get("description", "").strip(), panel["title"])

    def test_only_current_dashboard_set_is_provisioned(self) -> None:
        expected = {
            "sso-overview",
            "sso-authentication",
            "sso-mfa-otp",
            "sso-token-lifecycle",
            "sso-authorization",
            "sso-platform",
            "sso-reliability",
        }
        actual = {dashboard["uid"] for _, dashboard in self.dashboards()}
        self.assertEqual(actual, expected)

    def test_raw_metric_selectors_use_supported_labels(self) -> None:
        for path, dashboard in self.dashboards():
            expressions = [
                annotation["target"]["expr"]
                for annotation in dashboard.get("annotations", {}).get("list", [])
            ]
            expressions.extend(
                target["expr"]
                for panel in dashboard["panels"]
                for target in panel.get("targets", [])
            )
            for expression in expressions:
                for metric, selector in re.findall(
                    r"([a-zA-Z_:][a-zA-Z0-9_:]*)\{([^{}]*)\}",
                    expression,
                ):
                    if metric not in RAW_METRIC_LABELS:
                        continue
                    labels = set(
                        re.findall(
                            r"([a-zA-Z_][a-zA-Z0-9_]*)\s*(?:=|!=|=~|!~)",
                            selector,
                        )
                    )
                    unsupported = (
                        labels - RAW_METRIC_LABELS[metric] - EXTERNAL_LABELS
                    )
                    self.assertFalse(
                        unsupported,
                        f"{path.name}: {metric}: {sorted(unsupported)}",
                    )

    def test_legacy_raw_metrics_are_not_queried(self) -> None:
        legacy = re.compile(r"vid_(?:auth|otp|token|http|database|infrastructure)")
        for path, dashboard in self.dashboards():
            for panel in dashboard["panels"]:
                for target in panel.get("targets", []):
                    self.assertIsNone(
                        legacy.search(target["expr"]),
                        f"{path.name}: {panel['title']}",
                    )


if __name__ == "__main__":
    unittest.main()
