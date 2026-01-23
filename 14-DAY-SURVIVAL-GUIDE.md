# 14-Day Survival Guide
## Complete Grafana Setup for Absolute Beginners

**You have 14 days of root access. This guide gets you fully operational FAST.**

---

## DAY 1: Get Grafana Running (30 minutes)

### Step 1: Extract the toolkit
```bash
cd ~
unzip ads-grafana-toolkit.zip  # or however you received it
cd ads-grafana-toolkit
```

### Step 2: Run the automated setup
```bash
cd setup
./grafana_setup.py --automated
```

**That's it.** Grafana will be running at http://localhost:3000

- Username: `admin`
- Password: `admin` (change it when prompted)

### If something goes wrong:
```bash
# Try step-by-step mode to see what's happening
./grafana_setup.py --step-by-step
```

---

## DAY 2-3: Create Your First Dashboard (1 hour)

### Option A: Use the Wizard (Easiest)
```bash
cd ~/ads-grafana-toolkit
ads-grafana-toolkit wizard
```

Follow the prompts. It'll ask you simple questions and build a dashboard.

### Option B: Use a Template
```bash
# See available templates
ads-grafana-toolkit templates list

# Create a server monitoring dashboard
ads-grafana-toolkit templates create node-exporter -o my-dashboard.json

# Import it to Grafana
```

Then in Grafana web UI:
1. Go to http://localhost:3000
2. Click "Dashboards" → "Import"
3. Upload `my-dashboard.json`
4. Done!

### Option C: Write YAML (Super Easy)
Create `my-dashboard.yaml`:
```yaml
name: "My First Dashboard"
datasource: Prometheus

panels:
  - title: "CPU Usage"
    query: 'avg(rate(node_cpu_seconds_total{mode!="idle"}[5m])) * 100'
    type: gauge
    unit: percent
```

Convert it:
```bash
ads-grafana-toolkit convert my-dashboard.yaml -o dashboard.json
```

---

## DAY 4-5: Add Data Sources (30 minutes)

### If you have Prometheus:
1. Open Grafana → Configuration → Data Sources
2. Click "Add data source"
3. Select "Prometheus"
4. URL: `http://localhost:9090` (or your Prometheus URL)
5. Click "Save & Test"

### If you DON'T have Prometheus yet:
```bash
# Quick Prometheus setup with Docker
docker run -d --name prometheus \
  -p 9090:9090 \
  prom/prometheus
```

### Other data sources:
- MySQL: Use your database connection details
- InfluxDB: Install separately or use Docker
- PostgreSQL: Use your database connection details

**Templates are in:** `setup/templates/datasource.yaml`

---

## DAY 6-7: Advanced Features (1 hour)

### Build Queries Interactively
```bash
cd extras
python3 promql_builder.py interactive
```

This walks you through building PromQL queries step-by-step.

### Use Jsonnet for Complex Dashboards
```bash
cd extras

# Setup (one-time)
python3 jsonnet_support.py setup

# Create example
python3 jsonnet_support.py example

# Convert to JSON
python3 jsonnet_support.py convert example_dashboard.jsonnet
```

### Generate Documentation
```bash
cd extras

# Export dashboard to Markdown
python3 writers_toolkit.py ~/my-dashboard.json -f markdown

# Or HTML
python3 writers_toolkit.py ~/my-dashboard.json -f html
```

---

## DAY 8-10: Production Readiness (2 hours)

### 1. Change Default Password
```bash
# In Grafana UI: User icon → Change password
```

### 2. Set Up Persistent Storage
If using Docker:
```bash
# Already done! Data is in 'grafana-data' volume

# To backup:
docker run --rm -v grafana-data:/data -v $(pwd):/backup \
  ubuntu tar czf /backup/grafana-backup.tar.gz /data
```

### 3. Configure Alerts (Optional)
Edit `setup/config/setup_config.yaml`:
```yaml
grafana:
  smtp:
    enabled: true
    host: "smtp.gmail.com:587"
    user: "your-email@gmail.com"
    password: "your-app-password"
```

Then restart Grafana:
```bash
docker restart grafana
# OR
sudo systemctl restart grafana-server
```

### 4. Create API Key
1. Grafana UI → Configuration → API Keys
2. Click "Add API key"
3. Name: "toolkit"
4. Role: "Editor"
5. Save the key somewhere safe!

---

## DAY 11-12: Create Multiple Dashboards (2 hours)

### Batch Create from Templates
```bash
# Create several dashboards at once
for template in node-exporter nginx mysql; do
  ads-grafana-toolkit templates create $template -o ${template}-dashboard.json
done
```

### Import them all to Grafana
1. Go to Dashboards → Import
2. Upload each JSON file
3. Select your data source
4. Click Import

### Organize with Folders
In Grafana UI:
1. Dashboards → Manage
2. New Folder → "Production"
3. Drag dashboards into folders

---

## DAY 13: Document Everything (1 hour)

### Generate docs for all dashboards
```bash
cd extras

# For each dashboard
for dashboard in ~/ads-grafana-toolkit/*.json; do
  python3 writers_toolkit.py "$dashboard" -f html
done
```

### Create a README
```bash
cat > ~/grafana-setup-notes.md << 'EOF'
# My Grafana Setup

## Dashboards Created
- Server Monitoring (node-exporter-dashboard.json)
- MySQL Metrics (mysql-dashboard.json)
- Nginx Stats (nginx-dashboard.json)

## Data Sources
- Prometheus: http://localhost:9090
- MySQL: localhost:3306

## Backup Location
- Docker volume: grafana-data
- Backup command: [see DAY 8-10]

## Login
- URL: http://localhost:3000
- Username: admin
- Password: [STORED SECURELY]
- API Key: [STORED SECURELY]
EOF
```

