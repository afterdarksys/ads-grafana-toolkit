"""AWS multi-service monitoring dashboard template.

Uses Grafana CloudWatch datasource (built-in plugin).
Covers EC2, RDS, ELB/ALB, VPC Flow Logs, ECS, Lambda, S3, Direct Connect.
"""

from __future__ import annotations

from typing import Union

from ads_grafana_toolkit.sdk.dashboard import Dashboard
from ads_grafana_toolkit.sdk.datasource import Datasource
from ads_grafana_toolkit.template_library.base import DashboardTemplate, TemplateVariable
from ads_grafana_toolkit.template_library.registry import register_template


def _cw_panel(dashboard: Dashboard, title: str, namespace: str, metric: str,
               dimensions: dict, stat: str = "Average", period: int = 300,
               panel_type: str = "timeseries", unit: str = "short",
               width: int = 12, height: int = 8) -> None:
    """Add a CloudWatch panel with proper target format."""
    dim_str = ", ".join(f'"{k}": "{v}"' for k, v in dimensions.items())
    query = f'{{"dimensions": {{{dim_str}}}, "matchExact": true, "metricName": "{metric}", "namespace": "{namespace}", "period": "{period}", "refId": "A", "region": "default", "statistics": ["{stat}"]}}'
    dashboard.add_panel(
        title,
        query=query,
        panel_type=panel_type,
        width=width,
        height=height,
        unit=unit,
    )


