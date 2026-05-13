#!/usr/bin/env python3
"""gen_recording_rules.py — Generate Prometheus recording rules from dashboard templates.

Walks registered dashboard templates, extracts PromQL expressions from panels,
and emits a Prometheus recording_rules.yml. Attach this file to your Prometheus
config under `rule_files:` to pre-compute expensive queries.

Usage:
  python gen_recording_rules.py --out recording_rules.yml
  python gen_recording_rules.py --template isp-bgp --out isp_bgp_rules.yml
  python gen_recording_rules.py --list
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main() -> None:
    p = argparse.ArgumentParser(description="Generate Prometheus recording rules from dashboard templates")
    p.add_argument("--template", metavar="NAME", help="Generate rules for a single template")
    p.add_argument("--out", default="recording_rules.yml", help="Output file (default: recording_rules.yml)")
    p.add_argument("--list", action="store_true", help="List templates that have extractable PromQL and exit")
    p.add_argument("--stdout", action="store_true", help="Print to stdout instead of writing a file")
    args = p.parse_args()

    from ads_grafana_toolkit.recording_rules.generator import (
        generate_recording_rules_yaml,
        recording_rules_for_template,
    )
    from ads_grafana_toolkit.template_library.registry import list_templates

    if args.list:
        print("Templates with extractable PromQL expressions:")
        for t in list_templates():
            rules = recording_rules_for_template(t["name"])
            if rules:
                print(f"  {t['name']:30s}  {len(rules)} rule(s)")
        return

    yaml_out = generate_recording_rules_yaml(template=args.template)

    if not yaml_out.strip() or yaml_out.strip() == "groups: []":
        name = args.template or "any template"
        print(f"No PromQL expressions found for {name}.", file=sys.stderr)
        print("Only PromQL queries are extracted — CloudWatch/GCP/Azure metric blobs are skipped.", file=sys.stderr)
        sys.exit(1)

    if args.stdout:
        print(yaml_out)
    else:
        Path(args.out).write_text(yaml_out)
        # Count rules written
        import yaml
        doc = yaml.safe_load(yaml_out)
        total = sum(len(g.get("rules", [])) for g in doc.get("groups", []))
        groups = len(doc.get("groups", []))
        print(f"Written: {args.out}  ({groups} group(s), {total} rule(s))")
        print()
        print("Add to your prometheus.yml:")
        print(f"  rule_files:")
        print(f"    - '{args.out}'")


if __name__ == "__main__":
    main()
