# Auto-Scaling Infrastructure Monitoring

Prometheus + Grafana integration for capacity-monitor daemons across all 16 OCI instances.

## Architecture

```
┌─────────────────────────────────────────────────────┐
│  16× OCI Instances running capacity-monitor         │
│  Each exposes metrics on :9100/metrics              │
└────────────────┬────────────────────────────────────┘
                 │
                 │ scrape every 30s
                 │
                 ▼
        ┌────────────────┐
        │   Prometheus   │
        │  (ads-grafana- │
        │     toolkit)   │
        └────────┬───────┘
                 │
                 │ query
                 │
                 ▼
        ┌────────────────┐
        │    Grafana     │
        │   Dashboard    │
        └────────────────┘
```

## Setup Instructions

### 1. Update Prometheus Configuration

Add the capacity-monitor scrape config to your Prometheus configuration:

```bash
# Edit your prometheus.yml
cat prometheus-capacity-scrape.yml >> /path/to/prometheus.yml

# Or merge manually - add the scrape_configs section from:
# prometheus-capacity-scrape.yml
```

**Location of your Prometheus config:** Check `/Users/ryan/development/ads-grafana-toolkit/test/prometheus.yml` or your production Prometheus setup.

### 2. Reload Prometheus

After updating the config:

```bash
# If running as a service
sudo systemctl reload prometheus

# If running in Docker
docker restart prometheus

# Or send SIGHUP
kill -HUP $(pidof prometheus)
```

### 3. Import Grafana Dashboard

1. Open Grafana (default: http://localhost:3000)
2. Navigate to **Dashboards** → **Import**
3. Upload `grafana-dashboard-auto-scaling.json`
4. Select your Prometheus data source
5. Click **Import**

Alternatively, using the Grafana API:

```bash
curl -X POST http://localhost:3000/api/dashboards/db \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_GRAFANA_API_KEY" \
  -d @grafana-dashboard-auto-scaling.json
```

### 4. Verify Metrics

Check that Prometheus is scraping all 16 instances:

```bash
# Query Prometheus for all capacity-monitor targets
curl 'http://localhost:9090/api/v1/targets' | jq '.data.activeTargets[] | select(.job=="capacity-monitor")'

# Check specific metric
curl 'http://localhost:9090/api/v1/query?query=capacity_monitor_cpu_percent'
```

Or visit Prometheus UI:
- **Targets:** http://localhost:9090/targets (should see 16 capacity-monitor endpoints)
- **Graph:** http://localhost:9090/graph

## Metrics Exposed

Each capacity-monitor daemon exports the following metrics:

| Metric Name | Type | Description | Labels |
|------------|------|-------------|--------|
| `capacity_monitor_cpu_percent` | Gauge | Current CPU usage percentage | hostname, instance_id |
| `capacity_monitor_memory_percent` | Gauge | Current memory usage percentage | hostname, instance_id |
| `capacity_monitor_disk_percent` | Gauge | Current disk usage percentage | hostname, instance_id |
| `capacity_monitor_network_rx_bytes_total` | Gauge | Total network bytes received | hostname, instance_id |
| `capacity_monitor_network_tx_bytes_total` | Gauge | Total network bytes transmitted | hostname, instance_id |
| `capacity_monitor_over_capacity` | Gauge | Whether instance is over capacity (1=yes, 0=no) | hostname, instance_id |

## Example Queries

### Average CPU across fleet
```promql
avg(capacity_monitor_cpu_percent)
```

### Instances over 80% CPU
```promql
capacity_monitor_cpu_percent > 80
```

### Count of over-capacity instances
```promql
sum(capacity_monitor_over_capacity)
```

### Network bandwidth per instance (5min rate)
```promql
rate(capacity_monitor_network_rx_bytes_total[5m])
```

### Top 5 CPU consumers
```promql
topk(5, capacity_monitor_cpu_percent)
```

## Grafana Dashboard Panels

The auto-scaling dashboard includes:

1. **Fleet CPU Usage** - Time series graph of all 16 instances
2. **Fleet Memory Usage** - Time series graph of all 16 instances
3. **Fleet Disk Usage** - Time series graph of all 16 instances
4. **Over Capacity Instances** - Count of instances exceeding thresholds
5. **Average CPU Across Fleet** - Gauge showing fleet-wide average
6. **Average Memory Across Fleet** - Gauge showing fleet-wide average
7. **Average Disk Across Fleet** - Gauge showing fleet-wide average
8. **Total Network Traffic (Rx)** - Receive bandwidth per instance
9. **Total Network Traffic (Tx)** - Transmit bandwidth per instance
10. **Instance Status Heatmap** - Visual heatmap of CPU usage

### Alerts

The dashboard includes a **CPU Capacity Alert** that triggers when:
- Average CPU > 80% for 5 minutes
- This matches the auto-scaling trigger threshold

## Integration with Auto-Scaling Workflow

The capacity-monitor daemon:
1. **Collects metrics** every 30 seconds
2. **Exports to Prometheus** via :9100/metrics
3. **Sends webhooks to n8n** when CPU/Memory/Disk ≥ 80%
4. **Grafana visualizes** the data and shows fleet health

This provides:
- **Historical data** via Prometheus (can see trends before auto-scaling)
- **Real-time alerts** via n8n webhooks (triggers auto-scaling immediately)
- **Visual monitoring** via Grafana (operators can see what's happening)

## Firewall Rules

Ensure Prometheus can reach all instances on port 9100:

```bash
# On each OCI instance, allow port 9100
sudo firewall-cmd --permanent --add-port=9100/tcp
sudo firewall-cmd --reload

# Or using iptables
sudo iptables -A INPUT -p tcp --dport 9100 -j ACCEPT
sudo iptables-save > /etc/iptables/rules.v4
```

## Troubleshooting

### Prometheus not scraping?

1. Check Prometheus logs:
   ```bash
   journalctl -u prometheus -f
   ```

2. Verify capacity-monitor is running and exposing metrics:
   ```bash
   curl http://adrelay-1.afterdarksys.com:9100/metrics
   ```

3. Check for network connectivity:
   ```bash
   telnet adrelay-1.afterdarksys.com 9100
   ```

### Grafana dashboard shows "No Data"?

1. Verify Prometheus data source is configured
2. Check that Prometheus has data:
   ```bash
   curl 'http://localhost:9090/api/v1/query?query=capacity_monitor_cpu_percent'
   ```
3. Ensure time range in Grafana is recent (last 15 minutes)

### Metrics are stale?

1. Check capacity-monitor daemon status on instances:
   ```bash
   sudo systemctl status capacity-monitor
   ```

2. Verify metrics are updating:
   ```bash
   watch -n 5 'curl -s http://localhost:9100/metrics | grep capacity_monitor_cpu_percent'
   ```

## Production Deployment

Once deployed, you'll have:

- **16 instances** reporting metrics every 30 seconds
- **Prometheus** scraping and storing time-series data
- **Grafana** visualizing fleet health in real-time
- **Auto-scaling triggers** when capacity hits 80%
- **Budget enforcement** at $1,300/month
- **Slack + Email alerts** for all scaling events

This completes the monitoring stack for your auto-scaling infrastructure.
