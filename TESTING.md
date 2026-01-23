# Testing the Grafana Toolkit

Complete Docker-based testing environment for the ads-grafana-toolkit.

## Quick Start

### One Command Test
```bash
./test-toolkit.sh
```

This builds and starts a complete test environment with:
- Grafana (package installation)
- Prometheus
- Node Exporter
- MySQL
- Graphite
- Another Grafana instance (Docker)
- Another Prometheus instance

## Test Environment

### What Gets Installed

**Primary Test Container (`grafana-toolkit-test`):**
- Ubuntu 22.04 base
- Grafana (via apt package)
- Prometheus (binary installation)
- Node Exporter (binary installation)
- Complete toolkit at `/opt/ads-grafana-toolkit`
- All scripts ready to run

**Additional Services (Docker Compose):**
- Grafana (Docker container on port 3001)
- Prometheus (standalone on port 9091)
- MySQL 8.0 (port 3306)
- Graphite (port 8080)

This diverse setup lets you test **all detection scenarios** in one environment!

## Usage

### Start Test Environment
```bash
./test-toolkit.sh up
```

Access:
- **Grafana (test):** http://localhost:3000 (admin/admin)
- **Grafana (docker):** http://localhost:3001 (admin/admin)
- **Prometheus:** http://localhost:9090
- **Prometheus (standalone):** http://localhost:9091
- **Node Exporter:** http://localhost:9100/metrics
- **Graphite:** http://localhost:8080
- **MySQL:** localhost:3306 (root/testpassword)

### Run Audit Script
```bash
./test-toolkit.sh audit
```

This runs the monitoring stack audit and shows all detected services.

### Open Shell in Test Container
```bash
./test-toolkit.sh shell
```

Once inside, you can:
```bash
# Run audit
./setup/scripts/audit_monitoring_stack.py

# Detect Grafana only
./setup/scripts/detect_grafana.py

# Test setup script
./setup/grafana_setup.py --step-by-step

# Test extras
python3 extras/promql_builder.py interactive
python3 extras/jsonnet_support.py setup
python3 extras/writers_toolkit.py --help

# Use the main toolkit
ads-grafana-toolkit templates list
ads-grafana-toolkit wizard
```

### View Logs
```bash
./test-toolkit.sh logs
```

### Stop Environment
```bash
./test-toolkit.sh down
```

### Clean Everything
```bash
./test-toolkit.sh clean
```

Removes all containers, volumes, and images.

## Testing Scenarios

### 1. Test Audit Script
```bash
./test-toolkit.sh shell

# Inside container
./setup/scripts/audit_monitoring_stack.py

# Should detect:
# - Grafana (package)
# - Grafana (Docker - outside container)
# - Prometheus (binary)
# - Prometheus (Docker - outside container)
# - Node Exporter (binary)
# - MySQL (Docker - outside container)
# - Graphite (Docker - outside container)
```

### 2. Test Detection Script
```bash
./test-toolkit.sh shell

# Inside container
./setup/scripts/detect_grafana.py -v

# Should find:
# - Grafana package installation at /usr/share/grafana
# - Grafana systemd service
```

### 3. Test Setup Script (Dry Run)
```bash
./test-toolkit.sh shell

# Inside container - Grafana already installed
# Test detection and skip installation
./setup/grafana_setup.py --step-by-step
```

### 4. Test PromQL Builder
```bash
./test-toolkit.sh shell

# Inside container
python3 extras/promql_builder.py interactive --prometheus-url http://localhost:9090

# Prometheus is running, so it can fetch real metrics
```

### 5. Test Writers Toolkit
```bash
./test-toolkit.sh shell

# Inside container
# Create a test dashboard
ads-grafana-toolkit templates create node-exporter -o test-dashboard.json

# Export to documentation
python3 extras/writers_toolkit.py test-dashboard.json -f html
python3 extras/writers_toolkit.py test-dashboard.json -f markdown

# View generated docs
cat test-dashboard.html
cat test-dashboard.md
```

### 6. Test Jsonnet Support
```bash
./test-toolkit.sh shell

# Inside container
cd extras

# Setup Jsonnet
python3 jsonnet_support.py setup

# Create example
python3 jsonnet_support.py example

# Convert
python3 jsonnet_support.py convert example_dashboard.jsonnet

# View result
cat example_dashboard.json
```

## Manual Testing

### Build Only
```bash
./test-toolkit.sh build
```

### Start Without Building
```bash
./test-toolkit.sh up
```

