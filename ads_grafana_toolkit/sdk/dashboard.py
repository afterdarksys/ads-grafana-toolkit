"""Dashboard class for creating Grafana dashboards."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal

from ads_grafana_toolkit.sdk.datasource import Datasource
from ads_grafana_toolkit.sdk.panel import (
    Panel,
    TimeSeriesPanel,
    StatPanel,
    GaugePanel,
    TablePanel,
    TextPanel,
    LogsPanel,
)
from ads_grafana_toolkit.sdk.row import Row


@dataclass
class Variable:
    """A dashboard variable/template."""

    name: str
    label: str = ""
    type: Literal["query", "custom", "constant", "datasource", "interval", "textbox"] = "query"
    query: str = ""
    datasource: Datasource | None = None
    refresh: Literal[0, 1, 2] = 1  # 0=never, 1=on dashboard load, 2=on time range change
    multi: bool = False
    include_all: bool = False
    all_value: str = ""
    options: list[dict[str, Any]] = field(default_factory=list)
    current: dict[str, Any] = field(default_factory=dict)
    hide: Literal[0, 1, 2] = 0  # 0=show, 1=hide label, 2=hide variable

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "name": self.name,
            "label": self.label or self.name,
            "type": self.type,
            "refresh": self.refresh,
            "multi": self.multi,
            "includeAll": self.include_all,
            "hide": self.hide,
        }

        if self.type == "query":
            result["query"] = self.query
            if self.datasource:
                result["datasource"] = self.datasource.to_dict()

        if self.type == "custom":
            result["query"] = self.query
            result["options"] = self.options

        if self.type == "constant":
            result["query"] = self.query

        if self.type == "interval":
            result["query"] = self.query
            result["auto"] = True
            result["auto_min"] = "10s"

        if self.include_all and self.all_value:
            result["allValue"] = self.all_value

        if self.current:
            result["current"] = self.current

        return result


@dataclass
class Annotation:
    """A dashboard annotation query."""

    name: str
    datasource: Datasource
    expr: str = ""
    enable: bool = True
    hide: bool = False
    icon_color: str = "rgba(0, 211, 255, 1)"

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "datasource": self.datasource.to_dict(),
            "enable": self.enable,
            "hide": self.hide,
            "iconColor": self.icon_color,
            "expr": self.expr,
        }


@dataclass
class Dashboard:
    """A Grafana dashboard."""

    title: str
    uid: str | None = None
    description: str = ""
    tags: list[str] = field(default_factory=list)
    timezone: str = "browser"
    editable: bool = True
    refresh: str = ""
    time_from: str = "now-6h"
    time_to: str = "now"
    panels: list[Panel | Row] = field(default_factory=list)
    variables: list[Variable] = field(default_factory=list)
    annotations: list[Annotation] = field(default_factory=list)
    datasource: Datasource | None = None
    version: int = 1
    _next_panel_id: int = field(default=1, repr=False)
    _current_y: int = field(default=0, repr=False)

    def __post_init__(self):
        if self.uid is None:
            self.uid = str(uuid.uuid4())[:8]

    def add_panel(
        self,
        title: str,
        query: str | None = None,
        panel_type: Literal["timeseries", "stat", "gauge", "table", "text", "logs"] = "timeseries",
        width: int = 12,
        height: int = 8,
        datasource: Datasource | None = None,
        **kwargs,
    ) -> Panel:
        """Add a panel to the dashboard with smart defaults."""
        panel_classes = {
            "timeseries": TimeSeriesPanel,
            "stat": StatPanel,
            "gauge": GaugePanel,
            "table": TablePanel,
            "text": TextPanel,
            "logs": LogsPanel,
        }

        PanelClass = panel_classes.get(panel_type, TimeSeriesPanel)
        ds = datasource or self.datasource

        panel = PanelClass(
            title=title,
            id=self._next_panel_id,
            datasource=ds,
            **kwargs,
        )
        panel.set_size(width, height)

        if query and panel_type != "text":
            panel.add_query(query)

        self._auto_position(panel)
        self.panels.append(panel)
        self._next_panel_id += 1

        return panel

    def add_row(self, title: str, collapsed: bool = False) -> Row:
        """Add a collapsible row to the dashboard."""
        row = Row(
            title=title,
            id=self._next_panel_id,
            collapsed=collapsed,
        )
        row.gridPos["y"] = self._current_y
        self._current_y += 1
        self.panels.append(row)
        self._next_panel_id += 1
        return row

    def add_variable(
        self,
        name: str,
        query: str = "",
        label: str = "",
        var_type: Literal["query", "custom", "constant", "datasource", "interval", "textbox"] = "query",
        datasource: Datasource | None = None,
        multi: bool = False,
        include_all: bool = False,
    ) -> Variable:
        """Add a template variable to the dashboard."""
        ds = datasource or self.datasource
        var = Variable(
            name=name,
            label=label or name,
            type=var_type,
            query=query,
            datasource=ds,
            multi=multi,
            include_all=include_all,
        )
        self.variables.append(var)
        return var

    def add_annotation(
        self,
        name: str,
        expr: str,
        datasource: Datasource | None = None,
        color: str = "rgba(0, 211, 255, 1)",
    ) -> Annotation:
        """Add an annotation query to the dashboard."""
        ds = datasource or self.datasource
        if ds is None:
            raise ValueError("Datasource required for annotation")
        ann = Annotation(
            name=name,
            datasource=ds,
            expr=expr,
            icon_color=color,
        )
        self.annotations.append(ann)
        return ann

    def _auto_position(self, panel: Panel) -> None:
        """Automatically position a panel in the grid."""
        width = panel.gridPos["w"]
        height = panel.gridPos["h"]

        x_positions = [0, 12]
        for x in x_positions:
            if x + width <= 24:
                can_place = True
                for existing in self.panels:
                    if isinstance(existing, Row):
                        continue
                    ex = existing.gridPos
                    if (
                        self._current_y < ex["y"] + ex["h"]
                        and self._current_y + height > ex["y"]
                        and x < ex["x"] + ex["w"]
                        and x + width > ex["x"]
                    ):
                        can_place = False
                        break

                if can_place:
                    panel.gridPos["x"] = x
                    panel.gridPos["y"] = self._current_y
                    if x + width >= 24:
                        self._current_y += height
                    return

        panel.gridPos["x"] = 0
        panel.gridPos["y"] = self._current_y
        self._current_y += height

    def to_dict(self) -> dict[str, Any]:
        """Convert dashboard to Grafana JSON format."""
        panels_json = []
        for panel in self.panels:
            panels_json.append(panel.to_dict())

        result: dict[str, Any] = {
            "id": None,
            "uid": self.uid,
            "title": self.title,
            "tags": self.tags,
            "timezone": self.timezone,
            "editable": self.editable,
            "graphTooltip": 0,
            "panels": panels_json,
            "schemaVersion": 39,
            "version": self.version,
            "time": {
                "from": self.time_from,
                "to": self.time_to,
            },
            "timepicker": {},
            "templating": {
                "list": [v.to_dict() for v in self.variables],
            },
            "annotations": {
                "list": [
                    {
                        "builtIn": 1,
                        "datasource": {"type": "grafana", "uid": "-- Grafana --"},
                        "enable": True,
                        "hide": True,
                        "iconColor": "rgba(0, 211, 255, 1)",
                        "name": "Annotations & Alerts",
                        "type": "dashboard",
                    }
                ]
                + [a.to_dict() for a in self.annotations],
            },
        }

        if self.description:
            result["description"] = self.description
        if self.refresh:
            result["refresh"] = self.refresh

        return result

    def to_json(self, indent: int = 2) -> str:
        """Convert dashboard to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    def save(self, filepath: str) -> None:
        """Save dashboard to a JSON file."""
        with open(filepath, "w") as f:
            f.write(self.to_json())

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Dashboard:
        """Create a Dashboard from a Grafana JSON dictionary."""
        dashboard = cls(
            title=data.get("title", "Untitled"),
            uid=data.get("uid"),
            description=data.get("description", ""),
            tags=data.get("tags", []),
            timezone=data.get("timezone", "browser"),
            editable=data.get("editable", True),
            refresh=data.get("refresh", ""),
            time_from=data.get("time", {}).get("from", "now-6h"),
            time_to=data.get("time", {}).get("to", "now"),
        )
        return dashboard

    @classmethod
    def from_json(cls, json_str: str) -> Dashboard:
        """Create a Dashboard from a JSON string."""
        return cls.from_dict(json.loads(json_str))

    @classmethod
    def from_file(cls, filepath: str) -> Dashboard:
        """Load a Dashboard from a JSON file."""
        with open(filepath, "r") as f:
            return cls.from_json(f.read())
