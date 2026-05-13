"""GCP Cloud Monitoring (formerly Stackdriver) dashboard template.

Uses Grafana Cloud Monitoring datasource plugin (grafana-googlecloud-datasource).
Covers Compute Engine, GKE, Cloud SQL, Cloud Run, Cloud Load Balancing, Interconnect.
"""

from __future__ import annotations

from typing import Union

from ads_grafana_toolkit.sdk.dashboard import Dashboard
from ads_grafana_toolkit.sdk.datasource import Datasource
from ads_grafana_toolkit.template_library.base import DashboardTemplate, TemplateVariable
from ads_grafana_toolkit.template_library.registry import register_template


class GCPCloudMonitoringTemplate(DashboardTemplate):
    """Dashboard template for GCP Cloud Monitoring."""

    def __init__(self):
        super().__init__(
            name="cloud-gcp",
            description="GCP multi-service monitoring — Compute Engine, GKE, Cloud SQL, Cloud Run, Interconnect via Cloud Monitoring",
            category="cloud",
            tags=["gcp", "google-cloud", "compute-engine", "gke", "cloud-sql", "cloud-run", "cloud", "multi-cloud"],
            variables=[
                TemplateVariable(
                    name="project",
                    description="GCP Project ID",
                    default="my-project",
                ),
                TemplateVariable(
                    name="zone",
                    description="GCP Zone filter",
                    default=".*",
                    required=False,
                ),
            ],
        )

    def create(self, datasource: Union[Datasource, str], **kwargs) -> Dashboard:
        ds = self._resolve_datasource(datasource)
        project = kwargs.get("project", "$project")

        dashboard = Dashboard(
            title=kwargs.get("title", "GCP Cloud Monitoring Overview"),
            description="GCP — Compute Engine, GKE, Cloud SQL, Cloud Run, Interconnect",
            tags=["gcp", "google-cloud", "cloud"],
            datasource=ds,
            refresh="5m",
        )

        dashboard.add_variable(
            "project",
            var_type="textbox",
            query=project,
            label="GCP Project ID",
        )
        dashboard.add_variable(
            "zone",
            query='{"projectName": "$project", "selectedMetricName": "compute.googleapis.com/instance/cpu/utilization", "selectedSLOService": "", "refId": "A"}',
            label="Zone",
            multi=True,
            include_all=True,
        )

        # ── Compute Engine ────────────────────────────────────────────────
        dashboard.add_row("Compute Engine")

        dashboard.add_panel(
            "GCE Instance CPU Utilization",
            panel_type="timeseries",
            width=12,
            height=8,
            unit="percent",
        ).add_query(
            '{"aliasBy": "{{metric.labels.instance_name}}", "metricType": "compute.googleapis.com/instance/cpu/utilization", "filters": [], "groupBys": ["metric.labels.instance_name"], "aligner": "ALIGN_MEAN", "alignmentPeriod": "60s", "crossSeriesReducer": "REDUCE_MEAN", "projectName": "$project", "refId": "A"}',
            legend="{{instance_name}}"
        )

        dashboard.add_panel(
            "GCE Network Bytes (In/Out)",
            panel_type="timeseries",
            width=12,
            height=8,
            unit="Bps",
        ).add_query(
            '{"aliasBy": "IN {{metric.labels.instance_name}}", "metricType": "compute.googleapis.com/instance/network/received_bytes_count", "filters": [], "groupBys": ["metric.labels.instance_name"], "aligner": "ALIGN_RATE", "alignmentPeriod": "60s", "projectName": "$project", "refId": "A"}',
            legend="IN {{instance_name}}"
        ).add_query(
            '{"aliasBy": "OUT {{metric.labels.instance_name}}", "metricType": "compute.googleapis.com/instance/network/sent_bytes_count", "filters": [], "groupBys": ["metric.labels.instance_name"], "aligner": "ALIGN_RATE", "alignmentPeriod": "60s", "projectName": "$project", "refId": "B"}',
            legend="OUT {{instance_name}}"
        )

        dashboard.add_panel(
            "GCE Disk Read/Write Ops",
            panel_type="timeseries",
            width=12,
            height=8,
            unit="iops",
        ).add_query(
            '{"aliasBy": "Read {{metric.labels.instance_name}}", "metricType": "compute.googleapis.com/instance/disk/read_ops_count", "groupBys": ["metric.labels.instance_name"], "aligner": "ALIGN_RATE", "projectName": "$project", "refId": "A"}',
            legend="Read"
        ).add_query(
            '{"aliasBy": "Write {{metric.labels.instance_name}}", "metricType": "compute.googleapis.com/instance/disk/write_ops_count", "groupBys": ["metric.labels.instance_name"], "aligner": "ALIGN_RATE", "projectName": "$project", "refId": "B"}',
            legend="Write"
        )

        dashboard.add_panel(
            "GCE Instance Uptime",
            panel_type="timeseries",
            width=12,
            height=8,
            unit="s",
        ).add_query(
            '{"metricType": "compute.googleapis.com/instance/uptime", "groupBys": ["metric.labels.instance_name"], "aligner": "ALIGN_MEAN", "projectName": "$project", "refId": "A"}',
            legend="{{instance_name}}"
        )

        # ── GKE ──────────────────────────────────────────────────────────
        dashboard.add_row("Google Kubernetes Engine (GKE)")

        dashboard.add_panel(
            "GKE Container CPU Request Utilization",
            panel_type="timeseries",
            width=12,
            height=8,
            unit="percent",
        ).add_query(
            '{"metricType": "kubernetes.io/container/cpu/request_utilization", "groupBys": ["resource.labels.cluster_name", "resource.labels.namespace_name"], "aligner": "ALIGN_MEAN", "projectName": "$project", "refId": "A"}',
            legend="{{cluster_name}} / {{namespace_name}}"
        )

        dashboard.add_panel(
            "GKE Container Memory Request Utilization",
            panel_type="timeseries",
            width=12,
            height=8,
            unit="percent",
        ).add_query(
            '{"metricType": "kubernetes.io/container/memory/request_utilization", "groupBys": ["resource.labels.cluster_name", "resource.labels.namespace_name"], "aligner": "ALIGN_MEAN", "projectName": "$project", "refId": "A"}',
            legend="{{cluster_name}} / {{namespace_name}}"
        )

        dashboard.add_panel(
            "GKE Node CPU Allocatable Utilization",
            panel_type="timeseries",
            width=12,
            height=8,
            unit="percent",
        ).add_query(
            '{"metricType": "kubernetes.io/node/cpu/allocatable_utilization", "groupBys": ["resource.labels.cluster_name", "resource.labels.node_name"], "aligner": "ALIGN_MEAN", "projectName": "$project", "refId": "A"}',
            legend="{{cluster_name}} / {{node_name}}"
        )

        dashboard.add_panel(
            "GKE Pod Restarts",
            panel_type="timeseries",
            width=12,
            height=8,
        ).add_query(
            '{"metricType": "kubernetes.io/container/restart_count", "groupBys": ["resource.labels.cluster_name", "resource.labels.namespace_name", "resource.labels.pod_name"], "aligner": "ALIGN_RATE", "projectName": "$project", "refId": "A"}',
            legend="{{pod_name}}"
        )

        # ── Cloud SQL ─────────────────────────────────────────────────────
        dashboard.add_row("Cloud SQL")

        dashboard.add_panel(
            "Cloud SQL CPU Utilization",
            panel_type="timeseries",
            width=8,
            height=8,
            unit="percent",
        ).add_query(
            '{"metricType": "cloudsql.googleapis.com/database/cpu/utilization", "groupBys": ["resource.labels.database_id"], "aligner": "ALIGN_MEAN", "projectName": "$project", "refId": "A"}',
            legend="{{database_id}}"
        )

        dashboard.add_panel(
            "Cloud SQL Memory Utilization",
            panel_type="timeseries",
            width=8,
            height=8,
            unit="percent",
        ).add_query(
            '{"metricType": "cloudsql.googleapis.com/database/memory/utilization", "groupBys": ["resource.labels.database_id"], "aligner": "ALIGN_MEAN", "projectName": "$project", "refId": "A"}',
            legend="{{database_id}}"
        )

        dashboard.add_panel(
            "Cloud SQL Connections",
            panel_type="timeseries",
            width=8,
            height=8,
            unit="short",
        ).add_query(
            '{"metricType": "cloudsql.googleapis.com/database/network/connections", "groupBys": ["resource.labels.database_id"], "aligner": "ALIGN_MEAN", "projectName": "$project", "refId": "A"}',
            legend="{{database_id}}"
        )

        # ── Cloud Run ─────────────────────────────────────────────────────
        dashboard.add_row("Cloud Run")

        dashboard.add_panel(
            "Cloud Run Request Count",
            panel_type="timeseries",
            width=8,
            height=8,
            unit="short",
        ).add_query(
            '{"metricType": "run.googleapis.com/request_count", "groupBys": ["resource.labels.service_name", "metric.labels.response_code_class"], "aligner": "ALIGN_RATE", "projectName": "$project", "refId": "A"}',
            legend="{{service_name}} {{response_code_class}}"
        )

        dashboard.add_panel(
            "Cloud Run Request Latency (p99)",
            panel_type="timeseries",
            width=8,
            height=8,
            unit="ms",
        ).add_query(
            '{"metricType": "run.googleapis.com/request_latencies", "groupBys": ["resource.labels.service_name"], "aligner": "ALIGN_PERCENTILE_99", "projectName": "$project", "refId": "A"}',
            legend="p99 {{service_name}}"
        )

        dashboard.add_panel(
            "Cloud Run Container Instance Count",
            panel_type="timeseries",
            width=8,
            height=8,
            unit="short",
        ).add_query(
            '{"metricType": "run.googleapis.com/container/instance_count", "groupBys": ["resource.labels.service_name"], "aligner": "ALIGN_MEAN", "projectName": "$project", "refId": "A"}',
            legend="{{service_name}}"
        )

        # ── Interconnect / Networking ──────────────────────────────────────
        dashboard.add_row("Cloud Interconnect / Networking")

        dashboard.add_panel(
            "Interconnect Received Bytes",
            panel_type="timeseries",
            width=12,
            height=8,
            unit="Bps",
        ).add_query(
            '{"metricType": "interconnect.googleapis.com/network/attachment/received_bytes_count", "groupBys": ["resource.labels.attachment"], "aligner": "ALIGN_RATE", "projectName": "$project", "refId": "A"}',
            legend="{{attachment}}"
        )

        dashboard.add_panel(
            "Interconnect Sent Bytes",
            panel_type="timeseries",
            width=12,
            height=8,
            unit="Bps",
        ).add_query(
            '{"metricType": "interconnect.googleapis.com/network/attachment/sent_bytes_count", "groupBys": ["resource.labels.attachment"], "aligner": "ALIGN_RATE", "projectName": "$project", "refId": "A"}',
            legend="{{attachment}}"
        )

        return dashboard


register_template(GCPCloudMonitoringTemplate())
