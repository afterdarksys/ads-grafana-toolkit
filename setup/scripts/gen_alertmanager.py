#!/usr/bin/env python3
"""gen_alertmanager.py — Generate Alertmanager routing config from device inventory.

Routes alerts by vendor/role to appropriate receivers (Slack, PagerDuty, webhook).

Usage:
  python gen_alertmanager.py --out alertmanager.yml
  python gen_alertmanager.py --slack-backbone "#noc-backbone" --slack-security "#noc-security"
  python gen_alertmanager.py --pagerduty-key <key> --out alertmanager.yml
"""
from __future__ import annotations
import argparse, json, os
from pathlib import Path
import yaml

INVENTORY_PATH = Path(os.environ.get("DEVICE_INVENTORY", "device_inventory.json"))


def load_inventory() -> list[dict]:
    if INVENTORY_PATH.exists():
        return json.loads(INVENTORY_PATH.read_text())
    return []


def build_config(args: argparse.Namespace) -> dict:
    devices = load_inventory()

    # Collect distinct vendor/role combos for routing
    vendors = {d["vendor"] for d in devices}
    roles = {d.get("labels", {}).get("role", "") for d in devices} - {""}

    receivers = []
    routes = []

    # ── Global receivers ─────────────────────────────────────────────────
    if args.slack_default:
        receivers.append(_slack_receiver("slack-default", args.slack_default))
    if args.slack_backbone:
        receivers.append(_slack_receiver("slack-backbone", args.slack_backbone, color_ok="#36a64f"))
    if args.slack_security:
        receivers.append(_slack_receiver("slack-security", args.slack_security, color_ok="#764FA5"))
    if args.slack_cloud:
        receivers.append(_slack_receiver("slack-cloud", args.slack_cloud))
    if args.pagerduty_key:
        receivers.append(_pd_receiver("pagerduty-critical", args.pagerduty_key))
    if args.webhook_url:
        receivers.append({"name": "webhook-default", "webhook_configs": [{"url": args.webhook_url}]})
    if not receivers:
        receivers.append({"name": "null-receiver"})

    default_receiver = receivers[0]["name"]

    # ── Routes ───────────────────────────────────────────────────────────
    # Critical → PagerDuty
    if args.pagerduty_key:
        routes.append({"match": {"severity": "critical"}, "receiver": "pagerduty-critical", "continue": True})

    # Security team (firewalls)
    if args.slack_security:
        routes.append({"match_re": {"team": "security-noc"}, "receiver": "slack-security"})

    # Backbone NOC (ISP/routing)
    if args.slack_backbone:
        routes.append({"match_re": {"team": "backbone-noc"}, "receiver": "slack-backbone"})

    # Cloud ops
    if args.slack_cloud:
        routes.append({"match_re": {"team": "cloud-ops"}, "receiver": "slack-cloud"})

    # Per-vendor routes
    vendor_recv_map = {"paloalto": "slack-security", "fortinet": "slack-security",
                       "cisco": "slack-backbone", "juniper": "slack-backbone"}
    for vendor in vendors:
        recv = vendor_recv_map.get(vendor, default_receiver)
        if recv in {r["name"] for r in receivers}:
            routes.append({"match": {"vendor": vendor}, "receiver": recv})

    config: dict = {
        "global": {
            "resolve_timeout": "5m",
            "slack_api_url": args.slack_api_url or "https://hooks.slack.com/services/YOUR/WEBHOOK",
        },
        "route": {
            "group_by": ["alertname", "team", "vendor", "instance"],
            "group_wait": "30s",
            "group_interval": "5m",
            "repeat_interval": "4h",
            "receiver": default_receiver,
            "routes": routes,
        },
        "receivers": receivers,
        "inhibit_rules": [
            {
                "source_match": {"severity": "critical"},
                "target_match": {"severity": "warning"},
                "equal": ["alertname", "instance"],
            }
        ],
    }
    return config


def _slack_receiver(name: str, channel: str, color_ok: str = "#2eb886") -> dict:
    return {
        "name": name,
        "slack_configs": [{
            "channel": channel,
            "send_resolved": True,
            "color": '{{ if eq .Status "firing" }}#e01e5a{{ else }}' + color_ok + '{{ end }}',
            "title": '{{ .CommonAnnotations.summary | default .CommonLabels.alertname }}',
            "text": '{{ range .Alerts }}{{ .Annotations.description }}\n{{ end }}',
            "footer": "ads-grafana-toolkit | {{ .CommonLabels.team }}",
        }],
    }


def _pd_receiver(name: str, key: str) -> dict:
    return {
        "name": name,
        "pagerduty_configs": [{
            "routing_key": key,
            "description": '{{ .CommonAnnotations.summary | default .CommonLabels.alertname }}',
            "severity": '{{ .CommonLabels.severity | default "warning" }}',
            "details": {
                "instance": '{{ .CommonLabels.instance }}',
                "team": '{{ .CommonLabels.team }}',
                "vendor": '{{ .CommonLabels.vendor | default "n/a" }}',
            },
        }],
    }


def main() -> None:
    p = argparse.ArgumentParser(description="Generate Alertmanager config from device inventory")
    p.add_argument("--out", default="alertmanager.yml")
    p.add_argument("--slack-default", dest="slack_default", metavar="CHANNEL")
    p.add_argument("--slack-backbone", dest="slack_backbone", metavar="CHANNEL")
    p.add_argument("--slack-security", dest="slack_security", metavar="CHANNEL")
    p.add_argument("--slack-cloud", dest="slack_cloud", metavar="CHANNEL")
    p.add_argument("--slack-api-url", dest="slack_api_url")
    p.add_argument("--pagerduty-key", dest="pagerduty_key", metavar="KEY")
    p.add_argument("--webhook-url", dest="webhook_url", metavar="URL")
    args = p.parse_args()

    config = build_config(args)
    Path(args.out).write_text(yaml.dump(config, default_flow_style=False, sort_keys=False))
    print(f"Written: {args.out}")
    print(f"  {len(config['receivers'])} receivers, {len(config['route']['routes'])} routes")

if __name__ == "__main__": main()
