"""Main CLI entry point for ads-grafana-toolkit."""

from __future__ import annotations

import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


@click.group()
@click.version_option(package_name="ads-grafana-toolkit")
def cli():
    """ads-grafana-toolkit - Simplify Grafana dashboard creation.

    Create dashboards using config files, templates, interactive wizard,
    or natural language descriptions.
    """
    pass


@cli.command()
@click.argument("config_file", type=click.Path(exists=True))
@click.option("-o", "--output", type=click.Path(), help="Output JSON file path")
@click.option("--stdout", is_flag=True, help="Output to stdout instead of file")
def convert(config_file: str, output: str | None, stdout: bool):
    """Convert a YAML/TOML config file to Grafana dashboard JSON.

    Example:
        ads-grafana-toolkit convert dashboard.yaml -o dashboard.json
    """
    from ads_grafana_toolkit.simple.converter import convert_file, load_config, convert_config

    try:
        if stdout:
            config = load_config(config_file)
            dashboard = convert_config(config)
            click.echo(dashboard.to_json())
        else:
            output_path = output or Path(config_file).with_suffix(".json")
            result = convert_file(config_file, output_path)
            console.print(f"[green]✓[/green] Dashboard saved to: {result}")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)


@cli.command()
def wizard():
    """Launch interactive dashboard creation wizard.

    Guides you through creating a dashboard step by step.
    """
    from ads_grafana_toolkit.cli.wizard import run_wizard, save_dashboard_interactive

    try:
        dashboard = run_wizard()
        if dashboard:
            save_dashboard_interactive(dashboard)
        else:
            console.print("[yellow]Wizard cancelled.[/yellow]")
    except KeyboardInterrupt:
        console.print("\n[yellow]Wizard cancelled.[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)


@cli.group()
def templates():
    """Work with pre-built dashboard templates."""
    pass


@templates.command(name="list")
@click.option("-c", "--category", help="Filter by category")
def templates_list(category: str | None):
    """List available dashboard templates."""
    from ads_grafana_toolkit.template_library import list_templates

    templates_data = list_templates(category)

    if not templates_data:
        console.print("[yellow]No templates found.[/yellow]")
        return

    table = Table(title="Available Templates")
    table.add_column("Name", style="cyan")
    table.add_column("Category", style="green")
    table.add_column("Description")

    for t in templates_data:
        table.add_row(t["name"], t["category"], t["description"])

    console.print(table)


@templates.command(name="info")
@click.argument("name")
def templates_info(name: str):
    """Show details about a specific template."""
    from ads_grafana_toolkit.template_library import get_template

    try:
        template = get_template(name)

        console.print(Panel.fit(
            f"[bold]{template.name}[/bold]\n\n"
            f"[dim]Category:[/dim] {template.category}\n"
            f"[dim]Tags:[/dim] {', '.join(template.tags)}\n\n"
            f"{template.description}",
            title="Template Info",
            border_style="blue"
        ))

        if template.variables:
            table = Table(title="Variables")
            table.add_column("Name", style="cyan")
            table.add_column("Description")
            table.add_column("Default", style="dim")
            table.add_column("Required", style="yellow")

            for v in template.variables:
                table.add_row(
                    v.name,
                    v.description,
                    v.default or "-",
                    "Yes" if v.required else "No"
                )

            console.print(table)

    except KeyError as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)


@templates.command(name="create")
@click.argument("name")
@click.option("-d", "--datasource", default="Prometheus", help="Datasource name")
@click.option("-o", "--output", type=click.Path(), help="Output file path")
@click.option("--var", multiple=True, help="Template variable in key=value format")
def templates_create(name: str, datasource: str, output: str | None, var: tuple):
    """Create a dashboard from a template.

    Example:
        ads-grafana-toolkit templates create node-exporter -d Prometheus -o node.json
    """
    from ads_grafana_toolkit.template_library import create_from_template

    try:
        variables = {}
        for v in var:
            if "=" in v:
                key, value = v.split("=", 1)
                variables[key] = value

        dashboard = create_from_template(name, datasource, **variables)

        if output:
            dashboard.save(output)
            console.print(f"[green]✓[/green] Dashboard saved to: {output}")
        else:
            click.echo(dashboard.to_json())

    except KeyError as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)


