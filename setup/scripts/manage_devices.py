#!/usr/bin/env python3
"""
manage_devices.py — Device inventory manager for ISP monitoring environments.

Provides bulk operations, health checks, and SNMP connectivity tests
across network device inventory managed by setup_network_devices.py.

Usage:
  python manage_devices.py --help
  python manage_devices.py ping                     # ICMP reachability check for all devices
  python manage_devices.py snmp-test               # SNMP walk sysDescr for all devices
  python manage_devices.py export --format csv     # export inventory to CSV
  python manage_devices.py import --file devices.csv
  python manage_devices.py report                  # generate health summary
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import os
import socket
import subprocess
import sys
from pathlib import Path
from typing import Any


INVENTORY_PATH = Path(os.environ.get("DEVICE_INVENTORY", "device_inventory.json"))

CSV_FIELDS = ["name", "host", "vendor", "snmp_version", "port", "community",
              "location", "role"]

SYSDESCR_OID = "1.3.6.1.2.1.1.1.0"


def load_inventory() -> list[dict]:
    if INVENTORY_PATH.exists():
        return json.loads(INVENTORY_PATH.read_text())
    print(f"No inventory found at {INVENTORY_PATH}. Run setup_network_devices.py add first.")
    sys.exit(1)


def save_inventory(devices: list[dict]) -> None:
    INVENTORY_PATH.write_text(json.dumps(devices, indent=2))


# ── ICMP Ping ────────────────────────────────────────────────────────────────

def ping_host(host: str, timeout: int = 2) -> bool:
    """Ping a host, return True if reachable."""
    param = "-n" if sys.platform == "win32" else "-c"
    result = subprocess.run(
        ["ping", param, "1", "-W", str(timeout * 1000 if sys.platform == "win32" else timeout), host],
        capture_output=True,
        timeout=timeout + 2,
    )
    return result.returncode == 0


def cmd_ping(args: argparse.Namespace) -> None:
    devices = load_inventory()
    print(f"Pinging {len(devices)} devices...\n")
    reachable = 0
    unreachable = 0

    for d in devices:
        host = d["host"]
        try:
            ok = ping_host(host)
        except Exception:
            ok = False

        status = "UP  " if ok else "DOWN"
        if ok:
            reachable += 1
        else:
            unreachable += 1
        vendor_label = d["vendor"].upper()
        print(f"  [{status}] {d['name']:<30} {host:<20} ({vendor_label})")

    print(f"\nSummary: {reachable} up / {unreachable} down out of {len(devices)} devices")


# ── SNMP Test ────────────────────────────────────────────────────────────────

def snmp_get(host: str, port: int, version: str, community: str, oid: str,
             timeout: int = 5) -> str | None:
    """Run snmpget to retrieve a single OID value."""
    ver_flag = {"v1": "1", "v2c": "2c", "v3": "3"}.get(version, "2c")
    cmd = [
        "snmpget",
        f"-v{ver_flag}",
        "-c", community,
        "-t", str(timeout),
        "-r", "1",
        f"{host}:{port}",
        oid,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 2)
        if result.returncode == 0:
            return result.stdout.strip()
        return None
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None


def cmd_snmp_test(args: argparse.Namespace) -> None:
    devices = load_inventory()
    print(f"SNMP testing {len(devices)} devices (sysDescr)...\n")
    ok_count = 0
    fail_count = 0

    for d in devices:
        community = d.get("community", "public")
        result = snmp_get(d["host"], d["port"], d["snmp_version"], community, SYSDESCR_OID)
        if result:
            ok_count += 1
            # truncate long sysDescr
            desc = result.split("::", 1)[-1].strip()[:60]
            print(f"  [OK  ] {d['name']:<30} {d['host']:<20} {desc}")
        else:
            fail_count += 1
            print(f"  [FAIL] {d['name']:<30} {d['host']:<20} (SNMP unreachable or wrong community)")

    print(f"\nSNMP reachable: {ok_count} / {len(devices)}")
    if fail_count:
        print(f"Failed:        {fail_count} — check community strings, ACLs, and SNMP config")


# ── Export ───────────────────────────────────────────────────────────────────

def cmd_export(args: argparse.Namespace) -> None:
    devices = load_inventory()

    if args.format == "csv":
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for d in devices:
            row = {**d, **d.get("labels", {})}
            writer.writerow(row)
        content = buf.getvalue()
        if args.output:
            Path(args.output).write_text(content)
            print(f"Exported {len(devices)} devices to {args.output}")
        else:
            print(content)

    elif args.format == "json":
        content = json.dumps(devices, indent=2)
        if args.output:
            Path(args.output).write_text(content)
            print(f"Exported {len(devices)} devices to {args.output}")
        else:
            print(content)


def cmd_import(args: argparse.Namespace) -> None:
    path = Path(args.file)
    if not path.exists():
        print(f"ERROR: File not found: {args.file}")
        sys.exit(1)

    existing = load_inventory() if INVENTORY_PATH.exists() else []
    existing_names = {d["name"] for d in existing}
    added = 0
    skipped = 0

    if args.file.endswith(".csv"):
        with open(args.file) as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = row.get("name", "").strip()
                if not name:
                    continue
                if name in existing_names and not args.overwrite:
                    skipped += 1
                    continue
                device = {
                    "name": name,
                    "host": row.get("host", ""),
                    "vendor": row.get("vendor", "cisco"),
                    "snmp_version": row.get("snmp_version", "v2c"),
                    "port": int(row.get("port", 161)),
                    "community": row.get("community", "public"),
                    "labels": {
                        k: row[k] for k in ("location", "role") if row.get(k)
                    },
                }
                if name in existing_names:
                    existing = [d for d in existing if d["name"] != name]
                existing.append(device)
                existing_names.add(name)
                added += 1
    else:
        imported = json.loads(path.read_text())
        for device in imported:
            name = device.get("name", "")
            if name in existing_names and not args.overwrite:
                skipped += 1
                continue
            if name in existing_names:
                existing = [d for d in existing if d["name"] != name]
            existing.append(device)
            existing_names.add(name)
            added += 1

    save_inventory(existing)
    print(f"Import complete: {added} added, {skipped} skipped (use --overwrite to replace existing)")


# ── Report ────────────────────────────────────────────────────────────────────

def cmd_report(args: argparse.Namespace) -> None:
    devices = load_inventory()

    vendor_counts: dict[str, int] = {}
    role_counts: dict[str, int] = {}
    version_counts: dict[str, int] = {}

    for d in devices:
        vendor_counts[d["vendor"]] = vendor_counts.get(d["vendor"], 0) + 1
        role = d.get("labels", {}).get("role", "unspecified")
        role_counts[role] = role_counts.get(role, 0) + 1
        version_counts[d["snmp_version"]] = version_counts.get(d["snmp_version"], 0) + 1

    print("=" * 50)
    print(f"Device Inventory Report — {INVENTORY_PATH}")
    print("=" * 50)
    print(f"\nTotal devices: {len(devices)}")

    print("\nBy Vendor:")
    for vendor, count in sorted(vendor_counts.items(), key=lambda x: -x[1]):
        print(f"  {vendor:<15} {count}")

    print("\nBy Role:")
    for role, count in sorted(role_counts.items(), key=lambda x: -x[1]):
        print(f"  {role:<20} {count}")

    print("\nBy SNMP Version:")
    for ver, count in sorted(version_counts.items()):
        print(f"  {ver:<8} {count}")

    print()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Device inventory manager for ISP network monitoring",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("ping", help="ICMP reachability check for all devices")
    sub.add_parser("snmp-test", help="SNMP sysDescr test for all devices")
    sub.add_parser("report", help="Generate inventory health summary")

    exp_p = sub.add_parser("export", help="Export inventory")
    exp_p.add_argument("--format", choices=["csv", "json"], default="csv")
    exp_p.add_argument("--output", "-o", help="Output file (stdout if omitted)")

    imp_p = sub.add_parser("import", help="Import devices from CSV or JSON")
    imp_p.add_argument("--file", "-f", required=True, help="CSV or JSON file to import")
    imp_p.add_argument("--overwrite", action="store_true",
                       help="Overwrite existing devices with same name")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "ping":
        cmd_ping(args)
    elif args.command == "snmp-test":
        cmd_snmp_test(args)
    elif args.command == "report":
        cmd_report(args)
    elif args.command == "export":
        cmd_export(args)
    elif args.command == "import":
        cmd_import(args)


if __name__ == "__main__":
    main()
