"""Built-in dashboard templates."""

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
)

__all__ = [
    "node_exporter",
    "web_server",
    "docker",
    "kubernetes",
    "database",
    # ISP / Network
    "isp_bgp",
    "isp_traffic",
    "network_cisco",
    "network_juniper",
    "network_paloalto",
    "network_fortinet",
    # Multi-Cloud
    "cloud_aws",
    "cloud_gcp",
    "cloud_azure",
]
