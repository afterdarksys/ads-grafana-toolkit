# Grafana Setup Toolkit

Automated setup scripts for installing and configuring Grafana with multiple deployment options.

## Features

- **Automatic Detection** - Detects existing Grafana installations
- **Multiple Installation Methods** - Package manager, Docker, binary, or source
- **Platform Support** - Linux (Debian/Ubuntu, RHEL/CentOS, Arch), macOS, Windows
- **Docker Automation** - Installs Docker if needed and configures Grafana containers
- **Four Execution Modes** - Automated, step-by-step, play, and run modes
- **Configurable** - YAML-based configuration for all settings
- **Fallback Support** - Automatically tries alternative installation methods
- **User-Friendly** - Designed for beginners with clear prompts and guidance

## Quick Start

### Automated Installation (Recommended for Beginners)

Run the setup in fully automated mode:

```bash
./grafana_setup.py --automated
```

This will:
1. Detect any existing Grafana installations
2. Install Docker if needed (for Docker-based installation)
3. Install Grafana using your preferred method
4. Configure Grafana with sensible defaults
5. Perform health checks
6. Show you how to get started

### Step-by-Step Mode (Recommended for Learning)

Run the setup with interactive prompts to understand each step:

```bash
./grafana_setup.py --step-by-step
```

This mode explains each step and waits for your confirmation before proceeding.

### Other Modes

**Play Mode** - Runs automatically with pauses between steps (good for demonstrations):
```bash
./grafana_setup.py --play
```

**Run Mode** - Quick execution with minimal output:
```bash
./grafana_setup.py --run
```

## Installation Methods

The toolkit supports four installation methods:

### 1. Docker (Default - Easiest)

Uses Docker containers. Best for:
- Quick setup
- Isolated environments
- Easy upgrades
- Cross-platform consistency

```bash
./grafana_setup.py --automated
```

### 2. Package Manager

Uses system package managers (apt, yum, brew). Best for:
- Production deployments
- System integration
- Automatic updates

```bash
# Edit config/setup_config.yaml and set preferred_method: package
./grafana_setup.py --automated
```

### 3. Binary Installation

Downloads and installs pre-built binaries. Best for:
- Specific versions
- No package manager access
- Custom installation paths

```bash
./scripts/install_grafana.py binary --version 10.3.3 --path /opt/grafana
```

### 4. Source Installation

Builds from source code. Best for:
- Development
- Custom modifications
- Latest features

```bash
./scripts/install_grafana.py source --path /opt/grafana
```

## Configuration

### Using Configuration Files

Edit `config/setup_config.yaml` to customize the installation:

```yaml
installation:
  preferred_method: docker  # or package, binary, source
  version: ""              # empty for latest, or specify version
  fallback_order:
    - docker
    - package
    - binary

docker:
  port: 3000
  container_name: "grafana"

grafana:
  security:
    admin_user: "admin"
    admin_password: "admin"  # Change this!
```

Then run:
```bash
./grafana_setup.py --automated --config config/setup_config.yaml
```

### Docker Configuration

The toolkit can use docker-compose for more complex setups:

```bash
# Copy and customize the docker-compose template
cp templates/docker-compose-grafana.yml docker-compose.yml

# Edit docker-compose.yml to add Prometheus, Loki, etc.

# Deploy
docker-compose up -d
```

## Individual Scripts

You can run individual scripts for specific tasks:

### 1. Detect Grafana Installations

```bash
# Text output
./scripts/detect_grafana.py

# JSON output
./scripts/detect_grafana.py -f json

# Verbose mode
./scripts/detect_grafana.py -v
```

### 2. Setup Docker

```bash
# Check if Docker is installed
./scripts/setup_docker.py --check-only

# Install Docker
./scripts/setup_docker.py

# Install with auto-yes
./scripts/setup_docker.py -y
```

### 3. Install Grafana

```bash
# Install via Docker
./scripts/install_grafana.py docker --port 3000

# Install via package manager
./scripts/install_grafana.py package

# Install specific version
./scripts/install_grafana.py docker --version 10.3.3

# Install from binary
./scripts/install_grafana.py binary --path /opt/grafana

# Install from source
./scripts/install_grafana.py source --path /opt/grafana --branch main
```

## Platform-Specific Instructions

### Linux (Debian/Ubuntu)

**Package Installation:**
```bash
./scripts/install_grafana.py package
sudo systemctl start grafana-server
sudo systemctl enable grafana-server
```

**Docker Installation:**
```bash
./scripts/setup_docker.py
./scripts/install_grafana.py docker
```

### Linux (RHEL/CentOS/Fedora)

**Package Installation:**
```bash
./scripts/install_grafana.py package
sudo systemctl start grafana-server
sudo systemctl enable grafana-server
```

### macOS

**Homebrew Installation:**
```bash
./scripts/install_grafana.py package
brew services start grafana
```

**Docker Installation:**
```bash
brew install --cask docker
# Start Docker Desktop
./scripts/install_grafana.py docker
```

### Windows

Use Windows Subsystem for Linux (WSL2) with Docker:
```powershell
# Install WSL2 and Docker Desktop first
wsl
cd /mnt/c/path/to/setup
./grafana_setup.py --automated
```

## Troubleshooting

### Docker not running

```bash
# Linux
sudo systemctl start docker

# macOS
open -a Docker

# Check status
./scripts/setup_docker.py --check-only
```

### Port already in use

Edit `config/setup_config.yaml` and change the port:
```yaml
docker:
  port: 3001  # Use a different port
```

### Permission denied

Add your user to the docker group (Linux):
```bash
sudo usermod -aG docker $USER
newgrp docker
```

### Installation failed

