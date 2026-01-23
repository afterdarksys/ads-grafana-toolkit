#!/usr/bin/env python3
"""
Writers Toolkit
Export Grafana dashboards to documentation, reports, and other formats.
"""

import json
import sys
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass


@dataclass
class DashboardDoc:
    """Dashboard documentation structure."""
    title: str
    description: str
    tags: List[str]
    panels: List[Dict[str, Any]]
    variables: List[Dict[str, Any]]
    created: str
    updated: str


class WritersToolkit:
    """Generate documentation and reports from Grafana dashboards."""

    def __init__(self, grafana_url: str = "http://localhost:3000",
                 api_key: Optional[str] = None):
        self.grafana_url = grafana_url.rstrip("/")
        self.api_key = api_key

    def _request(self, endpoint: str) -> Any:
        """Make API request to Grafana."""
        url = f"{self.grafana_url}{endpoint}"
        headers = {"Accept": "application/json"}

        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as response:
                return json.loads(response.read())
        except urllib.error.HTTPError as e:
            if e.code == 401:
                print("Error: Unauthorized. API key may be required.", file=sys.stderr)
            else:
                print(f"HTTP Error {e.code}: {e.reason}", file=sys.stderr)
            raise
        except urllib.error.URLError as e:
            print(f"Connection error: {e.reason}", file=sys.stderr)
            raise

    def fetch_dashboard(self, uid: str) -> Dict[str, Any]:
        """Fetch dashboard by UID."""
        return self._request(f"/api/dashboards/uid/{uid}")

    def list_dashboards(self) -> List[Dict[str, Any]]:
        """List all dashboards."""
        return self._request("/api/search?type=dash-db")

    def load_dashboard_file(self, filepath: str) -> Dict[str, Any]:
        """Load dashboard from JSON file."""
        with open(filepath) as f:
            data = json.load(f)

        # Handle both raw dashboard and API response format
        if "dashboard" in data:
            return data
        else:
            return {"dashboard": data}

    def parse_dashboard(self, dashboard_data: Dict[str, Any]) -> DashboardDoc:
        """Parse dashboard into documentation structure."""
        dash = dashboard_data.get("dashboard", dashboard_data)

        return DashboardDoc(
            title=dash.get("title", "Untitled"),
            description=dash.get("description", ""),
            tags=dash.get("tags", []),
            panels=[p for p in dash.get("panels", []) if p.get("type") != "row"],
            variables=dash.get("templating", {}).get("list", []),
            created=dashboard_data.get("meta", {}).get("created", ""),
            updated=dashboard_data.get("meta", {}).get("updated", "")
        )

    def export_markdown(self, doc: DashboardDoc, output_file: str):
        """Export dashboard as Markdown documentation."""
        lines = []

        # Header
        lines.append(f"# {doc.title}\n")

        if doc.description:
            lines.append(f"{doc.description}\n")

        # Metadata
        lines.append("## Dashboard Information\n")
        lines.append(f"- **Tags**: {', '.join(doc.tags) if doc.tags else 'None'}")

        if doc.created:
            lines.append(f"- **Created**: {doc.created}")
        if doc.updated:
            lines.append(f"- **Updated**: {doc.updated}")

        lines.append("")

        # Variables
        if doc.variables:
            lines.append("## Variables\n")
            for var in doc.variables:
                name = var.get("name", "")
                var_type = var.get("type", "")
                label = var.get("label", name)
                lines.append(f"### {label} (`${name}`)\n")
                lines.append(f"- **Type**: {var_type}")

                if var_type == "query":
                    query = var.get("query", "")
                    if isinstance(query, str):
                        lines.append(f"- **Query**: `{query}`")

                if var.get("multi"):
                    lines.append("- **Multi-select**: Yes")
                if var.get("includeAll"):
                    lines.append("- **Include All**: Yes")

                lines.append("")

        # Panels
        lines.append("## Panels\n")

        for panel in doc.panels:
            title = panel.get("title", "Untitled Panel")
            panel_type = panel.get("type", "unknown")
            description = panel.get("description", "")

            lines.append(f"### {title}\n")
            lines.append(f"**Type**: {panel_type}\n")

            if description:
                lines.append(f"**Description**: {description}\n")

            # Queries/targets
            targets = panel.get("targets", [])
            if targets:
                lines.append("**Queries**:\n")
                for i, target in enumerate(targets, 1):
                    expr = target.get("expr") or target.get("query", "")
                    if expr:
                        lines.append(f"{i}. ```promql\n{expr}\n```")

                    legend = target.get("legendFormat", "")
                    if legend:
                        lines.append(f"   - Legend: `{legend}`")

                lines.append("")

            # Field config
            field_config = panel.get("fieldConfig", {}).get("defaults", {})
            unit = field_config.get("unit")
            if unit:
                lines.append(f"**Unit**: {unit}\n")

            # Thresholds
            thresholds = field_config.get("thresholds", {}).get("steps", [])
            if thresholds and len(thresholds) > 1:
                lines.append("**Thresholds**:\n")
                for threshold in thresholds:
                    value = threshold.get("value")
                    color = threshold.get("color")
                    if value is not None:
                        lines.append(f"- {value}: {color}")

            lines.append("")

        # Write file
        with open(output_file, 'w') as f:
            f.write("\n".join(lines))

        print(f"Markdown documentation written to: {output_file}")

    def export_html(self, doc: DashboardDoc, output_file: str):
        """Export dashboard as HTML documentation."""
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{doc.title} - Dashboard Documentation</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            line-height: 1.6;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }}
        .container {{
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #333;
            border-bottom: 3px solid #f96332;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #555;
            margin-top: 30px;
            border-bottom: 1px solid #ddd;
            padding-bottom: 5px;
        }}
        h3 {{
            color: #666;
            margin-top: 20px;
        }}
        .tags {{
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }}
        .tag {{
            background: #e7f3ff;
            color: #0066cc;
            padding: 4px 12px;
            border-radius: 4px;
            font-size: 0.9em;
        }}
        .panel {{
            background: #f9f9f9;
            padding: 15px;
            margin: 15px 0;
            border-left: 4px solid #f96332;
            border-radius: 4px;
        }}
        .query {{
            background: #2d2d2d;
            color: #f8f8f2;
            padding: 15px;
            border-radius: 4px;
            overflow-x: auto;
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
        }}
        .meta {{
            color: #666;
            font-size: 0.9em;
        }}
        .variable {{
            background: #fff8e6;
            padding: 10px;
            margin: 10px 0;
            border-radius: 4px;
        }}
        ul {{
            margin: 5px 0;
        }}
        .footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            color: #999;
            font-size: 0.85em;
            text-align: center;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{doc.title}</h1>
