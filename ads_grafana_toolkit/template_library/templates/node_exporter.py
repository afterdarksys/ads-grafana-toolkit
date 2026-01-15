"""Node Exporter dashboard template for basic server metrics."""

from __future__ import annotations

from typing import Union

from ads_grafana_toolkit.sdk.dashboard import Dashboard
from ads_grafana_toolkit.sdk.datasource import Datasource
from ads_grafana_toolkit.template_library.base import DashboardTemplate, TemplateVariable
from ads_grafana_toolkit.template_library.registry import register_template


class NodeExporterTemplate(DashboardTemplate):
    """Dashboard template for Node Exporter metrics."""

    def __init__(self):
        super().__init__(
            name="node-exporter",
            description="Basic server monitoring with Node Exporter (CPU, Memory, Disk, Network)",
            category="infrastructure",
            tags=["node-exporter", "linux", "server", "infrastructure"],
            variables=[
                TemplateVariable(
                    name="instance",
                    description="Target instance to monitor",
                    default="localhost:9100",
                ),
                TemplateVariable(
                    name="job",
                    description="Prometheus job name",
                    default="node",
                ),
            ],
        )

    def create(self, datasource: Union[Datasource, str], **kwargs) -> Dashboard:
        ds = self._resolve_datasource(datasource)
        instance = kwargs.get("instance", "$instance")
        job = kwargs.get("job", "$job")

        dashboard = Dashboard(
            title=kwargs.get("title", "Node Exporter Dashboard"),
            description="Server metrics from Node Exporter",
            tags=["node-exporter", "infrastructure"],
            datasource=ds,
            refresh="30s",
        )

        dashboard.add_variable(
            "job",
            query='label_values(node_uname_info, job)',
            label="Job",
        )
        dashboard.add_variable(
            "instance",
            query=f'label_values(node_uname_info{{job="$job"}}, instance)',
            label="Instance",
        )

        dashboard.add_row("Overview")

        dashboard.add_panel(
            "CPU Usage",
            query=f'100 - (avg by(instance) (irate(node_cpu_seconds_total{{job="{job}",instance=~"{instance}",mode="idle"}}[5m])) * 100)',
            panel_type="gauge",
            width=6,
            height=6,
            unit="percent",
        ).add_threshold(None, "green").add_threshold(70, "yellow").add_threshold(90, "red")

        dashboard.add_panel(
            "Memory Usage",
            query=f'100 * (1 - ((node_memory_MemAvailable_bytes{{job="{job}",instance=~"{instance}"}} or node_memory_MemFree_bytes{{job="{job}",instance=~"{instance}"}}) / node_memory_MemTotal_bytes{{job="{job}",instance=~"{instance}"}}))',
            panel_type="gauge",
            width=6,
            height=6,
            unit="percent",
        ).add_threshold(None, "green").add_threshold(70, "yellow").add_threshold(90, "red")

        dashboard.add_panel(
            "Disk Usage",
            query=f'100 - ((node_filesystem_avail_bytes{{job="{job}",instance=~"{instance}",fstype!="tmpfs"}} / node_filesystem_size_bytes{{job="{job}",instance=~"{instance}",fstype!="tmpfs"}}) * 100)',
            panel_type="gauge",
            width=6,
            height=6,
            unit="percent",
        ).add_threshold(None, "green").add_threshold(70, "yellow").add_threshold(90, "red")

        dashboard.add_panel(
            "Uptime",
            query=f'time() - node_boot_time_seconds{{job="{job}",instance=~"{instance}"}}',
            panel_type="stat",
            width=6,
            height=6,
            unit="s",
        )

        dashboard.add_row("CPU")

        dashboard.add_panel(
            "CPU Usage by Mode",
            query=f'sum by(mode) (irate(node_cpu_seconds_total{{job="{job}",instance=~"{instance}"}}[5m])) * 100',
            panel_type="timeseries",
            width=12,
            height=8,
            unit="percent",
        )

        dashboard.add_panel(
            "CPU Load Average",
            panel_type="timeseries",
            width=12,
            height=8,
        ).add_query(
            f'node_load1{{job="{job}",instance=~"{instance}"}}',
            legend="1m"
        ).add_query(
            f'node_load5{{job="{job}",instance=~"{instance}"}}',
            legend="5m"
        ).add_query(
            f'node_load15{{job="{job}",instance=~"{instance}"}}',
            legend="15m"
        )

        dashboard.add_row("Memory")

        dashboard.add_panel(
            "Memory Usage",
            panel_type="timeseries",
            width=12,
            height=8,
            unit="bytes",
        ).add_query(
            f'node_memory_MemTotal_bytes{{job="{job}",instance=~"{instance}"}}',
            legend="Total"
        ).add_query(
            f'node_memory_MemTotal_bytes{{job="{job}",instance=~"{instance}"}} - node_memory_MemAvailable_bytes{{job="{job}",instance=~"{instance}"}}',
            legend="Used"
        ).add_query(
            f'node_memory_Cached_bytes{{job="{job}",instance=~"{instance}"}}',
            legend="Cached"
        ).add_query(
            f'node_memory_Buffers_bytes{{job="{job}",instance=~"{instance}"}}',
            legend="Buffers"
        )

        dashboard.add_panel(
            "Swap Usage",
            panel_type="timeseries",
            width=12,
            height=8,
            unit="bytes",
        ).add_query(
            f'node_memory_SwapTotal_bytes{{job="{job}",instance=~"{instance}"}}',
            legend="Total"
        ).add_query(
            f'node_memory_SwapTotal_bytes{{job="{job}",instance=~"{instance}"}} - node_memory_SwapFree_bytes{{job="{job}",instance=~"{instance}"}}',
            legend="Used"
        )

        dashboard.add_row("Disk")

        dashboard.add_panel(
            "Disk Space Usage",
            query=f'100 - ((node_filesystem_avail_bytes{{job="{job}",instance=~"{instance}",fstype!="tmpfs"}} / node_filesystem_size_bytes{{job="{job}",instance=~"{instance}",fstype!="tmpfs"}}) * 100)',
            panel_type="timeseries",
            width=12,
            height=8,
            unit="percent",
        )

        dashboard.add_panel(
            "Disk I/O",
            panel_type="timeseries",
            width=12,
            height=8,
            unit="Bps",
        ).add_query(
            f'rate(node_disk_read_bytes_total{{job="{job}",instance=~"{instance}"}}[5m])',
            legend="Read {{device}}"
        ).add_query(
            f'rate(node_disk_written_bytes_total{{job="{job}",instance=~"{instance}"}}[5m])',
            legend="Write {{device}}"
        )

        dashboard.add_row("Network")

        dashboard.add_panel(
            "Network Traffic",
            panel_type="timeseries",
            width=12,
            height=8,
            unit="bps",
        ).add_query(
            f'rate(node_network_receive_bytes_total{{job="{job}",instance=~"{instance}",device!~"lo|veth.*|docker.*|br-.*"}}[5m]) * 8',
            legend="Receive {{device}}"
        ).add_query(
            f'rate(node_network_transmit_bytes_total{{job="{job}",instance=~"{instance}",device!~"lo|veth.*|docker.*|br-.*"}}[5m]) * 8',
            legend="Transmit {{device}}"
        )

        dashboard.add_panel(
            "Network Errors",
            panel_type="timeseries",
            width=12,
            height=8,
        ).add_query(
            f'rate(node_network_receive_errs_total{{job="{job}",instance=~"{instance}"}}[5m])',
            legend="Receive Errors {{device}}"
        ).add_query(
            f'rate(node_network_transmit_errs_total{{job="{job}",instance=~"{instance}"}}[5m])',
            legend="Transmit Errors {{device}}"
        )

        return dashboard


register_template(NodeExporterTemplate())
