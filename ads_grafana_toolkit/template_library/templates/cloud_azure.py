"""Azure Monitor dashboard template.

Uses Grafana Azure Monitor datasource (built-in plugin).
Covers Virtual Machines, AKS, Azure SQL, Azure Firewall, ExpressRoute, Application Gateway.
"""

from __future__ import annotations

from typing import Union

from ads_grafana_toolkit.sdk.dashboard import Dashboard
from ads_grafana_toolkit.sdk.datasource import Datasource
from ads_grafana_toolkit.template_library.base import DashboardTemplate, TemplateVariable
from ads_grafana_toolkit.template_library.registry import register_template


class AzureMonitorTemplate(DashboardTemplate):
    """Dashboard template for Azure Monitor multi-service monitoring."""

    def __init__(self):
        super().__init__(
            name="cloud-azure",
            description="Azure multi-service monitoring — VMs, AKS, SQL, Azure Firewall, ExpressRoute via Azure Monitor",
            category="cloud",
            tags=["azure", "azure-monitor", "vm", "aks", "sql", "expressroute", "cloud", "multi-cloud"],
            variables=[
                TemplateVariable(
                    name="subscription",
                    description="Azure Subscription ID",
                    default="",
                ),
                TemplateVariable(
                    name="resource_group",
                    description="Azure Resource Group",
                    default=".*",
                    required=False,
                ),
            ],
        )

    def create(self, datasource: Union[Datasource, str], **kwargs) -> Dashboard:
        ds = self._resolve_datasource(datasource)

        dashboard = Dashboard(
            title=kwargs.get("title", "Azure Monitor Overview"),
            description="Azure Monitor — VMs, AKS, SQL Database, Azure Firewall, ExpressRoute",
            tags=["azure", "azure-monitor", "cloud"],
            datasource=ds,
            refresh="5m",
        )

        dashboard.add_variable(
            "subscription",
            var_type="textbox",
            query=kwargs.get("subscription", ""),
            label="Subscription ID",
        )
        dashboard.add_variable(
            "resource_group",
            query='{"queryType": "Azure Resource Groups", "subscription": "$subscription"}',
            label="Resource Group",
            multi=True,
            include_all=True,
        )

        # ── Virtual Machines ──────────────────────────────────────────────
        dashboard.add_row("Virtual Machines")

        dashboard.add_panel(
            "VM CPU Percentage",
            panel_type="timeseries",
            width=12,
            height=8,
            unit="percent",
        ).add_query(
            '{"queryType": "Azure Monitor", "subscription": "$subscription", "resourceGroup": "$resource_group", "namespace": "Microsoft.Compute/virtualMachines", "resource": "", "metricName": "Percentage CPU", "aggregation": "Average", "timeGrain": "PT1M", "refId": "A"}',
            legend="CPU {{resourceName}}"
        )

        dashboard.add_panel(
            "VM Network In/Out",
            panel_type="timeseries",
            width=12,
            height=8,
            unit="bytes",
        ).add_query(
            '{"queryType": "Azure Monitor", "subscription": "$subscription", "resourceGroup": "$resource_group", "namespace": "Microsoft.Compute/virtualMachines", "metricName": "Network In Total", "aggregation": "Total", "timeGrain": "PT1M", "refId": "A"}',
            legend="In {{resourceName}}"
        ).add_query(
            '{"queryType": "Azure Monitor", "subscription": "$subscription", "resourceGroup": "$resource_group", "namespace": "Microsoft.Compute/virtualMachines", "metricName": "Network Out Total", "aggregation": "Total", "timeGrain": "PT1M", "refId": "B"}',
            legend="Out {{resourceName}}"
        )

        dashboard.add_panel(
            "VM Disk Read/Write Ops",
            panel_type="timeseries",
            width=12,
            height=8,
            unit="iops",
        ).add_query(
            '{"queryType": "Azure Monitor", "subscription": "$subscription", "resourceGroup": "$resource_group", "namespace": "Microsoft.Compute/virtualMachines", "metricName": "Disk Read Operations/Sec", "aggregation": "Average", "timeGrain": "PT1M", "refId": "A"}',
            legend="Read {{resourceName}}"
        ).add_query(
            '{"queryType": "Azure Monitor", "subscription": "$subscription", "resourceGroup": "$resource_group", "namespace": "Microsoft.Compute/virtualMachines", "metricName": "Disk Write Operations/Sec", "aggregation": "Average", "timeGrain": "PT1M", "refId": "B"}',
            legend="Write {{resourceName}}"
        )

        dashboard.add_panel(
            "VM Available Memory",
            panel_type="timeseries",
            width=12,
            height=8,
            unit="bytes",
        ).add_query(
            '{"queryType": "Azure Monitor", "subscription": "$subscription", "resourceGroup": "$resource_group", "namespace": "Microsoft.Compute/virtualMachines", "metricName": "Available Memory Bytes", "aggregation": "Average", "timeGrain": "PT1M", "refId": "A"}',
            legend="{{resourceName}}"
        )

        # ── AKS ───────────────────────────────────────────────────────────
        dashboard.add_row("Azure Kubernetes Service (AKS)")

        dashboard.add_panel(
            "AKS Node CPU %",
            panel_type="timeseries",
            width=8,
            height=8,
            unit="percent",
        ).add_query(
            '{"queryType": "Azure Monitor", "subscription": "$subscription", "resourceGroup": "$resource_group", "namespace": "Microsoft.ContainerService/managedClusters", "metricName": "node_cpu_usage_percentage", "aggregation": "Average", "timeGrain": "PT1M", "refId": "A"}',
            legend="{{resourceName}}"
        )

        dashboard.add_panel(
            "AKS Node Memory %",
            panel_type="timeseries",
            width=8,
            height=8,
            unit="percent",
        ).add_query(
            '{"queryType": "Azure Monitor", "subscription": "$subscription", "resourceGroup": "$resource_group", "namespace": "Microsoft.ContainerService/managedClusters", "metricName": "node_memory_working_set_percentage", "aggregation": "Average", "timeGrain": "PT1M", "refId": "A"}',
            legend="{{resourceName}}"
        )

        dashboard.add_panel(
            "AKS Pod Count",
            panel_type="timeseries",
            width=8,
            height=8,
            unit="short",
        ).add_query(
            '{"queryType": "Azure Monitor", "subscription": "$subscription", "resourceGroup": "$resource_group", "namespace": "Microsoft.ContainerService/managedClusters", "metricName": "kube_pod_status_ready", "aggregation": "Average", "timeGrain": "PT1M", "refId": "A"}',
            legend="Ready Pods {{resourceName}}"
        )

        # ── Azure SQL ─────────────────────────────────────────────────────
        dashboard.add_row("Azure SQL Database")

        dashboard.add_panel(
            "Azure SQL DTU Consumption",
            panel_type="timeseries",
            width=8,
            height=8,
            unit="percent",
        ).add_query(
            '{"queryType": "Azure Monitor", "subscription": "$subscription", "resourceGroup": "$resource_group", "namespace": "Microsoft.Sql/servers/databases", "metricName": "dtu_consumption_percent", "aggregation": "Average", "timeGrain": "PT1M", "refId": "A"}',
            legend="{{resourceName}}"
        )

        dashboard.add_panel(
            "Azure SQL Storage",
            panel_type="timeseries",
            width=8,
            height=8,
            unit="bytes",
        ).add_query(
            '{"queryType": "Azure Monitor", "subscription": "$subscription", "resourceGroup": "$resource_group", "namespace": "Microsoft.Sql/servers/databases", "metricName": "storage", "aggregation": "Maximum", "timeGrain": "PT5M", "refId": "A"}',
            legend="{{resourceName}}"
        )

        dashboard.add_panel(
            "Azure SQL Connections",
            panel_type="timeseries",
            width=8,
            height=8,
            unit="short",
        ).add_query(
            '{"queryType": "Azure Monitor", "subscription": "$subscription", "resourceGroup": "$resource_group", "namespace": "Microsoft.Sql/servers/databases", "metricName": "connection_successful", "aggregation": "Total", "timeGrain": "PT1M", "refId": "A"}',
            legend="Successful {{resourceName}}"
        ).add_query(
            '{"queryType": "Azure Monitor", "subscription": "$subscription", "resourceGroup": "$resource_group", "namespace": "Microsoft.Sql/servers/databases", "metricName": "connection_failed", "aggregation": "Total", "timeGrain": "PT1M", "refId": "B"}',
            legend="Failed {{resourceName}}"
        )

        # ── Azure Firewall ────────────────────────────────────────────────
        dashboard.add_row("Azure Firewall")

        dashboard.add_panel(
            "Azure Firewall SNAT Port Utilization",
            panel_type="timeseries",
            width=8,
            height=8,
            unit="percent",
        ).add_query(
            '{"queryType": "Azure Monitor", "subscription": "$subscription", "resourceGroup": "$resource_group", "namespace": "Microsoft.Network/azureFirewalls", "metricName": "SNATPortUtilization", "aggregation": "Average", "timeGrain": "PT1M", "refId": "A"}',
            legend="{{resourceName}}"
        )

        dashboard.add_panel(
            "Azure Firewall Throughput",
            panel_type="timeseries",
            width=8,
            height=8,
            unit="bps",
        ).add_query(
            '{"queryType": "Azure Monitor", "subscription": "$subscription", "resourceGroup": "$resource_group", "namespace": "Microsoft.Network/azureFirewalls", "metricName": "Throughput", "aggregation": "Average", "timeGrain": "PT1M", "refId": "A"}',
            legend="{{resourceName}}"
        )

        dashboard.add_panel(
            "Azure Firewall Health State",
            panel_type="timeseries",
            width=8,
            height=8,
            unit="percent",
        ).add_query(
            '{"queryType": "Azure Monitor", "subscription": "$subscription", "resourceGroup": "$resource_group", "namespace": "Microsoft.Network/azureFirewalls", "metricName": "FirewallHealth", "aggregation": "Average", "timeGrain": "PT1M", "refId": "A"}',
            legend="Health {{resourceName}}"
        )

        # ── ExpressRoute ──────────────────────────────────────────────────
        dashboard.add_row("ExpressRoute")

        dashboard.add_panel(
            "ExpressRoute BitsInPerSecond",
            panel_type="timeseries",
            width=12,
            height=8,
            unit="bps",
        ).add_query(
            '{"queryType": "Azure Monitor", "subscription": "$subscription", "resourceGroup": "$resource_group", "namespace": "Microsoft.Network/expressRouteCircuits", "metricName": "BitsInPerSecond", "aggregation": "Average", "timeGrain": "PT1M", "refId": "A"}',
            legend="In {{resourceName}}"
        )

        dashboard.add_panel(
            "ExpressRoute BitsOutPerSecond",
            panel_type="timeseries",
            width=12,
            height=8,
            unit="bps",
        ).add_query(
            '{"queryType": "Azure Monitor", "subscription": "$subscription", "resourceGroup": "$resource_group", "namespace": "Microsoft.Network/expressRouteCircuits", "metricName": "BitsOutPerSecond", "aggregation": "Average", "timeGrain": "PT1M", "refId": "A"}',
            legend="Out {{resourceName}}"
        )

        return dashboard


register_template(AzureMonitorTemplate())