"""

        if doc.description:
            html += f"        <p>{doc.description}</p>\n"

        # Metadata
        html += "        <div class='meta'>\n"
        if doc.tags:
            html += "            <div class='tags'>\n"
            for tag in doc.tags:
                html += f"                <span class='tag'>{tag}</span>\n"
            html += "            </div>\n"
        if doc.created:
            html += f"            <p>Created: {doc.created}</p>\n"
        if doc.updated:
            html += f"            <p>Updated: {doc.updated}</p>\n"
        html += "        </div>\n"

        # Variables
        if doc.variables:
            html += "        <h2>Variables</h2>\n"
            for var in doc.variables:
                name = var.get("name", "")
                label = var.get("label", name)
                var_type = var.get("type", "")

                html += f"        <div class='variable'>\n"
                html += f"            <h3>{label} (<code>${name}</code>)</h3>\n"
                html += f"            <p><strong>Type:</strong> {var_type}</p>\n"

                if var_type == "query":
                    query = var.get("query", "")
                    if isinstance(query, str):
                        html += f"            <p><strong>Query:</strong> <code>{query}</code></p>\n"

                html += "        </div>\n"

        # Panels
        html += "        <h2>Panels</h2>\n"

        for panel in doc.panels:
            title = panel.get("title", "Untitled Panel")
            panel_type = panel.get("type", "unknown")
            description = panel.get("description", "")

            html += f"        <div class='panel'>\n"
            html += f"            <h3>{title}</h3>\n"
            html += f"            <p><strong>Type:</strong> {panel_type}</p>\n"

            if description:
                html += f"            <p>{description}</p>\n"

            # Queries
            targets = panel.get("targets", [])
            if targets:
                html += "            <h4>Queries:</h4>\n"
                for target in targets:
                    expr = target.get("expr") or target.get("query", "")
                    if expr:
                        html += f"            <div class='query'>{expr}</div>\n"

            html += "        </div>\n"

        # Footer
        html += f"""        <div class='footer'>
            <p>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
    </div>
