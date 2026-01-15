"""Row class for organizing panels in Grafana dashboards."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from ads_grafana_toolkit.sdk.panel import Panel


@dataclass
class Row:
    """A collapsible row for organizing panels."""

    title: str
    id: int = 0
    collapsed: bool = False
    panels: list[Panel] = field(default_factory=list)
    gridPos: dict[str, int] = field(default_factory=lambda: {"h": 1, "w": 24, "x": 0, "y": 0})

    def add_panel(self, panel: Panel) -> Row:
        """Add a panel to this row."""
        self.panels.append(panel)
        return self

    def to_dict(self) -> dict[str, Any]:
        """Convert row to Grafana JSON format."""
        result: dict[str, Any] = {
            "id": self.id,
            "type": "row",
            "title": self.title,
            "collapsed": self.collapsed,
            "gridPos": self.gridPos.copy(),
            "panels": [],
        }

        if self.collapsed:
            result["panels"] = [p.to_dict() for p in self.panels]

        return result