The setup will automatically try fallback methods. To manually specify a method:
```bash
./scripts/install_grafana.py package  # Try package first
./scripts/install_grafana.py docker   # Or try Docker
./scripts/install_grafana.py binary   # Or try binary
```

## Examples

### Example 1: Quick Docker Setup

```bash
# One command to set up everything
./grafana_setup.py --automated
```

Access Grafana at http://localhost:3000 (admin/admin)

### Example 2: Production Package Installation

```bash
# Edit configuration
nano config/setup_config.yaml

# Set:
# preferred_method: package
# admin_password: <strong-password>

# Run setup
./grafana_setup.py --automated --config config/setup_config.yaml
```

### Example 3: Development Setup

```bash
# Install from source for development
./scripts/install_grafana.py source --path ~/grafana --branch main

# Run Grafana
cd ~/grafana
./bin/grafana-server
```

### Example 4: Multi-Container Setup with Prometheus

```bash
# Copy template
cp templates/docker-compose-grafana.yml docker-compose.yml

# Edit docker-compose.yml and uncomment Prometheus section

# Start all services
docker-compose up -d

# Check status
docker-compose ps
```

## Post-Installation

After installation, Grafana will be available at http://localhost:3000

**Default credentials:**
- Username: `admin`
- Password: `admin`

You'll be prompted to change the password on first login.

### Next Steps

1. **Add Data Sources:**
   - Navigate to Configuration > Data Sources
   - Click "Add data source"
   - Select your data source type (Prometheus, MySQL, etc.)

2. **Create Dashboards:**
   Use the ads-grafana-toolkit to generate dashboards:
   ```bash
   # Interactive wizard
   ads-grafana-toolkit wizard

   # From templates
   ads-grafana-toolkit templates create node-exporter -d Prometheus -o dashboard.json

   # From YAML config
   ads-grafana-toolkit convert config.yaml -o dashboard.json
   ```

3. **Import Dashboards:**
   - In Grafana, go to Dashboards > Import
   - Upload your generated JSON file
   - Select your data source
   - Click Import

## Configuration Templates

The `templates/` directory contains:

- `grafana.ini.j2` - Grafana configuration template (Jinja2 format)
- `datasource.yaml` - Data source provisioning template
- `docker-compose-grafana.yml` - Docker Compose template with optional services

Copy and customize these templates for your deployment.

## Advanced Usage

### Custom Configuration

Create a custom config file:

```yaml
# my-config.yaml
installation:
  preferred_method: docker
  version: "10.3.3"

docker:
  port: 3001
  environment:
    GF_SECURITY_ADMIN_USER: "myadmin"
    GF_SECURITY_ADMIN_PASSWORD: "MySecurePassword123!"
    GF_SERVER_ROOT_URL: "http://grafana.example.com"
    GF_SMTP_ENABLED: "true"
    GF_SMTP_HOST: "smtp.gmail.com:587"

datasources:
  enabled: true
  provision:
    - name: "My-Prometheus"
      type: "prometheus"
      url: "http://prometheus:9090"
      enabled: true
```

Run with custom config:
```bash
./grafana_setup.py --automated --config my-config.yaml
```

### Scripted Deployment

Create a deployment script:

```bash
#!/bin/bash
# deploy-grafana.sh

set -e

# Download and extract setup toolkit
wget https://github.com/afterdarksys/ads-grafana-toolkit/archive/main.zip
unzip main.zip
cd ads-grafana-toolkit-main/setup

# Run automated setup
./grafana_setup.py --automated --verbose

# Wait for Grafana to be ready
echo "Waiting for Grafana..."
until curl -s http://localhost:3000/api/health > /dev/null; do
    sleep 2
done

echo "Grafana is ready!"
```

### CI/CD Integration

Use in CI/CD pipelines:

```yaml
# .github/workflows/deploy-grafana.yml
name: Deploy Grafana
on: [push]
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Setup Grafana
        run: |
          cd setup
          ./grafana_setup.py --automated --run
      - name: Verify
        run: curl -f http://localhost:3000/api/health
```

## Architecture

```
setup/
├── grafana_setup.py          # Main orchestration script
├── scripts/
│   ├── detect_grafana.py     # Detection script
│   ├── setup_docker.py       # Docker setup
│   └── install_grafana.py    # Grafana installation
├── templates/
│   ├── grafana.ini.j2        # Config template
│   ├── datasource.yaml       # Datasource template
│   └── docker-compose-grafana.yml
├── config/
│   └── setup_config.yaml     # Default configuration
└── README.md                 # This file
```

## FAQ

**Q: Which installation method should I use?**
A: For beginners and quick setups, use Docker (default). For production, use package installation.

**Q: Can I change the port?**
A: Yes, edit `config/setup_config.yaml` or use `--port` flag with Docker installation.

**Q: How do I upgrade Grafana?**
A: For Docker: pull new image and recreate container. For packages: use your package manager.

**Q: Can I run multiple Grafana instances?**
A: Yes, with Docker use different ports and container names. With packages, use different config files.

**Q: Where are the data files stored?**
A: Docker: in named volumes. Packages: /var/lib/grafana. Source/Binary: configurable.

**Q: How do I backup Grafana?**
A: Backup the database file (sqlite: grafana.db) and /var/lib/grafana directory.

**Q: Can I use an external database?**
A: Yes, edit the database section in `config/setup_config.yaml` before installation.

## Requirements

**Minimum:**
- Python 3.7+
- Internet connection (for downloads)
- sudo access (for package/source installations)

**Optional:**
- Docker (for Docker installation)
- Go 1.21+ (for source installation)
- Node.js 18+ (for source installation)

## Support

- **Issues:** https://github.com/afterdarksys/ads-grafana-toolkit/issues
- **Documentation:** https://github.com/afterdarksys/ads-grafana-toolkit

## License

MIT License - See main repository LICENSE file
