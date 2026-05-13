"""Template registry for managing dashboard templates."""

from __future__ import annotations

from typing import Any, Union

from ads_grafana_toolkit.sdk.dashboard import Dashboard
from ads_grafana_toolkit.sdk.datasource import Datasource
from ads_grafana_toolkit.template_library.base import DashboardTemplate

_templates: dict[str, DashboardTemplate] = {}


def register_template(template: DashboardTemplate) -> None:
    """Register a template in the global registry."""
    _templates[template.name] = template


def get_template(name: str) -> DashboardTemplate:
    """Get a template by name."""
    if name not in _templates:
        available = ", ".join(_templates.keys())
        raise KeyError(f"Template '{name}' not found. Available: {available}")
    return _templates[name]


def list_templates(category: str | None = None) -> list[dict[str, Any]]:
    """List all available templates."""
    templates = []
    for template in _templates.values():
        if category and template.category != category:
            continue
        templates.append({
            "name": template.name,
            "description": template.description,
            "category": template.category,
            "tags": template.tags,
            "variables": [
                {
                    "name": v.name,
                    "description": v.description,
                    "default": v.default,
                    "required": v.required,
                }
                for v in template.variables
            ],
        })
    return templates


def create_from_template(
    name: str,
    datasource: Union[Datasource, str],
    **kwargs,
) -> Dashboard:
    """Create a dashboard from a template."""
    template = get_template(name)
    return template.create(datasource, **kwargs)


def _register_builtin_templates():
    """Register all built-in templates."""
    from ads_grafana_toolkit.template_library.templates import (
        node_exporter,
        web_server,
        docker,
        kubernetes,
        database,
        # ISP / Network
        isp_bgp,
        isp_traffic,
        network_cisco,
        network_juniper,
        network_paloalto,
        network_fortinet,
        # Multi-Cloud
        cloud_aws,
        cloud_gcp,
        cloud_azure,
        cloud_cost,
        cloud_connectivity,
    )


_register_builtin_templates()
