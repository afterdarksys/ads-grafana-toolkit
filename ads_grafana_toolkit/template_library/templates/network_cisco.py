"""Cisco IOS/IOS-XE/IOS-XR/NX-OS monitoring dashboard template.

Uses SNMP exporter or Telegraf SNMP plugin with standard MIBs:
- IF-MIB (interface counters)
- CISCO-PROCESS-MIB (CPU, memory)
- ENTITY-MIB (hardware inventory)
- CISCO-BGP4-MIB, BGP4-MIB
- OSPF-MIB
- CISCO-MEMORY-POOL-MIB
"""

from __future__ import annotations

from typing import Union

from ads_grafana_toolkit.sdk.dashboard import Dashboard
from ads_grafana_toolkit.sdk.datasource import Datasource
from ads_grafana_toolkit.template_library.base import DashboardTemplate, TemplateVariable
from ads_grafana_toolkit.template_library.registry import register_template


class CiscoTemplate(DashboardTemplate):
    """Dashboard template for Cisco network device monitoring via SNMP."""

    def __init__(self):
        super().__init__(
            name="network-cisco",
            description="Cisco IOS/IOS-XE/IOS-XR/NX-OS monitoring — CPU, memory, interfaces, BGP, OSPF via SNMP",
            category="network-devices",
            tags=["cisco", "ios", "ios-xe", "ios-xr", "nx-os", "snmp", "network", "isp"],
            variables=[
                TemplateVariable(
                    name="device",
                    description="Cisco device hostname or IP",
                    default="$device",
                ),
                TemplateVariable(
                    name="interface",
                    description="Interface filter regex",
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
            title=kwargs.get("title", "Cisco Device Monitoring"),
            description="Cisco IOS/IOS-XE/IOS-XR/NX-OS — CPU, memory, interfaces, routing protocols",
            tags=["cisco", "snmp", "network"],
            datasource=ds,
            refresh="60s",
        )

        dashboard.add_variable(
            "device",
            query='label_values(sysUpTime, instance)',
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

        # ── Device health overview ───────────────────────────────────────
        dashboard.add_row("Device Health")

        dashboard.add_panel(
            "CPU Utilization (5min)",
            query=f'cpmCPUTotal5minRev{{instance=~"{device}"}}',
            panel_type="gauge",
            width=6,
            height=6,
            unit="percent",
        ).add_threshold(None, "green").add_threshold(70, "yellow").add_threshold(90, "red")

        dashboard.add_panel(
            "Memory Utilization",
            query=f'ciscoMemoryPoolUsed{{instance=~"{device}"}} / (ciscoMemoryPoolUsed{{instance=~"{device}"}} + ciscoMemoryPoolFree{{instance=~"{device}"}}) * 100',
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
            "Environment Temperature",
            query=f'ciscoEnvMonTemperatureStatusValue{{instance=~"{device}"}}',
            panel_type="gauge",
            width=6,
            height=6,
            unit="celsius",
        ).add_threshold(None, "green").add_threshold(50, "yellow").add_threshold(65, "red")

        # ── CPU history ──────────────────────────────────────────────────
        dashboard.add_row("CPU & Memory")

        dashboard.add_panel(
            "CPU Utilization History",
            panel_type="timeseries",
            width=12,
            height=8,
            unit="percent",
        ).add_query(
            f'cpmCPUTotal5minRev{{instance=~"{device}"}}',
            legend="5min {{instance}}"
        ).add_query(
            f'cpmCPUTotal1minRev{{instance=~"{device}"}}',
            legend="1min {{instance}}"
        )

        dashboard.add_panel(
            "Memory Pool Usage",
            panel_type="timeseries",
            width=12,
            height=8,
            unit="bytes",
        ).add_query(
            f'ciscoMemoryPoolUsed{{instance=~"{device}"}}',
            legend="Used {{instance}} {{ciscoMemoryPoolName}}"
        ).add_query(
            f'ciscoMemoryPoolFree{{instance=~"{device}"}}',
            legend="Free {{instance}} {{ciscoMemoryPoolName}}"
        )

        # ── Interface counters ───────────────────────────────────────────
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
            "Interface Errors & Discards",
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
        ).add_query(
            f'rate(ifInDiscards{{instance=~"{device}",ifDescr=~"{iface}"}}[5m])',
            legend="In Discards {{ifDescr}}"
        ).add_query(
            f'rate(ifOutDiscards{{instance=~"{device}",ifDescr=~"{iface}"}}[5m])',
            legend="Out Discards {{ifDescr}}"
        )

        dashboard.add_panel(
            "Interface Operational Status",
            query=f'ifOperStatus{{instance=~"{device}",ifDescr=~"{iface}"}}',
            panel_type="table",
            width=24,
            height=6,
        )

        # ── OSPF ─────────────────────────────────────────────────────────
        dashboard.add_row("OSPF")

        dashboard.add_panel(
            "OSPF Neighbor States",
            query=f'ospfNbrState{{instance=~"{device}"}}',
            panel_type="table",
            width=12,
            height=6,
        )

        dashboard.add_panel(
            "OSPF LSA Counts",
            panel_type="timeseries",
            width=12,
            height=6,
        ).add_query(
            f'ospfAreaLsaCount{{instance=~"{device}"}}',
            legend="{{instance}} Area {{ospfAreaId}}"
        )

        # ── BGP ──────────────────────────────────────────────────────────
        dashboard.add_row("BGP")

        dashboard.add_panel(
            "BGP Peer States",
            query=f'bgpPeerState{{instance=~"{device}"}}',
            panel_type="table",
            width=12,
            height=8,
        )

        dashboard.add_panel(
            "BGP Prefixes Received",
            query=f'cbgpPeerAcceptedPrefixes{{instance=~"{device}"}}',
            panel_type="timeseries",
            width=12,
            height=8,
            unit="short",
        )

        # ── Hardware / Environment ────────────────────────────────────────
        dashboard.add_row("Hardware & Environment")

        dashboard.add_panel(
            "Fan Status",
            query=f'ciscoEnvMonFanState{{instance=~"{device}"}}',
            panel_type="table",
            width=12,
            height=6,
        )

        dashboard.add_panel(
            "Power Supply Status",
            query=f'ciscoEnvMonSupplyState{{instance=~"{device}"}}',
            panel_type="table",
            width=12,
            height=6,
        )

        return dashboard


register_template(CiscoTemplate())
