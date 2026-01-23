# Grafana Toolkit - Extras

Additional powerful features for advanced dashboard creation and documentation.

## What's Included

1. **Jsonnet/Grafonnet Support** - Programmatic dashboard generation
2. **PromQL Query Builder** - Interactive query creation
3. **Writers Toolkit** - Documentation and report generation

## Quick Start

### Option 1: Interactive Menu
```bash
python3 extras_setup.py
```

This gives you a menu to setup and try each feature.

### Option 2: Direct Usage

Each tool can be used standalone:

```bash
# Jsonnet support
python3 jsonnet_support.py setup
python3 jsonnet_support.py example
python3 jsonnet_support.py convert dashboard.jsonnet

# PromQL builder
python3 promql_builder.py interactive
python3 promql_builder.py template cpu_usage

# Writers toolkit
python3 writers_toolkit.py dashboard.json -f markdown
python3 writers_toolkit.py dashboard.json -f html
```

## Feature 1: Jsonnet/Grafonnet Support

### What is it?
Jsonnet is a data templating language. Grafonnet is a Jsonnet library specifically for Grafana dashboards. Together, they let you:
- Use variables and functions in dashboards
- Loop to create multiple similar panels
- Reuse dashboard components
- Generate complex dashboards from simple code

### Setup
```bash
python3 jsonnet_support.py setup
```

This auto-installs Jsonnet and downloads the Grafonnet library.

### Create Example
```bash
python3 jsonnet_support.py example -o my-dashboard.jsonnet
```

This creates `my-dashboard.jsonnet` with:
- Variables for datasource
- Reusable panel definitions
- Rows and layout

### Convert to JSON
```bash
python3 jsonnet_support.py convert my-dashboard.jsonnet -o my-dashboard.json
```

### Example Jsonnet Dashboard

```jsonnet
local grafana = import 'grafonnet/grafana.libsonnet';
local dashboard = grafana.dashboard;
local prometheus = grafana.prometheus;
local graphPanel = grafana.graphPanel;

dashboard.new(
  'My Dashboard',
  tags=['auto-generated'],
)
.addPanel(
  graphPanel.new(
    'CPU Usage',
    datasource='Prometheus',
    format='percent',
  )
  .addTarget(
    prometheus.target('rate(cpu[5m]) * 100')
  ),
  gridPos={x: 0, y: 0, w: 12, h: 8}
)
```

**Advantages over YAML/JSON:**
- Functions and variables
- Loops for repetitive panels
- Import and reuse components
- Mathematical operations
- Conditional logic

## Feature 2: PromQL Query Builder

### What is it?
An interactive tool that helps you build Prometheus queries without memorizing PromQL syntax.

### Interactive Mode
```bash
python3 promql_builder.py interactive
```

This walks you through:
1. Selecting a metric
2. Adding filters (labels)
3. Applying rate() function
4. Adding aggregations (sum, avg, etc.)
5. Math operations

**Example interaction:**
```
Step 1: Select Metric
Available categories:
  1. node_exporter
  2. kubernetes
  3. application
  4. Fetch from Prometheus
  5. Enter manually

Choice: 1

Metrics in 'node_exporter':
  1. node_cpu_seconds_total
  2. node_memory_MemTotal_bytes
  ...

Select metric: 1

Step 2: Add Filters
Filter (or Enter to skip): mode=idle

Step 3: Rate Interval
Interval (e.g., 5m, 1h) or Enter to skip: 5m

Step 4: Aggregation
Available aggregations:
  1. sum
  2. avg
  ...

Select aggregation: 2
Aggregate by labels: instance

Step 5: Math Operations
Operation (or Enter to skip): *
Value: 100

=== Generated Query ===
avg by(instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100
```

### Template Mode
```bash
# Use pre-built query templates
python3 promql_builder.py template cpu_usage
python3 promql_builder.py template memory_usage
python3 promql_builder.py template disk_usage
python3 promql_builder.py template http_latency_p99
```

### Validation
```bash
# Validate a query against Prometheus
python3 promql_builder.py validate 'up{job="node"}'
```

### Connect to Your Prometheus
```bash
python3 promql_builder.py interactive --prometheus-url http://your-prometheus:9090
```

This fetches actual metrics from your Prometheus instance.

## Feature 3: Writers Toolkit

### What is it?
Export Grafana dashboards to readable documentation in multiple formats.

### Markdown Export
```bash
python3 writers_toolkit.py dashboard.json -f markdown -o dashboard.md
```

Creates a Markdown file with:
- Dashboard description
- Variables documented
- Each panel explained
- Queries listed
- Thresholds shown

### HTML Export
```bash
python3 writers_toolkit.py dashboard.json -f html -o dashboard.html
```

Creates a styled HTML page with:
- Color-coded sections
- Syntax-highlighted queries
- Responsive layout
- Printable format

### JSON Report
```bash
python3 writers_toolkit.py dashboard.json -f json -o report.json
```

Creates structured data with:
- Dashboard statistics
- Panel inventory
- Query extraction
- Machine-readable format

### Fetch from Grafana
```bash
# Create API key in Grafana first
python3 writers_toolkit.py DASHBOARD_UID --fetch \
  --grafana-url http://localhost:3000 \
  --api-key YOUR_API_KEY \
  -f html
```

This fetches a dashboard directly from Grafana and exports it.

