"""Template library for common dashboard patterns."""

from ads_grafana_toolkit.template_library.registry import (
    get_template,
    list_templates,
    create_from_template,
    register_template,
)
from ads_grafana_toolkit.template_library.base import DashboardTemplate

__all__ = [
    "get_template",
    "list_templates",
    "create_from_template",
    "register_template",
    "DashboardTemplate",
]
