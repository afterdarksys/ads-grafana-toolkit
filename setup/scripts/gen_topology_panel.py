#!/usr/bin/env python3
"""gen_topology_panel.py — Generate a Grafana node-graph panel from device inventory.

Reads device_inventory.json (from setup_network_devices.py) and an optional
adjacency list, then writes a Grafana node-graph panel or full dashboard JSON.

Usage:
  python gen_topology_panel.py --out topology_panel.json
  python gen_topology_panel.py --mode dashboard --out topology_dashboard.json
  python gen_topology_panel.py --adjacency links.json --out topology.json

Adjacency list format (links.json):
  [
    {"src": "router-a", "dst": "router-b", "speed_mbps": 100000, "label": "100G"},
    {"src": "router-a", "dst": "fw-core",  "speed_mbps": 10000}
  ]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

INVENTORY_PATH = Path(os.environ.get("DEVICE_INVENTORY", "device_inventory.json"))


def load_inventory() -> list[dict]:
    if INVENTORY_PATH.exists():
        return json.loads(INVENTORY_PATH.read_text())
    return []


def load_adjacency(path: str | None) -> list[dict]:
    if not path:
        return []
    p = Path(path)
    if not p.exists():
        print(f"WARNING: adjacency file not found: {path}", file=sys.stderr)
        return []
    return json.loads(p.read_text())


def main() -> None:
    p = argparse.ArgumentParser(description="Generate Grafana topology panel from device inventory")
    p.add_argument("--inventory", default=str(INVENTORY_PATH), help="Device inventory JSON (default: device_inventory.json)")
    p.add_argument("--adjacency", metavar="FILE", help="Adjacency list JSON file (optional)")
    p.add_argument("--mode", choices=["panel", "dashboard"], default="panel",
                   help="Output a single panel JSON or a full dashboard JSON (default: panel)")
    p.add_argument("--title", default="Network Topology", help="Panel/dashboard title")
    p.add_argument("--out", default="topology_panel.json", help="Output file")
    p.add_argument("--stdout", action="store_true", help="Print to stdout instead of writing a file")
    p.add_argument("--tags", nargs="*", default=["topology", "network"], help="Dashboard tags (dashboard mode only)")
    args = p.parse_args()

    from ads_grafana_toolkit.topology import TopologyGraph

    # Load inventory
    inventory_path = Path(args.inventory)
    if not inventory_path.exists():
        print(f"WARNING: inventory not found at {args.inventory} — generating empty topology.", file=sys.stderr)
        devices = []
    else:
        devices = json.loads(inventory_path.read_text())

    adjacency = load_adjacency(args.adjacency)

    graph = TopologyGraph()
    graph.add_nodes_from_inventory(devices)
    if adjacency:
        graph.add_edges_from_adjacency(adjacency)

    output = graph.to_json(mode=args.mode, title=args.title)

    if args.stdout:
        print(output)
    else:
        Path(args.out).write_text(output)
        print(f"Written: {args.out}")
        print(f"  {len(graph.nodes)} node(s), {len(graph.edges)} edge(s)")
        print()
        if args.mode == "panel":
            print("Import into Grafana: Dashboard → Edit → Add panel → Import JSON")
        else:
            print("Import into Grafana: Dashboards → Import → Upload JSON file")

        if not devices:
            print()
            print("Tip: add devices first with setup_network_devices.py, then re-run.")
        if not adjacency and devices:
            print()
            print("Tip: pass --adjacency links.json to show link speeds between devices.")


if __name__ == "__main__":
    main()
