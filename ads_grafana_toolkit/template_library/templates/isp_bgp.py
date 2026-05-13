"""ISP BGP monitoring dashboard template.

Supports metrics from:
- gobgp_exporter (github.com/osrg/gobgp)
- frr_exporter (github.com/tynany/frr_exporter)
- bird_exporter (github.com/czerwonk/bird_exporter)
- SNMP exporter with BGP4-MIB (RFC 4273)
"""

from __future__ import annotations

from typing import Union

from ads_grafana_toolkit.sdk.dashboard import Dashboard
from ads_grafana_toolkit.sdk.datasource import Datasource
from ads_grafana_toolkit.template_library.base import DashboardTemplate, TemplateVariable
from ads_grafana_toolkit.template_library.registry import register_template


class ISPBGPTemplate(DashboardTemplate):
    """Dashboard template for ISP BGP session and prefix monitoring."""

    def __init__(self):
        super().__init__(
            name="isp-bgp",
            description="Tier-1 ISP BGP session monitoring — peer states, prefix counts, AS-path analytics, route flap detection",
            category="isp",
            tags=["isp", "bgp", "routing", "peering", "mpls", "network"],
            variables=[
                TemplateVariable(
                    name="router",
                    description="Router instance to monitor",
                    default="$router",
                ),
                TemplateVariable(
                    name="peer_as",
                    description="Filter by peer AS number (leave blank for all)",
                    default="",
                    required=False,
                ),
                TemplateVariable(
                    name="exporter",
                    description="BGP exporter type: gobgp, frr, bird, snmp",
                    default="frr",
                ),
            ],
        )

    def create(self, datasource: Union[Datasource, str], **kwargs) -> Dashboard:
        ds = self._resolve_datasource(datasource)
        router = kwargs.get("router", "$router")
        exporter = kwargs.get("exporter", "frr")

        dashboard = Dashboard(
            title=kwargs.get("title", "ISP BGP Monitoring"),
            description="BGP session health, prefix counts, and routing analytics for Tier-1 ISP operations",
            tags=["isp", "bgp", "routing", "peering"],
            datasource=ds,
            refresh="30s",
        )

        dashboard.add_variable(
            "router",
            query='label_values(bgp_session_state, router)',
            label="Router",
            multi=True,
            include_all=True,
        )
        dashboard.add_variable(
            "peer_as",
            query='label_values(bgp_session_state{router=~"$router"}, peer_as)',
            label="Peer AS",
            multi=True,
            include_all=True,
        )

        # ── Overview row ────────────────────────────────────────────────
        dashboard.add_row("BGP Session Overview")

        dashboard.add_panel(
            "Established Sessions",
            query='count(bgp_session_state{router=~"$router",state="Established"})',
            panel_type="stat",
            width=4,
            height=4,
            unit="short",
        ).add_threshold(None, "green")

        dashboard.add_panel(
            "Total Sessions",
            query='count(bgp_session_state{router=~"$router"})',
            panel_type="stat",
            width=4,
            height=4,
            unit="short",
        )

        dashboard.add_panel(
            "Sessions Down",
            query='count(bgp_session_state{router=~"$router",state!="Established"}) or vector(0)',
            panel_type="stat",
            width=4,
            height=4,
            unit="short",
        ).add_threshold(None, "green").add_threshold(1, "red")

        dashboard.add_panel(
            "Total Prefixes Received",
            query='sum(bgp_prefixes_received{router=~"$router",peer_as=~"$peer_as"})',
            panel_type="stat",
            width=4,
            height=4,
            unit="short",
        )

        dashboard.add_panel(
            "Total Prefixes Advertised",
            query='sum(bgp_prefixes_sent{router=~"$router",peer_as=~"$peer_as"})',
            panel_type="stat",
            width=4,
            height=4,
            unit="short",
        )

        dashboard.add_panel(
            "Route Flaps (5m)",
            query='sum(increase(bgp_session_resets_total{router=~"$router"}[5m]))',
            panel_type="stat",
            width=4,
            height=4,
            unit="short",
        ).add_threshold(None, "green").add_threshold(5, "yellow").add_threshold(20, "red")

        # ── Session state table ─────────────────────────────────────────
        dashboard.add_row("Session Details")

        dashboard.add_panel(
            "BGP Session States",
            query='bgp_session_state{router=~"$router",peer_as=~"$peer_as"}',
            panel_type="table",
            width=24,
            height=8,
        )

        # ── Prefix trends ───────────────────────────────────────────────
        dashboard.add_row("Prefix Trends")

        dashboard.add_panel(
            "Prefixes Received Over Time",
            panel_type="timeseries",
            width=12,
            height=8,
            unit="short",
        ).add_query(
            'bgp_prefixes_received{router=~"$router",peer_as=~"$peer_as"}',
            legend="AS{{peer_as}} {{peer_address}}"
        )

        dashboard.add_panel(
            "Prefixes Advertised Over Time",
            panel_type="timeseries",
            width=12,
            height=8,
            unit="short",
        ).add_query(
            'bgp_prefixes_sent{router=~"$router",peer_as=~"$peer_as"}',
            legend="AS{{peer_as}} {{peer_address}}"
        )

        # ── BGP message rates ───────────────────────────────────────────
        dashboard.add_row("BGP Message Rates")

        dashboard.add_panel(
            "BGP Messages In/Out (rate 5m)",
            panel_type="timeseries",
            width=12,
            height=8,
            unit="pps",
        ).add_query(
            'rate(bgp_messages_received_total{router=~"$router",peer_as=~"$peer_as"}[5m])',
            legend="In AS{{peer_as}}"
        ).add_query(
            'rate(bgp_messages_sent_total{router=~"$router",peer_as=~"$peer_as"}[5m])',
            legend="Out AS{{peer_as}}"
        )

        dashboard.add_panel(
            "BGP Update Messages (rate 5m)",
            panel_type="timeseries",
            width=12,
            height=8,
            unit="pps",
        ).add_query(
            'rate(bgp_update_messages_received_total{router=~"$router",peer_as=~"$peer_as"}[5m])',
            legend="Updates In AS{{peer_as}}"
        )

        # ── Session uptime / flap history ───────────────────────────────
        dashboard.add_row("Session Stability")

        dashboard.add_panel(
            "BGP Session Uptime",
            query='bgp_session_up_duration_seconds{router=~"$router",peer_as=~"$peer_as"}',
            panel_type="timeseries",
            width=12,
            height=8,
            unit="s",
        )

        dashboard.add_panel(
            "Session Resets (5m rate)",
            query='rate(bgp_session_resets_total{router=~"$router",peer_as=~"$peer_as"}[5m])',
            panel_type="timeseries",
            width=12,
            height=8,
        )

        # ── AS-path analytics ───────────────────────────────────────────
        dashboard.add_row("AS-Path & Route Analytics")

        dashboard.add_panel(
            "Top Peers by Prefix Count",
            query='topk(20, bgp_prefixes_received{router=~"$router"})',
            panel_type="table",
            width=12,
            height=8,
            unit="short",
        )

        dashboard.add_panel(
            "Route Origin Validation State",
            panel_type="timeseries",
            width=12,
            height=8,
        ).add_query(
            'bgp_rib_route_valid_total{router=~"$router"}',
            legend="Valid"
        ).add_query(
            'bgp_rib_route_invalid_total{router=~"$router"}',
            legend="Invalid"
        ).add_query(
            'bgp_rib_route_unknown_total{router=~"$router"}',
            legend="Unknown"
        )

        return dashboard


register_template(ISPBGPTemplate())
