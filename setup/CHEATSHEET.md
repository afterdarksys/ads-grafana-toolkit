# Grafana Setup - Command Cheatsheet

Quick reference for all commands and options.

## Main Setup Script

```bash
# Fully automated (recommended)
./grafana_setup.py --automated

# Step-by-step with prompts
./grafana_setup.py --step-by-step

# Automated with pauses
./grafana_setup.py --play

# Quick run, minimal output
./grafana_setup.py --run

# With custom config
./grafana_setup.py --automated --config my-config.yaml

# Verbose output
./grafana_setup.py --automated --verbose
```

## Detection Script

```bash
# Detect Grafana installations
./scripts/detect_grafana.py

# JSON output
./scripts/detect_grafana.py -f json

# Verbose mode
./scripts/detect_grafana.py -v
```

## Docker Setup Script

```bash
# Check if Docker is installed
./scripts/setup_docker.py --check-only

# Install Docker
./scripts/setup_docker.py

# Install with auto-yes
./scripts/setup_docker.py -y

# Verbose installation
./scripts/setup_docker.py -v -y
```

## Grafana Installation Script

### Docker Installation
```bash
# Default port 3000
./scripts/install_grafana.py docker

# Custom port
./scripts/install_grafana.py docker --port 3001

# Specific version
./scripts/install_grafana.py docker --version 10.3.3

# Auto-yes mode
./scripts/install_grafana.py docker -y

# Verbose
./scripts/install_grafana.py docker -v -y
```

### Package Installation
```bash
# Install via package manager
./scripts/install_grafana.py package

# Specific version
./scripts/install_grafana.py package --version 10.3.3

# Auto-yes
./scripts/install_grafana.py package -y
```

### Binary Installation
```bash
# Install to default location
./scripts/install_grafana.py binary

# Custom path
./scripts/install_grafana.py binary --path /opt/grafana

# Specific version
./scripts/install_grafana.py binary --version 10.3.3 --path ~/grafana
```

### Source Installation
```bash
# Install from main branch
./scripts/install_grafana.py source

# Custom path
./scripts/install_grafana.py source --path ~/grafana-dev

# Specific branch
./scripts/install_grafana.py source --branch v10.3.x --path /opt/grafana
```

## Docker Commands

```bash
# Start Grafana
docker start grafana

# Stop Grafana
docker stop grafana

# Restart Grafana
docker restart grafana

# View logs
docker logs grafana
docker logs -f grafana  # Follow logs

# Check status
docker ps | grep grafana

# Remove container
docker stop grafana && docker rm grafana

# Remove container and volume
docker stop grafana && docker rm grafana
docker volume rm grafana-data
```

## Systemd Commands (Linux Package Install)

```bash
# Start Grafana
sudo systemctl start grafana-server

# Stop Grafana
sudo systemctl stop grafana-server

# Restart Grafana
sudo systemctl restart grafana-server

# Status
sudo systemctl status grafana-server

# Enable on boot
sudo systemctl enable grafana-server

# Disable on boot
sudo systemctl disable grafana-server

# View logs
sudo journalctl -u grafana-server -f
```

## Configuration Files

```bash
# Edit main config
nano config/setup_config.yaml

# View Grafana config template
cat templates/grafana.ini.j2

# View datasource template
cat templates/datasource.yaml

# Edit docker-compose
cp templates/docker-compose-grafana.yml docker-compose.yml
nano docker-compose.yml
```

## Docker Compose

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# View logs
docker-compose logs -f

# Restart services
docker-compose restart

# Check status
docker-compose ps

# Remove everything
docker-compose down -v
```

## Common Workflows

### Fresh Install (Docker)
```bash
./grafana_setup.py --automated
```

### Fresh Install (Package)
```bash
# Edit config first
nano config/setup_config.yaml
# Set: preferred_method: package

./grafana_setup.py --automated
```

### Reinstall Grafana
```bash
# Docker
docker stop grafana && docker rm grafana
./scripts/install_grafana.py docker

