"""Interactive CLI wizard for dashboard creation."""

from __future__ import annotations

import questionary
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ads_grafana_toolkit.sdk.dashboard import Dashboard
from ads_grafana_toolkit.sdk.datasource import Datasource
from ads_grafana_toolkit.sdk.panel import TimeSeriesPanel, StatPanel, GaugePanel

console = Console()


COMMON_METRICS = {
    "CPU Usage": {
        "query": '100 - (avg(irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)',
        "unit": "percent",
        "type": "gauge",
    },
    "Memory Usage": {
        "query": "100 * (1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes))",
        "unit": "percent",
        "type": "gauge",
    },
    "Disk Usage": {
        "query": '100 - ((node_filesystem_avail_bytes{fstype!="tmpfs"} / node_filesystem_size_bytes{fstype!="tmpfs"}) * 100)',
        "unit": "percent",
        "type": "timeseries",
    },
    "Network Traffic (Receive)": {
        "query": 'rate(node_network_receive_bytes_total{device!~"lo|veth.*"}[5m]) * 8',
        "unit": "bps",
        "type": "timeseries",
    },
    "Network Traffic (Transmit)": {
        "query": 'rate(node_network_transmit_bytes_total{device!~"lo|veth.*"}[5m]) * 8',
        "unit": "bps",
        "type": "timeseries",
    },
    "HTTP Requests/sec": {
        "query": "rate(http_requests_total[5m])",
        "unit": "reqps",
        "type": "timeseries",
    },
    "HTTP Request Latency": {
        "query": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))",
        "unit": "s",
        "type": "timeseries",
    },
    "Container CPU": {
        "query": 'rate(container_cpu_usage_seconds_total{name!=""}[5m]) * 100',
        "unit": "percent",
        "type": "timeseries",
    },
    "Container Memory": {
        "query": 'container_memory_usage_bytes{name!=""}',
        "unit": "bytes",
        "type": "timeseries",
    },
    "Database Connections": {
        "query": "pg_stat_activity_count",
        "unit": "short",
        "type": "stat",
    },
    "Database Query Rate": {
        "query": "rate(pg_stat_database_xact_commit[5m])",
        "unit": "ops",
        "type": "timeseries",
    },
    "Redis Commands/sec": {
        "query": "rate(redis_commands_processed_total[5m])",
        "unit": "ops",
        "type": "timeseries",
    },
    "Custom Query": {
        "query": "",
        "unit": "short",
        "type": "timeseries",
    },
}

DATASOURCE_TYPES = [
    "Prometheus",
    "Graphite",
    "InfluxDB",
    "MySQL",
    "PostgreSQL",
    "Elasticsearch",
    "Loki",
    "CloudWatch",
]


def run_wizard() -> Dashboard | None:
    """Run the interactive dashboard creation wizard."""
    console.print(Panel.fit(
        "[bold blue]Dashboard Creation Wizard[/bold blue]\n"
        "Answer the following questions to create your dashboard.",
        border_style="blue"
    ))

    # Dashboard name
    name = questionary.text(
        "What would you like to name your dashboard?",
        default="My Dashboard",
    ).ask()

    if not name:
        return None

    # Datasource
    ds_type = questionary.select(
        "What datasource will you use?",
        choices=DATASOURCE_TYPES,
        default="Prometheus",
    ).ask()

    if not ds_type:
        return None

    ds_name = questionary.text(
        "What is the datasource name/UID in Grafana?",
        default=ds_type,
    ).ask()

    if not ds_name:
        return None

    datasource = Datasource(name=ds_name, type=ds_type.lower())

    # Create dashboard
    dashboard = Dashboard(
        title=name,
        datasource=datasource,
        refresh="30s",
    )

    # Add panels
    console.print("\n[bold]Now let's add some panels to your dashboard.[/bold]")
    console.print("You can add multiple panels. Select 'Done adding panels' when finished.\n")

    while True:
        metric_choices = list(COMMON_METRICS.keys()) + ["Done adding panels"]

        metric = questionary.select(
            "What would you like to monitor?",
            choices=metric_choices,
        ).ask()

        if not metric or metric == "Done adding panels":
            break

        metric_config = COMMON_METRICS[metric]

        if metric == "Custom Query":
            query = questionary.text(
                "Enter your PromQL/query:",
            ).ask()
            if not query:
                continue

            panel_title = questionary.text(
                "Panel title:",
                default="Custom Panel",
            ).ask()

            panel_type = questionary.select(
                "Panel type:",
                choices=["timeseries", "stat", "gauge", "table"],
                default="timeseries",
            ).ask()
        else:
            query = metric_config["query"]
            panel_title = metric
            panel_type = metric_config["type"]

        # Panel customization
        customize = questionary.confirm(
            "Would you like to customize this panel?",
            default=False,
        ).ask()

        width = 12
        height = 8

        if customize:
            width = int(questionary.text(
                "Panel width (1-24):",
                default="12",
            ).ask() or "12")

            height = int(questionary.text(
                "Panel height:",
                default="8",
            ).ask() or "8")

            if panel_type in ("gauge", "stat"):
                add_thresholds = questionary.confirm(
                    "Add threshold colors?",
                    default=True,
                ).ask()

                if add_thresholds:
                    panel = dashboard.add_panel(
                        panel_title,
                        query=query,
                        panel_type=panel_type,
                        width=width,
                        height=height,
                        unit=metric_config.get("unit", "short"),
                    )
                    panel.add_threshold(None, "green")
                    panel.add_threshold(70, "yellow")
                    panel.add_threshold(90, "red")
                    continue

        dashboard.add_panel(
            panel_title,
            query=query,
            panel_type=panel_type,
            width=width,
            height=height,
            unit=metric_config.get("unit", "short"),
        )

        console.print(f"[green]✓[/green] Added panel: {panel_title}")

    if not dashboard.panels:
        console.print("[yellow]No panels added. Adding a default CPU panel.[/yellow]")
        dashboard.add_panel(
            "CPU Usage",
            query=COMMON_METRICS["CPU Usage"]["query"],
            panel_type="gauge",
            unit="percent",
        )

    # Variables
    add_vars = questionary.confirm(
        "Would you like to add template variables?",
        default=False,
    ).ask()

    if add_vars:
        while True:
            var_name = questionary.text(
                "Variable name (or leave empty to finish):",
            ).ask()

            if not var_name:
                break

            var_query = questionary.text(
                f"Query for {var_name} (e.g., label_values(metric, label)):",
            ).ask()

            if var_query:
                dashboard.add_variable(
                    name=var_name,
                    query=var_query,
                    label=var_name.title(),
                )
                console.print(f"[green]✓[/green] Added variable: ${var_name}")

    # Summary
    console.print("\n")
    table = Table(title="Dashboard Summary")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Name", dashboard.title)
    table.add_row("Datasource", f"{datasource.name} ({datasource.type})")
    table.add_row("Panels", str(len(dashboard.panels)))
    table.add_row("Variables", str(len(dashboard.variables)))

    console.print(table)

    return dashboard


def save_dashboard_interactive(dashboard: Dashboard) -> str | None:
    """Prompt for save location and save dashboard."""
    save = questionary.confirm(
        "Save dashboard to file?",
        default=True,
    ).ask()

    if not save:
        return None

    filename = questionary.text(
        "Output filename:",
        default=f"{dashboard.title.lower().replace(' ', '-')}.json",
    ).ask()

    if filename:
        dashboard.save(filename)
        console.print(f"[green]✓[/green] Dashboard saved to: {filename}")
        return filename

    return None
