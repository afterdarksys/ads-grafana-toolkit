#!/usr/bin/env python3
"""
setup_cloud_providers.py — Configure Grafana datasources for GCP, AWS, and Azure.

Automates Grafana datasource provisioning via the Grafana API for:
  - AWS CloudWatch
  - GCP Cloud Monitoring (Stackdriver)
  - Azure Monitor

Usage:
  python setup_cloud_providers.py --help
  python setup_cloud_providers.py aws --region us-east-1 --access-key AKIA... --secret-key ...
  python setup_cloud_providers.py gcp --project my-project --key-file /path/to/sa.json
  python setup_cloud_providers.py azure --tenant-id ... --client-id ... --client-secret ...
  python setup_cloud_providers.py list     # list configured cloud datasources
  python setup_cloud_providers.py test     # test connectivity for all cloud datasources
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


GRAFANA_URL = os.environ.get("GRAFANA_URL", "http://localhost:3000")
GRAFANA_USER = os.environ.get("GRAFANA_USER", "admin")
GRAFANA_PASSWORD = os.environ.get("GRAFANA_PASSWORD", "admin")


def grafana_request(method: str, path: str, body: dict | None = None) -> Any:
    """Make a Grafana API request."""
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
        print("Set GRAFANA_URL, GRAFANA_USER, GRAFANA_PASSWORD env vars if needed.")
        sys.exit(1)


def upsert_datasource(payload: dict) -> None:
    """Create or update a Grafana datasource."""
    existing = grafana_request("GET", "/datasources")
    match = next((d for d in existing if d["name"] == payload["name"]), None)
    if match:
        ds_id = match["id"]
        grafana_request("PUT", f"/datasources/{ds_id}", payload)
        print(f"Updated datasource: {payload['name']}")
    else:
        grafana_request("POST", "/datasources", payload)
        print(f"Created datasource: {payload['name']}")


def cmd_aws(args: argparse.Namespace) -> None:
    """Configure AWS CloudWatch datasource."""
    payload: dict = {
        "name": args.name,
        "type": "cloudwatch",
        "access": "proxy",
        "jsonData": {
            "authType": "keys" if args.access_key else "default",
            "defaultRegion": args.region,
            "assumeRoleArn": args.role_arn or "",
            "externalId": args.external_id or "",
            "customMetricsNamespaces": args.custom_namespaces or "",
        },
        "isDefault": args.default,
    }

    if args.access_key and args.secret_key:
        payload["secureJsonData"] = {
            "accessKey": args.access_key,
            "secretKey": args.secret_key,
        }

    upsert_datasource(payload)

    print(f"\nAWS CloudWatch datasource '{args.name}' configured.")
    print(f"  Region: {args.region}")
    print(f"  Auth:   {'Access Key' if args.access_key else 'EC2 IAM Role / Default'}")
    if args.role_arn:
        print(f"  Assume Role: {args.role_arn}")


def cmd_gcp(args: argparse.Namespace) -> None:
    """Configure GCP Cloud Monitoring datasource."""
    payload: dict = {
        "name": args.name,
        "type": "stackdriver",
        "access": "proxy",
        "jsonData": {
            "authenticationType": "jwt" if args.key_file else "gce",
            "defaultProject": args.project,
            "tokenUri": "https://oauth2.googleapis.com/token",
        },
        "isDefault": args.default,
    }

    if args.key_file:
        key_path = Path(args.key_file)
        if not key_path.exists():
            print(f"ERROR: Service account key file not found: {args.key_file}")
            sys.exit(1)
        key_data = json.loads(key_path.read_text())
        payload["jsonData"]["clientEmail"] = key_data.get("client_email", "")
        payload["jsonData"]["defaultProject"] = args.project or key_data.get("project_id", "")
        payload["secureJsonData"] = {
            "privateKey": key_data.get("private_key", ""),
        }

    upsert_datasource(payload)

    print(f"\nGCP Cloud Monitoring datasource '{args.name}' configured.")
    print(f"  Project:  {args.project or '(from key file)'}")
    print(f"  Auth:     {'Service Account JSON' if args.key_file else 'GCE Metadata Server'}")


def cmd_azure(args: argparse.Namespace) -> None:
    """Configure Azure Monitor datasource."""
    payload: dict = {
        "name": args.name,
        "type": "grafana-azure-monitor-datasource",
        "access": "proxy",
        "jsonData": {
            "cloudName": args.cloud,
            "tenantId": args.tenant_id,
            "clientId": args.client_id,
            "subscriptionId": args.subscription_id or "",
            "azureAuthType": "clientsecret",
        },
        "secureJsonData": {
            "clientSecret": args.client_secret,
        },
        "isDefault": args.default,
    }

    upsert_datasource(payload)

    print(f"\nAzure Monitor datasource '{args.name}' configured.")
    print(f"  Tenant:       {args.tenant_id}")
    print(f"  Client ID:    {args.client_id}")
    print(f"  Cloud:        {args.cloud}")
    if args.subscription_id:
        print(f"  Subscription: {args.subscription_id}")


def cmd_list(args: argparse.Namespace) -> None:
    """List all cloud datasources."""
    cloud_types = {"cloudwatch", "stackdriver", "grafana-azure-monitor-datasource"}
    datasources = grafana_request("GET", "/datasources")
    cloud_ds = [d for d in datasources if d.get("type") in cloud_types]

    if not cloud_ds:
        print("No cloud datasources configured.")
        return

    type_labels = {
        "cloudwatch": "AWS CloudWatch",
        "stackdriver": "GCP Cloud Monitoring",
        "grafana-azure-monitor-datasource": "Azure Monitor",
    }

    print(f"{'Name':<35} {'Provider':<25} {'Default'}")
    print("-" * 70)
    for d in cloud_ds:
        label = type_labels.get(d["type"], d["type"])
        default = "yes" if d.get("isDefault") else ""
        print(f"{d['name']:<35} {label:<25} {default}")


def cmd_test(args: argparse.Namespace) -> None:
    """Test connectivity for all cloud datasources."""
    cloud_types = {"cloudwatch", "stackdriver", "grafana-azure-monitor-datasource"}
    datasources = grafana_request("GET", "/datasources")
    cloud_ds = [d for d in datasources if d.get("type") in cloud_types]

    if not cloud_ds:
        print("No cloud datasources to test.")
        return

    for ds in cloud_ds:
        print(f"Testing: {ds['name']} ... ", end="", flush=True)
        result = grafana_request("GET", f"/datasources/{ds['id']}/health")
        status = result.get("status", "unknown")
        message = result.get("message", "")
        icon = "OK" if status == "OK" else "FAIL"
        print(f"{icon}  {message}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Configure Grafana cloud datasources (AWS/GCP/Azure)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Environment variables:
  GRAFANA_URL       Grafana base URL (default: http://localhost:3000)
  GRAFANA_USER      Grafana username (default: admin)
  GRAFANA_PASSWORD  Grafana password (default: admin)
""",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # AWS
    aws_p = sub.add_parser("aws", help="Configure AWS CloudWatch datasource")
    aws_p.add_argument("--name", default="AWS CloudWatch", help="Datasource name")
    aws_p.add_argument("--region", default="us-east-1", help="Default AWS region")
    aws_p.add_argument("--access-key", dest="access_key", help="AWS Access Key ID")
    aws_p.add_argument("--secret-key", dest="secret_key", help="AWS Secret Access Key")
    aws_p.add_argument("--role-arn", dest="role_arn", help="IAM role ARN to assume")
    aws_p.add_argument("--external-id", dest="external_id", help="External ID for role assumption")
    aws_p.add_argument("--custom-namespaces", dest="custom_namespaces",
                       help="Comma-separated custom CloudWatch namespaces")
    aws_p.add_argument("--default", action="store_true", help="Set as default datasource")

    # GCP
    gcp_p = sub.add_parser("gcp", help="Configure GCP Cloud Monitoring datasource")
    gcp_p.add_argument("--name", default="Google Cloud Monitoring", help="Datasource name")
    gcp_p.add_argument("--project", help="GCP project ID")
    gcp_p.add_argument("--key-file", dest="key_file",
                       help="Path to service account JSON key file")
    gcp_p.add_argument("--default", action="store_true", help="Set as default datasource")

    # Azure
    az_p = sub.add_parser("azure", help="Configure Azure Monitor datasource")
    az_p.add_argument("--name", default="Azure Monitor", help="Datasource name")
    az_p.add_argument("--tenant-id", dest="tenant_id", required=True, help="Azure Tenant ID")
    az_p.add_argument("--client-id", dest="client_id", required=True, help="Azure App Registration Client ID")
    az_p.add_argument("--client-secret", dest="client_secret", required=True,
                       help="Azure App Registration Client Secret")
    az_p.add_argument("--subscription-id", dest="subscription_id",
                       help="Default Azure Subscription ID")
    az_p.add_argument("--cloud", default="AzureCloud",
                       choices=["AzureCloud", "AzureChinaCloud", "AzureUSGovernment"],
                       help="Azure cloud environment")
    az_p.add_argument("--default", action="store_true", help="Set as default datasource")

    # list / test
    sub.add_parser("list", help="List configured cloud datasources")
    sub.add_parser("test", help="Test all configured cloud datasource connections")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "aws":
        cmd_aws(args)
    elif args.command == "gcp":
        cmd_gcp(args)
    elif args.command == "azure":
        cmd_azure(args)
    elif args.command == "list":
        cmd_list(args)
    elif args.command == "test":
        cmd_test(args)


if __name__ == "__main__":
    main()
