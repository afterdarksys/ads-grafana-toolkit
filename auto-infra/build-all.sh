#!/bin/bash
set -e

echo "🔨 Building Auto-Infrastructure Platform..."
echo ""

# Build capacity-monitor
echo "=== Building capacity-monitor ==="
cd daemons/capacity-monitor
go mod tidy
make clean
make build-linux
echo "✅ capacity-monitor built"
echo ""

# Build provisioning-agent
echo "=== Building provisioning-agent ==="
cd ../provisioning-agent
go mod tidy
GOOS=linux GOARCH=amd64 go build -o provisioning-agent-linux-amd64 -ldflags="-s -w" .
GOOS=linux GOARCH=arm64 go build -o provisioning-agent-linux-arm64 -ldflags="-s -w" .
echo "✅ provisioning-agent built"
echo ""

cd ../..

echo "=== Build Summary ==="
echo "Binaries created:"
ls -lh daemons/capacity-monitor/capacity-monitor-linux-*
ls -lh daemons/provisioning-agent/provisioning-agent-linux-*
echo ""

echo "🎉 All components built successfully!"
echo ""
echo "Next steps:"
echo "1. Deploy capacity-monitor: cd deploy && ./deploy-capacity-monitor.sh"
echo "2. Import n8n workflows from n8n-workflows/"
echo "3. Deploy provisioning-agent to hosting instances"
echo "4. See DEPLOYMENT.md for detailed instructions"
