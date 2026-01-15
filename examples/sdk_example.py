#!/usr/bin/env python3
"""Example: Using the ads-grafana-toolkit Python SDK."""

from ads_grafana_toolkit import Dashboard, Datasource
from ads_grafana_toolkit.sdk.panel import TimeSeriesPanel, StatPanel, GaugePanel


def create_web_app_dashboard():
    """Create a dashboard for monitoring a web application."""

    # Create dashboard with Prometheus datasource
    dashboard = Dashboard(
        title="Web Application Metrics",
        description="Monitoring dashboard for web application",
        datasource=Datasource.prometheus("Prometheus"),
        refresh="30s",
        tags=["web", "application"],
    )

    # Add template variables for filtering
    dashboard.add_variable(
        "service",
        query='label_values(http_requests_total, service)',
        label="Service",
        multi=True,
        include_all=True,
    )

    dashboard.add_variable(
        "instance",
        query='label_values(http_requests_total{service=~"$service"}, instance)',
        label="Instance",
        multi=True,
        include_all=True,
    )

    # Overview row with key metrics
    dashboard.add_row("Overview")

    dashboard.add_panel(
        "Request Rate",
        query='sum(rate(http_requests_total{service=~"$service"}[5m]))',
        panel_type="stat",
        width=6,
        height=4,
        unit="reqps",
    )

    dashboard.add_panel(
        "Error Rate",
        query='sum(rate(http_requests_total{service=~"$service",status=~"5.."}[5m])) / sum(rate(http_requests_total{service=~"$service"}[5m])) * 100',
        panel_type="gauge",
        width=6,
        height=4,
        unit="percent",
    ).add_threshold(None, "green").add_threshold(1, "yellow").add_threshold(5, "red")

    dashboard.add_panel(
        "P95 Latency",
        query='histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket{service=~"$service"}[5m])) by (le))',
        panel_type="stat",
        width=6,
        height=4,
        unit="s",
    )

    dashboard.add_panel(
        "Active Connections",
        query='sum(http_connections_active{service=~"$service"})',
        panel_type="stat",
        width=6,
        height=4,
    )

    # Traffic row
    dashboard.add_row("Traffic")

    dashboard.add_panel(
        "Requests by Status",
        panel_type="timeseries",
        width=12,
        height=8,
        unit="reqps",
    ).add_query(
        'sum by(status) (rate(http_requests_total{service=~"$service"}[5m]))',
        legend="{{status}}"
    )

    dashboard.add_panel(
        "Requests by Service",
        panel_type="timeseries",
        width=12,
        height=8,
        unit="reqps",
    ).add_query(
        'sum by(service) (rate(http_requests_total{service=~"$service"}[5m]))',
        legend="{{service}}"
    )

    # Latency row
    dashboard.add_row("Latency")

    latency_panel = dashboard.add_panel(
        "Request Latency Percentiles",
        panel_type="timeseries",
        width=24,
        height=8,
        unit="s",
    )
    latency_panel.add_query(
        'histogram_quantile(0.50, sum(rate(http_request_duration_seconds_bucket{service=~"$service"}[5m])) by (le))',
        legend="P50"
    )
    latency_panel.add_query(
        'histogram_quantile(0.90, sum(rate(http_request_duration_seconds_bucket{service=~"$service"}[5m])) by (le))',
        legend="P90"
    )
    latency_panel.add_query(
        'histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket{service=~"$service"}[5m])) by (le))',
        legend="P95"
    )
    latency_panel.add_query(
        'histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket{service=~"$service"}[5m])) by (le))',
        legend="P99"
    )

    # Errors row
    dashboard.add_row("Errors")

    dashboard.add_panel(
        "Error Rate Over Time",
        query='sum(rate(http_requests_total{service=~"$service",status=~"5.."}[5m])) / sum(rate(http_requests_total{service=~"$service"}[5m])) * 100',
        panel_type="timeseries",
        width=12,
        height=8,
        unit="percent",
    )

    dashboard.add_panel(
        "Errors by Type",
        query='sum by(status) (rate(http_requests_total{service=~"$service",status=~"[45].."}[5m]))',
        panel_type="timeseries",
        width=12,
        height=8,
        unit="reqps",
    )

    return dashboard


