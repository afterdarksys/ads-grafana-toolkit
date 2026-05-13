"""Fortinet FortiGate monitoring dashboard template.

Uses SNMP exporter with Fortinet MIBs:
- FORTINET-FORTIGATE-MIB (fgSysCpuUsage, fgSysMemUsage, fgSysSes*)
- FORTINET-CORE-MIB
- Standard IF-MIB for interface counters
- FortiManager / FortiAnalyzer integration via syslog/API exporters
"""

from __future__ import annotations

from typing import Union

from ads_grafana_toolkit.sdk.dashboard import Dashboard
from ads_grafana_toolkit.sdk.datasource import Datasource
from ads_grafana_toolkit.template_library.base import DashboardTemplate, TemplateVariable
from ads_grafana_toolkit.template_library.registry import register_template


class FortinetTemplate(DashboardTemplate):
    """Dashboard template for Fortinet FortiGate monitoring."""

    def __init__(self):
        super().__init__(
            name="network-fortinet",
            description="Fortinet FortiGate monitoring — CPU, memory, sessions, VPN tunnels, IPS/AV, HA via SNMP",
            category="network-devices",
            tags=["fortinet", "fortigate", "firewall", "vpn", "snmp", "network", "security", "isp"],
            variables=[
                TemplateVariable(
                    name="device",
                    description="FortiGate hostname or IP",
                    default="$device",
                ),
                TemplateVariable(
                    name="vdom",
                    description="Virtual domain (root, vdom1, ...)",
                    default="root",
                    required=False,
                ),
            ],
        )

    def create(self, datasource: Union[Datasource, str], **kwargs) -> Dashboard:
        ds = self._resolve_datasource(datasource)
        device = kwargs.get("device", "$device")
        vdom = kwargs.get("vdom", "$vdom")

        dashboard = Dashboard(
            title=kwargs.get("title", "Fortinet FortiGate Monitoring"),
            description="FortiGate firewall — system resources, sessions, VPN, IPS, HA",
            tags=["fortinet", "fortigate", "firewall", "snmp"],
            datasource=ds,
            refresh="60s",
        )

        dashboard.add_variable(
            "device",
            query='label_values(fgSysCpuUsage, instance)',
            label="FortiGate",
            multi=True,
            include_all=True,
        )
        dashboard.add_variable(
            "vdom",
            query='label_values(fgVdEntCpuUsage{instance=~"$device"}, fgVdName)',
            label="VDOM",
            multi=True,
            include_all=True,
        )

        # ── System Overview ──────────────────────────────────────────────
        dashboard.add_row("System Resources")

        dashboard.add_panel(
            "CPU Usage",
            query=f'fgSysCpuUsage{{instance=~"{device}"}}',
            panel_type="gauge",
            width=6,
            height=6,
            unit="percent",
        ).add_threshold(None, "green").add_threshold(70, "yellow").add_threshold(90, "red")

        dashboard.add_panel(
            "Memory Usage",
            query=f'fgSysMemUsage{{instance=~"{device}"}}',
            panel_type="gauge",
            width=6,
            height=6,
            unit="percent",
        ).add_threshold(None, "green").add_threshold(70, "yellow").add_threshold(90, "red")

        dashboard.add_panel(
            "Active Sessions",
            query=f'fgSysSesCount{{instance=~"{device}"}}',
            panel_type="stat",
            width=6,
            height=6,
            unit="short",
        ).add_threshold(None, "green").add_threshold(800000, "yellow").add_threshold(950000, "red")

        dashboard.add_panel(
            "Session Setup Rate",
            query=f'fgSysSesRate1{{instance=~"{device}"}}',
            panel_type="stat",
            width=6,
            height=6,
            unit="pps",
        )

        dashboard.add_panel(
            "CPU History",
            panel_type="timeseries",
            width=12,
            height=8,
            unit="percent",
        ).add_query(
            f'fgSysCpuUsage{{instance=~"{device}"}}',
            legend="CPU {{instance}}"
        ).add_query(
            f'fgSysMemUsage{{instance=~"{device}"}}',
            legend="Memory {{instance}}"
        )

        dashboard.add_panel(
            "Sessions Over Time",
            panel_type="timeseries",
            width=12,
            height=8,
            unit="short",
        ).add_query(
            f'fgSysSesCount{{instance=~"{device}"}}',
            legend="Sessions {{instance}}"
        ).add_query(
            f'fgSysSes6Count{{instance=~"{device}"}}',
            legend="IPv6 Sessions {{instance}}"
        )

        # ── VPN ──────────────────────────────────────────────────────────
        dashboard.add_row("VPN Tunnels")

        dashboard.add_panel(
            "IPsec Tunnels Up",
            query=f'fgVpnTunEntStatus{{instance=~"{device}",fgVpnTunEntStatus="1"}}',
            panel_type="stat",
            width=6,
            height=4,
            unit="short",
        ).add_threshold(None, "green")

        dashboard.add_panel(
            "SSL-VPN Active Users",
            query=f'fgVpnSslStatsLoginUsers{{instance=~"{device}"}}',
            panel_type="stat",
            width=6,
            height=4,
            unit="short",
        )

        dashboard.add_panel(
            "IPsec Tunnel Traffic",
            panel_type="timeseries",
            width=12,
            height=8,
            unit="bps",
        ).add_query(
            f'rate(fgVpnTunEntInOctets{{instance=~"{device}"}}[5m]) * 8',
            legend="IN {{fgVpnTunEntPhase1Name}}"
        ).add_query(
            f'rate(fgVpnTunEntOutOctets{{instance=~"{device}"}}[5m]) * 8',
            legend="OUT {{fgVpnTunEntPhase1Name}}"
        )

        dashboard.add_panel(
            "Tunnel Status Table",
            query=f'fgVpnTunEntStatus{{instance=~"{device}"}}',
            panel_type="table",
            width=12,
            height=8,
        )

        # ── Security (IPS/AV) ────────────────────────────────────────────
        dashboard.add_row("Security Events")

        dashboard.add_panel(
            "IPS Detections (5m rate)",
            query=f'rate(fgIpsIntrusionsDetected{{instance=~"{device}"}}[5m])',
            panel_type="timeseries",
            width=12,
            height=8,
            unit="pps",
        )

        dashboard.add_panel(
            "Antivirus Detections (5m rate)",
            query=f'rate(fgAvVirusDetected{{instance=~"{device}"}}[5m])',
            panel_type="timeseries",
            width=12,
            height=8,
            unit="pps",
        )

        # ── Interface Statistics ─────────────────────────────────────────
        dashboard.add_row("Interface Statistics")

        dashboard.add_panel(
            "Interface Traffic",
            panel_type="timeseries",
            width=12,
            height=8,
            unit="bps",
        ).add_query(
            f'rate(ifHCInOctets{{instance=~"{device}"}}[5m]) * 8',
            legend="IN {{ifDescr}}"
        ).add_query(
            f'rate(ifHCOutOctets{{instance=~"{device}"}}[5m]) * 8',
            legend="OUT {{ifDescr}}"
        )

        dashboard.add_panel(
            "Interface Errors & Drops",
            panel_type="timeseries",
            width=12,
            height=8,
            unit="pps",
        ).add_query(
            f'rate(ifInErrors{{instance=~"{device}"}}[5m])',
            legend="In Errors {{ifDescr}}"
        ).add_query(
            f'rate(ifInDiscards{{instance=~"{device}"}}[5m])',
            legend="In Discards {{ifDescr}}"
        )

        # ── HA ───────────────────────────────────────────────────────────
        dashboard.add_row("High Availability")

        dashboard.add_panel(
            "HA Status",
            query=f'fgHaSystemMode{{instance=~"{device}"}}',
            panel_type="table",
            width=12,
            height=6,
        )

        dashboard.add_panel(
            "HA Cluster Members",
            query=f'fgHaStatsMemberSerial{{instance=~"{device}"}}',
            panel_type="table",
            width=12,
            height=6,
        )

        return dashboard


register_template(FortinetTemplate())
