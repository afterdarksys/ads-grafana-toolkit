"""Palo Alto Networks firewall monitoring dashboard template.

Uses SNMP exporter with PAN-OS MIBs:
- PAN-COMMON-MIB (panSysSwVersion, session stats)
- PAN-GLOBAL-REG-MIB
- Standard IF-MIB for interface counters
- Panorama/PAN-OS REST API metrics via custom exporters
"""

from __future__ import annotations

from typing import Union

from ads_grafana_toolkit.sdk.dashboard import Dashboard
from ads_grafana_toolkit.sdk.datasource import Datasource
from ads_grafana_toolkit.template_library.base import DashboardTemplate, TemplateVariable
from ads_grafana_toolkit.template_library.registry import register_template


class PaloAltoTemplate(DashboardTemplate):
    """Dashboard template for Palo Alto Networks NGFW monitoring."""

    def __init__(self):
        super().__init__(
            name="network-paloalto",
            description="Palo Alto Networks PA-Series/VM-Series/CN-Series NGFW — sessions, threats, interfaces, HA, GlobalProtect",
            category="network-devices",
            tags=["paloalto", "pan-os", "firewall", "ngfw", "snmp", "network", "security", "isp"],
            variables=[
                TemplateVariable(
                    name="device",
                    description="Palo Alto firewall hostname or IP",
                    default="$device",
                ),
                TemplateVariable(
                    name="vsys",
                    description="Virtual system (vsys1, vsys2, ...)",
                    default="vsys1",
                    required=False,
                ),
            ],
        )

    def create(self, datasource: Union[Datasource, str], **kwargs) -> Dashboard:
        ds = self._resolve_datasource(datasource)
        device = kwargs.get("device", "$device")
        vsys = kwargs.get("vsys", "$vsys")

        dashboard = Dashboard(
            title=kwargs.get("title", "Palo Alto Firewall Monitoring"),
            description="PA-Series/VM-Series NGFW — session table, threat activity, interfaces, HA state",
            tags=["paloalto", "firewall", "ngfw", "snmp"],
            datasource=ds,
            refresh="60s",
        )

        dashboard.add_variable(
            "device",
            query='label_values(panSysActiveSessions, instance)',
            label="Firewall",
            multi=True,
            include_all=True,
        )
        dashboard.add_variable(
            "vsys",
            query='label_values(panVsysActiveSessions{instance=~"$device"}, vsys)',
            label="VSYS",
            multi=True,
            include_all=True,
        )

        # ── Session Overview ─────────────────────────────────────────────
        dashboard.add_row("Session Table")

        dashboard.add_panel(
            "Active Sessions",
            query=f'panSysActiveSessions{{instance=~"{device}"}}',
            panel_type="gauge",
            width=6,
            height=6,
            unit="short",
        ).add_threshold(None, "green").add_threshold(500000, "yellow").add_threshold(900000, "red")

        dashboard.add_panel(
            "Max Sessions",
            query=f'panSysMaxSessions{{instance=~"{device}"}}',
            panel_type="stat",
            width=6,
            height=6,
            unit="short",
        )

        dashboard.add_panel(
            "Session Utilization %",
            query=f'panSysActiveSessions{{instance=~"{device}"}} / panSysMaxSessions{{instance=~"{device}"}} * 100',
            panel_type="gauge",
            width=6,
            height=6,
            unit="percent",
        ).add_threshold(None, "green").add_threshold(70, "yellow").add_threshold(90, "red")

        dashboard.add_panel(
            "HA State",
            query=f'panSysHAState{{instance=~"{device}"}}',
            panel_type="stat",
            width=6,
            height=6,
        )

        dashboard.add_panel(
            "Active Sessions Over Time",
            panel_type="timeseries",
            width=12,
            height=8,
            unit="short",
        ).add_query(
            f'panSysActiveSessions{{instance=~"{device}"}}',
            legend="Active {{instance}}"
        ).add_query(
            f'panSysActiveTCPSessions{{instance=~"{device}"}}',
            legend="TCP {{instance}}"
        ).add_query(
            f'panSysActiveUDPSessions{{instance=~"{device}"}}',
            legend="UDP {{instance}}"
        )

        dashboard.add_panel(
            "New Sessions per Second",
            query=f'rate(panSysSessionsCreated{{instance=~"{device}"}}[5m])',
            panel_type="timeseries",
            width=12,
            height=8,
            unit="pps",
        )

        # ── Threat & Security ────────────────────────────────────────────
        dashboard.add_row("Threat & Security Activity")

        dashboard.add_panel(
            "Threats Detected (rate 5m)",
            query=f'rate(panSysThreatTotal{{instance=~"{device}"}}[5m])',
            panel_type="stat",
            width=6,
            height=4,
            unit="pps",
        ).add_threshold(None, "green").add_threshold(10, "yellow").add_threshold(100, "red")

        dashboard.add_panel(
            "URL Filtering Violations",
            query=f'rate(panSysURLTotal{{instance=~"{device}"}}[5m])',
            panel_type="stat",
            width=6,
            height=4,
            unit="pps",
        )

        dashboard.add_panel(
            "SSL Proxy Sessions",
            query=f'panSysActiveSSLProxySessions{{instance=~"{device}"}}',
            panel_type="stat",
            width=6,
            height=4,
            unit="short",
        )

        dashboard.add_panel(
            "GlobalProtect Tunnels",
            query=f'panGPGatewayCurrentVPN{{instance=~"{device}"}}',
            panel_type="stat",
            width=6,
            height=4,
            unit="short",
        )

        dashboard.add_panel(
            "Threat Activity Over Time",
            panel_type="timeseries",
            width=24,
            height=8,
            unit="pps",
        ).add_query(
            f'rate(panSysThreatTotal{{instance=~"{device}"}}[5m])',
            legend="Threats {{instance}}"
        ).add_query(
            f'rate(panSysVulnerability{{instance=~"{device}"}}[5m])',
            legend="Vulnerabilities {{instance}}"
        ).add_query(
            f'rate(panSysVirus{{instance=~"{device}"}}[5m])',
            legend="Virus {{instance}}"
        ).add_query(
            f'rate(panSysSpyware{{instance=~"{device}"}}[5m])',
            legend="Spyware {{instance}}"
        )

        # ── Resource Utilization ─────────────────────────────────────────
        dashboard.add_row("Device Resources")

        dashboard.add_panel(
            "Dataplane CPU %",
            query=f'panSysDPCPUUtilizationPct{{instance=~"{device}"}}',
            panel_type="gauge",
            width=6,
            height=6,
            unit="percent",
        ).add_threshold(None, "green").add_threshold(60, "yellow").add_threshold(85, "red")

        dashboard.add_panel(
            "Management CPU %",
            query=f'panSysMgmtCPUUtilizationPct{{instance=~"{device}"}}',
            panel_type="gauge",
            width=6,
            height=6,
            unit="percent",
        ).add_threshold(None, "green").add_threshold(70, "yellow").add_threshold(90, "red")

        dashboard.add_panel(
            "Dataplane Memory %",
            query=f'panSysDPMemoryUtilization{{instance=~"{device}"}}',
            panel_type="gauge",
            width=6,
            height=6,
            unit="percent",
        ).add_threshold(None, "green").add_threshold(70, "yellow").add_threshold(90, "red")

        dashboard.add_panel(
            "Log Rate",
            query=f'rate(panSysLogRate{{instance=~"{device}"}}[5m])',
            panel_type="stat",
            width=6,
            height=6,
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
            "Interface Errors",
            panel_type="timeseries",
            width=12,
            height=8,
            unit="pps",
        ).add_query(
            f'rate(ifInErrors{{instance=~"{device}"}}[5m])',
            legend="In Errors {{ifDescr}}"
        ).add_query(
            f'rate(ifOutErrors{{instance=~"{device}"}}[5m])',
            legend="Out Errors {{ifDescr}}"
        )

        # ── HA Status ────────────────────────────────────────────────────
        dashboard.add_row("High Availability")

        dashboard.add_panel(
            "HA Sync State",
            query=f'panSysHASyncState{{instance=~"{device}"}}',
            panel_type="table",
            width=12,
            height=6,
        )

        dashboard.add_panel(
            "HA Failover Events",
            query=f'increase(panSysHAFailoverCount{{instance=~"{device}"}}[1h])',
            panel_type="timeseries",
            width=12,
            height=6,
        )

        return dashboard


register_template(PaloAltoTemplate())