</body>
</html>
"""

        with open(output_file, 'w') as f:
            f.write(html)

        print(f"HTML documentation written to: {output_file}")

    def export_json_report(self, doc: DashboardDoc, output_file: str):
        """Export dashboard as structured JSON report."""
        report = {
            "dashboard": {
                "title": doc.title,
                "description": doc.description,
                "tags": doc.tags,
                "created": doc.created,
                "updated": doc.updated,
            },
            "variables": [
                {
                    "name": var.get("name"),
                    "label": var.get("label"),
                    "type": var.get("type"),
                    "query": var.get("query") if var.get("type") == "query" else None,
                }
                for var in doc.variables
            ],
            "panels": [
                {
                    "title": panel.get("title"),
                    "type": panel.get("type"),
                    "description": panel.get("description"),
                    "queries": [
                        target.get("expr") or target.get("query")
                        for target in panel.get("targets", [])
                        if target.get("expr") or target.get("query")
                    ],
                }
                for panel in doc.panels
            ],
            "statistics": {
                "total_panels": len(doc.panels),
                "total_variables": len(doc.variables),
                "panel_types": self._count_panel_types(doc.panels),
            }
        }

        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)

        print(f"JSON report written to: {output_file}")

    def _count_panel_types(self, panels: List[Dict]) -> Dict[str, int]:
        """Count panel types."""
        counts = {}
        for panel in panels:
            panel_type = panel.get("type", "unknown")
            counts[panel_type] = counts.get(panel_type, 0) + 1
        return counts

    def generate_readme(self, dashboards: List[DashboardDoc], output_file: str):
        """Generate README documenting multiple dashboards."""
        lines = [
            "# Grafana Dashboards",
            "",
            f"Documentation generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## Dashboards",
            ""
        ]

        for doc in dashboards:
            lines.append(f"### {doc.title}")
            if doc.description:
                lines.append(f"{doc.description}")
            if doc.tags:
                lines.append(f"**Tags**: {', '.join(doc.tags)}")
            lines.append(f"**Panels**: {len(doc.panels)}")
            lines.append("")

        with open(output_file, 'w') as f:
            f.write("\n".join(lines))

        print(f"README written to: {output_file}")


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Writers Toolkit - Generate documentation from Grafana dashboards"
    )

    parser.add_argument("input", help="Dashboard JSON file or UID (if using --fetch)")
    parser.add_argument("-o", "--output", help="Output file")
    parser.add_argument("-f", "--format", choices=["markdown", "html", "json"],
                        default="markdown", help="Output format")
    parser.add_argument("--fetch", action="store_true",
                        help="Fetch dashboard from Grafana API")
    parser.add_argument("--grafana-url", default="http://localhost:3000",
                        help="Grafana URL")
    parser.add_argument("--api-key", help="Grafana API key")

    args = parser.parse_args()

    toolkit = WritersToolkit(grafana_url=args.grafana_url, api_key=args.api_key)

    # Load dashboard
    if args.fetch:
        print(f"Fetching dashboard {args.input} from Grafana...")
        dashboard_data = toolkit.fetch_dashboard(args.input)
    else:
        print(f"Loading dashboard from {args.input}...")
        dashboard_data = toolkit.load_dashboard_file(args.input)

    # Parse dashboard
    doc = toolkit.parse_dashboard(dashboard_data)

    # Generate output filename if not specified
    if not args.output:
        safe_title = "".join(c if c.isalnum() else "_" for c in doc.title).lower()
        ext_map = {"markdown": "md", "html": "html", "json": "json"}
        args.output = f"{safe_title}.{ext_map[args.format]}"

    # Export
    if args.format == "markdown":
        toolkit.export_markdown(doc, args.output)
    elif args.format == "html":
        toolkit.export_html(doc, args.output)
    elif args.format == "json":
        toolkit.export_json_report(doc, args.output)


if __name__ == "__main__":
    main()