### Generate README for Multiple Dashboards
```bash
# Export all dashboards
for file in *.json; do
  python3 writers_toolkit.py "$file" -f markdown
done

# Creates .md file for each dashboard
```

## Combined Workflows

### Workflow 1: Jsonnet → Grafana → Docs

```bash
# 1. Write dashboard in Jsonnet
cat > dashboard.jsonnet << 'EOF'
local grafana = import 'grafonnet/grafana.libsonnet';
// ... your dashboard code
EOF

# 2. Convert to JSON
python3 jsonnet_support.py convert dashboard.jsonnet

# 3. Import to Grafana via main toolkit
ads-grafana-toolkit convert dashboard.json

# 4. Generate documentation
python3 writers_toolkit.py dashboard.json -f html
```

### Workflow 2: Query Builder → YAML → Dashboard

```bash
# 1. Build query interactively
python3 promql_builder.py interactive -o query.txt

# 2. Create YAML with the query
cat > dashboard.yaml << EOF
name: "My Dashboard"
datasource: Prometheus
panels:
  - title: "My Metric"
    query: "$(cat query.txt)"
    type: gauge
EOF

# 3. Convert to Grafana JSON
ads-grafana-toolkit convert dashboard.yaml -o dashboard.json

# 4. Generate docs
python3 writers_toolkit.py dashboard.json -f markdown
```

### Workflow 3: Template → Customize → Document

```bash
# 1. Start with template
ads-grafana-toolkit templates create node-exporter -o dashboard.json

# 2. Customize queries with builder
python3 promql_builder.py interactive

# 3. Edit dashboard JSON with new queries

# 4. Generate documentation
python3 writers_toolkit.py dashboard.json -f html -o monitoring-docs.html
```

## Use Cases

### For Beginners
- Use query builder to learn PromQL
- Use templates in promql_builder.py
- Export dashboards to study their structure

### For Dashboard Developers
- Use Jsonnet for complex, repetitive dashboards
- Build query library with promql_builder
- Generate docs automatically

### For Teams
- Use Jsonnet to standardize dashboard structure
- Document all dashboards with writers_toolkit
- Share HTML docs with non-Grafana users

### For Operations
- Build alert queries with query builder
- Export dashboards for runbooks
- Create backup documentation

## Requirements

### Jsonnet Support
- Python 3.7+ (for pip install)
- OR Go (for binary install)
- Git (to clone Grafonnet)

Auto-installed by setup script.

### PromQL Builder
- Python 3.7+
- Network access to Prometheus (for validation)

No installation needed.

### Writers Toolkit
- Python 3.7+
- Network access to Grafana (for --fetch mode)

No installation needed.

## Tips & Tricks

### Jsonnet Tips
- Use `local` for variables
- Create functions for repeated patterns
- Import Grafonnet functions individually to reduce code
- Test locally before deploying

### PromQL Tips
- Start with simple queries and build up
- Use validation frequently
- Save working queries to a file
- Test queries in Grafana first if unsure

### Writers Tips
- Generate docs after each dashboard change
- Use HTML for sharing with stakeholders
- Use Markdown for version control
- Keep API keys secure

## Troubleshooting

### Jsonnet: "jsonnet: command not found"
```bash
python3 jsonnet_support.py setup
# This installs jsonnet automatically
```

### PromQL: "Could not connect to Prometheus"
```bash
# Check Prometheus is running
curl http://localhost:9090/api/v1/status/config

# Use correct URL
python3 promql_builder.py interactive --prometheus-url http://your-host:9090
```

### Writers: "Failed to fetch dashboard"
```bash
# Check Grafana is running
curl http://localhost:3000/api/health

# Create API key in Grafana
# Settings → API Keys → Add API key

# Use the key
python3 writers_toolkit.py UID --fetch --api-key YOUR_KEY
```

## Examples

See the `examples/` directory in the main toolkit for:
- Example Jsonnet dashboards
- Sample PromQL queries
- Generated documentation samples

## Command Reference

### Jsonnet Support
```bash
python3 jsonnet_support.py setup              # Install dependencies
python3 jsonnet_support.py example            # Create example
python3 jsonnet_support.py convert FILE       # Convert to JSON
python3 jsonnet_support.py convert FILE -o OUT # Specify output
```

### PromQL Builder
```bash
python3 promql_builder.py interactive                    # Interactive mode
python3 promql_builder.py interactive --prometheus-url URL  # Use specific Prometheus
python3 promql_builder.py template TYPE                  # Use template
python3 promql_builder.py validate QUERY                 # Validate query
python3 promql_builder.py interactive -o FILE            # Save to file
```

### Writers Toolkit
```bash
python3 writers_toolkit.py FILE -f FORMAT            # Export file
python3 writers_toolkit.py FILE -f FORMAT -o OUT     # Specify output
python3 writers_toolkit.py UID --fetch               # Fetch from Grafana
python3 writers_toolkit.py UID --fetch --api-key KEY # With authentication
python3 writers_toolkit.py UID --fetch --grafana-url URL # Specify Grafana
```

## Getting Help

Each tool has built-in help:
```bash
python3 jsonnet_support.py --help
python3 promql_builder.py --help
python3 writers_toolkit.py --help
```

For issues or questions:
- Main toolkit docs: ../README.md
- Setup docs: ../setup/README.md
- GitHub: https://github.com/afterdarksys/ads-grafana-toolkit/issues

## License

MIT License - See main repository LICENSE file
