#!/usr/bin/env python3
"""
Monitoring Stack Audit Script
Detects Grafana, Graphite, Prometheus, MySQL/InnoDB, and related services.
Provides comprehensive system audit before installation.
"""

import json
import os
import platform
import shutil
import socket
import subprocess
import sys
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import List, Optional, Dict, Any


@dataclass
class ServiceInfo:
    """Represents a detected service."""
    name: str
    type: str  # grafana, prometheus, graphite, mysql, etc.
    installed: bool = False
    running: bool = False
    version: Optional[str] = None
    install_method: Optional[str] = None  # docker, package, binary, source
    path: Optional[str] = None
    config_path: Optional[str] = None
    data_path: Optional[str] = None
    port: Optional[int] = None
    url: Optional[str] = None
    container_id: Optional[str] = None
    process_id: Optional[int] = None
    user: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self):
        return asdict(self)


class MonitoringStackAuditor:
    """Audits the complete monitoring stack."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.system = platform.system().lower()
        self.services: List[ServiceInfo] = []

    def log(self, message: str, level: str = "INFO"):
        """Log message."""
        if self.verbose or level in ("WARN", "ERROR"):
            prefix = f"[{level}]"
            print(f"{prefix} {message}", file=sys.stderr if level == "ERROR" else sys.stdout)

    def check_port(self, port: int) -> bool:
        """Check if a port is in use."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(('localhost', port))
        sock.close()
        return result == 0

    def get_process_on_port(self, port: int) -> Optional[Dict[str, Any]]:
        """Get process information for a port."""
        try:
            if self.system == "linux":
                result = subprocess.run(
                    ["sudo", "lsof", "-i", f":{port}", "-P", "-n"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
            else:
                result = subprocess.run(
                    ["lsof", "-i", f":{port}", "-P", "-n"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )

            if result.returncode == 0 and result.stdout:
                lines = result.stdout.strip().split('\n')
                if len(lines) > 1:
                    parts = lines[1].split()
                    if len(parts) >= 9:
                        return {
                            "command": parts[0],
                            "pid": int(parts[1]),
                            "user": parts[2],
                        }
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, ValueError):
            pass
        return None

    def detect_grafana(self):
        """Detect Grafana installations."""
        self.log("Scanning for Grafana...")

        # Docker
        if shutil.which("docker"):
            try:
                result = subprocess.run(
                    ["docker", "ps", "-a", "--filter", "ancestor=grafana/grafana",
                     "--format", "{{.ID}}\t{{.Names}}\t{{.Status}}\t{{.Ports}}"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )

                if result.returncode == 0 and result.stdout.strip():
                    for line in result.stdout.strip().split('\n'):
                        parts = line.split('\t')
                        if len(parts) >= 3:
                            container_id = parts[0]
                            name = parts[1]
                            status = parts[2]
                            ports = parts[3] if len(parts) > 3 else ""

                            running = "up" in status.lower()
                            port = self._extract_port_from_docker(ports)

                            # Get version
                            version = None
                            try:
                                ver_result = subprocess.run(
                                    ["docker", "exec", container_id, "grafana-server", "-v"],
                                    capture_output=True,
                                    text=True,
                                    timeout=5
                                )
                                if ver_result.returncode == 0:
                                    version = ver_result.stdout.strip().split()[-1]
                            except:
                                pass

                            service = ServiceInfo(
                                name=f"Grafana (Docker: {name})",
                                type="grafana",
                                installed=True,
                                running=running,
                                version=version,
                                install_method="docker",
                                path=f"docker:{name}",
                                container_id=container_id,
                                port=port,
                                url=f"http://localhost:{port}" if port else None,
                                details={"status": status, "ports": ports}
                            )
                            self.services.append(service)

            except (subprocess.TimeoutExpired, subprocess.SubprocessError):
                pass

        # Package installation
        if self.system == "linux":
            # Check systemd service
            try:
                result = subprocess.run(
                    ["systemctl", "is-active", "grafana-server"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                running = "active" in result.stdout

                # Check if installed
                if shutil.which("dpkg"):
                    pkg_result = subprocess.run(
                        ["dpkg", "-l", "grafana"],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if "ii" in pkg_result.stdout:
                        version = self._parse_dpkg_version(pkg_result.stdout)
                        service = ServiceInfo(
                            name="Grafana (Package)",
                            type="grafana",
                            installed=True,
                            running=running,
                            version=version,
                            install_method="package",
                            path="/usr/share/grafana",
                            config_path="/etc/grafana/grafana.ini",
                            data_path="/var/lib/grafana",
                            port=3000,
                            url="http://localhost:3000" if running else None
                        )
                        self.services.append(service)

                elif shutil.which("rpm"):
                    pkg_result = subprocess.run(
                        ["rpm", "-qa", "grafana"],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if pkg_result.stdout.strip():
                        version = pkg_result.stdout.strip().split('-')[1] if '-' in pkg_result.stdout else None
                        service = ServiceInfo(
                            name="Grafana (Package)",
                            type="grafana",
                            installed=True,
                            running=running,
                            version=version,
                            install_method="package",
                            path="/usr/share/grafana",
                            config_path="/etc/grafana/grafana.ini",
                            data_path="/var/lib/grafana",
                            port=3000,
                            url="http://localhost:3000" if running else None
                        )
                        self.services.append(service)

            except (subprocess.TimeoutExpired, subprocess.SubprocessError):
                pass

        # Binary in PATH
        if shutil.which("grafana-server"):
            service = ServiceInfo(
                name="Grafana (Binary)",
                type="grafana",
                installed=True,
                install_method="binary",
                path=shutil.which("grafana-server")
            )
            self.services.append(service)

    def detect_prometheus(self):
        """Detect Prometheus installations."""
        self.log("Scanning for Prometheus...")

        # Check common ports
        prometheus_ports = [9090, 9091]
        for port in prometheus_ports:
            if self.check_port(port):
                proc_info = self.get_process_on_port(port)

                # Try to get version via API
                version = None
                try:
                    import urllib.request
                    req = urllib.request.Request(f"http://localhost:{port}/api/v1/status/buildinfo")
                    with urllib.request.urlopen(req, timeout=5) as response:
                        data = json.loads(response.read())
                        if data.get("status") == "success":
                            version = data.get("data", {}).get("version")
                except:
                    pass

                service = ServiceInfo(
                    name=f"Prometheus (Port {port})",
                    type="prometheus",
                    installed=True,
                    running=True,
                    version=version,
                    port=port,
                    url=f"http://localhost:{port}",
                    process_id=proc_info["pid"] if proc_info else None,
                    user=proc_info["user"] if proc_info else None,
                    details=proc_info or {}
                )
                self.services.append(service)

        # Docker
        if shutil.which("docker"):
            try:
                result = subprocess.run(
                    ["docker", "ps", "-a", "--filter", "ancestor=prom/prometheus",
                     "--format", "{{.ID}}\t{{.Names}}\t{{.Status}}\t{{.Ports}}"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )

                if result.returncode == 0 and result.stdout.strip():
                    for line in result.stdout.strip().split('\n'):
                        parts = line.split('\t')
                        if len(parts) >= 3:
                            container_id = parts[0]
                            name = parts[1]
                            status = parts[2]
                            ports = parts[3] if len(parts) > 3 else ""

                            running = "up" in status.lower()
                            port = self._extract_port_from_docker(ports)

                            service = ServiceInfo(
                                name=f"Prometheus (Docker: {name})",
                                type="prometheus",
                                installed=True,
                                running=running,
                                install_method="docker",
                                path=f"docker:{name}",
                                container_id=container_id,
                                port=port,
                                url=f"http://localhost:{port}" if port else None,
                                details={"status": status}
                            )
                            self.services.append(service)

            except (subprocess.TimeoutExpired, subprocess.SubprocessError):
                pass

        # Binary in PATH
        if shutil.which("prometheus"):
            service = ServiceInfo(
                name="Prometheus (Binary)",
                type="prometheus",
                installed=True,
                install_method="binary",
                path=shutil.which("prometheus")
            )
            self.services.append(service)

    def detect_graphite(self):
        """Detect Graphite installations."""
        self.log("Scanning for Graphite...")

        # Check common ports
        graphite_ports = {
            80: "web",
            8080: "web",
            2003: "carbon-cache",
            2004: "carbon-relay",
            7002: "carbon-cache-query"
        }

        for port, component in graphite_ports.items():
            if self.check_port(port):
                proc_info = self.get_process_on_port(port)

                service = ServiceInfo(
                    name=f"Graphite {component.title()} (Port {port})",
                    type="graphite",
                    installed=True,
                    running=True,
                    port=port,
                    url=f"http://localhost:{port}" if "web" in component else None,
                    process_id=proc_info["pid"] if proc_info else None,
                    user=proc_info["user"] if proc_info else None,
                    details={"component": component, "process": proc_info or {}}
                )
                self.services.append(service)

        # Docker
        if shutil.which("docker"):
            try:
                result = subprocess.run(
                    ["docker", "ps", "-a", "--filter", "name=graphite",
                     "--format", "{{.ID}}\t{{.Names}}\t{{.Status}}\t{{.Ports}}"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )

                if result.returncode == 0 and result.stdout.strip():
                    for line in result.stdout.strip().split('\n'):
                        parts = line.split('\t')
                        if len(parts) >= 3:
                            container_id = parts[0]
                            name = parts[1]
                            status = parts[2]
                            ports = parts[3] if len(parts) > 3 else ""

                            running = "up" in status.lower()
                            port = self._extract_port_from_docker(ports)

                            service = ServiceInfo(
                                name=f"Graphite (Docker: {name})",
                                type="graphite",
                                installed=True,
                                running=running,
                                install_method="docker",
                                path=f"docker:{name}",
                                container_id=container_id,
                                port=port,
                                url=f"http://localhost:{port}" if port else None,
                                details={"status": status}
                            )
                            self.services.append(service)

            except (subprocess.TimeoutExpired, subprocess.SubprocessError):
                pass

        # Check for graphite-web package
        if self.system == "linux":
            for pkg in ["graphite-web", "graphite-carbon"]:
                if shutil.which("dpkg"):
                    try:
                        result = subprocess.run(
                            ["dpkg", "-l", pkg],
                            capture_output=True,
                            text=True,
                            timeout=5
                        )
                        if "ii" in result.stdout:
                            service = ServiceInfo(
                                name=f"{pkg.title()} (Package)",
                                type="graphite",
                                installed=True,
                                install_method="package",
                                details={"package": pkg}
                            )
                            self.services.append(service)
                    except:
                        pass

    def detect_mysql(self):
        """Detect MySQL/MariaDB installations."""
        self.log("Scanning for MySQL/MariaDB...")

        # Check port 3306
        if self.check_port(3306):
            proc_info = self.get_process_on_port(3306)

            # Try to get version
            version = None
            engine = "MySQL"
            try:
                result = subprocess.run(
                    ["mysql", "--version"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    version_str = result.stdout.strip()
                    version = version_str.split()[2] if len(version_str.split()) > 2 else None
                    if "mariadb" in version_str.lower():
                        engine = "MariaDB"
            except:
                pass

            # Check for InnoDB
            innodb_status = "Unknown"
            try:
                result = subprocess.run(
                    ["mysql", "-e", "SHOW ENGINES;"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    if "InnoDB" in result.stdout:
                        innodb_status = "Available"
                        if "DEFAULT" in result.stdout:
                            innodb_status = "Default"
            except:
                pass

            service = ServiceInfo(
                name=f"{engine} Server",
                type="mysql",
                installed=True,
                running=True,
                version=version,
                port=3306,
                process_id=proc_info["pid"] if proc_info else None,
                user=proc_info["user"] if proc_info else None,
                details={
                    "engine": engine,
                    "innodb": innodb_status,
                    "process": proc_info or {}
                }
            )
            self.services.append(service)

        # Docker
        if shutil.which("docker"):
            for image in ["mysql", "mariadb"]:
                try:
                    result = subprocess.run(
                        ["docker", "ps", "-a", "--filter", f"ancestor={image}",
                         "--format", "{{.ID}}\t{{.Names}}\t{{.Status}}\t{{.Ports}}"],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )

                    if result.returncode == 0 and result.stdout.strip():
                        for line in result.stdout.strip().split('\n'):
                            parts = line.split('\t')
                            if len(parts) >= 3:
                                container_id = parts[0]
                                name = parts[1]
                                status = parts[2]
                                ports = parts[3] if len(parts) > 3 else ""

                                running = "up" in status.lower()
                                port = self._extract_port_from_docker(ports)

                                service = ServiceInfo(
                                    name=f"{image.title()} (Docker: {name})",
                                    type="mysql",
                                    installed=True,
                                    running=running,
                                    install_method="docker",
                                    path=f"docker:{name}",
                                    container_id=container_id,
                                    port=port,
                                    details={"status": status, "image": image}
                                )
                                self.services.append(service)

                except (subprocess.TimeoutExpired, subprocess.SubprocessError):
                    pass

        # Package installation
        if shutil.which("mysql"):
            service = ServiceInfo(
                name="MySQL Client",
                type="mysql",
                installed=True,
                install_method="package",
                path=shutil.which("mysql"),
                details={"type": "client"}
            )
            self.services.append(service)

    def detect_legacy_monitoring(self):
        """Detect legacy monitoring systems."""
        self.log("Scanning for legacy monitoring systems...")

        # Nagios
        nagios_paths = [
            "/usr/local/nagios",
            "/usr/share/nagios",
            "/opt/nagios"
        ]

        for path in nagios_paths:
            if Path(path).exists():
                # Check for nagios binary
                nagios_bin = Path(path) / "bin" / "nagios"
                if nagios_bin.exists():
                    version = None
                    try:
                        result = subprocess.run(
                            [str(nagios_bin), "-V"],
                            capture_output=True,
                            text=True,
                            timeout=5
                        )
                        if result.returncode == 0:
                            # Parse version from output
                            for line in result.stdout.split('\n'):
                                if "Nagios Core" in line:
                                    parts = line.split()
                                    if len(parts) >= 3:
                                        version = parts[2]
                                    break
                    except:
                        pass

                    # Check if running
                    running = False
                    try:
                        result = subprocess.run(
                            ["pgrep", "-x", "nagios"],
                            capture_output=True,
                            timeout=5
                        )
                        running = result.returncode == 0
                    except:
                        pass

                    service = ServiceInfo(
                        name="Nagios Core",
                        type="nagios",
                        installed=True,
                        running=running,
                        version=version,
                        install_method="package" if path.startswith("/usr") else "source",
                        path=str(path),
                        config_path=str(Path(path) / "etc" / "nagios.cfg"),
                        details={"legacy": True}
                    )
                    self.services.append(service)
                    break

        # Check for Nagios web interface
        if self.check_port(80) or self.check_port(443):
            # Try to detect via Apache/Nginx serving Nagios
            for conf_path in ["/etc/apache2/conf-available/nagios.conf",
                             "/etc/httpd/conf.d/nagios.conf",
                             "/etc/nginx/sites-available/nagios"]:
                if Path(conf_path).exists():
                    service = ServiceInfo(
                        name="Nagios Web Interface",
                        type="nagios",
                        installed=True,
                        running=True,
                        url="http://localhost/nagios",
                        details={"component": "web", "legacy": True}
                    )
                    self.services.append(service)
                    break

        # Check-MK
        checkmk_paths = [
            "/omd/sites",
            "/opt/omd/sites"
        ]

        for base_path in checkmk_paths:
            if Path(base_path).exists():
                # List sites
                try:
                    sites = [d for d in Path(base_path).iterdir() if d.is_dir()]
                    for site in sites:
                        version_file = site / "version"
                        version = None
                        if version_file.exists():
                            try:
                                version = version_file.read_text().strip()
                            except:
                                pass

                        # Check if site is running
                        running = False
                        try:
                            result = subprocess.run(
                                ["omd", "status", site.name],
                                capture_output=True,
                                timeout=5
                            )
                            running = "running" in result.stdout.decode().lower()
                        except:
                            pass

                        service = ServiceInfo(
                            name=f"Check-MK Site: {site.name}",
                            type="checkmk",
                            installed=True,
                            running=running,
                            version=version,
                            install_method="package",
                            path=str(site),
                            url=f"http://localhost/{site.name}",
                            details={"site": site.name, "legacy": True}
                        )
                        self.services.append(service)
                except:
                    pass

        # Icinga
        icinga_paths = [
            ("/usr/sbin/icinga2", "/etc/icinga2", "icinga2"),
            ("/usr/bin/icinga2", "/etc/icinga2", "icinga2"),
            ("/usr/local/icinga2/sbin/icinga2", "/usr/local/icinga2/etc", "icinga2"),
        ]

        for binary_path, config_path, name in icinga_paths:
            if Path(binary_path).exists():
                version = None
                try:
                    result = subprocess.run(
                        [binary_path, "--version"],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if result.returncode == 0:
                        # Parse version
                        for line in result.stdout.split('\n'):
                            if "version" in line.lower():
                                parts = line.split()
                                for part in parts:
                                    if part[0].isdigit():
                                        version = part
                                        break
                                break
                except:
                    pass

                # Check if running
                running = False
                try:
                    if self.system == "linux":
                        result = subprocess.run(
                            ["systemctl", "is-active", "icinga2"],
                            capture_output=True,
                            text=True,
                            timeout=5
                        )
                        running = "active" in result.stdout
                    else:
                        result = subprocess.run(
                            ["pgrep", "-x", "icinga2"],
                            capture_output=True,
                            timeout=5
                        )
                        running = result.returncode == 0
                except:
                    pass

                service = ServiceInfo(
                    name="Icinga2",
                    type="icinga",
                    installed=True,
                    running=running,
                    version=version,
                    install_method="package",
                    path=binary_path,
                    config_path=config_path,
                    details={"legacy": True}
                )
                self.services.append(service)
                break

        # Icinga Web
        icinga_web_paths = [
            "/usr/share/icingaweb2",
            "/usr/local/share/icingaweb2"
        ]

        for web_path in icinga_web_paths:
            if Path(web_path).exists():
                service = ServiceInfo(
                    name="Icinga Web 2",
                    type="icinga",
                    installed=True,
                    path=web_path,
                    url="http://localhost/icingaweb2",
                    details={"component": "web", "legacy": True}
                )
                self.services.append(service)
                break

        # Sensu
        sensu_paths = [
            ("/opt/sensu/bin/sensu-backend", "backend"),
            ("/opt/sensu/bin/sensu-agent", "agent"),
            ("/usr/sbin/sensu-backend", "backend"),
            ("/usr/sbin/sensu-agent", "agent"),
        ]

        for binary_path, component in sensu_paths:
            if Path(binary_path).exists():
                version = None
                try:
                    result = subprocess.run(
                        [binary_path, "version"],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if result.returncode == 0:
                        # Parse version
                        lines = result.stdout.strip().split('\n')
                        if lines:
                            version = lines[0].split()[-1] if lines[0].split() else None
                except:
                    pass

                # Check if running
                running = False
                process_name = f"sensu-{component}"
                try:
                    if self.system == "linux":
                        result = subprocess.run(
                            ["systemctl", "is-active", process_name],
                            capture_output=True,
                            text=True,
                            timeout=5
                        )
                        running = "active" in result.stdout
                    else:
                        result = subprocess.run(
                            ["pgrep", "-f", process_name],
                            capture_output=True,
                            timeout=5
                        )
                        running = result.returncode == 0
                except:
                    pass

                # Backend typically runs on port 8080
                port = 8080 if component == "backend" else None
                url = f"http://localhost:{port}" if port and running else None

                service = ServiceInfo(
                    name=f"Sensu {component.title()}",
                    type="sensu",
                    installed=True,
                    running=running,
                    version=version,
                    install_method="package",
                    path=binary_path,
                    port=port,
                    url=url,
                    details={"component": component, "legacy": True}
                )
                self.services.append(service)

        # Check for Sensu via Docker
        if shutil.which("docker"):
            for image in ["sensu/sensu", "sensu/sensu-go-backend", "sensu/sensu-go-agent"]:
                try:
                    result = subprocess.run(
                        ["docker", "ps", "-a", "--filter", f"ancestor={image}",
                         "--format", "{{.ID}}\t{{.Names}}\t{{.Status}}"],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )

                    if result.returncode == 0 and result.stdout.strip():
                        for line in result.stdout.strip().split('\n'):
                            parts = line.split('\t')
                            if len(parts) >= 3:
                                container_id = parts[0]
                                name = parts[1]
                                status = parts[2]
                                running = "up" in status.lower()

                                component = "backend" if "backend" in image else "agent"

                                service = ServiceInfo(
                                    name=f"Sensu {component.title()} (Docker: {name})",
                                    type="sensu",
                                    installed=True,
                                    running=running,
                                    install_method="docker",
                                    path=f"docker:{name}",
                                    container_id=container_id,
                                    details={"component": component, "legacy": True}
                                )
                                self.services.append(service)
                except:
                    pass

    def detect_other_services(self):
        """Detect other monitoring-related services."""
        self.log("Scanning for other services...")

        services_to_check = [
            ("node_exporter", 9100, "node_exporter", "Prometheus Node Exporter"),
            ("alertmanager", 9093, "alertmanager", "Prometheus Alertmanager"),
            ("pushgateway", 9091, "pushgateway", "Prometheus Pushgateway"),
            ("loki", 3100, "loki", "Grafana Loki"),
            ("influxdb", 8086, "influxdb", "InfluxDB"),
            ("telegraf", None, "telegraf", "Telegraf"),
            ("collectd", None, "collectd", "Collectd"),
            ("statsd", 8125, "statsd", "StatsD"),
        ]

        for binary, port, service_type, name in services_to_check:
            # Check binary
            if shutil.which(binary):
                service = ServiceInfo(
                    name=f"{name} (Binary)",
                    type=service_type,
                    installed=True,
                    install_method="binary",
                    path=shutil.which(binary)
                )
                self.services.append(service)

            # Check port if specified
            if port and self.check_port(port):
                proc_info = self.get_process_on_port(port)
                service = ServiceInfo(
                    name=f"{name} (Port {port})",
                    type=service_type,
                    installed=True,
                    running=True,
                    port=port,
                    url=f"http://localhost:{port}",
                    process_id=proc_info["pid"] if proc_info else None,
                    user=proc_info["user"] if proc_info else None,
                    details=proc_info or {}
                )
                self.services.append(service)

    def _extract_port_from_docker(self, ports_str: str) -> Optional[int]:
        """Extract exposed port from Docker ports string."""
        if '->' in ports_str:
            parts = ports_str.split('->')
            if len(parts) > 0:
                host_part = parts[0]
                if ':' in host_part:
                    try:
                        return int(host_part.split(':')[-1])
                    except ValueError:
                        pass
        return None

    def _parse_dpkg_version(self, dpkg_output: str) -> Optional[str]:
        """Parse version from dpkg output."""
        for line in dpkg_output.split('\n'):
            if 'ii' in line:
                parts = line.split()
                if len(parts) >= 3:
                    return parts[2]
        return None

    def audit_all(self) -> List[ServiceInfo]:
        """Run complete audit."""
        self.log("Starting monitoring stack audit...")

        self.detect_grafana()
        self.detect_prometheus()
        self.detect_graphite()
        self.detect_mysql()
        self.detect_legacy_monitoring()
        self.detect_other_services()

        return self.services

    def generate_report(self, format_type: str = "text") -> str:
        """Generate audit report."""
        if format_type == "json":
            return json.dumps([s.to_dict() for s in self.services], indent=2)

        # Text report
        lines = []
        lines.append("=" * 70)
        lines.append("MONITORING STACK AUDIT REPORT".center(70))
        lines.append("=" * 70)
        lines.append("")

        if not self.services:
            lines.append("No monitoring services detected.")
            return "\n".join(lines)

        # Group by type
        by_type = {}
        for service in self.services:
            if service.type not in by_type:
                by_type[service.type] = []
            by_type[service.type].append(service)

        # Summary
        lines.append(f"Total services found: {len(self.services)}")
        lines.append("")
        lines.append("Service Types:")
        for service_type, services in sorted(by_type.items()):
            lines.append(f"  - {service_type.upper()}: {len(services)}")
        lines.append("")

        # Detailed info
        for service_type, services in sorted(by_type.items()):
            lines.append("-" * 70)
            lines.append(f"{service_type.upper()}")
            lines.append("-" * 70)
            lines.append("")

            for service in services:
                lines.append(f"  {service.name}")
                lines.append(f"    Installed: {'Yes' if service.installed else 'No'}")
                if service.running is not None:
                    lines.append(f"    Running: {'Yes' if service.running else 'No'}")
                if service.version:
                    lines.append(f"    Version: {service.version}")
                if service.install_method:
                    lines.append(f"    Method: {service.install_method}")
                if service.path:
                    lines.append(f"    Path: {service.path}")
                if service.config_path:
                    lines.append(f"    Config: {service.config_path}")
                if service.data_path:
                    lines.append(f"    Data: {service.data_path}")
                if service.port:
                    lines.append(f"    Port: {service.port}")
                if service.url:
                    lines.append(f"    URL: {service.url}")
                if service.container_id:
                    lines.append(f"    Container: {service.container_id}")
                if service.process_id:
                    lines.append(f"    PID: {service.process_id}")
                if service.user:
                    lines.append(f"    User: {service.user}")

                if service.details:
                    for key, value in service.details.items():
                        if not isinstance(value, dict):
                            lines.append(f"    {key.title()}: {value}")

                lines.append("")

        lines.append("=" * 70)

        return "\n".join(lines)


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Audit monitoring stack - detect Grafana, Prometheus, Graphite, MySQL, etc."
    )
    parser.add_argument(
        "-f", "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output"
    )
    parser.add_argument(
        "-o", "--output",
        help="Write report to file"
    )

    args = parser.parse_args()

    auditor = MonitoringStackAuditor(verbose=args.verbose)
    services = auditor.audit_all()

    report = auditor.generate_report(args.format)

    if args.output:
        with open(args.output, 'w') as f:
            f.write(report)
        print(f"Report written to: {args.output}")
    else:
        print(report)

    # Exit code: 0 if services found, 1 if none found
    sys.exit(0 if services else 1)


if __name__ == "__main__":
    main()
