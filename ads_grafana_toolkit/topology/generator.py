"""Generate Grafana node-graph panel JSON from device inventory and adjacency data.

The node-graph panel (Grafana 8+) renders network topologies with nodes (devices)
and edges (links). Each node carries arc fields for health visualization and a
mainStat for the primary label beneath the node title.

Usage:
    from ads_grafana_toolkit.topology import TopologyGraph, TopologyNode, TopologyEdge

    graph = TopologyGraph()
    graph.add_nodes_from_inventory(devices)          # list[dict] from device_inventory.json
    graph.add_edges_from_adjacency(adjacency_list)   # list[dict] with src/dst/speed_mbps
    panel_json = graph.to_panel_json()
    dashboard_json = graph.to_dashboard_json(title="Core Network Topology")
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from typing import Any

# Vendor → display color mapping (Grafana named colors)
_VENDOR_COLOR: dict[str, str] = {
    "cisco": "blue",
    "juniper": "green",
    "paloalto": "red",
    "fortinet": "orange",
    "arista": "purple",
    "nokia": "yellow",
    "huawei": "dark-blue",
    "mikrotik": "dark-green",
}

# Role → icon arc color
_ROLE_ARC: dict[str, str] = {
    "backbone": "blue",
    "edge": "green",
    "firewall": "red",
    "access": "yellow",
    "datacenter": "purple",
    "peering": "orange",
}


@dataclass
class TopologyNode:
    """A device node in the topology graph."""

    id: str
    title: str
    vendor: str = ""
    role: str = ""
    ip: str = ""
    location: str = ""
    # arc__* fields control the colored arc segments on the node circle.
    # Values 0.0–1.0; segments are painted in order until they sum to 1.
    arc_up: float = 1.0       # fraction healthy / up
    arc_down: float = 0.0     # fraction down / alerting
    main_stat: str = ""       # primary label shown under the node title
    detail_stat: str = ""     # secondary label

    def to_node_dict(self) -> dict[str, Any]:
        """Serialize to Grafana node-graph node field format."""
        color = _VENDOR_COLOR.get(self.vendor.lower(), "text")
        return {
            "id": self.id,
            "title": self.title,
            "mainStat": self.main_stat or self.role or self.vendor,
            "secondaryStat": self.detail_stat or self.ip,
            "arc__up": self.arc_up,
            "arc__down": self.arc_down,
            "detail__vendor": self.vendor,
            "detail__role": self.role,
            "detail__ip": self.ip,
            "detail__location": self.location,
            "color": color,
        }


@dataclass
class TopologyEdge:
    """A link between two devices."""

    id: str
    source: str       # node id
    target: str       # node id
    speed_mbps: int = 0
    utilization_pct: float = 0.0
    label: str = ""

    def to_edge_dict(self) -> dict[str, Any]:
        """Serialize to Grafana node-graph edge field format."""
        speed_label = _fmt_speed(self.speed_mbps) if self.speed_mbps else ""
        return {
            "id": self.id,
            "source": self.source,
            "target": self.target,
            "mainStat": self.label or speed_label,
            "secondaryStat": f"{self.utilization_pct:.1f}%" if self.utilization_pct else "",
        }


def _fmt_speed(mbps: int) -> str:
    if mbps >= 1_000_000:
        return f"{mbps // 1_000_000}Tbps"
    if mbps >= 1_000:
        return f"{mbps // 1_000}Gbps"
    return f"{mbps}Mbps"


@dataclass
class TopologyGraph:
    """Build and serialize a Grafana node-graph topology panel."""

    nodes: list[TopologyNode] = field(default_factory=list)
    edges: list[TopologyEdge] = field(default_factory=list)
    _node_ids: set[str] = field(default_factory=set, repr=False)

    # ── Construction helpers ─────────────────────────────────────────────

    def add_node(self, node: TopologyNode) -> TopologyNode:
        if node.id not in self._node_ids:
            self.nodes.append(node)
            self._node_ids.add(node.id)
        return node

    def add_edge(self, edge: TopologyEdge) -> TopologyEdge:
        self.edges.append(edge)
        return edge

    def add_nodes_from_inventory(self, devices: list[dict[str, Any]]) -> None:
        """Populate nodes from the device_inventory.json list format.

        Expected dict keys: hostname, ip_address, vendor, location, labels.role
        """
        for d in devices:
            hostname = d.get("hostname") or d.get("name") or d.get("ip_address", "unknown")
            node_id = hostname.replace(".", "-").replace("_", "-")
            labels = d.get("labels", {})
            role = labels.get("role", d.get("role", ""))
            node = TopologyNode(
                id=node_id,
                title=hostname,
                vendor=d.get("vendor", ""),
                role=role,
                ip=d.get("ip_address", ""),
                location=d.get("location", ""),
                main_stat=role or d.get("vendor", ""),
            )
            self.add_node(node)

    def add_edges_from_adjacency(self, adjacency: list[dict[str, Any]]) -> None:
        """Populate edges from an adjacency list.

        Expected dict keys: src (hostname), dst (hostname), speed_mbps,
        utilization_pct (optional), label (optional).
        """
        for i, link in enumerate(adjacency):
            src = (link.get("src") or link.get("source") or "").replace(".", "-").replace("_", "-")
            dst = (link.get("dst") or link.get("target") or link.get("destination") or "").replace(".", "-").replace("_", "-")
            if not src or not dst:
                continue
            edge = TopologyEdge(
                id=link.get("id") or f"edge-{i}",
                source=src,
                target=dst,
                speed_mbps=int(link.get("speed_mbps", 0)),
                utilization_pct=float(link.get("utilization_pct", 0.0)),
                label=link.get("label", ""),
            )
            self.add_edge(edge)

    # ── Serialization ────────────────────────────────────────────────────

    def _node_fields(self) -> list[dict[str, Any]]:
        return [
            {"name": "id", "type": "string"},
            {"name": "title", "type": "string"},
            {"name": "mainStat", "type": "string"},
            {"name": "secondaryStat", "type": "string"},
            {"name": "arc__up", "type": "number", "config": {"color": {"fixedColor": "green", "mode": "fixed"}, "displayName": "Up"}},
            {"name": "arc__down", "type": "number", "config": {"color": {"fixedColor": "red", "mode": "fixed"}, "displayName": "Down"}},
            {"name": "detail__vendor", "type": "string", "config": {"displayName": "Vendor"}},
            {"name": "detail__role", "type": "string", "config": {"displayName": "Role"}},
            {"name": "detail__ip", "type": "string", "config": {"displayName": "IP"}},
            {"name": "detail__location", "type": "string", "config": {"displayName": "Location"}},
            {"name": "color", "type": "string"},
        ]

    def _edge_fields(self) -> list[dict[str, Any]]:
        return [
            {"name": "id", "type": "string"},
            {"name": "source", "type": "string"},
            {"name": "target", "type": "string"},
            {"name": "mainStat", "type": "string"},
            {"name": "secondaryStat", "type": "string"},
        ]

    def to_node_frame(self) -> dict[str, Any]:
        """Return a Grafana data frame for nodes."""
        node_dicts = [n.to_node_dict() for n in self.nodes]
        fields = self._node_fields()
        for f in fields:
            fname = f["name"]
            f["values"] = [nd.get(fname, "") for nd in node_dicts]
        return {
            "name": "nodes",
            "meta": {"preferredVisualisationType": "nodeGraph"},
            "fields": fields,
        }

    def to_edge_frame(self) -> dict[str, Any]:
        """Return a Grafana data frame for edges."""
        edge_dicts = [e.to_edge_dict() for e in self.edges]
        fields = self._edge_fields()
        for f in fields:
            fname = f["name"]
            f["values"] = [ed.get(fname, "") for ed in edge_dicts]
        return {
            "name": "edges",
            "meta": {"preferredVisualisationType": "nodeGraph"},
            "fields": fields,
        }

    def to_panel_json(
        self,
        title: str = "Network Topology",
        panel_id: int = 1,
        width: int = 24,
        height: int = 16,
        x: int = 0,
        y: int = 0,
    ) -> dict[str, Any]:
        """Return a Grafana node-graph panel JSON dict."""
        return {
            "id": panel_id,
            "type": "nodeGraph",
            "title": title,
            "gridPos": {"h": height, "w": width, "x": x, "y": y},
            "options": {
                "nodes": {"mainStatUnit": "", "secondaryStatUnit": ""},
                "edges": {"mainStatUnit": "", "secondaryStatUnit": ""},
            },
            "fieldConfig": {"defaults": {}, "overrides": []},
            "targets": [
                {
                    "refId": "A",
                    "rawFrames": [self.to_node_frame(), self.to_edge_frame()],
                }
            ],
            "datasource": {"type": "-- Mixed --", "uid": "-- Mixed --"},
        }

    def to_dashboard_json(
        self,
        title: str = "Network Topology",
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        """Return a minimal Grafana dashboard JSON containing the topology panel."""
        return {
            "id": None,
            "uid": str(uuid.uuid4())[:8],
            "title": title,
            "tags": tags or ["topology", "network"],
            "timezone": "browser",
            "editable": True,
            "schemaVersion": 39,
            "version": 1,
            "time": {"from": "now-6h", "to": "now"},
            "timepicker": {},
            "templating": {"list": []},
            "annotations": {"list": []},
            "panels": [self.to_panel_json(title=title)],
        }

    def to_json(self, mode: str = "panel", title: str = "Network Topology", indent: int = 2) -> str:
        """Serialize to JSON string.

        Args:
            mode: "panel" (just the panel object) or "dashboard" (full dashboard).
            title: Dashboard/panel title.
        """
        if mode == "dashboard":
            return json.dumps(self.to_dashboard_json(title=title), indent=indent)
        return json.dumps(self.to_panel_json(title=title), indent=indent)
