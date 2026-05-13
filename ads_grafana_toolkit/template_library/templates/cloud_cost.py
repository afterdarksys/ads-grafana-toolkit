"""Multi-cloud cost monitoring dashboard template (AWS + GCP + Azure billing)."""
from __future__ import annotations
from typing import Union
from ads_grafana_toolkit.sdk.dashboard import Dashboard
from ads_grafana_toolkit.sdk.datasource import Datasource
from ads_grafana_toolkit.template_library.base import DashboardTemplate, TemplateVariable
from ads_grafana_toolkit.template_library.registry import register_template


class CloudCostTemplate(DashboardTemplate):
    def __init__(self):
        super().__init__(
            name="cloud-cost",
            description="Multi-cloud cost monitoring — AWS Cost Explorer, GCP Billing, Azure Cost Management",
            category="cloud",
            tags=["cloud", "cost", "billing", "aws", "gcp", "azure", "finops", "multi-cloud"],
            variables=[TemplateVariable(name="period", description="Billing period", default="30d")],
        )

    def create(self, datasource: Union[Datasource, str], **kwargs) -> Dashboard:
        ds = self._resolve_datasource(datasource)
        dashboard = Dashboard(
            title=kwargs.get("title", "Multi-Cloud Cost Overview"),
            description="AWS + GCP + Azure billing and spend monitoring",
            tags=["cloud", "cost", "finops"], datasource=ds, refresh="1h",
        )

        dashboard.add_row("AWS Cost & Usage")
        dashboard.add_panel("AWS Estimated Charges (Total)", panel_type="stat", width=6, height=4, unit="currencyUSD",
            query='{"metricName":"EstimatedCharges","namespace":"AWS/Billing","dimensions":{"Currency":"USD"},"statistics":["Maximum"],"period":"86400","region":"us-east-1"}',
        ).add_threshold(None, "green").add_threshold(1000, "yellow").add_threshold(5000, "red")
        dashboard.add_panel("AWS Charges by Service", panel_type="timeseries", width=18, height=6, unit="currencyUSD",
            query='{"metricName":"EstimatedCharges","namespace":"AWS/Billing","dimensions":{},"statistics":["Maximum"],"matchExact":false,"period":"86400","region":"us-east-1"}',
        )
        dashboard.add_panel("AWS Data Transfer Out", panel_type="timeseries", width=12, height=6, unit="bytes",
            query='{"metricName":"BytesTransferred","namespace":"AWS/CloudFront","statistics":["Sum"],"period":"3600","region":"us-east-1"}',
        )
        dashboard.add_panel("AWS EC2 Running Hours", panel_type="timeseries", width=12, height=6,
            query='count(aws_ec2_instance_state_code{state="running"})',
        )

        dashboard.add_row("GCP Billing")
        dashboard.add_panel("GCP Monthly Spend", panel_type="stat", width=6, height=4, unit="currencyUSD",
            query='{"metricType":"billing.googleapis.com/billing/total_cost","aligner":"ALIGN_SUM","crossSeriesReducer":"REDUCE_SUM","groupBys":["resource.labels.project_id"]}',
        ).add_threshold(None, "green").add_threshold(1000, "yellow").add_threshold(5000, "red")
        dashboard.add_panel("GCP Cost by Service", panel_type="timeseries", width=18, height=6, unit="currencyUSD",
            query='{"metricType":"billing.googleapis.com/billing/total_cost","groupBys":["resource.labels.service_description"],"aligner":"ALIGN_SUM"}',
        )
        dashboard.add_panel("GCP BigQuery Bytes Processed", panel_type="timeseries", width=12, height=6, unit="bytes",
            query='{"metricType":"bigquery.googleapis.com/storage/table_count","aligner":"ALIGN_MEAN"}',
        )

        dashboard.add_row("Azure Cost Management")
        dashboard.add_panel("Azure Total Cost (MTD)", panel_type="stat", width=6, height=4, unit="currencyUSD",
            query='{"queryType":"Azure Monitor","namespace":"Microsoft.CostManagement","metricName":"ActualCost","aggregation":"Total"}',
        ).add_threshold(None, "green").add_threshold(1000, "yellow").add_threshold(5000, "red")
        dashboard.add_panel("Azure Cost by Resource Group", panel_type="timeseries", width=18, height=6, unit="currencyUSD",
            query='{"queryType":"Azure Monitor","namespace":"Microsoft.CostManagement","metricName":"ActualCost","aggregation":"Total"}',
        )

        dashboard.add_row("Multi-Cloud Summary")
        dashboard.add_panel("Total Cloud Spend (All Providers)", panel_type="stat", width=24, height=4, unit="currencyUSD",
            query='sum(cloud_provider_cost_total)',
        ).add_threshold(None, "green").add_threshold(5000, "yellow").add_threshold(20000, "red")

        return dashboard

register_template(CloudCostTemplate())
