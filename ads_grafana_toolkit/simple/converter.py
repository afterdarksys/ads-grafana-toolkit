"""Convert simple YAML/TOML configs to Grafana dashboard JSON."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

try:
    import toml
except ImportError:
    toml = None

from ads_grafana_toolkit.sdk.dashboard import Dashboard
from ads_grafana_toolkit.sdk.datasource import Datasource
from ads_grafana_toolkit.sdk.panel import TimeSeriesPanel, StatPanel, GaugePanel, TablePanel


def load_config(filepath: str | Path) -> dict[str, Any]:
    """Load configuration from YAML or TOML file."""
    filepath = Path(filepath)

    if not filepath.exists():
        raise FileNotFoundError(f"Config file not found: {filepath}")

    content = filepath.read_text()

    if filepath.suffix in (".yaml", ".yml"):
        return yaml.safe_load(content)
    elif filepath.suffix == ".toml":
        if toml is None:
            raise ImportError("toml package required for .toml files: pip install toml")
        return toml.loads(content)
    elif filepath.suffix == ".json":
        return json.loads(content)
    else:
        try:
            return yaml.safe_load(content)
        except Exception:
            if toml:
                return toml.loads(content)
            raise ValueError(f"Unknown config format: {filepath.suffix}")


def _parse_datasource(ds_config: str | dict[str, Any] | None) -> Datasource | None:
    """Parse datasource configuration."""
    if ds_config is None:
        return None
    if isinstance(ds_config, str):
        ds_type = ds_config.lower()
        type_map = {
            "prometheus": "prometheus",
            "mysql": "mysql",
            "postgres": "postgres",
            "postgresql": "postgres",
            "influxdb": "influxdb",
            "elasticsearch": "elasticsearch",
            "loki": "loki",
            "cloudwatch": "cloudwatch",
        }
        return Datasource(name=ds_config, type=type_map.get(ds_type, "prometheus"))
    return Datasource(
        name=ds_config.get("name", "default"),
        type=ds_config.get("type", "prometheus"),
        uid=ds_config.get("uid"),
    )


def _infer_panel_type(panel_config: dict[str, Any]) -> str:
    """Infer the best panel type based on configuration."""
    if "type" in panel_config:
        return panel_config["type"]

    query = panel_config.get("query", "").lower()
    title = panel_config.get("title", "").lower()

    if any(word in title for word in ["total", "count", "current", "status"]):
        return "stat"

    if any(word in title for word in ["percent", "usage", "utilization", "health"]):
        if "gauge" in title:
            return "gauge"

    if "table" in title or panel_config.get("format") == "table":
        return "table"

    return "timeseries"


def _parse_panel(panel_config: dict[str, Any], default_ds: Datasource | None) -> dict[str, Any]:
    """Parse panel configuration into SDK-compatible format."""
    panel_type = _infer_panel_type(panel_config)
    ds = _parse_datasource(panel_config.get("datasource")) or default_ds

    result = {
        "title": panel_config.get("title", "Untitled Panel"),
        "panel_type": panel_type,
        "datasource": ds,
    }

    if "query" in panel_config:
        result["query"] = panel_config["query"]

    if "queries" in panel_config:
        result["queries"] = panel_config["queries"]

    if "width" in panel_config:
        result["width"] = panel_config["width"]
    if "height" in panel_config:
        result["height"] = panel_config["height"]

    if "unit" in panel_config:
        result["unit"] = panel_config["unit"]
    if "description" in panel_config:
        result["description"] = panel_config["description"]

    if "thresholds" in panel_config:
        result["thresholds"] = panel_config["thresholds"]

    return result


def convert_config(config: dict[str, Any]) -> Dashboard:
    """Convert a simple config dictionary to a Dashboard object."""
    default_ds = _parse_datasource(config.get("datasource"))

    dashboard = Dashboard(
        title=config.get("name", config.get("title", "Untitled Dashboard")),
        description=config.get("description", ""),
        tags=config.get("tags", []),
        datasource=default_ds,
        refresh=config.get("refresh", ""),
        time_from=config.get("time_from", config.get("from", "now-6h")),
        time_to=config.get("time_to", config.get("to", "now")),
    )

    for var_config in config.get("variables", []):
        dashboard.add_variable(
            name=var_config.get("name", "var"),
            query=var_config.get("query", ""),
            label=var_config.get("label", ""),
            var_type=var_config.get("type", "query"),
            multi=var_config.get("multi", False),
            include_all=var_config.get("include_all", False),
        )

    for row_config in config.get("rows", []):
        row = dashboard.add_row(
            title=row_config.get("title", "Row"),
            collapsed=row_config.get("collapsed", False),
        )
        for panel_config in row_config.get("panels", []):
            parsed = _parse_panel(panel_config, default_ds)
            panel = dashboard.add_panel(**parsed)
            if "queries" in parsed:
                for i, q in enumerate(parsed["queries"]):
                    if i == 0:
                        continue
                    if isinstance(q, str):
                        panel.add_query(q)
                    else:
                        panel.add_query(
                            q.get("expr", q.get("query", "")),
                            legend=q.get("legend", ""),
                        )

    for panel_config in config.get("panels", []):
        parsed = _parse_panel(panel_config, default_ds)
        panel = dashboard.add_panel(**parsed)

        if "queries" in parsed:
            for i, q in enumerate(parsed["queries"]):
                if i == 0:
                    continue
                if isinstance(q, str):
                    panel.add_query(q)
                else:
                    panel.add_query(
                        q.get("expr", q.get("query", "")),
                        legend=q.get("legend", ""),
                    )

        if "thresholds" in parsed:
            for thresh in parsed["thresholds"]:
                if isinstance(thresh, dict):
                    panel.add_threshold(
                        value=thresh.get("value"),
                        color=thresh.get("color", "green"),
                    )

    return dashboard


def convert_file(input_path: str | Path, output_path: str | Path | None = None) -> str:
    """Convert a config file to Grafana dashboard JSON."""
    config = load_config(input_path)
    dashboard = convert_config(config)

    if output_path:
        dashboard.save(str(output_path))
        return str(output_path)

    return dashboard.to_json()
