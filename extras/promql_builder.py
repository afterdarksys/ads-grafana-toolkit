#!/usr/bin/env python3
"""
PromQL Query Builder
Visual/interactive builder for Prometheus queries.
"""

import json
import re
import sys
import urllib.request
import urllib.error
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict


@dataclass
class PromQLQuery:
    """Represents a PromQL query."""
    metric: str
    filters: Dict[str, str] = None
    rate_interval: Optional[str] = None
    aggregation: Optional[str] = None
    aggregation_by: List[str] = None
    math_operation: Optional[str] = None
    math_value: Optional[float] = None

    def __post_init__(self):
        if self.filters is None:
            self.filters = {}
        if self.aggregation_by is None:
            self.aggregation_by = []

    def build(self) -> str:
        """Build the PromQL query string."""
        query = self.metric

        # Add filters
        if self.filters:
            filter_strs = [f'{k}="{v}"' for k, v in self.filters.items()]
            query += "{" + ",".join(filter_strs) + "}"

        # Apply rate if specified
        if self.rate_interval:
            query = f"rate({query}[{self.rate_interval}])"

        # Apply aggregation
        if self.aggregation:
            if self.aggregation_by:
                by_clause = "by(" + ",".join(self.aggregation_by) + ")"
                query = f"{self.aggregation} {by_clause} ({query})"
            else:
                query = f"{self.aggregation}({query})"

        # Apply math operation
        if self.math_operation and self.math_value is not None:
            query = f"({query}) {self.math_operation} {self.math_value}"

        return query