---

## DAY 14: Final Checklist & Handoff

### ✓ Verify Everything Works
```bash
# Check Grafana is running
curl http://localhost:3000/api/health

# Check Docker (if using Docker)
docker ps | grep grafana

# Check service (if using packages)
sudo systemctl status grafana-server
```

### ✓ Create Backup
```bash
cd ~/ads-grafana-toolkit

# Backup everything
tar czf grafana-complete-backup-$(date +%Y%m%d).tar.gz \
  setup/ \
  extras/ \
  *.json \
  *.yaml \
  ~/grafana-setup-notes.md

# Backup Grafana data
./setup/scripts/detect_grafana.py -v
# Follow backup instructions for your installation type
```

### ✓ Test Recovery
```bash
# Stop Grafana
docker stop grafana  # OR sudo systemctl stop grafana-server

# Start it again
docker start grafana  # OR sudo systemctl start grafana-server

# Verify dashboards still exist
curl -s http://localhost:3000/api/search | jq
```

### ✓ Prepare Documentation
Create `HANDOFF.md`:
```markdown
# Grafana Handoff Documentation

## Access
- URL: http://[SERVER_IP]:3000
- Username: admin
- Password: [see secure location]
- API Key: [see secure location]

## Dashboards
[List all dashboards]

## Data Sources
[List all data sources]

## Maintenance
- Restart: `docker restart grafana` OR `sudo systemctl restart grafana-server`
- Logs: `docker logs grafana` OR `sudo journalctl -u grafana-server`
- Backup: See ~/ads-grafana-toolkit/14-DAY-SURVIVAL-GUIDE.md DAY 8-10

## Support
- Full docs: ~/ads-grafana-toolkit/README.md
- Setup docs: ~/ads-grafana-toolkit/setup/README.md
- Toolkit repo: https://github.com/afterdarksys/ads-grafana-toolkit

## Created by: [YOUR NAME]
## Date: [TODAY'S DATE]
```

---

## Emergency Commands (Keep This Handy!)

### Grafana won't start
```bash
# Docker
docker logs grafana --tail 50
docker restart grafana

# Package
sudo systemctl status grafana-server
sudo journalctl -u grafana-server -n 50
sudo systemctl restart grafana-server
```

### Can't login
```bash
# Reset admin password (Docker)
docker exec -it grafana grafana-cli admin reset-admin-password newpassword

# Reset admin password (Package)
grafana-cli admin reset-admin-password newpassword
```

### Port conflict
```bash
# Check what's using port 3000
sudo lsof -i :3000

# Change Grafana port (Docker)
docker stop grafana && docker rm grafana
./setup/scripts/install_grafana.py docker --port 3001

# Change Grafana port (Package)
sudo nano /etc/grafana/grafana.ini
# Change: http_port = 3001
sudo systemctl restart grafana-server
```

### Complete reinstall
```bash
# Docker
docker stop grafana && docker rm grafana
docker volume rm grafana-data
./setup/grafana_setup.py --automated

# Package (Debian/Ubuntu)
sudo systemctl stop grafana-server
sudo apt-get remove --purge grafana
./setup/grafana_setup.py --automated
```

### Backup NOW
```bash
# Docker
docker run --rm -v grafana-data:/data -v $(pwd):/backup \
  ubuntu tar czf /backup/emergency-backup-$(date +%Y%m%d-%H%M%S).tar.gz /data

# Package
sudo tar czf emergency-backup-$(date +%Y%m%d-%H%M%S).tar.gz \
  /var/lib/grafana \
  /etc/grafana/grafana.ini
```

---

## Day-by-Day Checklist

- [ ] **Day 1**: Grafana installed and running
- [ ] **Day 2-3**: First dashboard created
- [ ] **Day 4-5**: Data sources connected
- [ ] **Day 6-7**: Explored advanced features
- [ ] **Day 8-10**: Production-ready (passwords, backups, alerts)
- [ ] **Day 11-12**: Multiple dashboards created
- [ ] **Day 13**: Documentation generated
- [ ] **Day 14**: Final backup and handoff prepared

---

## Quick Reference Card (Print This!)

```
┌─────────────────────────────────────────────────────────────┐
│                   GRAFANA QUICK REFERENCE                    │
├─────────────────────────────────────────────────────────────┤
│ URL: http://localhost:3000                                   │
│ Login: admin / [your-password]                               │
├─────────────────────────────────────────────────────────────┤
│ RESTART:                                                     │
│   Docker: docker restart grafana                             │
│   Package: sudo systemctl restart grafana-server             │
├─────────────────────────────────────────────────────────────┤
│ LOGS:                                                        │
│   Docker: docker logs grafana                                │
│   Package: sudo journalctl -u grafana-server                 │
├─────────────────────────────────────────────────────────────┤
│ BACKUP:                                                      │
│   See ~/ads-grafana-toolkit/14-DAY-SURVIVAL-GUIDE.md         │
│   Day 8-10 section                                           │
├─────────────────────────────────────────────────────────────┤
│ TOOLKIT LOCATION:                                            │
│   ~/ads-grafana-toolkit                                      │
├─────────────────────────────────────────────────────────────┤
│ CREATE DASHBOARD:                                            │
│   ads-grafana-toolkit wizard                                 │
│   ads-grafana-toolkit templates list                         │
└─────────────────────────────────────────────────────────────┘
```

**REMEMBER**: If you run into issues, the setup scripts have `--step-by-step` mode to show you exactly what's happening!

Good luck! 🚀
