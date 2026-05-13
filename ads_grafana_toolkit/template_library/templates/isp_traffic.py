"""ISP traffic engineering and flow monitoring dashboard template.

Supports metrics from:
- pmacct (nfacctd/sfacctd) with Prometheus output
- sflow-rt with Prometheus exporter
- NetFlow/IPFIX via Telegraf + InfluxDB
- SNMP interface counters via snmp_exporter or Telegraf
"""

from __future__ import annotations

from typing import Union

from ads_grafana_toolkit.sdk.dashboard import Dashboard
from ads_grafana_toolkit.sdk.datasource import Datasource
from ads_grafana_toolkit.template_library.base import DashboardTemplate, TemplateVariable
from ads_grafana_toolkit.template_library.registry import register_template


class ISPTrafficTemplate(DashboardTemplate):
    """Dashboard template for ISP traffic engineering and flow analysis."""

    def __init__(self):
        super().__init__(
            name="isp-traffic",
            description="ISP traffic engineering — interface utilization, NetFlow/sFlow analytics, top talkers, MPLS TE tunnels",
            category="isp",
            tags=["isp", "traffic", "netflow", "sflow", "mpls", "te", "bandwidth", "network"],
            variables=[
                TemplateVariable(
                    name="router",
                    description="Router/PE device to monitor",
                    default="$router",
                ),
                TemplateVariable(
                    name="interface",
                    description="Interface filter (e.g. GigabitEthernet, xe-, et-)",
                    default=".*",
                    required=False,
                ),
                TemplateVariable(
                    name="interval",
                    description="Rate calculation interval",
                    default="5m",
                    required=False,
                ),
            ],
        )

    def create(self, datasource: Union[Datasource, str], **kwargs) -> Dashboard:
        ds = self._resolve_datasource(datasource)
        router = kwargs.get("router", "$router")
        iface = kwargs.get("interface", "$interface")
        interval = kwargs.get("interval", "$interval")

        dashboard = Dashboard(
            title=kwargs.get("title", "ISP Traffic Engineering"),
            description="Interface utilization, flow analytics, top talkers, and MPLS TE tunnel monitoring",
            tags=["isp", "traffic", "netflow", "mpls"],
            datasource=ds,
            refresh="60s",
        )

        dashboard.add_variable(
            "router",
            query='label_values(ifHCInOctets, router)',
            label="Router",
            multi=True,
            include_all=True,
        )
        dashboard.add_variable(
            "interface",
            query='label_values(ifHCInOctets{router=~"$router"}, ifDescr)',
            label="Interface",
            multi=True,
            include_all=True,
        )
        dashboard.add_variable(
            "interval",
            var_type="interval",
            query="1m,5m,15m,30m,1h",
            label="Rate Interval",
        )

        # ── Aggregate bandwidth overview ─────────────────────────────────
        dashboard.add_row("Aggregate Bandwidth")

        dashboard.add_panel(
            "Total Inbound Traffic",
            query=f'sum(rate(ifHCInOctets{{router=~"{router}",ifDescr=~"{iface}"}}[{interval}])) * 8',
            panel_type="stat",
            width=6,
            height=4,
            unit="bps",
        )

        dashboard.add_panel(
            "Total Outbound Traffic",
            query=f'sum(rate(ifHCOutOctets{{router=~"{router}",ifDescr=~"{iface}"}}[{interval}])) * 8',
            panel_type="stat",
            width=6,
            height=4,
            unit="bps",
        )

        dashboard.add_panel(
            "Peak Inbound (1h)",
            query=f'max_over_time(sum(rate(ifHCInOctets{{router=~"{router}"}}[{interval}]))[1h:1m]) * 8',
            panel_type="stat",
            width=6,
            height=4,
            unit="bps",
        )

        dashboard.add_panel(
            "Interface Errors",
            query=f'sum(rate(ifInErrors{{router=~"{router}"}}[{interval}])) + sum(rate(ifOutErrors{{router=~"{router}"}}[{interval}]))',
            panel_type="stat",
            width=6,
            height=4,
            unit="pps",
        ).add_threshold(None, "green").add_threshold(1, "yellow").add_threshold(100, "red")

        # ── Interface utilization ────────────────────────────────────────
        dashboard.add_row("Interface Utilization")

        dashboard.add_panel(
            "Interface Utilization (% of capacity)",
            panel_type="timeseries",
            width=24,
            height=10,
            unit="percent",
        ).add_query(
            f'rate(ifHCInOctets{{router=~"{router}",ifDescr=~"{iface}"}}[{interval}]) * 8 / ifHighSpeed{{router=~"{router}",ifDescr=~"{iface}"}} / 1000000 * 100',
            legend="IN {{router}} {{ifDescr}}"
        ).add_query(
            f'rate(ifHCOutOctets{{router=~"{router}",ifDescr=~"{iface}"}}[{interval}]) * 8 / ifHighSpeed{{router=~"{router}",ifDescr=~"{iface}"}} / 1000000 * 100',
            legend="OUT {{router}} {{ifDescr}}"
        )

        dashboard.add_panel(
            "Inbound Traffic by Interface",
            panel_type="timeseries",
            width=12,
            height=8,
            unit="bps",
        ).add_query(
            f'rate(ifHCInOctets{{router=~"{router}",ifDescr=~"{iface}"}}[{interval}]) * 8',
            legend="{{router}} {{ifDescr}}"
        )

        dashboard.add_panel(
            "Outbound Traffic by Interface",
            panel_type="timeseries",
            width=12,
            height=8,
            unit="bps",
        ).add_query(
            f'rate(ifHCOutOctets{{router=~"{router}",ifDescr=~"{iface}"}}[{interval}]) * 8',
            legend="{{router}} {{ifDescr}}"
        )

        # ── Top talkers (NetFlow/sFlow) ──────────────────────────────────
        dashboard.add_row("Top Talkers (Flow Data)")

        dashboard.add_panel(
            "Top Source IPs by Volume",
            query=f'topk(20, sum by(src_addr) (rate(flow_bytes_total{{router=~"{router}"}}[{interval}])))',
            panel_type="table",
            width=12,
            height=8,
            unit="Bps",
        )

        dashboard.add_panel(
            "Top Destination IPs by Volume",
            query=f'topk(20, sum by(dst_addr) (rate(flow_bytes_total{{router=~"{router}"}}[{interval}])))',
            panel_type="table",
            width=12,
            height=8,
            unit="Bps",
        )

        dashboard.add_panel(
            "Top Protocols",
            query=f'topk(10, sum by(proto) (rate(flow_bytes_total{{router=~"{router}"}}[{interval}])))',
            panel_type="timeseries",
            width=12,
            height=8,
            unit="Bps",
        )

        dashboard.add_panel(
            "Top AS Pairs (Src → Dst)",
            query=f'topk(20, sum by(src_as, dst_as) (rate(flow_bytes_total{{router=~"{router}"}}[{interval}])))',
            panel_type="table",
            width=12,
            height=8,
            unit="Bps",
        )

        # ── MPLS TE Tunnels ──────────────────────────────────────────────
        dashboard.add_row("MPLS Traffic Engineering")

        dashboard.add_panel(
            "MPLS TE Tunnel Bandwidth",
            panel_type="timeseries",
            width=12,
            height=8,
            unit="bps",
        ).add_query(
            f'rate(mplsTunnelHCInOctets{{router=~"{router}"}}[{interval}]) * 8',
            legend="{{router}} {{mplsTunnelName}} IN"
        ).add_query(
            f'rate(mplsTunnelHCOutOctets{{router=~"{router}"}}[{interval}]) * 8',
            legend="{{router}} {{mplsTunnelName}} OUT"
        )

        dashboard.add_panel(
            "MPLS TE Tunnel States",
            query=f'mplsTunnelOperStatus{{router=~"{router}"}}',
            panel_type="table",
            width=12,
            height=8,
        )

        # ── QoS ─────────────────────────────────────────────────────────
        dashboard.add_row("QoS & Traffic Shaping")

        dashboard.add_panel(
            "QoS Queue Drops",
            panel_type="timeseries",
            width=12,
            height=8,
            unit="pps",
        ).add_query(
            f'rate(cbqos_drop_pkt_total{{router=~"{router}"}}[{interval}])',
            legend="{{router}} {{policy_name}} {{class_name}}"
        )

        dashboard.add_panel(
            "QoS Queue Utilization",
            panel_type="timeseries",
            width=12,
            height=8,
            unit="percent",
        ).add_query(
            f'cbqos_queue_size_bytes{{router=~"{router}"}} / cbqos_queue_max_size_bytes{{router=~"{router}"}} * 100',
            legend="{{router}} {{class_name}}"
        )

        return dashboard


register_template(ISPTrafficTemplate())
