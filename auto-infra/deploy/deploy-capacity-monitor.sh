#!/bin/bash
set -e

# Deploy capacity-monitor to all OCI instances
# Usage: ./deploy-capacity-monitor.sh [n8n_webhook_url]

N8N_WEBHOOK_URL="${1:-https://n8n.afterdarksys.com/webhook/capacity-alert}"
BINARY_AMD64="../daemons/capacity-monitor/capacity-monitor-linux-amd64"
BINARY_ARM64="../daemons/capacity-monitor/capacity-monitor-linux-arm64"
SERVICE_FILE="../daemons/capacity-monitor/capacity-monitor.service"

# Get list of all running instances
echo "Fetching OCI instances..."
INSTANCES=$(oci compute instance list \
  --compartment-id ocid1.tenancy.oc1..aaaaaaaaiqfc57o25y3424skethbodacbasc2zy3yp2b423zj6qkhcwjkqta \
  --lifecycle-state RUNNING \
  --all 2>/dev/null | jq -r '.data[] | "\(.["display-name"])|\(.["shape"])|\(.id)"')

if [ -z "$INSTANCES" ]; then
  echo "No running instances found"
  exit 1
fi

echo "Found instances:"
echo "$INSTANCES" | column -t -s'|'
echo ""

# Deploy to each instance
while IFS='|' read -r NAME SHAPE INSTANCE_ID; do
  echo "=== Deploying to $NAME ($SHAPE) ==="

  # Determine architecture
  if [[ "$SHAPE" == *"A1.Flex"* ]]; then
    BINARY="$BINARY_ARM64"
    ARCH="ARM64"
  else
    BINARY="$BINARY_AMD64"
    ARCH="AMD64"
  fi

  echo "Architecture: $ARCH"

  # Get instance IP (assuming it has a public IP)
  PUBLIC_IP=$(oci compute instance list-vnics \
    --instance-id "$INSTANCE_ID" 2>/dev/null | \
    jq -r '.data[0]["public-ip"]' 2>/dev/null || echo "")

  if [ -z "$PUBLIC_IP" ] || [ "$PUBLIC_IP" == "null" ]; then
    echo "⚠️  No public IP found, skipping $NAME"
    continue
  fi

  echo "IP: $PUBLIC_IP"

  # Deploy via SSH
  echo "Copying binary..."
  scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
    "$BINARY" "ubuntu@$PUBLIC_IP:/tmp/capacity-monitor" 2>/dev/null || {
    echo "❌ Failed to copy to $NAME"
    continue
  }

  echo "Installing..."
  ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
    "ubuntu@$PUBLIC_IP" << EOF
sudo mv /tmp/capacity-monitor /usr/local/bin/
sudo chmod +x /usr/local/bin/capacity-monitor

# Create systemd service
sudo tee /etc/systemd/system/capacity-monitor.service > /dev/null << 'SERVICE'
[Unit]
Description=Capacity Monitor Daemon
After=network.target

[Service]
Type=simple
User=root
ExecStart=/usr/local/bin/capacity-monitor
Restart=always
RestartSec=10

Environment="N8N_WEBHOOK_URL=$N8N_WEBHOOK_URL"
Environment="OCI_INSTANCE_ID=$INSTANCE_ID"

StandardOutput=journal
StandardError=journal
SyslogIdentifier=capacity-monitor

[Install]
WantedBy=multi-user.target
SERVICE

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable capacity-monitor
sudo systemctl restart capacity-monitor
sudo systemctl status capacity-monitor --no-pager
EOF

  echo "✅ Deployed to $NAME"
  echo ""
done <<< "$INSTANCES"

echo "=== Deployment Complete ==="
echo "Monitor logs with: ssh ubuntu@<ip> 'sudo journalctl -u capacity-monitor -f'"
