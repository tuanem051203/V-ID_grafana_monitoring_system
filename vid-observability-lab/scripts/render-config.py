from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any, cast
from urllib.parse import urlparse


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "deployments" / "config.json"
TEMPLATE_ROOT = PROJECT_ROOT / "deployments" / "templates"


def mapping(value: object, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be an object")
    return cast(dict[str, Any], value)


def scalar(value: object, name: str) -> str:
    if not isinstance(value, str | int | float | bool):
        raise ValueError(f"{name} must be a scalar")
    if isinstance(value, bool):
        return str(value).lower()
    return str(value)


def flatten(value: dict[str, Any], prefix: str = "") -> dict[str, str]:
    result: dict[str, str] = {}
    for key, item in value.items():
        name = f"{prefix}_{key}" if prefix else key
        if isinstance(item, dict):
            result.update(flatten(cast(dict[str, Any], item), name))
        elif isinstance(item, list):
            result[name] = ", ".join(str(entry) for entry in item)
        else:
            result[name] = scalar(item, name)
    return result


def render(template_name: str, destination: Path, values: dict[str, str]) -> None:
    content = (TEMPLATE_ROOT / template_name).read_text(encoding="utf-8")
    for key, value in values.items():
        content = content.replace(f"@@{key.upper()}@@", value)
    if "@@" in content:
        unresolved = sorted({part.split("@@", 1)[0] for part in content.split("@@")[1::2]})
        raise ValueError(f"Unresolved placeholders in {template_name}: {unresolved}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(content, encoding="utf-8")


def load_environment(environment: str) -> dict[str, str]:
    raw = mapping(json.loads(CONFIG_PATH.read_text(encoding="utf-8")), "deployment config")
    if raw.get("version") != 1:
        raise ValueError("Unsupported deployment config version")
    defaults = mapping(raw.get("defaults"), "defaults")
    environments = mapping(raw.get("environments"), "environments")
    if environment not in environments:
        raise ValueError(f"Unknown environment {environment!r}")
    selected = mapping(environments[environment], f"environments.{environment}")
    values = flatten(defaults)
    values.update(flatten(selected))
    values["environment"] = environment
    for key in (
        "public_urls_metrics_simulator",
        "public_urls_prometheus",
        "public_urls_alertmanager",
        "public_urls_grafana",
        "public_urls_runbooks",
        "grafana_datasource_url",
    ):
        parsed = urlparse(values[key])
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError(f"{key} must be an absolute HTTP(S) URL")
    return values


def main() -> None:
    parser = argparse.ArgumentParser(description="Render environment-specific observability config")
    parser.add_argument("--environment", default="local")
    parser.add_argument("--output")
    args = parser.parse_args()

    output = Path(args.output) if args.output else PROJECT_ROOT / "generated" / args.environment
    values = load_environment(args.environment)
    output.mkdir(parents=True, exist_ok=True)
    (output / "resolved.json").write_text(
        json.dumps(values, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    render("docker-compose.yml.tpl", output / "docker-compose.yml", values)
    render("prometheus.yml.tpl", output / "prometheus" / "prometheus.yml", values)
    render(
        "../../observability/prometheus/rules/vid-alert-rules.yml",
        output / "prometheus" / "rules" / "vid-alert-rules.yml",
        values,
    )
    shutil.copy2(
        PROJECT_ROOT / "observability" / "prometheus" / "rules" / "vid-kpi-rules.yml",
        output / "prometheus" / "rules" / "vid-kpi-rules.yml",
    )
    render(
        "../../observability/prometheus/rules/vid-cross-region-rules.yml",
        output / "prometheus" / "rules" / "vid-cross-region-rules.yml",
        values,
    )
    render(
        "../../observability/prometheus/rules/vid-otp-journey-rules.yml",
        output / "prometheus" / "rules" / "vid-otp-journey-rules.yml",
        values,
    )
    render("alertmanager.yml.tpl", output / "alertmanager" / "alertmanager.yml", values)
    shutil.copytree(
        PROJECT_ROOT / "observability" / "alertmanager" / "templates",
        output / "alertmanager" / "templates",
        dirs_exist_ok=True,
    )
    render("grafana-prometheus.yml.tpl", output / "grafana" / "prometheus.yml", values)
    render("tempo.yml.tpl", output / "tempo" / "tempo.yml", values)
    render("loki.yml.tpl", output / "loki" / "loki.yml", values)
    render(
        "otel-collector.yml.tpl",
        output / "otel-collector" / "config.yml",
        values,
    )
    print(output)


if __name__ == "__main__":
    main()