### Run Specific Tests
```bash
# Start environment
./test-toolkit.sh up

# Run automated test suite
./test-toolkit.sh test
```

## Docker Compose Commands

You can also use docker-compose directly:

```bash
# Start all services
docker-compose -f docker-compose.test.yml up -d

# View logs
docker-compose -f docker-compose.test.yml logs -f

# Stop all services
docker-compose -f docker-compose.test.yml down

# Restart a service
docker-compose -f docker-compose.test.yml restart grafana-docker

# Execute command in container
docker-compose -f docker-compose.test.yml exec grafana-toolkit-test bash
```

## Testing Individual Components

### Test Grafana Detection
```bash
docker exec grafana-toolkit-test python3 /opt/ads-grafana-toolkit/setup/scripts/detect_grafana.py -v
```

### Test Docker Detection
```bash
docker exec grafana-toolkit-test python3 /opt/ads-grafana-toolkit/setup/scripts/setup_docker.py --check-only
```

### Test Main Toolkit
```bash
docker exec grafana-toolkit-test bash -c "cd /opt/ads-grafana-toolkit && python3 -m ads_grafana_toolkit.cli.main templates list"
```

## Troubleshooting

### Container Won't Start
```bash
# Check logs
docker logs grafana-toolkit-test

# Check if ports are in use
lsof -i :3000
lsof -i :9090

# Use different ports by editing docker-compose.test.yml
```

### Services Not Running Inside Container
```bash
# Shell into container
./test-toolkit.sh shell

# Check service status
ps aux | grep grafana
ps aux | grep prometheus

# Check logs
tail -f /var/log/grafana.log
tail -f /var/log/prometheus.log

# Restart services manually
sudo systemctl restart grafana-server
```

### Can't Access Services
```bash
# Check if containers are running
docker ps

# Check if services are listening
docker exec grafana-toolkit-test netstat -tlnp

# Check container networking
docker network inspect monitoring-test
```

## CI/CD Integration

### GitHub Actions Example
```yaml
name: Test Toolkit

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2

      - name: Build test environment
        run: ./test-toolkit.sh build

      - name: Start services
        run: ./test-toolkit.sh up

      - name: Run tests
        run: ./test-toolkit.sh test

      - name: Stop services
        run: ./test-toolkit.sh down
```

### Local Automated Testing
```bash
# Run full test cycle
./test-toolkit.sh full

# Or step by step
./test-toolkit.sh build
./test-toolkit.sh up
./test-toolkit.sh test
./test-toolkit.sh down
```

## Development Workflow

### Edit and Test Loop
```bash
# 1. Start environment once
./test-toolkit.sh up

# 2. Make changes to scripts

# 3. Test changes immediately (volume is mounted)
./test-toolkit.sh shell
# Run your modified scripts

# 4. When done
./test-toolkit.sh down
```

The toolkit directory is volume-mounted, so changes are reflected immediately!

## Performance Notes

- **Build time:** ~5-10 minutes (first time, downloads packages)
- **Startup time:** ~10-15 seconds
- **Disk usage:** ~2-3 GB (all images and volumes)
- **Memory usage:** ~1-2 GB (all services running)

## Cleanup

### Remove Everything
```bash
./test-toolkit.sh clean
```

This removes:
- All test containers
- All test volumes (data is deleted!)
- Test images

### Preserve Data, Remove Containers
```bash
./test-toolkit.sh down
```

Volumes persist, can restart with `./test-toolkit.sh up`.

## What to Test

**Before Release:**
- [ ] Audit script detects all services
- [ ] Detection script finds Grafana
- [ ] Setup script runs without errors
- [ ] PromQL builder can fetch metrics
- [ ] Jsonnet support installs correctly
- [ ] Writers toolkit exports dashboards
- [ ] All CLI commands work
- [ ] Templates generate valid JSON
- [ ] Documentation is accessible

**Regression Testing:**
- [ ] Multi-platform support
- [ ] Docker detection works
- [ ] Package detection works
- [ ] Binary detection works
- [ ] Legacy system detection
- [ ] Health checks pass
- [ ] Error handling works

## Tips

1. **Fast iteration:** Keep environment running, just re-run scripts
2. **Test isolation:** Each container has its own network
3. **Data persistence:** Volumes preserve data between restarts
4. **Multiple methods:** Test both Docker and package installations
5. **Real services:** Prometheus and Grafana are actually running

## Help

```bash
./test-toolkit.sh help
```

Shows all available commands and modes.
