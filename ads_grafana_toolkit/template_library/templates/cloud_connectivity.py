"""Multi-cloud connectivity dashboard — AWS Direct Connect, GCP Interconnect, Azure ExpressRoute."""
from __future__ import annotations
from typing import Union
from ads_grafana_toolkit.sdk.dashboard import Dashboard
from ads_grafana_toolkit.sdk.datasource import Datasource
from ads_grafana_toolkit.template_library.base import DashboardTemplate, TemplateVariable
from ads_grafana_toolkit.template_library.registry import register_template


class CloudConnectivityTemplate(DashboardTemplate):
    def __init__(self):
        super().__init__(
            name="cloud-connectivity",
            description="Multi-cloud WAN connectivity — AWS Direct Connect, GCP Cloud Interconnect, Azure ExpressRoute in one view",
            category="cloud",
            tags=["cloud", "connectivity", "direct-connect", "expressroute", "interconnect", "wan", "isp", "multi-cloud"],
            variables=[TemplateVariable(name="region", description="Primary cloud region", default="us-east-1")],
        )

    def create(self, datasource: Union[Datasource, str], **kwargs) -> Dashboard:
        ds = self._resolve_datasource(datasource)
        dashboard = Dashboard(
            title=kwargs.get("title", "Multi-Cloud WAN Connectivity"),
            description="AWS Direct Connect, GCP Interconnect, Azure ExpressRoute — unified view",
            tags=["cloud", "connectivity", "wan"], datasource=ds, refresh="2m",
        )

        # ── Overview Stats ───────────────────────────────────────────────
        dashboard.add_row("Connectivity Overview")
        dashboard.add_panel("AWS Direct Connect — State", panel_type="stat", width=8, height=4,
            query='{"metricName":"ConnectionState","namespace":"AWS/DX","statistics":["Minimum"],"period":"60","region":"$region"}',
        ).add_threshold(None, "red").add_threshold(1, "green")
        dashboard.add_panel("GCP Interconnect — Attachment State", panel_type="stat", width=8, height=4,
            query='{"metricType":"interconnect.googleapis.com/network/attachment/capacity","aligner":"ALIGN_MEAN"}',
        ).add_threshold(None, "green")
        dashboard.add_panel("Azure ExpressRoute — BGP Availability", panel_type="stat", width=8, height=4,
            query='{"namespace":"Microsoft.Network/expressRouteCircuits","metricName":"BgpAvailability","aggregation":"Average"}',
        ).add_threshold(None, "red").add_threshold(90, "yellow").add_threshold(99, "green")

        # ── AWS Direct Connect ───────────────────────────────────────────
        dashboard.add_row("AWS Direct Connect")
        dashboard.add_panel("DX Inbound bps", panel_type="timeseries", width=12, height=8, unit="bps",
            query='{"metricName":"ConnectionBpsIngress","namespace":"AWS/DX","statistics":["Average"],"period":"300","region":"$region"}',
        )
        dashboard.add_panel("DX Outbound bps", panel_type="timeseries", width=12, height=8, unit="bps",
            query='{"metricName":"ConnectionBpsEgress","namespace":"AWS/DX","statistics":["Average"],"period":"300","region":"$region"}',
        )
        dashboard.add_panel("DX PPS In/Out", panel_type="timeseries", width=12, height=6, unit="pps",
        ).add_query(
            '{"metricName":"ConnectionPpsIngress","namespace":"AWS/DX","statistics":["Average"],"period":"300","region":"$region"}', legend="PPS In"
        ).add_query(
            '{"metricName":"ConnectionPpsEgress","namespace":"AWS/DX","statistics":["Average"],"period":"300","region":"$region"}', legend="PPS Out"
        )
        dashboard.add_panel("DX CRC Errors", panel_type="timeseries", width=12, height=6,
            query='{"metricName":"ConnectionCRCErrorCount","namespace":"AWS/DX","statistics":["Sum"],"period":"300","region":"$region"}',
        )

        # ── GCP Cloud Interconnect ───────────────────────────────────────
        dashboard.add_row("GCP Cloud Interconnect")
        dashboard.add_panel("Interconnect Capacity", panel_type="timeseries", width=12, height=8, unit="bps",
            query='{"metricType":"interconnect.googleapis.com/network/attachment/capacity","groupBys":["resource.labels.attachment"],"aligner":"ALIGN_MEAN"}',
        )
        dashboard.add_panel("Interconnect Rx/Tx Bytes", panel_type="timeseries", width=12, height=8, unit="Bps",
        ).add_query(
            '{"metricType":"interconnect.googleapis.com/network/attachment/received_bytes_count","aligner":"ALIGN_RATE"}', legend="RX {{attachment}}"
        ).add_query(
            '{"metricType":"interconnect.googleapis.com/network/attachment/sent_bytes_count","aligner":"ALIGN_RATE"}', legend="TX {{attachment}}"
        )
        dashboard.add_panel("Interconnect Dropped Packets", panel_type="timeseries", width=12, height=6,
            query='{"metricType":"interconnect.googleapis.com/network/attachment/dropped_packets_count","aligner":"ALIGN_RATE"}',
        )
        dashboard.add_panel("Interconnect Operational Status", panel_type="table", width=12, height=6,
            query='{"metricType":"interconnect.googleapis.com/network/interconnect/operational","aligner":"ALIGN_MEAN"}',
        )

        # ── Azure ExpressRoute ───────────────────────────────────────────
        dashboard.add_row("Azure ExpressRoute")
        dashboard.add_panel("ExpressRoute Bits In/Out", panel_type="timeseries", width=12, height=8, unit="bps",
        ).add_query(
            '{"namespace":"Microsoft.Network/expressRouteCircuits","metricName":"BitsInPerSecond","aggregation":"Average"}', legend="In {{resourceName}}"
        ).add_query(
            '{"namespace":"Microsoft.Network/expressRouteCircuits","metricName":"BitsOutPerSecond","aggregation":"Average"}', legend="Out {{resourceName}}"
        )
        dashboard.add_panel("ExpressRoute ARP Availability", panel_type="timeseries", width=12, height=8, unit="percent",
            query='{"namespace":"Microsoft.Network/expressRouteCircuits","metricName":"ArpAvailability","aggregation":"Average"}',
        )
        dashboard.add_panel("ExpressRoute BGP Availability", panel_type="timeseries", width=12, height=8, unit="percent",
            query='{"namespace":"Microsoft.Network/expressRouteCircuits","metricName":"BgpAvailability","aggregation":"Average"}',
        ).add_threshold(None, "red").add_threshold(90, "yellow").add_threshold(99, "green")
        dashboard.add_panel("ExpressRoute Gateway Bits/s", panel_type="timeseries", width=12, height=8, unit="bps",
            query='{"namespace":"Microsoft.Network/virtualNetworkGateways","metricName":"ExpressRouteBitsPerSecond","aggregation":"Average"}',
        )

        return dashboard

register_template(CloudConnectivityTemplate())