class PromQLBuilder:
    """Interactive PromQL query builder."""

    COMMON_METRICS = {
        "node_exporter": [
            "node_cpu_seconds_total",
            "node_memory_MemTotal_bytes",
            "node_memory_MemAvailable_bytes",
            "node_disk_read_bytes_total",
            "node_disk_written_bytes_total",
            "node_network_receive_bytes_total",
            "node_network_transmit_bytes_total",
            "node_filesystem_size_bytes",
            "node_filesystem_avail_bytes",
            "node_load1",
            "node_load5",
            "node_load15",
        ],
        "kubernetes": [
            "kube_pod_status_phase",
            "kube_pod_container_status_restarts_total",
            "container_cpu_usage_seconds_total",
            "container_memory_usage_bytes",
            "kube_deployment_status_replicas",
            "kube_node_status_condition",
        ],
        "application": [
            "http_requests_total",
            "http_request_duration_seconds",
            "http_response_size_bytes",
            "process_cpu_seconds_total",
            "process_resident_memory_bytes",
        ]
    }

    AGGREGATIONS = [
        "sum", "avg", "min", "max", "count",
        "stddev", "stdvar", "topk", "bottomk",
        "count_values", "quantile"
    ]

    def __init__(self, prometheus_url: Optional[str] = None):
        self.prometheus_url = prometheus_url or "http://localhost:9090"

    def get_metrics(self) -> List[str]:
        """Fetch available metrics from Prometheus."""
        try:
            url = f"{self.prometheus_url}/api/v1/label/__name__/values"
            req = urllib.request.Request(url, headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read())
                if data.get("status") == "success":
                    return data["data"]
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError):
            print("Warning: Could not connect to Prometheus, using common metrics", file=sys.stderr)

        # Fallback to common metrics
        metrics = []
        for category_metrics in self.COMMON_METRICS.values():
            metrics.extend(category_metrics)
        return sorted(set(metrics))

    def get_label_values(self, label: str) -> List[str]:
        """Fetch label values from Prometheus."""
        try:
            url = f"{self.prometheus_url}/api/v1/label/{label}/values"
            req = urllib.request.Request(url, headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read())
                if data.get("status") == "success":
                    return data["data"]
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError):
            pass
        return []

    def interactive_build(self) -> str:
        """Build query interactively."""
        print("=== PromQL Query Builder ===\n")

        # Step 1: Select metric
        print("Step 1: Select Metric")
        print("Available categories:")
        for i, category in enumerate(self.COMMON_METRICS.keys(), 1):
            print(f"  {i}. {category}")
        print(f"  {len(self.COMMON_METRICS) + 1}. Fetch from Prometheus")
        print(f"  {len(self.COMMON_METRICS) + 2}. Enter manually")

        choice = input("\nChoice: ").strip()

        if choice.isdigit() and 1 <= int(choice) <= len(self.COMMON_METRICS):
            category = list(self.COMMON_METRICS.keys())[int(choice) - 1]
            metrics = self.COMMON_METRICS[category]
            print(f"\nMetrics in '{category}':")
            for i, metric in enumerate(metrics, 1):
                print(f"  {i}. {metric}")
            metric_choice = input("\nSelect metric: ").strip()
            if metric_choice.isdigit() and 1 <= int(metric_choice) <= len(metrics):
                metric = metrics[int(metric_choice) - 1]
            else:
                metric = input("Enter metric name: ").strip()

        elif choice == str(len(self.COMMON_METRICS) + 1):
            print("\nFetching metrics from Prometheus...")
            metrics = self.get_metrics()
            print(f"Found {len(metrics)} metrics")
            print("First 20 metrics:")
            for i, m in enumerate(metrics[:20], 1):
                print(f"  {i}. {m}")
            print("  ... (more)")
            metric = input("\nEnter metric name: ").strip()

        else:
            metric = input("Enter metric name: ").strip()

        query = PromQLQuery(metric=metric)

        # Step 2: Add filters
        print(f"\nStep 2: Add Filters (for {metric})")
        print("Enter filters in format: label=value")
        print("Examples: job=node, instance=localhost:9090")
        print("Press Enter without input to skip")

        while True:
            filter_input = input("Filter (or Enter to skip): ").strip()
            if not filter_input:
                break

            if "=" in filter_input:
                label, value = filter_input.split("=", 1)
                query.filters[label.strip()] = value.strip()
            else:
                print("Invalid format. Use: label=value")

        # Step 3: Rate interval
        print(f"\nStep 3: Rate Interval")
        print("Apply rate() function? (for counter metrics)")
        rate_choice = input("Interval (e.g., 5m, 1h) or Enter to skip: ").strip()
        if rate_choice:
            query.rate_interval = rate_choice

        # Step 4: Aggregation
        print(f"\nStep 4: Aggregation")
        print("Available aggregations:")
        for i, agg in enumerate(self.AGGREGATIONS, 1):
            print(f"  {i}. {agg}")
        agg_choice = input("Select aggregation (or Enter to skip): ").strip()

        if agg_choice.isdigit() and 1 <= int(agg_choice) <= len(self.AGGREGATIONS):
            query.aggregation = self.AGGREGATIONS[int(agg_choice) - 1]

            # Aggregation by labels
            by_input = input("Aggregate by labels (comma-separated, or Enter): ").strip()
            if by_input:
                query.aggregation_by = [label.strip() for label in by_input.split(",")]

        # Step 5: Math operations
        print(f"\nStep 5: Math Operations")
        print("Apply math operation? (*, /, +, -)")
        math_op = input("Operation (or Enter to skip): ").strip()
        if math_op in ["*", "/", "+", "-"]:
            math_val = input("Value: ").strip()
            try:
                query.math_operation = math_op
                query.math_value = float(math_val)
            except ValueError:
                print("Invalid value, skipping math operation")

        # Build final query
        promql = query.build()
        print(f"\n=== Generated Query ===")
        print(promql)
        print()

        return promql

    def guided_query(self, query_type: str) -> str:
        """Build query from templates."""
        templates = {
            "cpu_usage": {
                "description": "CPU usage percentage",
                "query": 'avg(rate(node_cpu_seconds_total{mode!="idle"}[5m])) * 100'
            },
            "memory_usage": {
                "description": "Memory usage percentage",
                "query": '(node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes) / node_memory_MemTotal_bytes * 100'
            },
            "disk_usage": {
                "description": "Disk usage percentage",
                "query": '(node_filesystem_size_bytes - node_filesystem_avail_bytes) / node_filesystem_size_bytes * 100'
            },
            "network_throughput": {
                "description": "Network throughput in bytes/sec",
                "query": 'rate(node_network_receive_bytes_total[5m])'
            },
            "http_request_rate": {
                "description": "HTTP requests per second",
                "query": 'rate(http_requests_total[5m])'
            },
            "http_latency_p99": {
                "description": "HTTP latency 99th percentile",
                "query": 'histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))'
            },
        }

        if query_type in templates:
            template = templates[query_type]
            print(f"{template['description']}")
            print(f"Query: {template['query']}")
            return template['query']

        print(f"Unknown query type: {query_type}")
        print("Available types:", ", ".join(templates.keys()))
        return ""

    def validate_query(self, query: str) -> bool:
        """Validate PromQL query syntax."""
        # Basic syntax validation
        if not query:
            return False

        # Check balanced parentheses
        if query.count("(") != query.count(")"):
            print("Error: Unbalanced parentheses", file=sys.stderr)
            return False

        # Check balanced braces
        if query.count("{") != query.count("}"):
            print("Error: Unbalanced braces", file=sys.stderr)
            return False

        # Check balanced brackets
        if query.count("[") != query.count("]"):
            print("Error: Unbalanced brackets", file=sys.stderr)
            return False

        # Try to validate with Prometheus API
        try:
            import urllib.parse
            encoded_query = urllib.parse.quote(query)
            url = f"{self.prometheus_url}/api/v1/query?query={encoded_query}&time=0"
            req = urllib.request.Request(url, headers={"Accept": "application/json"})

            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read())
                if data.get("status") == "success":
                    print("✓ Query is valid")
                    return True
                else:
                    print(f"✗ Query error: {data.get('error', 'Unknown error')}", file=sys.stderr)
                    return False

        except (urllib.error.URLError, urllib.error.HTTPError) as e:
            print(f"Warning: Could not validate with Prometheus: {e}", file=sys.stderr)
            print("Query syntax looks OK (basic check)", file=sys.stderr)
            return True
        except Exception as e:
            print(f"Validation error: {e}", file=sys.stderr)
            return False


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="PromQL Query Builder - Build Prometheus queries interactively"
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # Interactive command
    interactive_parser = subparsers.add_parser("interactive", help="Build query interactively")
    interactive_parser.add_argument("--prometheus-url", default="http://localhost:9090")
    interactive_parser.add_argument("-o", "--output", help="Save query to file")

    # Template command
    template_parser = subparsers.add_parser("template", help="Use query template")
    template_parser.add_argument("query_type", choices=[
        "cpu_usage", "memory_usage", "disk_usage",
        "network_throughput", "http_request_rate", "http_latency_p99"
    ])
    template_parser.add_argument("-o", "--output", help="Save query to file")

    # Validate command
    validate_parser = subparsers.add_parser("validate", help="Validate PromQL query")
    validate_parser.add_argument("query", help="PromQL query to validate")
    validate_parser.add_argument("--prometheus-url", default="http://localhost:9090")

    args = parser.parse_args()

    builder = PromQLBuilder(prometheus_url=getattr(args, 'prometheus_url', None))

    if args.command == "interactive":
        query = builder.interactive_build()

        if args.output:
            with open(args.output, 'w') as f:
                f.write(query)
            print(f"Query saved to: {args.output}")

    elif args.command == "template":
        query = builder.guided_query(args.query_type)

        if args.output:
            with open(args.output, 'w') as f:
                f.write(query)
            print(f"Query saved to: {args.output}")

    elif args.command == "validate":
        valid = builder.validate_query(args.query)
        sys.exit(0 if valid else 1)


if __name__ == "__main__":
    main()
