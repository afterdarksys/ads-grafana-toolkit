"""Kubernetes dashboard templates."""

from __future__ import annotations

from typing import Union

from ads_grafana_toolkit.sdk.dashboard import Dashboard
from ads_grafana_toolkit.sdk.datasource import Datasource
from ads_grafana_toolkit.template_library.base import DashboardTemplate, TemplateVariable
from ads_grafana_toolkit.template_library.registry import register_template


class KubernetesClusterTemplate(DashboardTemplate):
    """Dashboard template for Kubernetes cluster overview."""

    def __init__(self):
        super().__init__(
            name="kubernetes-cluster",
            description="Kubernetes cluster overview (nodes, pods, deployments, resources)",
            category="kubernetes",
            tags=["kubernetes", "k8s", "cluster"],
        )

    def create(self, datasource: Union[Datasource, str], **kwargs) -> Dashboard:
        ds = self._resolve_datasource(datasource)

        dashboard = Dashboard(
            title=kwargs.get("title", "Kubernetes Cluster Overview"),
            description="Kubernetes cluster metrics",
            tags=["kubernetes", "cluster"],
            datasource=ds,
            refresh="30s",
        )

        dashboard.add_variable(
            "namespace",
            query='label_values(kube_pod_info, namespace)',
            label="Namespace",
            multi=True,
            include_all=True,
        )

        dashboard.add_row("Cluster Overview")

        dashboard.add_panel(
            "Nodes",
            query='sum(kube_node_info)',
            panel_type="stat",
            width=4,
            height=4,
        )

        dashboard.add_panel(
            "Namespaces",
            query='count(kube_namespace_created)',
            panel_type="stat",
            width=4,
            height=4,
        )

        dashboard.add_panel(
            "Running Pods",
            query='sum(kube_pod_status_phase{phase="Running"})',
            panel_type="stat",
            width=4,
            height=4,
        )

        dashboard.add_panel(
            "Deployments",
            query='count(kube_deployment_created)',
            panel_type="stat",
            width=4,
            height=4,
        )

        dashboard.add_panel(
            "CPU Requests",
            query='sum(kube_pod_container_resource_requests{resource="cpu"}) / sum(kube_node_status_allocatable{resource="cpu"}) * 100',
            panel_type="gauge",
            width=4,
            height=4,
            unit="percent",
        ).add_threshold(None, "green").add_threshold(70, "yellow").add_threshold(90, "red")

        dashboard.add_panel(
            "Memory Requests",
            query='sum(kube_pod_container_resource_requests{resource="memory"}) / sum(kube_node_status_allocatable{resource="memory"}) * 100',
            panel_type="gauge",
            width=4,
            height=4,
            unit="percent",
        ).add_threshold(None, "green").add_threshold(70, "yellow").add_threshold(90, "red")

        dashboard.add_row("Node Resources")

        dashboard.add_panel(
            "Node CPU Usage",
            query='100 - (avg by(node) (irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)',
            panel_type="timeseries",
            width=12,
            height=8,
            unit="percent",
        )

        dashboard.add_panel(
            "Node Memory Usage",
            query='100 * (1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes))',
            panel_type="timeseries",
            width=12,
            height=8,
            unit="percent",
        )

        dashboard.add_row("Pod Status")

        dashboard.add_panel(
            "Pods by Phase",
            query='sum by(phase) (kube_pod_status_phase{namespace=~"$namespace"})',
            panel_type="timeseries",
            width=12,
            height=8,
        )

        dashboard.add_panel(
            "Pod Restarts",
            query='sum by(namespace, pod) (increase(kube_pod_container_status_restarts_total{namespace=~"$namespace"}[1h]))',
            panel_type="timeseries",
            width=12,
            height=8,
        )

        dashboard.add_row("Deployments")

        dashboard.add_panel(
            "Deployment Replicas",
            panel_type="timeseries",
            width=12,
            height=8,
        ).add_query(
            'sum by(deployment) (kube_deployment_status_replicas{namespace=~"$namespace"})',
            legend="Available {{deployment}}"
        ).add_query(
            'sum by(deployment) (kube_deployment_spec_replicas{namespace=~"$namespace"})',
            legend="Desired {{deployment}}"
        )

        dashboard.add_panel(
            "Unavailable Replicas",
            query='sum by(deployment, namespace) (kube_deployment_status_replicas_unavailable{namespace=~"$namespace"}) > 0',
            panel_type="timeseries",
            width=12,
            height=8,
        )

        return dashboard


class KubernetesPodTemplate(DashboardTemplate):
    """Dashboard template for Kubernetes pod details."""

    def __init__(self):
        super().__init__(
            name="kubernetes-pod",
            description="Kubernetes pod resource usage details",
            category="kubernetes",
            tags=["kubernetes", "k8s", "pod"],
        )

    def create(self, datasource: Union[Datasource, str], **kwargs) -> Dashboard:
        ds = self._resolve_datasource(datasource)

        dashboard = Dashboard(
            title=kwargs.get("title", "Kubernetes Pod Resources"),
            description="Pod-level resource metrics",
            tags=["kubernetes", "pod"],
            datasource=ds,
            refresh="30s",
        )

        dashboard.add_variable(
            "namespace",
            query='label_values(kube_pod_info, namespace)',
            label="Namespace",
        )
        dashboard.add_variable(
            "pod",
            query='label_values(kube_pod_info{namespace="$namespace"}, pod)',
            label="Pod",
        )

        dashboard.add_row("Pod Overview")

        dashboard.add_panel(
            "Pod Phase",
            query='kube_pod_status_phase{namespace="$namespace", pod="$pod"} == 1',
            panel_type="stat",
            width=6,
            height=4,
        )

        dashboard.add_panel(
            "Container Restarts",
            query='sum(kube_pod_container_status_restarts_total{namespace="$namespace", pod="$pod"})',
            panel_type="stat",
            width=6,
            height=4,
        )

        dashboard.add_panel(
            "Age",
            query='time() - kube_pod_created{namespace="$namespace", pod="$pod"}',
            panel_type="stat",
            width=6,
            height=4,
            unit="s",
        )

        dashboard.add_panel(
            "Ready Containers",
            query='sum(kube_pod_container_status_ready{namespace="$namespace", pod="$pod"})',
            panel_type="stat",
            width=6,
            height=4,
        )

        dashboard.add_row("Resource Usage")

        dashboard.add_panel(
            "CPU Usage",
            query='sum(rate(container_cpu_usage_seconds_total{namespace="$namespace", pod="$pod"}[5m])) by (container)',
            panel_type="timeseries",
            width=12,
            height=8,
            unit="cores",
        )

        dashboard.add_panel(
            "Memory Usage",
            query='sum(container_memory_working_set_bytes{namespace="$namespace", pod="$pod"}) by (container)',
            panel_type="timeseries",
            width=12,
            height=8,
            unit="bytes",
        )

        dashboard.add_row("Network")

        dashboard.add_panel(
            "Network Receive",
            query='sum(rate(container_network_receive_bytes_total{namespace="$namespace", pod="$pod"}[5m]))',
            panel_type="timeseries",
            width=12,
            height=8,
            unit="Bps",
        )

        dashboard.add_panel(
            "Network Transmit",
            query='sum(rate(container_network_transmit_bytes_total{namespace="$namespace", pod="$pod"}[5m]))',
            panel_type="timeseries",
            width=12,
            height=8,
            unit="Bps",
        )

        return dashboard


register_template(KubernetesClusterTemplate())
register_template(KubernetesPodTemplate())