@cli.command()
@click.argument("prompt", nargs=-1, required=True)
@click.option("-d", "--datasource", default="Prometheus", help="Datasource name")
@click.option("-o", "--output", type=click.Path(), help="Output file path")
@click.option("--no-openai", is_flag=True, help="Don't use OpenAI API")
def generate(prompt: tuple, datasource: str, output: str | None, no_openai: bool):
    """Generate a dashboard from a natural language description.

    Example:
        ads-grafana-toolkit generate "Create a dashboard showing CPU and memory usage"

        ads-grafana-toolkit generate "Dashboard for HTTP latency p99 grouped by service" -o api.json
    """
    from ads_grafana_toolkit.nlp_interface import generate_from_text

    try:
        prompt_text = " ".join(prompt)
        dashboard = generate_from_text(
            prompt_text,
            datasource=datasource,
            use_openai=not no_openai,
        )

        if output:
            dashboard.save(output)
            console.print(f"[green]✓[/green] Dashboard saved to: {output}")
        else:
            click.echo(dashboard.to_json())

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)


@cli.command()
@click.argument("input_file", type=click.Path(exists=True))
@click.option("-o", "--output", type=click.Path(), help="Output file path")
def validate(input_file: str, output: str | None):
    """Validate a Grafana dashboard JSON file.

    Checks for common issues and optionally outputs a cleaned version.
    """
    import json

    try:
        with open(input_file) as f:
            data = json.load(f)

        issues = []

        # Check required fields
        if "title" not in data:
            issues.append("Missing 'title' field")
        if "panels" not in data:
            issues.append("Missing 'panels' field")

        # Check panels
        for i, panel in enumerate(data.get("panels", [])):
            if "id" not in panel:
                issues.append(f"Panel {i}: missing 'id'")
            if "type" not in panel:
                issues.append(f"Panel {i}: missing 'type'")
            if "gridPos" not in panel:
                issues.append(f"Panel {i}: missing 'gridPos'")

        if issues:
            console.print("[yellow]Validation issues found:[/yellow]")
            for issue in issues:
                console.print(f"  - {issue}")
        else:
            console.print("[green]✓[/green] Dashboard is valid")

        if output:
            # Load and re-export to clean up formatting
            from ads_grafana_toolkit.sdk.dashboard import Dashboard
            dashboard = Dashboard.from_dict(data)
            dashboard.save(output)
            console.print(f"[green]✓[/green] Cleaned dashboard saved to: {output}")

    except json.JSONDecodeError as e:
        console.print(f"[red]Invalid JSON:[/red] {e}")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)


@cli.command()
@click.option("-h", "--host", default="0.0.0.0", help="Host to bind to")
@click.option("-p", "--port", default=8080, type=int, help="Port to bind to")
@click.option("--db", default="dashboards.db", help="Database file path")
@click.option("--debug", is_flag=True, help="Enable debug mode")
def serve(host: str, port: int, db: str, debug: bool):
    """Start the web interface server.

    Example:
        ads-grafana-toolkit serve --port 8080
    """
    try:
        from ads_grafana_toolkit.web.app import run_server
        console.print(f"[green]Starting server at http://{host}:{port}[/green]")
        console.print(f"[dim]Database: {db}[/dim]")
        run_server(host=host, port=port, debug=debug, db_path=db)
    except ImportError:
        console.print("[red]Error:[/red] Flask not installed. Run: pip install ads-grafana-toolkit[web]")
        sys.exit(1)


@cli.command()
def sdk_example():
    """Show example code for using the Python SDK."""
    example = '''
from ads_grafana_toolkit import Dashboard, Datasource

# Create a dashboard
dashboard = Dashboard(
    title="My Application Metrics",
    datasource=Datasource.prometheus("Prometheus"),
    refresh="30s",
)

# Add template variables
dashboard.add_variable(
    "instance",
    query='label_values(up, instance)',
    label="Instance",
)

# Add panels
dashboard.add_panel(
    "CPU Usage",
    query='100 - (avg(irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)',
    panel_type="gauge",
    unit="percent",
).add_threshold(None, "green").add_threshold(70, "yellow").add_threshold(90, "red")

dashboard.add_panel(
    "Memory Usage",
    query="100 * (1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes))",
    panel_type="timeseries",
    unit="percent",
)

dashboard.add_panel(
    "Network Traffic",
    panel_type="timeseries",
    unit="bps",
).add_query(
    'rate(node_network_receive_bytes_total[5m]) * 8',
    legend="Receive"
).add_query(
    'rate(node_network_transmit_bytes_total[5m]) * 8',
    legend="Transmit"
)

# Save to file
dashboard.save("my-dashboard.json")

# Or get JSON string
json_str = dashboard.to_json()
'''
    console.print(Panel(example, title="Python SDK Example", border_style="blue"))


if __name__ == "__main__":
    cli()
