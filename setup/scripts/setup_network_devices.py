#!/usr/bin/env python3
"""
setup_network_devices.py — SNMP exporter config generator for ISP network hardware.

Generates snmp_exporter generator.yml and prometheus.yml scrape configs for:
  - Cisco IOS / IOS-XE / IOS-XR / NX-OS
  - Juniper Junos (MX, QFX, EX, SRX, PTX)
  - Palo Alto Networks PA-Series / VM-Series
  - Fortinet FortiGate

Usage:
  python setup_network_devices.py --help
  python setup_network_devices.py add --vendor cisco --host 192.168.1.1 --community public --name core-router-01
  python setup_network_devices.py add --vendor juniper --host 10.0.0.1 --community readonly --name pe-01 --version v3
  python setup_network_devices.py generate    # write snmp.yml + prometheus scrape block
  python setup_network_devices.py list        # show current device inventory
  python setup_network_devices.py remove --name core-router-01
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import yaml


INVENTORY_PATH = Path(os.environ.get("DEVICE_INVENTORY", "device_inventory.json"))

VENDOR_MODULES = {
    "cisco": {
        "modules": ["if_mib", "cisco_process_mib", "cisco_memory_pool_mib",
                    "bgp4_mib", "ospf_mib", "cisco_entity_mib", "cisco_env_mon"],
        "walk": [
            "1.3.6.1.2.1.2",       # IF-MIB
            "1.3.6.1.4.1.9.9.109", # CISCO-PROCESS-MIB
            "1.3.6.1.4.1.9.9.48",  # CISCO-MEMORY-POOL-MIB
            "1.3.6.1.2.1.15",      # BGP4-MIB
            "1.3.6.1.2.1.14",      # OSPF-MIB
            "1.3.6.1.2.1.47",      # ENTITY-MIB
            "1.3.6.1.4.1.9.9.13",  # CISCO-ENVMON-MIB
        ],
        "description": "Cisco IOS/IOS-XE/IOS-XR/NX-OS",
    },
    "juniper": {
        "modules": ["if_mib", "juniper_mib", "juniper_bgp4v2_mib", "juniper_chassis_mib"],
        "walk": [
            "1.3.6.1.2.1.2",        # IF-MIB
            "1.3.6.1.4.1.2636.3.1", # JUNIPER-MIB (operating table)
            "1.3.6.1.4.1.2636.5.1", # JUNIPER-BGP4V2-MIB
            "1.3.6.1.4.1.2636.3.26",# JUNIPER-DOM-MIB (optical)
            "1.3.6.1.2.1.15",       # BGP4-MIB
            "1.3.6.1.2.1.14",       # OSPF-MIB
        ],
        "description": "Juniper Junos (MX/QFX/EX/SRX/PTX)",
    },
    "paloalto": {
        "modules": ["if_mib", "pan_common_mib"],
        "walk": [
            "1.3.6.1.2.1.2",         # IF-MIB
            "1.3.6.1.4.1.25461.2.1", # PAN-COMMON-MIB
        ],
        "description": "Palo Alto Networks PA/VM-Series",
    },
    "fortinet": {
        "modules": ["if_mib", "fortinet_fortigate_mib"],
        "walk": [
            "1.3.6.1.2.1.2",       # IF-MIB
            "1.3.6.1.4.1.12356.1", # FORTINET-FORTIGATE-MIB
            "1.3.6.1.4.1.12356.2", # FORTINET-CORE-MIB
        ],
        "description": "Fortinet FortiGate",
    },
}

SNMPV3_DEFAULTS = {
    "auth_protocol": "SHA",
    "priv_protocol": "AES",
}


def load_inventory() -> list[dict]:
    if INVENTORY_PATH.exists():
        return json.loads(INVENTORY_PATH.read_text())
    return []


def save_inventory(devices: list[dict]) -> None:
    INVENTORY_PATH.write_text(json.dumps(devices, indent=2))
    print(f"Inventory saved to {INVENTORY_PATH}")


def cmd_add(args: argparse.Namespace) -> None:
    devices = load_inventory()

    if any(d["name"] == args.name for d in devices):
        print(f"ERROR: Device '{args.name}' already exists. Remove it first.")
        sys.exit(1)

    device: dict = {
        "name": args.name,
        "host": args.host,
        "vendor": args.vendor,
        "snmp_version": args.version,
        "port": args.port,
        "labels": {},
    }

    if args.version in ("v1", "v2c"):
        device["community"] = args.community or "public"
    else:  # v3
        device["v3_username"] = args.v3_username or ""
        device["v3_auth_key"] = args.v3_auth_key or ""
        device["v3_priv_key"] = args.v3_priv_key or ""
        device["v3_auth_protocol"] = args.v3_auth_protocol or SNMPV3_DEFAULTS["auth_protocol"]
        device["v3_priv_protocol"] = args.v3_priv_protocol or SNMPV3_DEFAULTS["priv_protocol"]

    if args.location:
        device["labels"]["location"] = args.location
    if args.role:
        device["labels"]["role"] = args.role

    devices.append(device)
    save_inventory(devices)
    info = VENDOR_MODULES[args.vendor]
    print(f"Added {info['description']} device: {args.name} ({args.host})")


def cmd_remove(args: argparse.Namespace) -> None:
    devices = load_inventory()
    before = len(devices)
    devices = [d for d in devices if d["name"] != args.name]
    if len(devices) == before:
        print(f"ERROR: Device '{args.name}' not found.")
        sys.exit(1)
    save_inventory(devices)
    print(f"Removed device: {args.name}")


def cmd_list(args: argparse.Namespace) -> None:
    devices = load_inventory()
    if not devices:
        print("No devices in inventory.")
        return
    print(f"{'Name':<30} {'Host':<20} {'Vendor':<12} {'SNMP':<6} {'Role'}")
    print("-" * 90)
    for d in devices:
        role = d.get("labels", {}).get("role", "")
        print(f"{d['name']:<30} {d['host']:<20} {d['vendor']:<12} {d['snmp_version']:<6} {role}")


def _build_snmp_module(vendor: str) -> dict:
    """Build an snmp_exporter generator config block for a vendor."""
    info = VENDOR_MODULES[vendor]
    return {
        "walk": info["walk"],
        "version": 2,
        "max_repetitions": 25,
        "retries": 3,
        "timeout": "10s",
    }


def cmd_generate(args: argparse.Namespace) -> None:
    devices = load_inventory()
    if not devices:
        print("No devices in inventory — add devices first with 'add'.")
        sys.exit(1)

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # ── snmp_exporter generator.yml ─────────────────────────────────────
    generator_config: dict = {"modules": {}}
    for vendor in VENDOR_MODULES:
        module_name = f"ads_{vendor}"
        generator_config["modules"][module_name] = _build_snmp_module(vendor)

    gen_path = out_dir / "snmp_generator.yml"
    gen_path.write_text(yaml.dump(generator_config, default_flow_style=False, sort_keys=False))
    print(f"Written: {gen_path}")

    # ── Prometheus scrape config ─────────────────────────────────────────
    scrape_configs = []
    by_vendor: dict[str, list] = {}
    for d in devices:
        by_vendor.setdefault(d["vendor"], []).append(d)

    for vendor, vdevices in by_vendor.items():
        targets = []
        for d in vdevices:
            targets.append({
                "targets": [f"{d['host']}:{d['port']}"],
                "labels": {
                    "device": d["name"],
                    "vendor": vendor,
                    **d.get("labels", {}),
                },
            })

        job: dict = {
            "job_name": f"snmp_{vendor}",
            "scrape_interval": "60s",
            "scrape_timeout": "30s",
            "metrics_path": "/snmp",
            "params": {"module": [f"ads_{vendor}"]},
            "file_sd_configs": [{"files": [f"{out_dir}/targets_{vendor}.yml"]}],
            "relabel_configs": [
                {
                    "source_labels": ["__address__"],
                    "target_label": "__param_target",
                },
                {
                    "source_labels": ["__param_target"],
                    "target_label": "instance",
                },
                {
                    "target_label": "__address__",
                    "replacement": "snmp-exporter:9116",
                },
            ],
        }
        scrape_configs.append(job)

        # per-vendor file_sd targets
        targets_path = out_dir / f"targets_{vendor}.yml"
        targets_path.write_text(yaml.dump(targets, default_flow_style=False))
        print(f"Written: {targets_path}")

    prom_path = out_dir / "prometheus_snmp_scrape.yml"
    prom_path.write_text(yaml.dump({"scrape_configs": scrape_configs},
                                    default_flow_style=False, sort_keys=False))
    print(f"Written: {prom_path}")

    # ── Docker Compose snippet for snmp_exporter ─────────────────────────
    compose_snippet = {
        "version": "3.8",
        "services": {
            "snmp-exporter": {
                "image": "prom/snmp-exporter:latest",
                "container_name": "snmp-exporter",
                "restart": "unless-stopped",
                "ports": ["9116:9116"],
                "volumes": ["./snmp.yml:/etc/snmp_exporter/snmp.yml:ro"],
                "command": ["--config.file=/etc/snmp_exporter/snmp.yml"],
            }
        },
    }
    compose_path = out_dir / "docker-compose.snmp.yml"
    compose_path.write_text(yaml.dump(compose_snippet, default_flow_style=False))
    print(f"Written: {compose_path}")

    print(f"\nDone. {len(devices)} devices configured across {len(by_vendor)} vendor module(s).")
    print("\nNext steps:")
    print("  1. Install snmp_exporter generator: https://github.com/prometheus/snmp_exporter/tree/main/generator")
    print(f"  2. Run: snmp-generator generate -g {gen_path}")
    print("  3. Copy generated snmp.yml to your snmp_exporter container")
    print(f"  4. Add contents of {prom_path} to your prometheus.yml scrape_configs")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Network device SNMP inventory and config generator for ISP monitoring",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # add
    add_p = sub.add_parser("add", help="Add a device to the inventory")
    add_p.add_argument("--name", required=True, help="Device name (e.g. core-router-01)")
    add_p.add_argument("--host", required=True, help="Device IP or hostname")
    add_p.add_argument("--vendor", required=True, choices=list(VENDOR_MODULES),
                       help="Hardware vendor")
    add_p.add_argument("--version", default="v2c", choices=["v1", "v2c", "v3"],
                       help="SNMP version (default: v2c)")
    add_p.add_argument("--port", type=int, default=161, help="SNMP port (default: 161)")
    add_p.add_argument("--community", default="public", help="SNMPv1/v2c community string")
    add_p.add_argument("--v3-username", dest="v3_username", help="SNMPv3 username")
    add_p.add_argument("--v3-auth-key", dest="v3_auth_key", help="SNMPv3 auth key")
    add_p.add_argument("--v3-priv-key", dest="v3_priv_key", help="SNMPv3 privacy key")
    add_p.add_argument("--v3-auth-protocol", dest="v3_auth_protocol", default="SHA",
                       choices=["MD5", "SHA", "SHA224", "SHA256", "SHA384", "SHA512"])
    add_p.add_argument("--v3-priv-protocol", dest="v3_priv_protocol", default="AES",
                       choices=["DES", "AES", "AES192", "AES256"])
    add_p.add_argument("--location", help="Physical location label")
    add_p.add_argument("--role", help="Device role label (e.g. pe, p, ce, edge-fw)")

    # remove
    rm_p = sub.add_parser("remove", help="Remove a device from the inventory")
    rm_p.add_argument("--name", required=True, help="Device name to remove")

    # list
    sub.add_parser("list", help="List all devices in the inventory")

    # generate
    gen_p = sub.add_parser("generate", help="Generate SNMP exporter and Prometheus configs")
    gen_p.add_argument("--output-dir", default="snmp_configs",
                       help="Directory for output files (default: snmp_configs/)")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "add":
        cmd_add(args)
    elif args.command == "remove":
        cmd_remove(args)
    elif args.command == "list":
        cmd_list(args)
    elif args.command == "generate":
        cmd_generate(args)


if __name__ == "__main__":
    main()
