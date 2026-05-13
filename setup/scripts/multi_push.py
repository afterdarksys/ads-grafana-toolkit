#!/usr/bin/env python3
"""multi_push.py — Push dashboards/manifests to a fleet of Grafana instances.

Fleet file (grafana_fleet.yml):
  instances:
    - name: noc-east
      url: http://grafana-east:3000
      user: admin
      password: secret
    - name: noc-west
      url: http://grafana-west:3000
      api_key: glsa_xxxx

Usage:
  python multi_push.py --fleet grafana_fleet.yml manifest isp_manifest.yml
  python multi_push.py --fleet grafana_fleet.yml template isp-bgp --datasource Prometheus
  python multi_push.py --fleet grafana_fleet.yml file dashboard.json --folder "ISP"
  python multi_push.py --fleet grafana_fleet.yml status
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from _grafana_client import GrafanaClient, client_from_instance, GrafanaError
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
try:
    from ads_grafana_toolkit.template_library import create_from_template, list_templates
    TOOLKIT = True
except ImportError:
    TOOLKIT = False


def load_fleet(path: str) -> list[dict]:
    data = yaml.safe_load(Path(path).read_text())
    instances = data.get("instances", [])
    filter_tags = data.get("default_tags", [])
    return instances


def push_to_instance(client: GrafanaClient, name: str, cmd: str, args: argparse.Namespace) -> bool:
    try:
        if cmd == "template":
            if not TOOLKIT: print(f"  [{name}] SKIP: toolkit not available"); return False
            dash = create_from_template(args.template, args.datasource).to_dict()
            folder_id = client.get_or_create_folder(args.folder) if args.folder else None
            client.push_dashboard(dash, folder_id=folder_id)
            print(f"  [{name}] OK: {dash['title']}")

        elif cmd == "file":
            dash = json.loads(Path(args.file).read_text())
            folder_id = client.get_or_create_folder(args.folder) if args.folder else None
            client.push_dashboard(dash, folder_id=folder_id)
            print(f"  [{name}] OK: {dash.get('title', args.file)}")

        elif cmd == "manifest":
            manifest = yaml.safe_load(Path(args.manifest).read_text())
            ok = err = 0
            for folder_cfg in manifest.get("folders", []):
                folder_id = client.get_or_create_folder(folder_cfg.get("name", "General"))
                for dash_cfg in folder_cfg.get("dashboards", []):
                    try:
                        if "template" in dash_cfg and TOOLKIT:
                            dash = create_from_template(dash_cfg["template"], dash_cfg.get("datasource", "Prometheus")).to_dict()
                        elif "file" in dash_cfg:
                            dash = json.loads(Path(dash_cfg["file"]).read_text())
                        else:
                            err += 1; continue
                        if "title" in dash_cfg: dash["title"] = dash_cfg["title"]
                        client.push_dashboard(dash, folder_id=folder_id)
                        ok += 1
                    except Exception as e:
                        print(f"    [{name}] ERR {dash_cfg}: {e}"); err += 1
            print(f"  [{name}] manifest: {ok} OK, {err} errors")

        return True
    except GrafanaError as e:
        print(f"  [{name}] FAIL: {e}")
        return False


def cmd_status(instances: list[dict]) -> None:
    print(f"{'Instance':<20} {'URL':<35} {'Status':<10} {'Version'}")
    print("-" * 80)
    for inst in instances:
        client = client_from_instance(inst)
        name = inst.get("name", inst.get("url", "?"))
        try:
            v = client.version()
            h = client.health()
            print(f"  {name:<20} {client.url:<35} {'OK':<10} {v}")
        except Exception as e:
            print(f"  {name:<20} {client.url:<35} {'DOWN':<10} {e}")


def main() -> None:
    p = argparse.ArgumentParser(description="Push dashboards to a Grafana fleet")
    p.add_argument("--fleet", default="grafana_fleet.yml")
    p.add_argument("--only", nargs="*", help="Only push to these instance names")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("status")

    tp = sub.add_parser("template")
    tp.add_argument("template"); tp.add_argument("--datasource", "-d", default="Prometheus")
    tp.add_argument("--folder", "-f"); tp.add_argument("--title")

    fp = sub.add_parser("file")
    fp.add_argument("file"); fp.add_argument("--folder", "-f")

    mp = sub.add_parser("manifest")
    mp.add_argument("manifest")

    args = p.parse_args()
    fleet_path = Path(args.fleet)
    if not fleet_path.exists():
        print(f"ERROR: Fleet file not found: {args.fleet}"); sys.exit(1)

    instances = load_fleet(args.fleet)
    if args.only:
        instances = [i for i in instances if i.get("name") in args.only]

    if args.cmd == "status":
        cmd_status(instances); return

    print(f"Pushing to {len(instances)} instance(s)...")
    ok = sum(push_to_instance(client_from_instance(i), i.get("name", i.get("url")), args.cmd, args)
             for i in instances)
    print(f"\n{ok}/{len(instances)} instances succeeded.")

if __name__ == "__main__": main()
