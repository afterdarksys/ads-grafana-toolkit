#!/usr/bin/env python3
"""manage_annotations.py — Add, list, and delete Grafana annotations.

Usage:
  python manage_annotations.py add "Maintenance window — core router upgrade" --tags maintenance,backbone
  python manage_annotations.py window "Router upgrade" --start "2026-05-14 02:00" --end "2026-05-14 04:00"
  python manage_annotations.py list --tags maintenance --limit 20
  python manage_annotations.py delete 42
  python manage_annotations.py import --file maintenance_schedule.csv
"""
from __future__ import annotations
import argparse, csv, sys
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from _grafana_client import client_from_env


def _ts(dt_str: str) -> int:
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M", "%Y-%m-%d"):
        try:
            return int(datetime.strptime(dt_str, fmt).replace(tzinfo=timezone.utc).timestamp() * 1000)
        except ValueError:
            continue
    raise ValueError(f"Cannot parse datetime: {dt_str!r}")


def main() -> None:
    p = argparse.ArgumentParser(description="Manage Grafana annotations")
    sub = p.add_subparsers(dest="cmd", required=True)

    ap = sub.add_parser("add", help="Add a point annotation")
    ap.add_argument("text"); ap.add_argument("--tags", default="")
    ap.add_argument("--time", help="ISO datetime (default: now)")
    ap.add_argument("--dashboard", dest="dashboard_uid", help="Pin to dashboard UID")

    wp = sub.add_parser("window", help="Add a time-range annotation (maintenance window)")
    wp.add_argument("text"); wp.add_argument("--tags", default="maintenance")
    wp.add_argument("--start", required=True); wp.add_argument("--end", required=True)
    wp.add_argument("--dashboard", dest="dashboard_uid")

    lp = sub.add_parser("list", help="List annotations")
    lp.add_argument("--tags", default=""); lp.add_argument("--limit", type=int, default=50)
    lp.add_argument("--from", dest="from_dt"); lp.add_argument("--to", dest="to_dt")

    dp = sub.add_parser("delete", help="Delete annotation by ID")
    dp.add_argument("id", type=int)

    ip = sub.add_parser("import", help="Bulk import from CSV (columns: text,tags,start,end)")
    ip.add_argument("--file", required=True)

    args = p.parse_args()
    c = client_from_env()

    if args.cmd == "add":
        tags = [t.strip() for t in args.tags.split(",") if t.strip()]
        ts = _ts(args.time) if args.time else None
        r = c.create_annotation(args.text, tags=tags, time_ms=ts, dashboard_uid=args.dashboard_uid)
        print(f"Created annotation ID {r.get('id')}: {args.text}")

    elif args.cmd == "window":
        tags = [t.strip() for t in args.tags.split(",") if t.strip()]
        r = c.create_annotation(args.text, tags=tags,
                                 time_ms=_ts(args.start), time_end_ms=_ts(args.end),
                                 dashboard_uid=args.dashboard_uid)
        print(f"Created window annotation ID {r.get('id')}: {args.text} ({args.start} → {args.end})")

    elif args.cmd == "list":
        tags = [t.strip() for t in args.tags.split(",") if t.strip()] if args.tags else None
        from_ts = _ts(args.from_dt) if args.from_dt else None
        to_ts = _ts(args.to_dt) if args.to_dt else None
        annotations = c.list_annotations(from_ts=from_ts, to_ts=to_ts, limit=args.limit, tags=tags)
        if not annotations:
            print("No annotations found.")
        else:
            print(f"{'ID':<8} {'Time':<22} {'Tags':<30} Text")
            print("-" * 80)
            for a in annotations:
                ts = datetime.fromtimestamp(a.get("time", 0) / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
                tag_str = ",".join(a.get("tags", []))
                print(f"  {a['id']:<8} {ts:<22} {tag_str:<30} {a.get('text','')[:40]}")

    elif args.cmd == "delete":
        c.delete_annotation(args.id)
        print(f"Deleted annotation {args.id}")

    elif args.cmd == "import":
        path = Path(args.file)
        if not path.exists():
            print(f"ERROR: {args.file} not found"); sys.exit(1)
        ok = err = 0
        with open(path) as f:
            for row in csv.DictReader(f):
                try:
                    tags = [t.strip() for t in row.get("tags", "").split(",") if t.strip()]
                    time_ms = _ts(row["start"]) if row.get("start") else None
                    end_ms = _ts(row["end"]) if row.get("end") else None
                    c.create_annotation(row["text"], tags=tags, time_ms=time_ms, time_end_ms=end_ms)
                    ok += 1
                except Exception as e:
                    print(f"  ERR row {row}: {e}"); err += 1
        print(f"Imported {ok} annotations, {err} errors.")

if __name__ == "__main__": main()
