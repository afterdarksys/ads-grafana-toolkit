# ads-grafana-toolkit

A Python toolkit for simplifying Grafana dashboard creation. Abstracts away the complexity of Grafana's JSON schema and provides multiple intuitive interfaces for generating dashboards.

## Features

- **Config Files** - Write simple YAML/TOML, get valid Grafana JSON
- **Python SDK** - Programmatic dashboard generation with smart defaults
- **Template Library** - Pre-built templates for common monitoring scenarios
- **Interactive CLI** - Guided wizard for dashboard creation
- **Natural Language** - Describe what you want in plain English

## Installation

```bash
pip install ads-grafana-toolkit
```

For development:
```bash
git clone https://github.com/afterdarktech/ads-grafana-toolkit.git
cd ads-grafana-toolkit
pip install -e ".[dev]"
```

For NLP features (requires OpenAI API key):
```bash
pip install ads-grafana-toolkit[nlp]
```

## Quick Start

### 1. Config File Approach

Create a simple YAML file:

```yaml
# dashboard.yaml
name: "My App Metrics"
datasource: Prometheus
refresh: "30s"

panels:
  - title: "CPU Usage"
    query: 'avg(irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100'
    type: gauge
    unit: percent

  - title: "Memory Usage"
    query: "node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes * 100"
    type: timeseries
    unit: percent
```

Convert to Grafana JSON:
```bash
ads-grafana-toolkit convert dashboard.yaml -o dashboard.json
```

### 2. Python SDK

```python
from ads_grafana_toolkit import Dashboard, Datasource

dashboard = Dashboard(
    title="My App",
    datasource=Datasource.prometheus("Prometheus"),
    refresh="30s",
)

# Add panels with smart defaults
dashboard.add_panel(
    "CPU Usage",
    query='100 - avg(irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100',
    panel_type="gauge",
    unit="percent",
).add_threshold(None, "green").add_threshold(70, "yellow").add_threshold(90, "red")

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

# Add template variables
dashboard.add_variable(
    "instance",
    query='label_values(up, instance)',
    label="Instance",
)

# Save to file
dashboard.save("my-dashboard.json")
```

### 3. Templates

List available templates:
```bash
ads-grafana-toolkit templates list
```

Create from template:
```bash
ads-grafana-toolkit templates create node-exporter -d Prometheus -o node.json
ads-grafana-toolkit templates create mysql -d Prometheus -o mysql.json
ads-grafana-toolkit templates create kubernetes-cluster -o k8s.json
```

Available templates:
- `node-exporter` - Linux server metrics (CPU, memory, disk, network)
- `nginx` - Nginx web server metrics
- `apache` - Apache HTTP server metrics
- `http-endpoints` - HTTP endpoint monitoring via Blackbox Exporter
- `docker` - Docker container metrics via cAdvisor
- `kubernetes-cluster` - Kubernetes cluster overview
- `kubernetes-pod` - Kubernetes pod details
- `mysql` - MySQL/MariaDB with InnoDB metrics
- `postgresql` - PostgreSQL database metrics
- `redis` - Redis cache metrics

### 4. Interactive Wizard

```bash
ads-grafana-toolkit wizard
```

The wizard guides you through:
- Naming your dashboard
- Selecting a datasource
- Adding panels from common metrics
- Configuring thresholds
- Adding template variables

### 5. Natural Language

```bash
ads-grafana-toolkit generate "Create a dashboard showing CPU and memory usage"

ads-grafana-toolkit generate "Dashboard for HTTP request latency p99 grouped by service" -o api.json
```

With OpenAI (set `OPENAI_API_KEY` env var):
```bash
export OPENAI_API_KEY=sk-...
ads-grafana-toolkit generate "Create a comprehensive Kubernetes monitoring dashboard with pod resources and network metrics"
```

## CLI Reference

```bash
# Convert config to dashboard JSON
ads-grafana-toolkit convert config.yaml -o dashboard.json

# Interactive wizard
ads-grafana-toolkit wizard

# Templates
ads-grafana-toolkit templates list
ads-grafana-toolkit templates info node-exporter
ads-grafana-toolkit templates create mysql -d Prometheus -o mysql.json

# Natural language generation
ads-grafana-toolkit generate "dashboard for web server monitoring"

# Validate existing dashboard
ads-grafana-toolkit validate dashboard.json

# Show SDK example code
ads-grafana-toolkit sdk-example
```

