#!/usr/bin/env python3
"""dashboard_diff.py — Diff and lint Grafana dashboard JSON files.

Usage:
  python dashboard_diff.py diff dashboard_v1.json dashboard_v2.json
  python dashboard_diff.py diff --live <uid> dashboard_local.json
  python dashboard_diff.py lint dashboard.json
  python dashboard_diff.py lint --live <uid>
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from _grafana_client import client_from_env


# ── Diff ────────────────────────────────────────────────────────────────────

def _flatten(obj: object, prefix: str = "") -> dict:
    out = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.update(_flatten(v, f"{prefix}.{k}" if prefix else k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            out.update(_flatten(v, f"{prefix}[{i}]"))
    else:
        out[prefix] = obj
    return out


def diff_dashboards(a: dict, b: dict, label_a: str = "A", label_b: str = "B") -> int:
    fa, fb = _flatten(a), _flatten(b)
    all_keys = sorted(set(fa) | set(fb))
    changes = 0
    for key in all_keys:
        va, vb = fa.get(key, "___MISSING___"), fb.get(key, "___MISSING___")
        if va != vb:
            changes += 1
            if va == "___MISSING___":
                print(f"  + {key}: {vb!r}")
            elif vb == "___MISSING___":
                print(f"  - {key}: {va!r}")
            else:
                print(f"  ~ {key}")
                print(f"      {label_a}: {str(va)[:120]}")
                print(f"      {label_b}: {str(vb)[:120]}")
    return changes


# ── Lint ─────────────────────────────────────────────────────────────────────

def lint_dashboard(dash: dict) -> list[str]:
    issues = []
    panels = dash.get("panels", [])
    variables = {v["name"] for v in dash.get("templating", {}).get("list", [])}

    # Duplicate panel IDs
    panel_ids = [p.get("id") for p in panels if "id" in p]
    seen = set()
    for pid in panel_ids:
        if pid in seen:
            issues.append(f"DUPLICATE panel ID: {pid}")
        seen.add(pid)

    for panel in panels:
        title = panel.get("title", f"panel#{panel.get('id','?')}")

        # Missing refId
        for i, target in enumerate(panel.get("targets", [])):
            if not target.get("refId"):
                issues.append(f"MISSING refId on target {i} in panel '{title}'")

        # Gauge/stat without thresholds
        if panel.get("type") in ("gauge", "stat"):
            thresholds = panel.get("fieldConfig", {}).get("defaults", {}).get("thresholds", {}).get("steps", [])
            if not thresholds:
                issues.append(f"NO thresholds set on {panel['type']} panel '{title}'")

        # Variables referenced in queries but not defined
        for target in panel.get("targets", []):
            expr = target.get("expr", "") or target.get("query", "")
            import re
            for var in re.findall(r'\$(\w+)', expr):
                if var not in variables and var not in ("__interval", "__rate_interval", "__range"):
                    issues.append(f"UNDEFINED variable '${var}' used in panel '{title}'")

    # Dashboard-level
    if not dash.get("title"):
        issues.append("MISSING dashboard title")
    if not dash.get("uid"):
        issues.append("MISSING dashboard uid")
    if dash.get("schemaVersion", 0) < 36:
        issues.append(f"OLD schemaVersion {dash.get('schemaVersion')} (36+ recommended)")

    return issues


# ── CLI ───────────────────────────────────────────────────────────────────────

def load_dash(path: str | None, uid: str | None) -> dict:
    if uid:
        c = client_from_env()
        detail = c.get_dashboard(uid)
        return detail.get("dashboard", detail)
    return json.loads(Path(path).read_text())


def main() -> None:
    p = argparse.ArgumentParser(description="Grafana dashboard diff and linter")
    sub = p.add_subparsers(dest="cmd", required=True)

    dp = sub.add_parser("diff")
    dp.add_argument("a", nargs="?"); dp.add_argument("b", nargs="?")
    dp.add_argument("--live", help="Fetch dashboard by UID from live Grafana for comparison with 'b'")

    lp = sub.add_parser("lint")
    lp.add_argument("file", nargs="?"); lp.add_argument("--live", help="Dashboard UID from live Grafana")

    args = p.parse_args()

    if args.cmd == "diff":
        if args.live:
            dash_a = load_dash(None, args.live)
            dash_b = load_dash(args.a or args.b, None)
            label_a, label_b = f"live:{args.live}", args.a or args.b
        else:
            dash_a = load_dash(args.a, None)
            dash_b = load_dash(args.b, None)
            label_a, label_b = args.a, args.b

        print(f"Diff: {label_a}  vs  {label_b}\n")
        n = diff_dashboards(dash_a, dash_b, label_a, label_b)
        print(f"\n{n} differences found.")
        sys.exit(0 if n == 0 else 1)

    elif args.cmd == "lint":
        dash = load_dash(args.file, args.live)
        title = dash.get("title", "Untitled")
        print(f"Linting: {title}\n")
        issues = lint_dashboard(dash)
        if not issues:
            print("  No issues found.")
        else:
            for issue in issues:
                print(f"  WARN  {issue}")
        print(f"\n{len(issues)} issue(s).")
        sys.exit(0 if not issues else 1)

if __name__ == "__main__": main()
