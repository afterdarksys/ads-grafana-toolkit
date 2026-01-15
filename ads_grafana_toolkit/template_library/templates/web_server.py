"""Web server dashboard templates for HTTP metrics."""

from __future__ import annotations

from typing import Union

from ads_grafana_toolkit.sdk.dashboard import Dashboard
from ads_grafana_toolkit.sdk.datasource import Datasource
from ads_grafana_toolkit.template_library.base import DashboardTemplate, TemplateVariable
from ads_grafana_toolkit.template_library.registry import register_template


class NginxTemplate(DashboardTemplate):
    """Dashboard template for Nginx metrics."""

    def __init__(self):
        super().__init__(
            name="nginx",
            description="Nginx web server monitoring (requests, connections, response times)",
            category="web-server",
            tags=["nginx", "web", "http"],
            variables=[
                TemplateVariable(
                    name="instance",
                    description="Nginx instance",
                    default="localhost:9113",
                ),
            ],
        )

    def create(self, datasource: Union[Datasource, str], **kwargs) -> Dashboard:
        ds = self._resolve_datasource(datasource)
        instance = kwargs.get("instance", "$instance")
        job = kwargs.get("job", "nginx")

        dashboard = Dashboard(
            title=kwargs.get("title", "Nginx Dashboard"),
            description="Nginx web server metrics",
            tags=["nginx", "web-server"],
            datasource=ds,
            refresh="30s",
        )

        dashboard.add_variable(
            "instance",
            query=f'label_values(nginx_up, instance)',
            label="Instance",
        )

        dashboard.add_row("Overview")

        dashboard.add_panel(
            "Nginx Up",
            query=f'nginx_up{{instance=~"{instance}"}}',
            panel_type="stat",
            width=4,
            height=4,
        ).add_threshold(None, "red").add_threshold(1, "green")

        dashboard.add_panel(
            "Active Connections",
            query=f'nginx_connections_active{{instance=~"{instance}"}}',
            panel_type="stat",
            width=4,
            height=4,
        )

        dashboard.add_panel(
            "Total Requests",
            query=f'nginx_http_requests_total{{instance=~"{instance}"}}',
            panel_type="stat",
            width=4,
            height=4,
        )

        dashboard.add_panel(
            "Requests/sec",
            query=f'rate(nginx_http_requests_total{{instance=~"{instance}"}}[5m])',
            panel_type="stat",
            width=4,
            height=4,
            unit="reqps",
        )

        dashboard.add_panel(
            "Reading Connections",
            query=f'nginx_connections_reading{{instance=~"{instance}"}}',
            panel_type="stat",
            width=4,
            height=4,
        )

        dashboard.add_panel(
            "Writing Connections",
            query=f'nginx_connections_writing{{instance=~"{instance}"}}',
            panel_type="stat",
            width=4,
            height=4,
        )

        dashboard.add_row("Connections")

        dashboard.add_panel(
            "Connection States",
            panel_type="timeseries",
            width=12,
            height=8,
        ).add_query(
            f'nginx_connections_active{{instance=~"{instance}"}}',
            legend="Active"
        ).add_query(
            f'nginx_connections_reading{{instance=~"{instance}"}}',
            legend="Reading"
        ).add_query(
            f'nginx_connections_writing{{instance=~"{instance}"}}',
            legend="Writing"
        ).add_query(
            f'nginx_connections_waiting{{instance=~"{instance}"}}',
            legend="Waiting"
        )

        dashboard.add_panel(
            "Connections Accepted/Handled",
            panel_type="timeseries",
            width=12,
            height=8,
        ).add_query(
            f'rate(nginx_connections_accepted{{instance=~"{instance}"}}[5m])',
            legend="Accepted"
        ).add_query(
            f'rate(nginx_connections_handled{{instance=~"{instance}"}}[5m])',
            legend="Handled"
        )

        dashboard.add_row("Requests")

        dashboard.add_panel(
            "Request Rate",
            query=f'rate(nginx_http_requests_total{{instance=~"{instance}"}}[5m])',
            panel_type="timeseries",
            width=24,
            height=8,
            unit="reqps",
        )

        return dashboard


