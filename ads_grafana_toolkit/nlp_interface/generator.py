"""Natural language to dashboard generator."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any, Optional, Union

from ads_grafana_toolkit.sdk.dashboard import Dashboard
from ads_grafana_toolkit.sdk.datasource import Datasource


METRIC_PATTERNS = {
    r"\bcpu\b": {
        "title": "CPU Usage",
        "query": '100 - (avg(irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)',
        "unit": "percent",
        "type": "timeseries",
    },
    r"\bmemory\b|\bram\b": {
        "title": "Memory Usage",
        "query": "100 * (1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes))",
        "unit": "percent",
        "type": "timeseries",
    },
    r"\bdisk\b|\bstorage\b|\bfilesystem\b": {
        "title": "Disk Usage",
        "query": '100 - ((node_filesystem_avail_bytes{fstype!="tmpfs"} / node_filesystem_size_bytes) * 100)',
        "unit": "percent",
        "type": "timeseries",
    },
    r"\bnetwork\b|\bbandwidth\b|\btraffic\b": {
        "title": "Network Traffic",
        "query": 'rate(node_network_receive_bytes_total{device!~"lo|veth.*"}[5m]) * 8',
        "unit": "bps",
        "type": "timeseries",
    },
    r"\bhttp\b.*\brequest": {
        "title": "HTTP Requests",
        "query": "rate(http_requests_total[5m])",
        "unit": "reqps",
        "type": "timeseries",
    },
    r"\blatency\b|\bresponse.?time\b|\bduration\b": {
        "title": "Request Latency",
        "query": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))",
        "unit": "s",
        "type": "timeseries",
    },
    r"\bp99\b|\bp95\b|\bpercentile\b": {
        "title": "Latency Percentiles",
        "query": "histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))",
        "unit": "s",
        "type": "timeseries",
    },
    r"\berror\b|\bfailure\b|\bfail\b": {
        "title": "Error Rate",
        "query": 'rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m]) * 100',
        "unit": "percent",
        "type": "timeseries",
    },
    r"\bcontainer\b|\bdocker\b": {
        "title": "Container Resources",
        "query": 'rate(container_cpu_usage_seconds_total{name!=""}[5m]) * 100',
        "unit": "percent",
        "type": "timeseries",
    },
    r"\bpod\b|\bkubernetes\b|\bk8s\b": {
        "title": "Pod Resources",
        "query": 'sum by(pod) (rate(container_cpu_usage_seconds_total[5m]))',
        "unit": "cores",
        "type": "timeseries",
    },
    r"\bdatabase\b|\bdb\b|\bquery\b": {
        "title": "Database Queries",
        "query": "rate(pg_stat_database_xact_commit[5m])",
        "unit": "ops",
        "type": "timeseries",
    },
    r"\bconnection": {
        "title": "Connections",
        "query": "pg_stat_activity_count",
        "unit": "short",
        "type": "stat",
    },
    r"\bredis\b|\bcache\b": {
        "title": "Cache Operations",
        "query": "rate(redis_commands_processed_total[5m])",
        "unit": "ops",
        "type": "timeseries",
    },
    r"\buptime\b|\bavailability\b": {
        "title": "Uptime",
        "query": "up",
        "unit": "short",
        "type": "stat",
    },
    r"\bload\b": {
        "title": "System Load",
        "query": "node_load1",
        "unit": "short",
        "type": "timeseries",
    },
}

GROUP_PATTERNS = {
    r"by\s+(\w+)": lambda m: f"{{{{.{m.group(1)}}}}}",
    r"grouped\s+by\s+(\w+)": lambda m: f"{{{{.{m.group(1)}}}}}",
    r"per\s+(\w+)": lambda m: f"{{{{.{m.group(1)}}}}}",
}


@dataclass
class NLPGenerator:
    """Generate dashboards from natural language descriptions."""

    datasource: Optional[Datasource] = None
    use_openai: bool = True
    use_openrouter: bool = True

    def __post_init__(self):
        self._openai_client = None
        self._openrouter_key = os.environ.get("OPENROUTER_API_KEY")
        self._openrouter_model = os.environ.get("OPENROUTER_MODEL", "openai/gpt-4o-mini")

        if self.use_openai:
            try:
                import openai
                api_key = os.environ.get("OPENAI_API_KEY")
                if api_key:
                    self._openai_client = openai.OpenAI(api_key=api_key)
            except ImportError:
                pass

    def generate(self, prompt: str, datasource: Optional[Union[Datasource, str]] = None) -> Dashboard:
        """Generate a dashboard from a natural language prompt."""
        ds = self._resolve_datasource(datasource)

        # Try OpenRouter first if configured
        if self._openrouter_key and self.use_openrouter:
            try:
                return self._generate_with_openrouter(prompt, ds)
            except Exception:
                pass

        # Then try OpenAI
        if self._openai_client:
            try:
                return self._generate_with_openai(prompt, ds)
            except Exception:
                pass

        return self._generate_with_patterns(prompt, ds)

    def _resolve_datasource(self, datasource: Optional[Union[Datasource, str]]) -> Datasource:
        """Resolve datasource to a Datasource object."""
        if datasource is None:
            return self.datasource or Datasource.prometheus()
        if isinstance(datasource, str):
            return Datasource(name=datasource, type="prometheus")
        return datasource

    def _generate_with_openrouter(self, prompt: str, datasource: Datasource) -> Dashboard:
        """Generate dashboard using OpenRouter API."""
        import urllib.request

        system_prompt = """You are a Grafana dashboard generator. Given a natural language description,
output a JSON object with the following structure:
{
  "title": "Dashboard Title",
  "panels": [
    {
      "title": "Panel Title",
      "query": "PromQL query",
      "type": "timeseries|stat|gauge|table",
      "unit": "percent|bytes|s|ops|reqps|short"
    }
  ]
}

