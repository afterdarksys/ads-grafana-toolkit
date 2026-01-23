# Quick Start Guide

Get Grafana up and running in minutes!

## For Complete Beginners

Just run this one command:

```bash
./grafana_setup.py --automated
```

That's it! The script will:
1. Detect if you already have Grafana
2. Install Docker if needed
3. Install and configure Grafana
4. Start Grafana on http://localhost:3000

Login with `admin` / `admin` (you'll be prompted to change the password).

## I Want to See What's Happening

Run in step-by-step mode to see and confirm each action:

```bash
./grafana_setup.py --step-by-step
```

This is great for learning what the setup is doing.

## Just the Commands

### Detect Existing Grafana

```bash
./scripts/detect_grafana.py
```

### Install Docker

```bash
./scripts/setup_docker.py
```

### Install Grafana (Docker)

```bash
./scripts/install_grafana.py docker
```

### Install Grafana (Package Manager)

```bash
./scripts/install_grafana.py package
```

## What Gets Installed

**Docker Method (Default):**
- Grafana container running on port 3000
- Persistent data volume for your dashboards
- Auto-restart enabled

**Package Method:**
- Grafana installed via apt/yum/brew
- Systemd service configured (Linux)
- Config files in `/etc/grafana`

## After Installation

1. **Access Grafana:** http://localhost:3000
2. **Login:** admin / admin
3. **Add a data source:** Configuration → Data Sources
4. **Create dashboards:** Use the ads-grafana-toolkit:
   ```bash
   ads-grafana-toolkit wizard
   ```

## Troubleshooting

**Can't connect to Grafana?**
```bash
# Check if it's running
docker ps  # for Docker
sudo systemctl status grafana-server  # for packages
```

**Port 3000 already in use?**
```bash
# Use a different port
./scripts/install_grafana.py docker --port 3001
```

**Permission denied?**
```bash
# Add yourself to docker group (Linux)
sudo usermod -aG docker $USER
newgrp docker
```

## Common Workflows

### Docker Setup (Easiest)
```bash
./grafana_setup.py --automated
```

### Production Package Setup
```bash
# Edit config first
nano config/setup_config.yaml
# Change preferred_method to "package"
# Change admin password

./grafana_setup.py --automated
```

### Development from Source
```bash
./scripts/install_grafana.py source --path ~/grafana
cd ~/grafana
./bin/grafana-server
```

## Next Steps

See the full [README.md](README.md) for:
- Configuration options
- Platform-specific instructions
- Advanced usage
- Docker Compose with Prometheus/Loki
- CI/CD integration

## Need Help?

- Full documentation: [README.md](README.md)
- Issues: https://github.com/afterdarksys/ads-grafana-toolkit/issues
- Grafana docs: https://grafana.com/docs/
