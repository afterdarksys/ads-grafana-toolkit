"""Docker dashboard template."""

from __future__ import annotations

from typing import Union

from ads_grafana_toolkit.sdk.dashboard import Dashboard
from ads_grafana_toolkit.sdk.datasource import Datasource
from ads_grafana_toolkit.template_library.base import DashboardTemplate, TemplateVariable
from ads_grafana_toolkit.template_library.registry import register_template


class DockerTemplate(DashboardTemplate):
    """Dashboard template for Docker container metrics via cAdvisor."""

    def __init__(self):
        super().__init__(
            name="docker",
            description="Docker container monitoring (CPU, Memory, Network, I/O) via cAdvisor",
            category="containers",
            tags=["docker", "containers", "cadvisor"],
            variables=[
                TemplateVariable(
                    name="container",
                    description="Container name filter",
                    default=".*",
                ),
            ],
        )

    def create(self, datasource: Union[Datasource, str], **kwargs) -> Dashboard:
        ds = self._resolve_datasource(datasource)
        container = kwargs.get("container", "$container")

        dashboard = Dashboard(
            title=kwargs.get("title", "Docker Containers Dashboard"),
            description="Docker container metrics via cAdvisor",
            tags=["docker", "containers"],
            datasource=ds,
            refresh="30s",
        )

        dashboard.add_variable(
            "container",
            query='label_values(container_last_seen{name!=""}, name)',
            label="Container",
            multi=True,
            include_all=True,
        )

        dashboard.add_row("Overview")

        dashboard.add_panel(
            "Running Containers",
            query='count(container_last_seen{name!=""})',
            panel_type="stat",
            width=6,
            height=4,
        )

        dashboard.add_panel(
            "Total CPU Usage",
            query='sum(rate(container_cpu_usage_seconds_total{name!=""}[5m])) * 100',
            panel_type="stat",
            width=6,
            height=4,
            unit="percent",
        )

        dashboard.add_panel(
            "Total Memory Usage",
            query='sum(container_memory_usage_bytes{name!=""})',
            panel_type="stat",
            width=6,
            height=4,
            unit="bytes",
        )

        dashboard.add_panel(
            "Total Network I/O",
            query='sum(rate(container_network_receive_bytes_total{name!=""}[5m])) + sum(rate(container_network_transmit_bytes_total{name!=""}[5m]))',
            panel_type="stat",
            width=6,
            height=4,
            unit="Bps",
        )

        dashboard.add_row("CPU")

        dashboard.add_panel(
            "Container CPU Usage",
            query=f'rate(container_cpu_usage_seconds_total{{name=~"{container}"}}[5m]) * 100',
            panel_type="timeseries",
            width=12,
            height=8,
            unit="percent",
        )

        dashboard.add_panel(
            "CPU Throttling",
            query=f'rate(container_cpu_cfs_throttled_seconds_total{{name=~"{container}"}}[5m])',
            panel_type="timeseries",
            width=12,
            height=8,
            unit="s",
        )

        dashboard.add_row("Memory")

        dashboard.add_panel(
            "Container Memory Usage",
            query=f'container_memory_usage_bytes{{name=~"{container}"}}',
            panel_type="timeseries",
            width=12,
            height=8,
            unit="bytes",
        )

        dashboard.add_panel(
            "Memory Usage %",
            query=f'container_memory_usage_bytes{{name=~"{container}"}} / container_spec_memory_limit_bytes{{name=~"{container}"}} * 100',
            panel_type="timeseries",
            width=12,
            height=8,
            unit="percent",
        )

        dashboard.add_row("Network")

        dashboard.add_panel(
            "Network Receive",
            query=f'rate(container_network_receive_bytes_total{{name=~"{container}"}}[5m])',
            panel_type="timeseries",
            width=12,
            height=8,
            unit="Bps",
        )

        dashboard.add_panel(
            "Network Transmit",
            query=f'rate(container_network_transmit_bytes_total{{name=~"{container}"}}[5m])',
            panel_type="timeseries",
            width=12,
            height=8,
            unit="Bps",
        )

        dashboard.add_row("Disk I/O")

        dashboard.add_panel(
            "Disk Read",
            query=f'rate(container_fs_reads_bytes_total{{name=~"{container}"}}[5m])',
            panel_type="timeseries",
            width=12,
            height=8,
            unit="Bps",
        )

        dashboard.add_panel(
            "Disk Write",
            query=f'rate(container_fs_writes_bytes_total{{name=~"{container}"}}[5m])',
            panel_type="timeseries",
            width=12,
            height=8,
            unit="Bps",
        )

        return dashboard


register_template(DockerTemplate())