class AWSCloudWatchTemplate(DashboardTemplate):
    """Dashboard template for AWS CloudWatch multi-service monitoring."""

    def __init__(self):
        super().__init__(
            name="cloud-aws",
            description="AWS multi-service monitoring — EC2, RDS, ALB, Lambda, ECS, VPC via CloudWatch",
            category="cloud",
            tags=["aws", "cloudwatch", "ec2", "rds", "alb", "lambda", "ecs", "cloud", "multi-cloud"],
            variables=[
                TemplateVariable(
                    name="region",
                    description="AWS region",
                    default="us-east-1",
                ),
                TemplateVariable(
                    name="instance_id",
                    description="EC2 instance ID filter",
                    default=".*",
                    required=False,
                ),
            ],
        )

    def create(self, datasource: Union[Datasource, str], **kwargs) -> Dashboard:
        ds = self._resolve_datasource(datasource)
        region = kwargs.get("region", "$region")

        dashboard = Dashboard(
            title=kwargs.get("title", "AWS Multi-Service Overview"),
            description="AWS CloudWatch — EC2, RDS, ALB, Lambda, ECS, Direct Connect",
            tags=["aws", "cloudwatch", "cloud"],
            datasource=ds,
            refresh="5m",
        )

        dashboard.add_variable(
            "region",
            var_type="custom",
            query="us-east-1,us-east-2,us-west-1,us-west-2,eu-west-1,eu-west-2,eu-central-1,ap-southeast-1,ap-northeast-1",
            label="AWS Region",
        )
        dashboard.add_variable(
            "instance_id",
            query='{"namespace": "AWS/EC2", "dimension": "InstanceId", "region": "$region", "dimensionFilters": {}}',
            label="EC2 Instance",
            multi=True,
            include_all=True,
        )
        dashboard.add_variable(
            "db_instance",
            query='{"namespace": "AWS/RDS", "dimension": "DBInstanceIdentifier", "region": "$region"}',
            label="RDS Instance",
            multi=True,
            include_all=True,
        )

        # ── EC2 ──────────────────────────────────────────────────────────
        dashboard.add_row("EC2 Compute")

        dashboard.add_panel(
            "EC2 CPU Utilization",
            panel_type="timeseries",
            width=12,
            height=8,
            unit="percent",
        ).add_query(
            '{"dimensions": {"InstanceId": "$instance_id"}, "matchExact": true, "metricName": "CPUUtilization", "namespace": "AWS/EC2", "period": "300", "refId": "A", "region": "$region", "statistics": ["Average"]}',
            legend="{{InstanceId}}"
        )

        dashboard.add_panel(
            "EC2 Network In/Out",
            panel_type="timeseries",
            width=12,
            height=8,
            unit="Bps",
        ).add_query(
            '{"dimensions": {"InstanceId": "$instance_id"}, "metricName": "NetworkIn", "namespace": "AWS/EC2", "period": "300", "refId": "A", "region": "$region", "statistics": ["Sum"]}',
            legend="IN {{InstanceId}}"
        ).add_query(
            '{"dimensions": {"InstanceId": "$instance_id"}, "metricName": "NetworkOut", "namespace": "AWS/EC2", "period": "300", "refId": "B", "region": "$region", "statistics": ["Sum"]}',
            legend="OUT {{InstanceId}}"
        )

        dashboard.add_panel(
            "EC2 Disk Read/Write Ops",
            panel_type="timeseries",
            width=12,
            height=8,
            unit="iops",
        ).add_query(
            '{"dimensions": {"InstanceId": "$instance_id"}, "metricName": "DiskReadOps", "namespace": "AWS/EC2", "period": "300", "refId": "A", "region": "$region", "statistics": ["Sum"]}',
            legend="Read {{InstanceId}}"
        ).add_query(
            '{"dimensions": {"InstanceId": "$instance_id"}, "metricName": "DiskWriteOps", "namespace": "AWS/EC2", "period": "300", "refId": "B", "region": "$region", "statistics": ["Sum"]}',
            legend="Write {{InstanceId}}"
        )

        dashboard.add_panel(
            "EC2 Status Check Failures",
            panel_type="timeseries",
            width=12,
            height=8,
        ).add_query(
            '{"dimensions": {"InstanceId": "$instance_id"}, "metricName": "StatusCheckFailed", "namespace": "AWS/EC2", "period": "60", "refId": "A", "region": "$region", "statistics": ["Sum"]}',
            legend="Status Check Failed {{InstanceId}}"
        )

        # ── RDS ──────────────────────────────────────────────────────────
        dashboard.add_row("RDS Database")

        dashboard.add_panel(
            "RDS CPU Utilization",
            panel_type="timeseries",
            width=8,
            height=8,
            unit="percent",
        ).add_query(
            '{"dimensions": {"DBInstanceIdentifier": "$db_instance"}, "metricName": "CPUUtilization", "namespace": "AWS/RDS", "period": "300", "refId": "A", "region": "$region", "statistics": ["Average"]}',
            legend="{{DBInstanceIdentifier}}"
        )

        dashboard.add_panel(
            "RDS Freeable Memory",
            panel_type="timeseries",
            width=8,
            height=8,
            unit="bytes",
        ).add_query(
            '{"dimensions": {"DBInstanceIdentifier": "$db_instance"}, "metricName": "FreeableMemory", "namespace": "AWS/RDS", "period": "300", "refId": "A", "region": "$region", "statistics": ["Average"]}',
            legend="{{DBInstanceIdentifier}}"
        )

        dashboard.add_panel(
            "RDS Database Connections",
            panel_type="timeseries",
            width=8,
            height=8,
            unit="short",
        ).add_query(
            '{"dimensions": {"DBInstanceIdentifier": "$db_instance"}, "metricName": "DatabaseConnections", "namespace": "AWS/RDS", "period": "300", "refId": "A", "region": "$region", "statistics": ["Average"]}',
            legend="{{DBInstanceIdentifier}}"
        )

        dashboard.add_panel(
            "RDS Read/Write Latency",
            panel_type="timeseries",
            width=12,
            height=8,
            unit="s",
        ).add_query(
            '{"dimensions": {"DBInstanceIdentifier": "$db_instance"}, "metricName": "ReadLatency", "namespace": "AWS/RDS", "period": "300", "refId": "A", "region": "$region", "statistics": ["Average"]}',
            legend="Read {{DBInstanceIdentifier}}"
        ).add_query(
            '{"dimensions": {"DBInstanceIdentifier": "$db_instance"}, "metricName": "WriteLatency", "namespace": "AWS/RDS", "period": "300", "refId": "B", "region": "$region", "statistics": ["Average"]}',
            legend="Write {{DBInstanceIdentifier}}"
        )

        dashboard.add_panel(
            "RDS Free Storage",
            panel_type="timeseries",
            width=12,
            height=8,
            unit="bytes",
        ).add_query(
            '{"dimensions": {"DBInstanceIdentifier": "$db_instance"}, "metricName": "FreeStorageSpace", "namespace": "AWS/RDS", "period": "300", "refId": "A", "region": "$region", "statistics": ["Average"]}',
            legend="{{DBInstanceIdentifier}}"
        )

        # ── ALB / ELB ────────────────────────────────────────────────────
        dashboard.add_row("Application Load Balancer")

        dashboard.add_panel(
            "ALB Request Count",
            panel_type="timeseries",
            width=8,
            height=8,
            unit="short",
        ).add_query(
            '{"dimensions": {}, "metricName": "RequestCount", "namespace": "AWS/ApplicationELB", "period": "300", "refId": "A", "region": "$region", "statistics": ["Sum"]}',
            legend="Requests"
        )

        dashboard.add_panel(
            "ALB Target Response Time (p99)",
            panel_type="timeseries",
            width=8,
            height=8,
            unit="s",
        ).add_query(
            '{"dimensions": {}, "metricName": "TargetResponseTime", "namespace": "AWS/ApplicationELB", "period": "300", "refId": "A", "region": "$region", "statistics": ["p99"]}',
            legend="p99 Latency"
        )

        dashboard.add_panel(
            "ALB HTTP 5xx Errors",
            panel_type="timeseries",
            width=8,
            height=8,
            unit="short",
        ).add_query(
            '{"dimensions": {}, "metricName": "HTTPCode_Target_5XX_Count", "namespace": "AWS/ApplicationELB", "period": "300", "refId": "A", "region": "$region", "statistics": ["Sum"]}',
            legend="5xx Errors"
        )

        # ── Lambda ────────────────────────────────────────────────────────
        dashboard.add_row("Lambda Functions")

        dashboard.add_panel(
            "Lambda Invocations",
            panel_type="timeseries",
            width=8,
            height=8,
            unit="short",
        ).add_query(
            '{"dimensions": {}, "matchExact": false, "metricName": "Invocations", "namespace": "AWS/Lambda", "period": "300", "refId": "A", "region": "$region", "statistics": ["Sum"]}',
            legend="{{FunctionName}}"
        )

        dashboard.add_panel(
            "Lambda Error Rate",
            panel_type="timeseries",
            width=8,
            height=8,
            unit="percent",
        ).add_query(
            '{"dimensions": {}, "matchExact": false, "metricName": "Errors", "namespace": "AWS/Lambda", "period": "300", "refId": "A", "region": "$region", "statistics": ["Sum"]}',
            legend="Errors {{FunctionName}}"
        )

        dashboard.add_panel(
            "Lambda Duration (p99)",
            panel_type="timeseries",
            width=8,
            height=8,
            unit="ms",
        ).add_query(
            '{"dimensions": {}, "matchExact": false, "metricName": "Duration", "namespace": "AWS/Lambda", "period": "300", "refId": "A", "region": "$region", "statistics": ["p99"]}',
            legend="p99 {{FunctionName}}"
        )

        # ── Direct Connect ────────────────────────────────────────────────
        dashboard.add_row("Direct Connect / Network")

        dashboard.add_panel(
            "Direct Connect Connection State",
            panel_type="timeseries",
            width=12,
            height=6,
        ).add_query(
            '{"dimensions": {}, "metricName": "ConnectionState", "namespace": "AWS/DX", "period": "60", "refId": "A", "region": "$region", "statistics": ["Minimum"]}',
            legend="{{ConnectionId}}"
        )

        dashboard.add_panel(
            "Direct Connect Bps In/Out",
            panel_type="timeseries",
            width=12,
            height=6,
            unit="bps",
        ).add_query(
            '{"dimensions": {}, "metricName": "ConnectionBpsIngress", "namespace": "AWS/DX", "period": "300", "refId": "A", "region": "$region", "statistics": ["Average"]}',
            legend="Ingress {{ConnectionId}}"
        ).add_query(
            '{"dimensions": {}, "metricName": "ConnectionBpsEgress", "namespace": "AWS/DX", "period": "300", "refId": "B", "region": "$region", "statistics": ["Average"]}',
            legend="Egress {{ConnectionId}}"
        )

        return dashboard


register_template(AWSCloudWatchTemplate())
