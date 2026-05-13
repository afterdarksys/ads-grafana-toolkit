"""Extract PromQL expressions from dashboard templates and emit Prometheus recording rules.

Recording rules pre-compute expensive PromQL queries so dashboards load instantly.
Each extracted expression becomes a rule named `recording:<template>:<panel_slug>`.

Only PromQL expressions are extracted — CloudWatch/GCP/Azure metric JSON blobs
and raw metric names (no operators) are skipped automatically.

Usage:
    from ads_grafana_toolkit.recording_rules import generate_recording_rules_yaml
    yaml_str = generate_recording_rules_yaml()                 # all templates
    yaml_str = generate_recording_rules_yaml(template="isp-bgp")  # one template
"""
from __future__ import annotations

import json
import re
from typing import Any

import yaml

# PromQL heuristic: expression contains a function call or operator that
# signals it's actual PromQL rather than a metric blob or bare name.
_PROMQL_HINTS = re.compile(
    r"\b(rate|irate|increase|sum|avg|min|max|count|histogram_quantile|"
    r"delta|predict_linear|label_replace|topk|bottomk|absent|vector|"
    r"round|ceil|floor|scalar|sort|sort_desc|clamp|time)\s*\("
    r"|[{}]"          # label selectors
    r"|\[[\d]+[smhdwy]\]"  # range vector selector
    r"|by\s*\("
    r"|without\s*\("
    r"|on\s*\("
    r"|group_left|group_right"
    r"|\bunless\b|\band\b|\bor\b"
)

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _slugify(text: str) -> str:
    return _SLUG_RE.sub("_", text.lower()).strip("_")


def _is_promql(expr: str) -> bool:
    """Return True if the string looks like a PromQL expression."""
    expr = expr.strip()
    if not expr or expr.startswith("{") and "metricName" in expr:
        return False
    try:
        json.loads(expr)
        return False  # It's a JSON blob (CloudWatch / GCP / Azure)
    except (json.JSONDecodeError, ValueError):
        pass
    return bool(_PROMQL_HINTS.search(expr))


def _extract_queries_from_panel(panel: Any) -> list[str]:
    """Pull PromQL expressions from a Panel object or dict."""
    exprs: list[str] = []

    # Panel objects store queries in .targets (list of Target objects)
    targets = getattr(panel, "targets", None)
    if targets:
        for t in targets:
            expr = getattr(t, "expr", None) or ""
            if isinstance(expr, str) and _is_promql(expr):
                exprs.append(expr)
        return exprs

    # Fallback: dict representation (e.g. from to_dict())
    if isinstance(panel, dict):
        for t in panel.get("targets", []):
            expr = t.get("expr") or t.get("query") or ""
            if isinstance(expr, str) and _is_promql(expr):
                exprs.append(expr)

    return exprs


def recording_rules_for_template(template_name: str) -> list[dict[str, str]]:
    """Return a list of {record, expr} dicts for a single template.

    Creates a throwaway dashboard using a fake datasource so we can inspect
    the panel structure without touching any real Grafana instance.
    """
    from ads_grafana_toolkit.template_library.registry import get_template

    template = get_template(template_name)

    # Instantiate with a placeholder datasource string — templates accept str.
    try:
        dashboard = template.create("prometheus")
    except Exception:
        return []

    rules: list[dict[str, str]] = []
    seen: set[str] = set()
    name_slug = _slugify(template_name)

    for panel in dashboard.panels:
        title = getattr(panel, "title", "") or ""
        title_slug = _slugify(title) if title else f"panel_{len(rules)}"
        exprs = _extract_queries_from_panel(panel)
        for i, expr in enumerate(exprs):
            if expr in seen:
                continue
            seen.add(expr)
            suffix = f"_{i}" if i > 0 else ""
            record = f"recording:{name_slug}:{title_slug}{suffix}"
            # Truncate to Prometheus 256-char limit on metric names
            record = record[:256]
            rules.append({"record": record, "expr": expr})

    return rules


def generate_recording_rules_yaml(template: str | None = None) -> str:
    """Generate Prometheus recording rules YAML.

    Args:
        template: If given, only generate rules for this template name.
                  If None, generate for all registered templates.

    Returns:
        YAML string ready to write to a `recording_rules.yml` file.
    """
    from ads_grafana_toolkit.template_library.registry import list_templates

    if template:
        names = [template]
    else:
        names = [t["name"] for t in list_templates()]

    groups = []
    for name in names:
        rules = recording_rules_for_template(name)
        if rules:
            groups.append({"name": f"recording_{_slugify(name)}", "rules": rules})

    doc = {"groups": groups}
    return yaml.dump(doc, default_flow_style=False, sort_keys=False, allow_unicode=True)
