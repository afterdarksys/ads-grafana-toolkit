#!/usr/bin/env python3
"""
Grafana Detection Script
Detects existing Grafana installations on the system.
"""

import json
import os
import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Optional, Dict


@dataclass
class GrafanaInstallation:
    """Represents a detected Grafana installation."""
    type: str  # binary, docker, package, source
    path: Optional[str] = None
    version: Optional[str] = None
    config_path: Optional[str] = None
    data_path: Optional[str] = None
    running: bool = False
    port: Optional[int] = None
    url: Optional[str] = None
    container_id: Optional[str] = None

    def to_dict(self):
        return asdict(self)


class GrafanaDetector:
    """Detects Grafana installations across different deployment types."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.installations: List[GrafanaInstallation] = []
        self.system = platform.system().lower()

    def log(self, message: str):
        """Print verbose logging."""
        if self.verbose:
            print(f"[DEBUG] {message}", file=sys.stderr)

    def detect_all(self) -> List[GrafanaInstallation]:
        """Run all detection methods."""
        self.log("Starting Grafana detection...")

        self.detect_docker()
        self.detect_package()
        self.detect_binary()
        self.detect_systemd()
        self.detect_source()

        return self.installations

    def detect_docker(self):
        """Detect Grafana running in Docker containers."""
        self.log("Checking for Docker installations...")

        if not shutil.which("docker"):
            self.log("Docker not found")
            return

        try:
            # Check for running containers
            result = subprocess.run(
                ["docker", "ps", "--filter", "ancestor=grafana/grafana", "--format", "{{.ID}}\t{{.Names}}\t{{.Ports}}"],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0 and result.stdout.strip():
                for line in result.stdout.strip().split('\n'):
                    parts = line.split('\t')
                    if len(parts) >= 3:
                        container_id = parts[0]
                        container_name = parts[1]
                        ports = parts[2]

                        # Extract port
                        port = self._extract_port_from_docker(ports)

                        # Get version
                        version = self._get_docker_grafana_version(container_id)

                        installation = GrafanaInstallation(
                            type="docker",
                            container_id=container_id,
                            version=version,
                            running=True,
                            port=port,
                            url=f"http://localhost:{port}" if port else None,
                            path=f"docker:{container_name}"
                        )
                        self.installations.append(installation)
                        self.log(f"Found Docker Grafana: {container_name} (port {port})")

            # Check for stopped containers
            result = subprocess.run(
                ["docker", "ps", "-a", "--filter", "ancestor=grafana/grafana", "--filter", "status=exited", "--format", "{{.ID}}\t{{.Names}}"],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0 and result.stdout.strip():
                for line in result.stdout.strip().split('\n'):
                    parts = line.split('\t')
                    if len(parts) >= 2:
                        container_id = parts[0]
                        container_name = parts[1]
                        version = self._get_docker_grafana_version(container_id)

                        installation = GrafanaInstallation(
                            type="docker",
                            container_id=container_id,
                            version=version,
                            running=False,
                            path=f"docker:{container_name}"
                        )
                        self.installations.append(installation)
                        self.log(f"Found stopped Docker Grafana: {container_name}")

        except (subprocess.TimeoutExpired, subprocess.SubprocessError) as e:
            self.log(f"Error checking Docker: {e}")

    def _extract_port_from_docker(self, ports_str: str) -> Optional[int]:
        """Extract exposed port from Docker ports string."""
        # Format: 0.0.0.0:3000->3000/tcp
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

    def _get_docker_grafana_version(self, container_id: str) -> Optional[str]:
        """Get Grafana version from Docker container."""
        try:
            result = subprocess.run(
                ["docker", "exec", container_id, "grafana", "cli", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                # Parse version from output
                for line in result.stdout.split('\n'):
                    if 'version' in line.lower():
                        parts = line.split()
                        if len(parts) >= 2:
                            return parts[-1]
        except (subprocess.TimeoutExpired, subprocess.SubprocessError):
            pass
        return None

    def detect_package(self):
        """Detect Grafana installed via package manager."""
        self.log("Checking for package installations...")

        # Debian/Ubuntu
        if self.system == "linux":
            if shutil.which("dpkg"):
                try:
                    result = subprocess.run(
                        ["dpkg", "-l", "grafana"],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if result.returncode == 0 and "ii" in result.stdout:
                        version = self._parse_dpkg_version(result.stdout)
                        installation = GrafanaInstallation(
                            type="package",
                            path="/usr/share/grafana",
                            version=version,
                            config_path="/etc/grafana/grafana.ini",
                            data_path="/var/lib/grafana",
                            running=self._check_grafana_running()
                        )
                        self.installations.append(installation)
                        self.log(f"Found package Grafana: {version}")
                        return
                except (subprocess.TimeoutExpired, subprocess.SubprocessError):
                    pass

            # RedHat/CentOS/Fedora
            if shutil.which("rpm"):
                try:
                    result = subprocess.run(
                        ["rpm", "-qa", "grafana"],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if result.returncode == 0 and result.stdout.strip():
                        version = result.stdout.strip().split('-')[1] if '-' in result.stdout else None
                        installation = GrafanaInstallation(
                            type="package",
                            path="/usr/share/grafana",
                            version=version,
                            config_path="/etc/grafana/grafana.ini",
                            data_path="/var/lib/grafana",
                            running=self._check_grafana_running()
                        )
                        self.installations.append(installation)
                        self.log(f"Found package Grafana: {version}")
                        return
                except (subprocess.TimeoutExpired, subprocess.SubprocessError):
                    pass

        # macOS Homebrew
        elif self.system == "darwin":
            if shutil.which("brew"):
                try:
                    result = subprocess.run(
                        ["brew", "list", "--versions", "grafana"],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if result.returncode == 0 and result.stdout.strip():
                        parts = result.stdout.strip().split()
                        version = parts[1] if len(parts) > 1 else None

                        # Get brew prefix
                        prefix_result = subprocess.run(
                            ["brew", "--prefix", "grafana"],
                            capture_output=True,
                            text=True,
                            timeout=5
                        )
                        path = prefix_result.stdout.strip() if prefix_result.returncode == 0 else None

                        installation = GrafanaInstallation(
                            type="package",
                            path=path,
                            version=version,
                            running=self._check_grafana_running()
                        )
                        self.installations.append(installation)
                        self.log(f"Found Homebrew Grafana: {version}")
                        return
                except (subprocess.TimeoutExpired, subprocess.SubprocessError):
                    pass

    def _parse_dpkg_version(self, dpkg_output: str) -> Optional[str]:
        """Parse version from dpkg output."""
        for line in dpkg_output.split('\n'):
            if 'grafana' in line.lower():
                parts = line.split()
                if len(parts) >= 3:
                    return parts[2]
        return None

    def detect_binary(self):
        """Detect Grafana binary in PATH."""
        self.log("Checking for Grafana binary...")

        binary_path = shutil.which("grafana-server")
        if binary_path:
            version = self._get_binary_version(binary_path)
            installation = GrafanaInstallation(
                type="binary",
                path=binary_path,
                version=version,
                running=self._check_grafana_running()
            )
            self.installations.append(installation)
            self.log(f"Found Grafana binary: {binary_path}")

    def _get_binary_version(self, binary_path: str) -> Optional[str]:
        """Get version from Grafana binary."""
        try:
            result = subprocess.run(
                [binary_path, "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                # Parse version from output
                for line in result.stdout.split('\n'):
                    if 'version' in line.lower():
                        parts = line.split()
                        if len(parts) >= 2:
                            return parts[-1]
        except (subprocess.TimeoutExpired, subprocess.SubprocessError):
            pass
        return None

    def detect_systemd(self):
        """Detect Grafana running as systemd service."""
        self.log("Checking for systemd service...")

        if self.system != "linux" or not shutil.which("systemctl"):
            return

        try:
            result = subprocess.run(
                ["systemctl", "is-active", "grafana-server"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0 and "active" in result.stdout:
                # Service is active but we might have already detected it
                # Just update running status
                for installation in self.installations:
                    if installation.type in ("package", "binary"):
                        installation.running = True
                        self.log("Grafana systemd service is active")
        except (subprocess.TimeoutExpired, subprocess.SubprocessError):
            pass

    def detect_source(self):
        """Detect Grafana installed from source."""
        self.log("Checking for source installations...")

        common_paths = [
            "/opt/grafana",
            "/usr/local/grafana",
            str(Path.home() / "grafana"),
            "/srv/grafana"
        ]

        for path in common_paths:
            if Path(path).exists():
                # Check if it looks like Grafana
                if (Path(path) / "bin" / "grafana-server").exists():
                    version = self._get_binary_version(str(Path(path) / "bin" / "grafana-server"))
                    installation = GrafanaInstallation(
                        type="source",
                        path=path,
                        version=version,
                        running=self._check_grafana_running()
                    )
                    self.installations.append(installation)
                    self.log(f"Found source Grafana: {path}")

    def _check_grafana_running(self) -> bool:
        """Check if Grafana is running by checking common ports."""
        import socket

        ports = [3000, 3001, 3002]  # Common Grafana ports

        for port in ports:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('localhost', port))
            sock.close()
            if result == 0:
                return True

        return False

    def format_output(self, format_type: str = "text") -> str:
        """Format detection results."""
        if format_type == "json":
            return json.dumps(
                [inst.to_dict() for inst in self.installations],
                indent=2
            )

        elif format_type == "text":
            if not self.installations:
                return "No Grafana installations detected."

            output = []
            output.append(f"Found {len(self.installations)} Grafana installation(s):\n")

            for i, inst in enumerate(self.installations, 1):
                output.append(f"{i}. Type: {inst.type}")
                if inst.path:
                    output.append(f"   Path: {inst.path}")
                if inst.version:
                    output.append(f"   Version: {inst.version}")
                if inst.config_path:
                    output.append(f"   Config: {inst.config_path}")
                if inst.data_path:
                    output.append(f"   Data: {inst.data_path}")
                output.append(f"   Running: {'Yes' if inst.running else 'No'}")
                if inst.port:
                    output.append(f"   Port: {inst.port}")
                if inst.url:
                    output.append(f"   URL: {inst.url}")
                if inst.container_id:
                    output.append(f"   Container: {inst.container_id}")
                output.append("")

            return "\n".join(output)

        else:
            raise ValueError(f"Unknown format: {format_type}")


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Detect Grafana installations on the system"
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

    args = parser.parse_args()

    detector = GrafanaDetector(verbose=args.verbose)
    installations = detector.detect_all()

    print(detector.format_output(args.format))

    # Exit code: 0 if found, 1 if not found
    sys.exit(0 if installations else 1)


if __name__ == "__main__":
    main()