## Project Structure

```
ads-grafana-toolkit/
├── ads_grafana_toolkit/
│   ├── sdk/                  # Core SDK (Dashboard, Panel, etc.)
│   ├── simple/               # YAML/TOML config converter
│   ├── template_library/     # Pre-built templates
│   ├── cli/                  # CLI commands and wizard
│   └── nlp_interface/        # Natural language generation
├── examples/                 # Example configs and scripts
└── tests/                    # Test suite
```

## SDK Reference

### Dashboard

```python
from ads_grafana_toolkit import Dashboard, Datasource

dashboard = Dashboard(
    title="My Dashboard",
    description="Dashboard description",
    datasource=Datasource.prometheus("Prometheus"),
    tags=["app", "metrics"],
    refresh="30s",
    time_from="now-6h",
    time_to="now",
)
```

### Panels

```python
# Add panel with auto-positioning
panel = dashboard.add_panel(
    title="Panel Title",
    query="up",
    panel_type="timeseries",  # timeseries, stat, gauge, table, text, logs
    width=12,
    height=8,
    unit="percent",
)

# Add multiple queries
panel.add_query("rate(requests[5m])", legend="Requests")
panel.add_query("rate(errors[5m])", legend="Errors")

# Add thresholds (for gauge/stat)
panel.add_threshold(None, "green")  # Base
panel.add_threshold(70, "yellow")
panel.add_threshold(90, "red")
```

### Datasources

```python
from ads_grafana_toolkit import Datasource

# Factory methods
ds = Datasource.prometheus("Prometheus")
ds = Datasource.mysql("MySQL")
ds = Datasource.postgres("PostgreSQL")
ds = Datasource.influxdb("InfluxDB")
ds = Datasource.elasticsearch("Elasticsearch")
ds = Datasource.loki("Loki")
ds = Datasource.graphite("Graphite")
ds = Datasource.cloudwatch("CloudWatch")

# Or custom
ds = Datasource(name="MyDS", type="prometheus", uid="abc123")
```

### Variables

```python
dashboard.add_variable(
    name="instance",
    query='label_values(up, instance)',
    label="Instance",
    var_type="query",  # query, custom, constant, datasource, interval, textbox
    multi=True,
    include_all=True,
)
```

### Rows

```python
dashboard.add_row("Section Title", collapsed=False)
```

## Pain Points Solved

| Problem | Solution |
|---------|----------|
| Complex JSON schema | Simple YAML config or SDK |
| PromQL syntax learning curve | Templates with pre-built queries |
| Panel grid positioning | Auto-layout handles positioning |
| Choosing visualizations | Smart defaults based on query type |
| Datasource configuration | Simple name references |

## Supported Datasources

- Prometheus
- Graphite
- InfluxDB
- MySQL
- PostgreSQL
- Elasticsearch
- Loki
- CloudWatch
- Tempo

## Prior Art

This toolkit builds on ideas from:
- [grafanalib](https://github.com/weaveworks/grafanalib) - Python library for programmatic dashboards
- [grafonnet](https://github.com/grafana/grafonnet-lib) - Jsonnet library for Grafana dashboards
- [Grafana Provisioning](https://grafana.com/docs/grafana/latest/administration/provisioning/) - Native dashboard provisioning

## Deployment

### Docker (Local/Server)

```bash
# Using docker-compose
docker-compose up -d

# Or build manually
docker build -t grafana-toolkit .
docker run -p 8080:8080 -v toolkit-data:/data grafana-toolkit
```

Access the web UI at http://localhost:8080

### Cloudflare Workers (Edge)

```bash
cd workers

# Install dependencies
npm install

# Create D1 database
npm run db:create

# Update wrangler.toml with your database_id

# Run migrations
npm run db:migrate

# Set secrets
wrangler secret put OPENAI_API_KEY
# OR for OpenRouter:
wrangler secret put OPENROUTER_API_KEY
wrangler secret put OPENROUTER_MODEL  # e.g., "anthropic/claude-3-haiku"

# Deploy
npm run deploy
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `DATABASE_PATH` | SQLite database path (default: `dashboards.db`) |
| `OPENAI_API_KEY` | OpenAI API key for NLP features |
| `OPENROUTER_API_KEY` | OpenRouter API key (alternative to OpenAI) |
| `OPENROUTER_MODEL` | Model name for OpenRouter (e.g., `anthropic/claude-3-haiku`) |

## License

MIT