class ApacheTemplate(DashboardTemplate):
    """Dashboard template for Apache HTTP Server metrics."""

    def __init__(self):
        super().__init__(
            name="apache",
            description="Apache HTTP Server monitoring",
            category="web-server",
            tags=["apache", "httpd", "web", "http"],
        )

    def create(self, datasource: Union[Datasource, str], **kwargs) -> Dashboard:
        ds = self._resolve_datasource(datasource)
        instance = kwargs.get("instance", "$instance")
        job = kwargs.get("job", "apache")

        dashboard = Dashboard(
            title=kwargs.get("title", "Apache Dashboard"),
            description="Apache HTTP Server metrics",
            tags=["apache", "web-server"],
            datasource=ds,
            refresh="30s",
        )

        dashboard.add_variable(
            "instance",
            query='label_values(apache_up, instance)',
            label="Instance",
        )

        dashboard.add_row("Overview")

        dashboard.add_panel(
            "Apache Up",
            query=f'apache_up{{instance=~"{instance}"}}',
            panel_type="stat",
            width=4,
            height=4,
        ).add_threshold(None, "red").add_threshold(1, "green")

        dashboard.add_panel(
            "Current Workers",
            query=f'apache_workers{{instance=~"{instance}",state="busy"}}',
            panel_type="stat",
            width=4,
            height=4,
        )

        dashboard.add_panel(
            "Requests/sec",
            query=f'rate(apache_accesses_total{{instance=~"{instance}"}}[5m])',
            panel_type="stat",
            width=4,
            height=4,
            unit="reqps",
        )

        dashboard.add_panel(
            "Total Bytes Sent",
            query=f'rate(apache_sent_kilobytes_total{{instance=~"{instance}"}}[5m]) * 1024',
            panel_type="stat",
            width=4,
            height=4,
            unit="Bps",
        )

        dashboard.add_panel(
            "Uptime",
            query=f'apache_uptime_seconds_total{{instance=~"{instance}"}}',
            panel_type="stat",
            width=4,
            height=4,
            unit="s",
        )

        dashboard.add_panel(
            "Total Requests",
            query=f'apache_accesses_total{{instance=~"{instance}"}}',
            panel_type="stat",
            width=4,
            height=4,
        )

        dashboard.add_row("Workers")

        dashboard.add_panel(
            "Worker States",
            panel_type="timeseries",
            width=12,
            height=8,
        ).add_query(
            f'apache_workers{{instance=~"{instance}",state="busy"}}',
            legend="Busy"
        ).add_query(
            f'apache_workers{{instance=~"{instance}",state="idle"}}',
            legend="Idle"
        )

        dashboard.add_panel(
            "Scoreboard",
            panel_type="timeseries",
            width=12,
            height=8,
        ).add_query(
            f'apache_scoreboard{{instance=~"{instance}"}}',
            legend="{{state}}"
        )

        dashboard.add_row("Traffic")

        dashboard.add_panel(
            "Request Rate",
            query=f'rate(apache_accesses_total{{instance=~"{instance}"}}[5m])',
            panel_type="timeseries",
            width=12,
            height=8,
            unit="reqps",
        )

        dashboard.add_panel(
            "Bytes Sent",
            query=f'rate(apache_sent_kilobytes_total{{instance=~"{instance}"}}[5m]) * 1024',
            panel_type="timeseries",
            width=12,
            height=8,
            unit="Bps",
        )

        return dashboard


class HTTPBlackboxTemplate(DashboardTemplate):
    """Dashboard template for HTTP endpoint monitoring via Blackbox Exporter."""

    def __init__(self):
        super().__init__(
            name="http-endpoints",
            description="HTTP endpoint monitoring (uptime, latency, SSL) via Blackbox Exporter",
            category="web-server",
            tags=["http", "blackbox", "uptime", "ssl"],
        )

    def create(self, datasource: Union[Datasource, str], **kwargs) -> Dashboard:
        ds = self._resolve_datasource(datasource)
        job = kwargs.get("job", "blackbox")

        dashboard = Dashboard(
            title=kwargs.get("title", "HTTP Endpoints Dashboard"),
            description="HTTP endpoint monitoring via Blackbox Exporter",
            tags=["http", "blackbox", "endpoints"],
            datasource=ds,
            refresh="30s",
        )

        dashboard.add_variable(
            "target",
            query=f'label_values(probe_success{{job="{job}"}}, instance)',
            label="Target",
            multi=True,
            include_all=True,
        )

        dashboard.add_row("Overview")

        dashboard.add_panel(
            "Endpoint Status",
            query=f'probe_success{{job="{job}",instance=~"$target"}}',
            panel_type="stat",
            width=6,
            height=4,
        ).add_threshold(None, "red").add_threshold(1, "green")

        dashboard.add_panel(
            "HTTP Duration",
            query=f'probe_http_duration_seconds{{job="{job}",instance=~"$target"}}',
            panel_type="stat",
            width=6,
            height=4,
            unit="s",
        )

        dashboard.add_panel(
            "SSL Expiry",
            query=f'probe_ssl_earliest_cert_expiry{{job="{job}",instance=~"$target"}} - time()',
            panel_type="stat",
            width=6,
            height=4,
            unit="s",
        ).add_threshold(None, "red").add_threshold(604800, "yellow").add_threshold(2592000, "green")

        dashboard.add_panel(
            "HTTP Status Code",
            query=f'probe_http_status_code{{job="{job}",instance=~"$target"}}',
            panel_type="stat",
            width=6,
            height=4,
        )

        dashboard.add_row("Latency")

        dashboard.add_panel(
            "HTTP Response Time",
            query=f'probe_http_duration_seconds{{job="{job}",instance=~"$target"}}',
            panel_type="timeseries",
            width=24,
            height=8,
            unit="s",
        )

        dashboard.add_row("Status History")

        dashboard.add_panel(
            "Probe Success",
            query=f'probe_success{{job="{job}",instance=~"$target"}}',
            panel_type="timeseries",
            width=24,
            height=8,
        )

        return dashboard


register_template(NginxTemplate())
register_template(ApacheTemplate())
register_template(HTTPBlackboxTemplate())
