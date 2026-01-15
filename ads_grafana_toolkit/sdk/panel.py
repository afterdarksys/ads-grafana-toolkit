"""Panel classes for Grafana dashboards."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal
from abc import ABC, abstractmethod

from ads_grafana_toolkit.sdk.datasource import Datasource


@dataclass
class Target:
    """A query target for a panel."""

    expr: str
    refId: str = "A"
    legendFormat: str = ""
    datasource: Datasource | None = None

    def to_dict(self, panel_datasource: Datasource | None = None) -> dict[str, Any]:
        ds = self.datasource or panel_datasource
        result = {
            "refId": self.refId,
            "expr": self.expr,
        }
        if self.legendFormat:
            result["legendFormat"] = self.legendFormat
        if ds:
            result["datasource"] = ds.to_dict()
        return result


@dataclass
class Threshold:
    """A threshold for panel visualization."""

    value: float | None
    color: str
    mode: Literal["absolute", "percentage"] = "absolute"

    def to_dict(self) -> dict[str, Any]:
        result = {"color": self.color}
        if self.value is not None:
            result["value"] = self.value
        return result


@dataclass
class Panel(ABC):
    """Base class for all panel types."""

    title: str
    id: int = 0
    datasource: Datasource | None = None
    description: str = ""
    transparent: bool = False
    gridPos: dict[str, int] = field(default_factory=lambda: {"h": 8, "w": 12, "x": 0, "y": 0})
    targets: list[Target] = field(default_factory=list)
    thresholds: list[Threshold] = field(default_factory=list)
    unit: str = ""
    decimals: int | None = None
    min_val: float | None = None
    max_val: float | None = None

    @property
    @abstractmethod
    def panel_type(self) -> str:
        """Return the Grafana panel type string."""
        pass

    def add_query(
        self,
        expr: str,
        legend: str = "",
        refId: str | None = None,
        datasource: Datasource | None = None,
    ) -> Panel:
        """Add a query target to the panel."""
        if refId is None:
            refId = chr(ord("A") + len(self.targets))
        self.targets.append(
            Target(expr=expr, refId=refId, legendFormat=legend, datasource=datasource)
        )
        return self

    def add_threshold(
        self, value: float | None, color: str, mode: Literal["absolute", "percentage"] = "absolute"
    ) -> Panel:
        """Add a threshold to the panel."""
        self.thresholds.append(Threshold(value=value, color=color, mode=mode))
        return self

    def set_size(self, width: int, height: int) -> Panel:
        """Set the panel size in grid units."""
        self.gridPos["w"] = width
        self.gridPos["h"] = height
        return self

    def set_position(self, x: int, y: int) -> Panel:
        """Set the panel position in grid units."""
        self.gridPos["x"] = x
        self.gridPos["y"] = y
        return self

    def _get_field_config(self) -> dict[str, Any]:
        """Get field configuration for the panel."""
        defaults: dict[str, Any] = {
            "color": {"mode": "palette-classic"},
        }

        if self.unit:
            defaults["unit"] = self.unit
        if self.decimals is not None:
            defaults["decimals"] = self.decimals
        if self.min_val is not None:
            defaults["min"] = self.min_val
        if self.max_val is not None:
            defaults["max"] = self.max_val

        if self.thresholds:
            defaults["thresholds"] = {
                "mode": self.thresholds[0].mode if self.thresholds else "absolute",
                "steps": [t.to_dict() for t in self.thresholds],
            }
        else:
            defaults["thresholds"] = {
                "mode": "absolute",
                "steps": [{"color": "green", "value": None}],
            }

        return {"defaults": defaults, "overrides": []}

    @abstractmethod
    def _get_options(self) -> dict[str, Any]:
        """Get panel-specific options."""
        pass

    def to_dict(self) -> dict[str, Any]:
        """Convert panel to Grafana JSON format."""
        result: dict[str, Any] = {
            "id": self.id,
            "type": self.panel_type,
            "title": self.title,
            "gridPos": self.gridPos.copy(),
            "targets": [t.to_dict(self.datasource) for t in self.targets],
            "fieldConfig": self._get_field_config(),
            "options": self._get_options(),
        }

        if self.datasource:
            result["datasource"] = self.datasource.to_dict()
        if self.description:
            result["description"] = self.description
        if self.transparent:
            result["transparent"] = True

        return result


@dataclass
class TimeSeriesPanel(Panel):
    """Time series visualization panel (line/area/bar charts)."""

    draw_style: Literal["line", "bars", "points"] = "line"
    line_width: int = 1
    fill_opacity: int = 0
    gradient_mode: Literal["none", "opacity", "hue", "scheme"] = "none"
    show_points: Literal["auto", "always", "never"] = "auto"
    point_size: int = 5
    stack: Literal["none", "normal", "percent"] = "none"
    legend_mode: Literal["list", "table", "hidden"] = "list"
    legend_placement: Literal["bottom", "right"] = "bottom"
    tooltip_mode: Literal["single", "all", "none"] = "single"

    @property
    def panel_type(self) -> str:
        return "timeseries"

    def _get_options(self) -> dict[str, Any]:
        return {
            "legend": {
                "displayMode": self.legend_mode,
                "placement": self.legend_placement,
                "showLegend": self.legend_mode != "hidden",
            },
            "tooltip": {"mode": self.tooltip_mode, "sort": "none"},
        }

    def _get_field_config(self) -> dict[str, Any]:
        config = super()._get_field_config()
        config["defaults"]["custom"] = {
            "drawStyle": self.draw_style,
            "lineWidth": self.line_width,
            "fillOpacity": self.fill_opacity,
            "gradientMode": self.gradient_mode,
            "showPoints": self.show_points,
            "pointSize": self.point_size,
            "stacking": {"mode": self.stack, "group": "A"},
            "axisPlacement": "auto",
            "barAlignment": 0,
            "lineInterpolation": "linear",
            "spanNulls": False,
        }
        return config


@dataclass
class StatPanel(Panel):
    """Single stat visualization panel."""

    color_mode: Literal["value", "background", "background_solid", "none"] = "value"
    graph_mode: Literal["area", "none"] = "area"
    text_mode: Literal["auto", "value", "value_and_name", "name", "none"] = "auto"
    orientation: Literal["auto", "horizontal", "vertical"] = "auto"
    reduce_calc: str = "lastNotNull"

    @property
    def panel_type(self) -> str:
        return "stat"

    def _get_options(self) -> dict[str, Any]:
        return {
            "colorMode": self.color_mode,
            "graphMode": self.graph_mode,
            "textMode": self.text_mode,
            "orientation": self.orientation,
            "reduceOptions": {
                "values": False,
                "calcs": [self.reduce_calc],
                "fields": "",
            },
        }


@dataclass
class GaugePanel(Panel):
    """Gauge visualization panel."""

    show_threshold_labels: bool = False
    show_threshold_markers: bool = True
    orientation: Literal["auto", "horizontal", "vertical"] = "auto"
    reduce_calc: str = "lastNotNull"

    @property
    def panel_type(self) -> str:
        return "gauge"

    def _get_options(self) -> dict[str, Any]:
        return {
            "showThresholdLabels": self.show_threshold_labels,
            "showThresholdMarkers": self.show_threshold_markers,
            "orientation": self.orientation,
            "reduceOptions": {
                "values": False,
                "calcs": [self.reduce_calc],
                "fields": "",
            },
        }


@dataclass
class TablePanel(Panel):
    """Table visualization panel."""

    show_header: bool = True
    footer_show: bool = False
    footer_reducer: list[str] = field(default_factory=lambda: ["sum"])

    @property
    def panel_type(self) -> str:
        return "table"

    def _get_options(self) -> dict[str, Any]:
        return {
            "showHeader": self.show_header,
            "footer": {
                "show": self.footer_show,
                "reducer": self.footer_reducer,
                "fields": "",
            },
        }


@dataclass
class TextPanel(Panel):
    """Text/markdown panel."""

    content: str = ""
    mode: Literal["markdown", "html"] = "markdown"

    @property
    def panel_type(self) -> str:
        return "text"

    def _get_options(self) -> dict[str, Any]:
        return {
            "content": self.content,
            "mode": self.mode,
        }

    def to_dict(self) -> dict[str, Any]:
        result = super().to_dict()
        result.pop("targets", None)
        return result


@dataclass
class LogsPanel(Panel):
    """Logs visualization panel."""

    show_time: bool = True
    show_labels: bool = False
    wrap_lines: bool = False
    prettify_json: bool = False
    enable_log_details: bool = True
    sort_order: Literal["Descending", "Ascending"] = "Descending"

    @property
    def panel_type(self) -> str:
        return "logs"

    def _get_options(self) -> dict[str, Any]:
        return {
            "showTime": self.show_time,
            "showLabels": self.show_labels,
            "wrapLogMessage": self.wrap_lines,
            "prettifyLogMessage": self.prettify_json,
            "enableLogDetails": self.enable_log_details,
            "sortOrder": self.sort_order,
        }
