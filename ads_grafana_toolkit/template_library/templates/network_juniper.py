"""Juniper Junos monitoring dashboard template.

Uses SNMP exporter or Telegraf SNMP plugin with:
- IF-MIB (interface counters)
- JUNIPER-MIB (jnxOperatingCPU, jnxOperatingBuffer)
- JUNIPER-BGP4V2-MIB
- JUNIPER-CHASSIS-MIB (temperature, fans, PSU)
- BGP4-MIB (RFC 4273)
- OSPF-MIB
- Junos Telemetry (gRPC/JTI) via telegraf for modern platforms
"""

from __future__ import annotations

from typing import Union

from ads_grafana_toolkit.sdk.dashboard import Dashboard
from ads_grafana_toolkit.sdk.datasource import Datasource
from ads_grafana_toolkit.template_library.base import DashboardTemplate, TemplateVariable
from ads_grafana_toolkit.template_library.registry import register_template


class JuniperTemplate(DashboardTemplate):
    """Dashboard template for Juniper Junos device monitoring."""

    def __init__(self):
        super().__init__(
            name="network-juniper",
            description="Juniper Junos monitoring — routing engine CPU/memory, interfaces, BGP, OSPF, chassis health via SNMP/JTI",
            category="network-devices",
            tags=["juniper", "junos", "mx", "qfx", "ex", "srx", "ptx", "snmp", "jti", "network", "isp"],
            variables=[
                TemplateVariable(
                    name="device",
                    description="Juniper device hostname or IP",
                    default="$device",
                ),
                TemplateVariable(
                    name="interface",
                    description="Interface filter regex (e.g. ge-, xe-, et-)",
                    default=".*",
                    required=False,
                ),
            ],
        )

    def create(self, datasource: Union[Datasource, str], **kwargs) -> Dashboard:
        ds = self._resolve_datasource(datasource)
        device = kwargs.get("device", "$device")
        iface = kwargs.get("interface", "$interface")

        dashboard = Dashboard(
            title=kwargs.get("title", "Juniper Junos Monitoring"),
            description="Juniper MX/QFX/EX/SRX/PTX — routing engine, interfaces, BGP, OSPF, chassis",
            tags=["juniper", "junos", "snmp", "network"],
            datasource=ds,
            refresh="60s",
        )

        dashboard.add_variable(
            "device",
            query='label_values(jnxOperatingCPU, instance)',
            label="Device",
            multi=True,
            include_all=True,
        )
        dashboard.add_variable(
            "interface",
            query='label_values(ifDescr{instance=~"$device"}, ifDescr)',
            label="Interface",
            multi=True,
            include_all=True,
        )

        # ── Routing Engine Health ────────────────────────────────────────
        dashboard.add_row("Routing Engine")

        dashboard.add_panel(
            "RE CPU Utilization",
            query=f'jnxOperatingCPU{{instance=~"{device}",jnxOperatingContentsIndex="Routing Engine @0"}}',
            panel_type="gauge",
            width=6,
            height=6,
            unit="percent",
        ).add_threshold(None, "green").add_threshold(70, "yellow").add_threshold(90, "red")

        dashboard.add_panel(
            "RE Memory Utilization",
            query=f'jnxOperatingBuffer{{instance=~"{device}",jnxOperatingContentsIndex="Routing Engine @0"}}',
            panel_type="gauge",
            width=6,
            height=6,
            unit="percent",
        ).add_threshold(None, "green").add_threshold(70, "yellow").add_threshold(90, "red")

        dashboard.add_panel(
            "System Uptime",
            query=f'sysUpTime{{instance=~"{device}"}} / 100',
            panel_type="stat",
            width=6,
            height=6,
            unit="s",
        )

        dashboard.add_panel(
            "Chassis Temperature",
            query=f'jnxOperatingTemp{{instance=~"{device}"}}',
            panel_type="gauge",
            width=6,
            height=6,
            unit="celsius",
        ).add_threshold(None, "green").add_threshold(55, "yellow").add_threshold(70, "red")

        dashboard.add_panel(
            "RE CPU History",
            panel_type="timeseries",
            width=12,
            height=8,
            unit="percent",
        ).add_query(
            f'jnxOperatingCPU{{instance=~"{device}"}}',
            legend="CPU {{instance}} {{jnxOperatingContentsIndex}}"
        )

        dashboard.add_panel(
            "RE Memory History",
            panel_type="timeseries",
            width=12,
            height=8,
            unit="percent",
        ).add_query(
            f'jnxOperatingBuffer{{instance=~"{device}"}}',
            legend="Mem {{instance}} {{jnxOperatingContentsIndex}}"
        )

        # ── Interface Statistics ─────────────────────────────────────────
        dashboard.add_row("Interface Statistics")

        dashboard.add_panel(
            "Interface Traffic (bps)",
            panel_type="timeseries",
            width=12,
            height=8,
            unit="bps",
        ).add_query(
            f'rate(ifHCInOctets{{instance=~"{device}",ifDescr=~"{iface}"}}[5m]) * 8',
            legend="IN {{instance}} {{ifDescr}}"
        ).add_query(
            f'rate(ifHCOutOctets{{instance=~"{device}",ifDescr=~"{iface}"}}[5m]) * 8',
            legend="OUT {{instance}} {{ifDescr}}"
        )

        dashboard.add_panel(
            "Interface Errors",
            panel_type="timeseries",
            width=12,
            height=8,
            unit="pps",
        ).add_query(
            f'rate(ifInErrors{{instance=~"{device}",ifDescr=~"{iface}"}}[5m])',
            legend="In Errors {{ifDescr}}"
        ).add_query(
            f'rate(ifOutErrors{{instance=~"{device}",ifDescr=~"{iface}"}}[5m])',
            legend="Out Errors {{ifDescr}}"
        )

        dashboard.add_panel(
            "Juniper Interface Queue Drops",
            panel_type="timeseries",
            width=12,
            height=8,
            unit="pps",
        ).add_query(
            f'rate(jnxIfStatsOutqueueDrops{{instance=~"{device}",ifDescr=~"{iface}"}}[5m])',
            legend="Queue Drops {{ifDescr}}"
        )

        dashboard.add_panel(
            "Interface Optical Power (dBm)",
            panel_type="timeseries",
            width=12,
            height=8,
            unit="dBm",
        ).add_query(
            f'jnxDomCurrentRxLaserPower{{instance=~"{device}",ifDescr=~"{iface}"}} / 1000',
            legend="RX {{ifDescr}}"
        ).add_query(
            f'jnxDomCurrentTxLaserPower{{instance=~"{device}",ifDescr=~"{iface}"}} / 1000',
            legend="TX {{ifDescr}}"
        )

        # ── BGP ──────────────────────────────────────────────────────────
        dashboard.add_row("BGP (Juniper BGP4V2 MIB)")

        dashboard.add_panel(
            "BGP Peer States",
            query=f'jnxBgpM2PeerState{{instance=~"{device}"}}',
            panel_type="table",
            width=12,
            height=8,
        )

        dashboard.add_panel(
            "BGP Prefixes Received",
            query=f'jnxBgpM2PrefixInPrefixes{{instance=~"{device}"}}',
            panel_type="timeseries",
            width=12,
            height=8,
            unit="short",
        )

        # ── OSPF ─────────────────────────────────────────────────────────
        dashboard.add_row("OSPF")

        dashboard.add_panel(
            "OSPF Neighbor States",
            query=f'ospfNbrState{{instance=~"{device}"}}',
            panel_type="table",
            width=24,
            height=6,
        )

        # ── Chassis Health ───────────────────────────────────────────────
        dashboard.add_row("Chassis Health")

        dashboard.add_panel(
            "FPC / PIC Status",
            query=f'jnxOperatingState{{instance=~"{device}"}}',
            panel_type="table",
            width=12,
            height=8,
        )

        dashboard.add_panel(
            "Power Supply & Fan Health",
            panel_type="timeseries",
            width=12,
            height=8,
            unit="celsius",
        ).add_query(
            f'jnxOperatingTemp{{instance=~"{device}"}}',
            legend="Temp {{instance}} {{jnxOperatingContentsIndex}}"
        )

        return dashboard


register_template(JuniperTemplate())
