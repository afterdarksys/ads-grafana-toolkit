#!/usr/bin/env python3
"""
provision_dashboards.py — Bulk dashboard provisioning to Grafana for ISP environments.

Generates and pushes dashboards to Grafana via the API. Supports:
  - Generating from the ads-grafana-toolkit template library
  - Pushing existing JSON dashboard files
  - Creating folders for organization
  - Bulk provisioning from a manifest file

Usage:
  python provision_dashboards.py --help
  python provision_dashboards.py template isp-bgp --datasource Prometheus --folder "ISP / Network"
  python provision_dashboards.py template network-cisco --datasource Prometheus --folder "Network Devices"
  python provision_dashboards.py template cloud-aws --datasource "AWS CloudWatch" --folder "Cloud"
  python provision_dashboards.py file my-dashboard.json --folder "Custom"
  python provision_dashboards.py manifest isp_manifest.yml
  python provision_dashboards.py list-templates
  python provision_dashboards.py list-grafana    # list dashboards already in Grafana
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import urllib.request
import urllib.error
from pathlib import Path
from typing import Any

import yaml

# Allow running from repo root
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

try:
    from ads_grafana_toolkit.template_library import list_templates, create_from_template
    from ads_grafana_toolkit.sdk.datasource import Datasource
    TOOLKIT_AVAILABLE = True
except ImportError:
    TOOLKIT_AVAILABLE = False


GRAFANA_URL = os.environ.get("GRAFANA_URL", "http://localhost:3000")
GRAFANA_USER = os.environ.get("GRAFANA_USER", "admin")
GRAFANA_PASSWORD = os.environ.get("GRAFANA_PASSWORD", "admin")


def grafana_request(method: str, path: str, body: dict | None = None) -> Any:
    url = f"{GRAFANA_URL.rstrip('/')}/api{path}"
    credentials = base64.b64encode(f"{GRAFANA_USER}:{GRAFANA_PASSWORD}".encode()).decode()
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Basic {credentials}",
    }
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body_text = e.read().decode()
        print(f"ERROR {e.code} {method} {url}: {body_text}")
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"ERROR connecting to Grafana at {GRAFANA_URL}: {e.reason}")
        sys.exit(1)


def get_or_create_folder(name: str) -> int | None:
    """Get or create a Grafana folder, return folder ID (None = General)."""
    if not name or name.lower() == "general":
        return None

    folders = grafana_request("GET", "/folders")
    existing = next((f for f in folders if f["title"] == name), None)
    if existing:
        return existing["id"]

    result = grafana_request("POST", "/folders", {"title": name})
    print(f"Created folder: {name}")
    return result["id"]


def push_dashboard(dashboard_json: dict, folder_id: int | None, overwrite: bool = True) -> dict:
    """Push a dashboard JSON to Grafana."""
    # Grafana requires these fields to be unset on import
    dashboard_json.pop("id", None)
    dashboard_json.pop("version", None)

    payload = {
        "dashboard": dashboard_json,
        "overwrite": overwrite,
        "message": "Provisioned by ads-grafana-toolkit",
    }
    if folder_id is not None:
        payload["folderId"] = folder_id

    return grafana_request("POST", "/dashboards/db", payload)


def cmd_template(args: argparse.Namespace) -> None:
    if not TOOLKIT_AVAILABLE:
        print("ERROR: ads_grafana_toolkit package not importable. Run from repo root or install it.")
        sys.exit(1)

    template_name = args.template
    datasource = args.datasource
    folder_id = get_or_create_folder(args.folder) if args.folder else None

    print(f"Generating dashboard from template: {template_name}")
    try:
        dashboard = create_from_template(template_name, datasource)
    except KeyError as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    if args.title:
        dashboard.title = args.title

    dashboard_json = dashboard.to_dict()
    result = push_dashboard(dashboard_json, folder_id, overwrite=args.overwrite)

    status = result.get("status", "unknown")
    uid = result.get("uid", "")
    url = result.get("url", "")
    print(f"  {status}: {dashboard.title}")
    print(f"  URL: {GRAFANA_URL.rstrip('/')}{url}")


def cmd_file(args: argparse.Namespace) -> None:
    path = Path(args.file)
    if not path.exists():
        print(f"ERROR: File not found: {args.file}")
        sys.exit(1)

    dashboard_json = json.loads(path.read_text())
    folder_id = get_or_create_folder(args.folder) if args.folder else None
    result = push_dashboard(dashboard_json, folder_id, overwrite=args.overwrite)

    title = dashboard_json.get("title", path.stem)
    url = result.get("url", "")
    print(f"Pushed: {title}")
    print(f"  URL: {GRAFANA_URL.rstrip('/')}{url}")


def cmd_manifest(args: argparse.Namespace) -> None:
    """
    Provision from a YAML manifest file.

    Manifest format:
      defaults:
        overwrite: true
      folders:
        - name: "ISP / Network"
          dashboards:
            - template: isp-bgp
              datasource: Prometheus
            - template: network-cisco
              datasource: Prometheus-SNMP
        - name: "Cloud"
          dashboards:
            - template: cloud-aws
              datasource: AWS CloudWatch
            - file: /path/to/custom.json
    """
    path = Path(args.manifest)
    if not path.exists():
        print(f"ERROR: Manifest not found: {args.manifest}")
        sys.exit(1)

    manifest = yaml.safe_load(path.read_text())
    defaults = manifest.get("defaults", {})
    overwrite = defaults.get("overwrite", True)
    total = 0
    errors = 0

    for folder_cfg in manifest.get("folders", []):
        folder_name = folder_cfg.get("name", "General")
        folder_id = get_or_create_folder(folder_name)
        print(f"\nFolder: {folder_name}")

        for dash_cfg in folder_cfg.get("dashboards", []):
            try:
                if "template" in dash_cfg:
                    if not TOOLKIT_AVAILABLE:
                        print("  ERROR: toolkit not available for template dashboards")
                        errors += 1
                        continue
                    dashboard = create_from_template(
                        dash_cfg["template"],
                        dash_cfg.get("datasource", "Prometheus"),
                    )
                    if "title" in dash_cfg:
                        dashboard.title = dash_cfg["title"]
                    dashboard_json = dashboard.to_dict()
                elif "file" in dash_cfg:
                    dashboard_json = json.loads(Path(dash_cfg["file"]).read_text())
                else:
                    print("  ERROR: Each dashboard entry needs 'template' or 'file'")
                    errors += 1
                    continue

                result = push_dashboard(dashboard_json, folder_id, overwrite=overwrite)
                url = result.get("url", "")
                title = dashboard_json.get("title", "Untitled")
                print(f"  OK: {title}  {GRAFANA_URL.rstrip('/')}{url}")
                total += 1
            except Exception as exc:
                print(f"  ERROR: {exc}")
                errors += 1

    print(f"\nProvisioned {total} dashboards, {errors} errors.")


def cmd_list_templates(args: argparse.Namespace) -> None:
    if not TOOLKIT_AVAILABLE:
        print("ERROR: ads_grafana_toolkit not available.")
        sys.exit(1)
    templates = list_templates()
    print(f"{'Name':<30} {'Category':<20} {'Description'}")
    print("-" * 90)
    for t in sorted(templates, key=lambda x: (x["category"], x["name"])):
        print(f"{t['name']:<30} {t['category']:<20} {t['description'][:50]}")


def cmd_list_grafana(args: argparse.Namespace) -> None:
    results = grafana_request("GET", "/search?type=dash-db&limit=1000")
    if not results:
        print("No dashboards found in Grafana.")
        return
    print(f"{'Title':<50} {'Folder':<25} {'UID'}")
    print("-" * 90)
    for d in results:
        folder = d.get("folderTitle", "General")
        print(f"{d['title']:<50} {folder:<25} {d.get('uid', '')}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Bulk dashboard provisioner for ISP Grafana environments",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Environment variables:
  GRAFANA_URL       Grafana base URL (default: http://localhost:3000)
  GRAFANA_USER      Grafana username (default: admin)
  GRAFANA_PASSWORD  Grafana password (default: admin)
""",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # template
    tmpl_p = sub.add_parser("template", help="Generate and push a dashboard from a template")
    tmpl_p.add_argument("template", help="Template name (e.g. isp-bgp, cloud-aws)")
    tmpl_p.add_argument("--datasource", "-d", default="Prometheus", help="Datasource name")
    tmpl_p.add_argument("--folder", "-f", help="Grafana folder name")
    tmpl_p.add_argument("--title", help="Override dashboard title")
    tmpl_p.add_argument("--overwrite", action="store_true", default=True,
                        help="Overwrite existing dashboard (default: True)")

    # file
    file_p = sub.add_parser("file", help="Push a dashboard JSON file")
    file_p.add_argument("file", help="Path to dashboard JSON file")
    file_p.add_argument("--folder", "-f", help="Grafana folder name")
    file_p.add_argument("--overwrite", action="store_true", default=True)

    # manifest
    mfst_p = sub.add_parser("manifest", help="Provision from a YAML manifest")
    mfst_p.add_argument("manifest", help="Path to manifest YAML file")

    # list-templates
    sub.add_parser("list-templates", help="List available toolkit templates")

    # list-grafana
    sub.add_parser("list-grafana", help="List dashboards in Grafana")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "template":
        cmd_template(args)
    elif args.command == "file":
        cmd_file(args)
    elif args.command == "manifest":
        cmd_manifest(args)
    elif args.command == "list-templates":
        cmd_list_templates(args)
    elif args.command == "list-grafana":
        cmd_list_grafana(args)


if __name__ == "__main__":
    main()