Use appropriate PromQL queries for Prometheus. Only output valid JSON, no explanations."""

        data = json.dumps({
            "model": self._openrouter_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.3,
        }).encode()

        req = urllib.request.Request(
            "https://openrouter.ai/api/v1/chat/completions",
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._openrouter_key}",
                "HTTP-Referer": "https://grafana-toolkit.local",
                "X-Title": "Grafana Dashboard Toolkit",
            },
        )

        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode())

        content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            spec = json.loads(json_match.group())
        else:
            raise ValueError("No JSON found in response")

        return self._build_dashboard_from_spec(spec, datasource)

    def _generate_with_openai(self, prompt: str, datasource: Datasource) -> Dashboard:
        """Generate dashboard using OpenAI API."""
        system_prompt = """You are a Grafana dashboard generator. Given a natural language description,
output a JSON object with the following structure:
{
  "title": "Dashboard Title",
  "panels": [
    {
      "title": "Panel Title",
      "query": "PromQL query",
      "type": "timeseries|stat|gauge|table",
      "unit": "percent|bytes|s|ops|reqps|short"
    }
  ]
}

Use appropriate PromQL queries for Prometheus. Common metrics:
- CPU: node_cpu_seconds_total, container_cpu_usage_seconds_total
- Memory: node_memory_MemAvailable_bytes, container_memory_usage_bytes
- Disk: node_filesystem_avail_bytes
- Network: node_network_receive_bytes_total
- HTTP: http_requests_total, http_request_duration_seconds_bucket
- Pods: kube_pod_status_phase, container_*

Only output valid JSON, no explanations."""

        response = self._openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
        )

        content = response.choices[0].message.content
        # Extract JSON from response
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            spec = json.loads(json_match.group())
        else:
            raise ValueError("No JSON found in response")

        return self._build_dashboard_from_spec(spec, datasource)

    def _generate_with_patterns(self, prompt: str, datasource: Datasource) -> Dashboard:
        """Generate dashboard using pattern matching (fallback)."""
        prompt_lower = prompt.lower()

        # Extract dashboard title
        title_match = re.search(r"(?:create|make|build)?\s*(?:a|an)?\s*dashboard\s+(?:for\s+)?(.+?)(?:\s+showing|\s+with|\s+that|$)", prompt_lower)
        if title_match:
            title = title_match.group(1).strip().title() + " Dashboard"
        else:
            title = "Generated Dashboard"

        dashboard = Dashboard(
            title=title,
            datasource=datasource,
            refresh="30s",
        )

        # Find matching panels
        panels_added = set()
        for pattern, config in METRIC_PATTERNS.items():
            if re.search(pattern, prompt_lower) and config["title"] not in panels_added:
                query = config["query"]

                # Check for grouping
                for group_pattern, replacer in GROUP_PATTERNS.items():
                    match = re.search(group_pattern, prompt_lower)
                    if match:
                        label = match.group(1)
                        if "by(" not in query:
                            query = f"sum by({label}) ({query})"
                        break

                dashboard.add_panel(
                    config["title"],
                    query=query,
                    panel_type=config["type"],
                    unit=config["unit"],
                )
                panels_added.add(config["title"])

        # If no patterns matched, add some defaults based on common keywords
        if not panels_added:
            if "server" in prompt_lower or "node" in prompt_lower:
                for metric in ["cpu", "memory", "disk"]:
                    config = METRIC_PATTERNS[rf"\b{metric}\b"]
                    dashboard.add_panel(
                        config["title"],
                        query=config["query"],
                        panel_type=config["type"],
                        unit=config["unit"],
                    )
            elif "web" in prompt_lower or "api" in prompt_lower:
                for pattern in [r"\bhttp\b.*\brequest", r"\blatency\b|\bresponse.?time\b|\bduration\b", r"\berror\b|\bfailure\b|\bfail\b"]:
                    config = METRIC_PATTERNS[pattern]
                    dashboard.add_panel(
                        config["title"],
                        query=config["query"],
                        panel_type=config["type"],
                        unit=config["unit"],
                    )
            else:
                # Absolute fallback
                dashboard.add_panel(
                    "System Overview",
                    query="up",
                    panel_type="stat",
                )

        return dashboard

    def _build_dashboard_from_spec(self, spec: dict[str, Any], datasource: Datasource) -> Dashboard:
        """Build a Dashboard from a parsed specification."""
        dashboard = Dashboard(
            title=spec.get("title", "Generated Dashboard"),
            datasource=datasource,
            refresh="30s",
        )

        for panel_spec in spec.get("panels", []):
            dashboard.add_panel(
                panel_spec.get("title", "Panel"),
                query=panel_spec.get("query", "up"),
                panel_type=panel_spec.get("type", "timeseries"),
                unit=panel_spec.get("unit", "short"),
            )

        return dashboard


def generate_from_text(
    prompt: str,
    datasource: Optional[Union[Datasource, str]] = None,
    use_openai: bool = True,
) -> Dashboard:
    """Generate a dashboard from a natural language description.

    Args:
        prompt: Natural language description of the desired dashboard.
        datasource: Datasource to use (name string or Datasource object).
        use_openai: Whether to try OpenAI API first (requires OPENAI_API_KEY env var).

    Returns:
        A Dashboard object ready to be saved or exported.

    Examples:
        >>> dashboard = generate_from_text("Create a dashboard showing CPU and memory usage")
        >>> dashboard = generate_from_text("Dashboard for HTTP request latency p99 grouped by service")
    """
    generator = NLPGenerator(use_openai=use_openai)
    return generator.generate(prompt, datasource)
