# Deployment Guide

## Prerequisites

1. **OCI CLI configured** with proper credentials
2. **n8n instance running** (recommend n8n.afterdarksys.com)
3. **SSH access** to all compute instances
4. **Keycloak** running at adsas.id

## Step 1: Build Go Daemons

```bash
cd daemons/capacity-monitor
make build-linux

cd ../provisioning-agent
make build-linux
```

This creates:
- `capacity-monitor-linux-amd64`
- `capacity-monitor-linux-arm64`
- `provisioning-agent-linux-amd64`
- `provisioning-agent-linux-arm64`

## Step 2: Deploy Capacity Monitor

Deploy to all 16 instances to start monitoring:

```bash
cd ../../deploy
chmod +x deploy-capacity-monitor.sh

# Set your n8n webhook URL
export N8N_WEBHOOK_URL="https://n8n.afterdarksys.com/webhook/capacity-alert"

./deploy-capacity-monitor.sh $N8N_WEBHOOK_URL
```

Monitor deployment:
```bash
# SSH to any instance
ssh ubuntu@<instance-ip>

# Check status
sudo systemctl status capacity-monitor

# View logs
sudo journalctl -u capacity-monitor -f
```

## Step 3: Deploy Provisioning Agent

Deploy to web hosting instances:

```bash
# Identify which instances will host customers
# Recommend: dedicated instances for customer workloads

# SSH to target instance
ssh ubuntu@<instance-ip>

# Copy binary
scp provisioning-agent-linux-amd64 ubuntu@<instance-ip>:/tmp/

# Install
sudo mv /tmp/provisioning-agent-linux-amd64 /usr/local/bin/provisioning-agent
sudo chmod +x /usr/local/bin/provisioning-agent

# Create systemd service
sudo tee /etc/systemd/system/provisioning-agent.service > /dev/null << 'EOF'
[Unit]
Description=Customer Provisioning Agent
After=network.target

[Service]
Type=simple
User=root
ExecStart=/usr/local/bin/provisioning-agent
Restart=always
RestartSec=10
Environment="PORT=8081"

StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Start service
sudo systemctl daemon-reload
sudo systemctl enable provisioning-agent
sudo systemctl start provisioning-agent
sudo systemctl status provisioning-agent
```

## Step 4: Import n8n Workflows

1. **Access n8n**: Navigate to https://n8n.afterdarksys.com

2. **Import Auto-Scale Workflow**:
   - Click "Workflows" → "Add workflow" → "Import from File"
   - Select `n8n-workflows/auto-scale-workflow.json`
   - Configure OCI credentials in HTTP Request nodes
   - Activate workflow

3. **Import HostScience Provisioning**:
   - Import `n8n-workflows/hostscience-provisioning.json`
   - Set environment variables:
     - `HOSTSCIENCE_ZONE_ID`: OCI DNS zone ID for hostscience.io
     - `WEB_SERVER_IP`: IP of provisioning-agent instance
   - Configure email sender credentials
   - Activate workflow

## Step 5: Test the System

### Test Capacity Monitoring

Simulate high CPU load on an instance:

```bash
# SSH to instance
ssh ubuntu@<instance-ip>

# Create CPU load (will trigger 80% threshold)
stress --cpu 4 --timeout 120s
```

Check n8n workflow execution logs for auto-scale trigger.

### Test Customer Provisioning

```bash
curl -X POST https://n8n.afterdarksys.com/webhook/hostscience/signup \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "domain": "testsite.com",
    "plan": "professional"
  }'
```

Expected response:
```json
{
  "success": true,
  "customer_id": "hsc_...",
  "domain": "testsite.com",
  "plan": "professional",
  "message": "Your hosting account has been created!",
  "login_url": "https://adsas.id",
  "dashboard_url": "https://hostscience.io/dashboard"
}
```

## Step 6: Monitor Operations

### View Capacity Metrics

All instances report every 30s. Aggregate metrics dashboard:

```bash
# TODO: Set up Grafana dashboard
# Metrics API endpoint: http://localhost:8080/api/metrics
```

### View Provisioning Logs

```bash
ssh ubuntu@<provisioning-instance>
sudo journalctl -u provisioning-agent -f
```

### n8n Execution History

Check n8n dashboard for:
- Successful auto-scaling events
- Customer provisioning completions
- Error notifications

## Scaling Thresholds

Current configuration:
- **Scale UP**: CPU/Memory/Disk ≥ 80% → Add 15-20% capacity
- **Scale DOWN**: CPU < 30% sustained → Remove idle instances
- **Alert Cooldown**: 5 minutes (prevent alert spam)

## Current Capacity

| Resource | Current | Max Budget | Remaining |
|----------|---------|------------|-----------|
| Monthly Budget | $900 | $1,100 | $200 |
| Instances | 16 | ~20 | 4 |
| OCPUs | 26 | ~32 | 6 |

## Next Steps

1. **Build frontend** for hostscience.io signup
2. **Implement blazebase.io** (database hosting)
3. **Wire up adtelco.io** (IP telephony)
4. **Add metrics dashboard** (Grafana)
5. **Implement auto-shrink** workflow
6. **Set up billing integration** (Stripe)

## Troubleshooting

### Capacity monitor not reporting

```bash
# Check service status
sudo systemctl status capacity-monitor

# Check network connectivity to n8n
curl -X POST $N8N_WEBHOOK_URL -d '{"test": true}'

# Verify OCI metadata service
curl http://169.254.169.254/opc/v1/instance/id
```

### Provisioning fails

```bash
# Check provisioning-agent logs
sudo journalctl -u provisioning-agent -n 100

# Verify directories exist
ls -la /var/lib/customers
ls -la /var/www/customers

# Check nginx/php-fpm
sudo nginx -t
sudo systemctl status php8.2-fpm
```

### Auto-scaling not triggering

1. Verify webhook URL in capacity-monitor service
2. Check n8n workflow is activated
3. Review n8n execution logs for errors
4. Ensure OCI API credentials are configured
