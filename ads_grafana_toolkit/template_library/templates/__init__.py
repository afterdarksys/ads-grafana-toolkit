"""Built-in dashboard templates."""

from ads_grafana_toolkit.template_library.templates import (
    node_exporter,
    web_server,
    docker,
    kubernetes,
    database,
)

__all__ = [
    "node_exporter",
    "web_server",
    "docker",
    "kubernetes",
    "database",
]