# Package (Debian/Ubuntu)
sudo apt-get remove grafana
./scripts/install_grafana.py package

# Package (RHEL/CentOS)
sudo yum remove grafana
./scripts/install_grafana.py package
```

### Change Grafana Port
```bash
# Docker
docker stop grafana && docker rm grafana
./scripts/install_grafana.py docker --port 3001

# Package - edit config
sudo nano /etc/grafana/grafana.ini
# Change http_port = 3001
sudo systemctl restart grafana-server
```

### Upgrade Grafana
```bash
# Docker
docker pull grafana/grafana:latest
docker stop grafana && docker rm grafana
./scripts/install_grafana.py docker

# Package (Debian/Ubuntu)
sudo apt-get update
sudo apt-get upgrade grafana

# Package (RHEL/CentOS)
sudo yum update grafana
```

### Backup Grafana
```bash
# Docker - backup volume
docker run --rm -v grafana-data:/data -v $(pwd):/backup \
  ubuntu tar czf /backup/grafana-backup.tar.gz /data

# Package - backup files
sudo tar czf grafana-backup.tar.gz \
  /var/lib/grafana \
  /etc/grafana/grafana.ini
```

### Restore Grafana
```bash
# Docker - restore volume
docker run --rm -v grafana-data:/data -v $(pwd):/backup \
  ubuntu tar xzf /backup/grafana-backup.tar.gz -C /

# Package - restore files
sudo tar xzf grafana-backup.tar.gz -C /
sudo systemctl restart grafana-server
```

## Troubleshooting Commands

```bash
# Check if port is in use
netstat -tlnp | grep 3000
lsof -i :3000

# Check Docker status
docker info
systemctl status docker

# Check Grafana container
docker inspect grafana

# Test Grafana HTTP
curl http://localhost:3000/api/health

# Check Grafana logs (Docker)
docker logs grafana --tail 100

# Check Grafana logs (Package)
sudo tail -f /var/log/grafana/grafana.log

# Verify Docker permissions
groups | grep docker

# Test Docker without sudo
docker ps
```

## File Locations

### Docker
- Data: Docker volume `grafana-data`
- Config: Container `/etc/grafana/grafana.ini`
- Logs: `docker logs grafana`

### Package (Linux)
- Data: `/var/lib/grafana`
- Config: `/etc/grafana/grafana.ini`
- Logs: `/var/log/grafana/`
- Plugins: `/var/lib/grafana/plugins`
- Provisioning: `/etc/grafana/provisioning`

### Package (macOS Homebrew)
- Data: `/usr/local/var/lib/grafana`
- Config: `/usr/local/etc/grafana/grafana.ini`
- Logs: `/usr/local/var/log/grafana`

### Binary/Source
- Configurable via `--path` option
- Default: `/opt/grafana`

## Environment Variables

```bash
# Set Grafana admin password
export GF_SECURITY_ADMIN_PASSWORD=mypassword

# Set database type
export GF_DATABASE_TYPE=mysql
export GF_DATABASE_HOST=localhost:3306
export GF_DATABASE_NAME=grafana
export GF_DATABASE_USER=grafana
export GF_DATABASE_PASSWORD=password

# Set SMTP
export GF_SMTP_ENABLED=true
export GF_SMTP_HOST=smtp.gmail.com:587
export GF_SMTP_USER=your@email.com
export GF_SMTP_PASSWORD=yourpassword
```

## URLs

- Grafana UI: http://localhost:3000
- Health check: http://localhost:3000/api/health
- Metrics: http://localhost:3000/metrics
- API docs: http://localhost:3000/swagger

## Default Credentials

- Username: `admin`
- Password: `admin`
- Change password on first login!

## Quick Help

```bash
# Script help
./grafana_setup.py --help
./scripts/detect_grafana.py --help
./scripts/setup_docker.py --help
./scripts/install_grafana.py --help

# Read documentation
cat README.md
cat QUICKSTART.md
cat FEATURES.md
```
