#!/usr/bin/env python3
"""grafana_backup.py — Backup/restore Grafana dashboards, datasources, alert rules, folders.

Usage:
  python grafana_backup.py backup --out ./grafana-backup
  python grafana_backup.py restore --from ./grafana-backup
  python grafana_backup.py backup --out ./grafana-backup --include-datasources --include-alerts
"""
from __future__ import annotations
import argparse, json, os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from _grafana_client import GrafanaClient, client_from_env


def cmd_backup(args: argparse.Namespace) -> None:
    c = client_from_env()
    out = Path(args.out)

    try:
        info = c.health()
        print(f"Connected to Grafana — {c.url}  (db: {info.get('database','?')})")
    except SystemExit:
        raise

    # Folders
    folders = {f["id"]: f["title"] for f in c.list_folders()}
    folders[0] = "General"
    (out / "folders.json").parent.mkdir(parents=True, exist_ok=True)
    (out / "folders.json").write_text(json.dumps(list(folders.values()), indent=2))

    # Dashboards
    total = 0
    for item in c.search_dashboards():
        uid = item["uid"]
        folder_title = item.get("folderTitle", "General")
        folder_dir = out / "dashboards" / _safe(folder_title)
        folder_dir.mkdir(parents=True, exist_ok=True)
        detail = c.get_dashboard(uid)
        dash = detail.get("dashboard", detail)
        fname = _safe(dash.get("title", uid)) + ".json"
        (folder_dir / fname).write_text(json.dumps(dash, indent=2))
        total += 1

    print(f"Backed up {total} dashboards → {out}/dashboards/")

    if args.include_datasources:
        ds_dir = out / "datasources"
        ds_dir.mkdir(parents=True, exist_ok=True)
        for ds in c.list_datasources():
            ds.pop("id", None); ds.pop("orgId", None)
            fname = _safe(ds["name"]) + ".json"
            (ds_dir / fname).write_text(json.dumps(ds, indent=2))
        print(f"Backed up {len(c.list_datasources())} datasources → {out}/datasources/")

    if args.include_alerts:
        rules = c.list_alert_rules()
        (out / "alert_rules.json").write_text(json.dumps(rules, indent=2))
        count = sum(len(g.get("rules", [])) for group in rules.values() for g in (group if isinstance(group, list) else [group]))
        print(f"Backed up alert rules → {out}/alert_rules.json")

    print(f"\nBackup complete: {out}")


def cmd_restore(args: argparse.Namespace) -> None:
    c = client_from_env()
    src = Path(args.from_dir)
    if not src.exists():
        print(f"ERROR: {src} not found"); sys.exit(1)

    # Folders
    existing_folders = {f["title"]: f["id"] for f in c.list_folders()}
    folders_file = src / "folders.json"
    if folders_file.exists():
        for title in json.loads(folders_file.read_text()):
            if title != "General" and title not in existing_folders:
                result = c.post("/folders", {"title": title})
                existing_folders[title] = result["id"]

    # Dashboards
    total = restored = 0
    for json_file in sorted((src / "dashboards").rglob("*.json")):
        total += 1
        folder_title = json_file.parent.name.replace("_", " ")
        folder_id = existing_folders.get(folder_title)
        dash = json.loads(json_file.read_text())
        try:
            c.push_dashboard(dash, folder_id=folder_id, overwrite=args.overwrite)
            restored += 1
        except Exception as e:
            print(f"  SKIP {json_file.name}: {e}")

    print(f"Restored {restored}/{total} dashboards.")

    if args.include_datasources:
        for ds_file in sorted((src / "datasources").glob("*.json")):
            ds = json.loads(ds_file.read_text())
            try:
                c.upsert_datasource(ds)
            except Exception as e:
                print(f"  SKIP datasource {ds_file.name}: {e}")


def _safe(s: str) -> str:
    return "".join(c if c.isalnum() or c in "-_. " else "_" for c in s).strip()


def main() -> None:
    p = argparse.ArgumentParser(description="Grafana backup & restore tool")
    sub = p.add_subparsers(dest="cmd", required=True)

    bp = sub.add_parser("backup")
    bp.add_argument("--out", default="./grafana-backup")
    bp.add_argument("--include-datasources", action="store_true")
    bp.add_argument("--include-alerts", action="store_true")

    rp = sub.add_parser("restore")
    rp.add_argument("--from", dest="from_dir", default="./grafana-backup")
    rp.add_argument("--overwrite", action="store_true", default=True)
    rp.add_argument("--include-datasources", action="store_true")

    args = p.parse_args()
    if args.cmd == "backup": cmd_backup(args)
    elif args.cmd == "restore": cmd_restore(args)

if __name__ == "__main__": main()