def create_database_dashboard():
    """Create a dashboard for database monitoring."""

    dashboard = Dashboard(
        title="PostgreSQL Monitoring",
        datasource=Datasource.prometheus("Prometheus"),
        refresh="30s",
        tags=["database", "postgresql"],
    )

    dashboard.add_variable(
        "instance",
        query='label_values(pg_up, instance)',
        label="Instance",
    )

    dashboard.add_variable(
        "datname",
        query='label_values(pg_stat_database_tup_fetched{instance=~"$instance"}, datname)',
        label="Database",
        multi=True,
        include_all=True,
    )

    # Overview
    dashboard.add_row("Overview")

    dashboard.add_panel(
        "PostgreSQL Up",
        query='pg_up{instance=~"$instance"}',
        panel_type="stat",
        width=4,
        height=4,
    ).add_threshold(None, "red").add_threshold(1, "green")

    dashboard.add_panel(
        "Active Connections",
        query='sum(pg_stat_activity_count{instance=~"$instance",state="active"})',
        panel_type="stat",
        width=4,
        height=4,
    )

    dashboard.add_panel(
        "Transactions/sec",
        query='sum(rate(pg_stat_database_xact_commit{instance=~"$instance",datname=~"$datname"}[5m]))',
        panel_type="stat",
        width=4,
        height=4,
        unit="tps",
    )

    dashboard.add_panel(
        "Cache Hit Ratio",
        query='sum(pg_stat_database_blks_hit{instance=~"$instance"}) / (sum(pg_stat_database_blks_hit{instance=~"$instance"}) + sum(pg_stat_database_blks_read{instance=~"$instance"}))',
        panel_type="gauge",
        width=4,
        height=4,
        unit="percentunit",
    ).add_threshold(None, "red").add_threshold(0.9, "yellow").add_threshold(0.99, "green")

    dashboard.add_panel(
        "Database Size",
        query='sum(pg_database_size_bytes{instance=~"$instance",datname=~"$datname"})',
        panel_type="stat",
        width=4,
        height=4,
        unit="bytes",
    )

    dashboard.add_panel(
        "Deadlocks",
        query='sum(increase(pg_stat_database_deadlocks{instance=~"$instance",datname=~"$datname"}[1h]))',
        panel_type="stat",
        width=4,
        height=4,
    )

    # Queries
    dashboard.add_row("Query Performance")

    dashboard.add_panel(
        "Transactions",
        panel_type="timeseries",
        width=12,
        height=8,
        unit="ops",
    ).add_query(
        'rate(pg_stat_database_xact_commit{instance=~"$instance",datname=~"$datname"}[5m])',
        legend="Commits"
    ).add_query(
        'rate(pg_stat_database_xact_rollback{instance=~"$instance",datname=~"$datname"}[5m])',
        legend="Rollbacks"
    )

    dashboard.add_panel(
        "Tuple Operations",
        panel_type="timeseries",
        width=12,
        height=8,
        unit="ops",
    ).add_query(
        'rate(pg_stat_database_tup_fetched{instance=~"$instance",datname=~"$datname"}[5m])',
        legend="Fetched"
    ).add_query(
        'rate(pg_stat_database_tup_inserted{instance=~"$instance",datname=~"$datname"}[5m])',
        legend="Inserted"
    ).add_query(
        'rate(pg_stat_database_tup_updated{instance=~"$instance",datname=~"$datname"}[5m])',
        legend="Updated"
    ).add_query(
        'rate(pg_stat_database_tup_deleted{instance=~"$instance",datname=~"$datname"}[5m])',
        legend="Deleted"
    )

    return dashboard


if __name__ == "__main__":
    # Create and save the web app dashboard
    web_dashboard = create_web_app_dashboard()
    web_dashboard.save("web-app-dashboard.json")
    print(f"Created: web-app-dashboard.json ({len(web_dashboard.panels)} panels)")

    # Create and save the database dashboard
    db_dashboard = create_database_dashboard()
    db_dashboard.save("postgresql-dashboard.json")
    print(f"Created: postgresql-dashboard.json ({len(db_dashboard.panels)} panels)")
