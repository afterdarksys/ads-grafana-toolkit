#!/usr/bin/env python3
"""
Grafana Installation Script
Supports multiple installation methods: package, docker, binary, source.
"""

import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import tarfile
import urllib.request
from pathlib import Path
from typing import Optional, Dict, List


class GrafanaInstaller:
    """Handles Grafana installation across different methods and platforms."""

    GRAFANA_VERSION = "10.3.3"  # Default version
    GRAFANA_DOWNLOAD_BASE = "https://dl.grafana.com/oss/release"

    def __init__(self, verbose: bool = False, auto_yes: bool = False):
        self.verbose = verbose
        self.auto_yes = auto_yes
        self.system = platform.system().lower()
        self.distro = self._detect_linux_distro()
        self.arch = self._detect_architecture()

    def log(self, message: str, level: str = "INFO"):
        """Print log message."""
        if self.verbose or level in ("WARN", "ERROR"):
            prefix = f"[{level}]"
            print(f"{prefix} {message}", file=sys.stderr if level == "ERROR" else sys.stdout)

    def _detect_linux_distro(self) -> Optional[str]:
        """Detect Linux distribution."""
        if self.system != "linux":
            return None

        os_release_path = Path("/etc/os-release")
        if os_release_path.exists():
            with open(os_release_path) as f:
                for line in f:
                    if line.startswith("ID="):
                        return line.split("=")[1].strip().strip('"').lower()

        if Path("/etc/debian_version").exists():
            return "debian"
        elif Path("/etc/redhat-release").exists():
            return "rhel"

        return None

    def _detect_architecture(self) -> str:
        """Detect system architecture."""
        machine = platform.machine().lower()
        if machine in ("x86_64", "amd64"):
            return "amd64"
        elif machine in ("aarch64", "arm64"):
            return "arm64"
        elif machine.startswith("arm"):
            return "armv7"
        else:
            return machine

    def confirm(self, message: str) -> bool:
        """Ask user for confirmation."""
        if self.auto_yes:
            return True

        while True:
            response = input(f"{message} [y/N]: ").strip().lower()
            if response in ("y", "yes"):
                return True
            elif response in ("n", "no", ""):
                return False

    def _run_command(self, cmd: List[str], check: bool = True, timeout: int = 300) -> bool:
        """Run a shell command."""
        self.log(f"Running: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd,
                check=check,
                capture_output=not self.verbose,
                text=True,
                timeout=timeout
            )
            return result.returncode == 0
        except subprocess.CalledProcessError as e:
            self.log(f"Command failed: {e}", "ERROR")
            return False
        except subprocess.TimeoutExpired:
            self.log("Command timed out", "ERROR")
            return False
        except Exception as e:
            self.log(f"Error running command: {e}", "ERROR")
            return False

    def install_package(self, version: Optional[str] = None) -> bool:
        """Install Grafana using package manager."""
        self.log("Installing Grafana via package manager...")

        if self.system == "linux":
            if self.distro in ("ubuntu", "debian"):
                return self._install_package_debian(version)
            elif self.distro in ("centos", "rhel", "fedora"):
                return self._install_package_rhel(version)
            else:
                self.log(f"Package installation not supported for {self.distro}", "ERROR")
                return False
        elif self.system == "darwin":
            return self._install_package_macos(version)
        else:
            self.log(f"Package installation not supported for {self.system}", "ERROR")
            return False

    def _install_package_debian(self, version: Optional[str] = None) -> bool:
        """Install Grafana on Debian/Ubuntu."""
        self.log("Installing Grafana for Debian/Ubuntu...")

        commands = [
            ["sudo", "apt-get", "install", "-y", "apt-transport-https", "software-properties-common", "wget"],
            ["sudo", "mkdir", "-p", "/etc/apt/keyrings/"],
        ]

        for cmd in commands:
            if not self._run_command(cmd):
                return False

        # Download and add GPG key
        try:
            self.log("Downloading Grafana GPG key...")
            result = subprocess.run(
                ["wget", "-q", "-O", "-", "https://apt.grafana.com/gpg.key"],
                capture_output=True,
                timeout=30
            )
            if result.returncode == 0:
                subprocess.run(
                    ["sudo", "gpg", "--dearmor", "-o", "/etc/apt/keyrings/grafana.gpg"],
                    input=result.stdout,
                    timeout=10
                )
        except Exception as e:
            self.log(f"Failed to download GPG key: {e}", "ERROR")
            return False

        # Add repository
        repo_line = "deb [signed-by=/etc/apt/keyrings/grafana.gpg] https://apt.grafana.com stable main"
        if not self._run_command(["sudo", "sh", "-c", f"echo '{repo_line}' > /etc/apt/sources.list.d/grafana.list"]):
            return False

        # Install Grafana
        install_commands = [
            ["sudo", "apt-get", "update"],
            ["sudo", "apt-get", "install", "-y", "grafana"],
        ]

        for cmd in install_commands:
            if not self._run_command(cmd):
                return False

        return self._post_install_package()

    def _install_package_rhel(self, version: Optional[str] = None) -> bool:
        """Install Grafana on RHEL/CentOS/Fedora."""
        self.log("Installing Grafana for RHEL/CentOS/Fedora...")

        # Create repo file
        repo_content = """[grafana]
name=grafana
baseurl=https://rpm.grafana.com
repo_gpgcheck=1
enabled=1
gpgcheck=1
gpgkey=https://rpm.grafana.com/gpg.key
sslverify=1
sslcacert=/etc/pki/tls/certs/ca-bundle.crt
"""

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.repo') as f:
            f.write(repo_content)
            repo_file = f.name

        if not self._run_command(["sudo", "mv", repo_file, "/etc/yum.repos.d/grafana.repo"]):
            return False

        # Install Grafana
        if not self._run_command(["sudo", "yum", "install", "-y", "grafana"]):
            return False

        return self._post_install_package()

    def _install_package_macos(self, version: Optional[str] = None) -> bool:
        """Install Grafana on macOS using Homebrew."""
        self.log("Installing Grafana for macOS...")

        if not shutil.which("brew"):
            self.log("Homebrew is required for macOS installation", "ERROR")
            self.log("Install from https://brew.sh/")
            return False

        commands = [
            ["brew", "update"],
            ["brew", "install", "grafana"],
        ]

        for cmd in commands:
            if not self._run_command(cmd):
                return False

        self.log("Grafana installed via Homebrew", "INFO")
        self.log("Start with: brew services start grafana", "INFO")
        return True

    def _post_install_package(self) -> bool:
        """Post-installation steps for package installation."""
        self.log("Running post-installation steps...")

        if self.system == "linux":
            # Reload systemd
            self._run_command(["sudo", "systemctl", "daemon-reload"])

            if self.confirm("Would you like to start Grafana now?"):
                if not self._run_command(["sudo", "systemctl", "start", "grafana-server"]):
                    self.log("Failed to start Grafana", "WARN")
                    return False

            if self.confirm("Would you like to enable Grafana to start on boot?"):
                self._run_command(["sudo", "systemctl", "enable", "grafana-server"])

            self.log("Grafana is now running on http://localhost:3000", "INFO")
            self.log("Default credentials: admin / admin", "INFO")

        return True

    def install_docker(self, version: Optional[str] = None, port: int = 3000) -> bool:
        """Install Grafana using Docker."""
        self.log("Installing Grafana via Docker...")

        if not shutil.which("docker"):
            self.log("Docker is not installed", "ERROR")
            self.log("Run setup_docker.py first")
            return False

        version = version or self.GRAFANA_VERSION
        image = f"grafana/grafana:{version}"

        self.log(f"Pulling Grafana image: {image}")
        if not self._run_command(["docker", "pull", image]):
            return False

        # Create volume for persistent data
        volume_name = "grafana-data"
        self._run_command(["docker", "volume", "create", volume_name], check=False)

        # Run container
        container_name = "grafana"

        # Stop and remove existing container if present
        self._run_command(["docker", "stop", container_name], check=False)
        self._run_command(["docker", "rm", container_name], check=False)

        self.log(f"Starting Grafana container on port {port}...")
        cmd = [
            "docker", "run", "-d",
            "--name", container_name,
            "-p", f"{port}:3000",
            "-v", f"{volume_name}:/var/lib/grafana",
            "--restart", "unless-stopped",
            image
        ]

        if not self._run_command(cmd):
            return False

        self.log(f"Grafana is now running on http://localhost:{port}", "INFO")
        self.log("Default credentials: admin / admin", "INFO")
        return True

    def install_binary(self, version: Optional[str] = None, install_path: str = "/opt/grafana") -> bool:
        """Install Grafana from binary tarball."""
        self.log("Installing Grafana from binary...")

        version = version or self.GRAFANA_VERSION
        install_path = Path(install_path)

        # Determine download URL
        if self.system == "linux":
            filename = f"grafana-{version}.linux-{self.arch}.tar.gz"
        elif self.system == "darwin":
            filename = f"grafana-{version}.darwin-{self.arch}.tar.gz"
        else:
            self.log(f"Binary installation not supported for {self.system}", "ERROR")
            return False

        url = f"{self.GRAFANA_DOWNLOAD_BASE}/{filename}"

        # Download
        self.log(f"Downloading from {url}...")
        with tempfile.TemporaryDirectory() as tmpdir:
            archive_path = Path(tmpdir) / filename

            try:
                urllib.request.urlretrieve(url, archive_path)
            except Exception as e:
                self.log(f"Failed to download: {e}", "ERROR")
                return False

            # Extract
            self.log(f"Extracting to {install_path}...")
            try:
                with tarfile.open(archive_path) as tar:
                    tar.extractall(tmpdir)

                # Move to install path
                extracted_dir = Path(tmpdir) / f"grafana-{version}"

                # Create install directory
                if self._run_command(["sudo", "mkdir", "-p", str(install_path.parent)]):
                    self._run_command(["sudo", "mv", str(extracted_dir), str(install_path)])
                else:
                    self.log("Failed to create install directory", "ERROR")
                    return False

            except Exception as e:
                self.log(f"Failed to extract: {e}", "ERROR")
                return False

        # Create symlink
        bin_link = Path("/usr/local/bin/grafana-server")
        if self.confirm(f"Create symlink at {bin_link}?"):
            self._run_command(["sudo", "ln", "-sf", str(install_path / "bin" / "grafana-server"), str(bin_link)])

        self.log(f"Grafana installed to {install_path}", "INFO")
        self.log(f"Start with: {install_path}/bin/grafana-server", "INFO")
        return True

    def install_source(self, install_path: str = "/opt/grafana", branch: str = "main") -> bool:
        """Install Grafana from source (git clone)."""
        self.log("Installing Grafana from source...")

        if not shutil.which("git"):
            self.log("Git is required for source installation", "ERROR")
            return False

        install_path = Path(install_path)

        # Check for Go
        if not shutil.which("go"):
            self.log("Go is required to build Grafana from source", "ERROR")
            self.log("Install Go from https://golang.org/dl/")
            return False

        # Check for Node.js/npm
        if not shutil.which("npm"):
            self.log("Node.js/npm is required to build Grafana from source", "ERROR")
            return False

        # Clone repository
        self.log("Cloning Grafana repository...")
        if install_path.exists():
            if not self.confirm(f"Directory {install_path} exists. Remove it?"):
                return False
            self._run_command(["sudo", "rm", "-rf", str(install_path)])

        if not self._run_command([
            "sudo", "git", "clone",
            "-b", branch,
            "--depth", "1",
            "https://github.com/grafana/grafana.git",
            str(install_path)
        ], timeout=600):
            return False

        # Build
        self.log("Building Grafana (this may take several minutes)...")

        build_commands = [
            ["sudo", "chown", "-R", f"{os.getuid()}:{os.getgid()}", str(install_path)],
        ]

        for cmd in build_commands:
            if not self._run_command(cmd):
                return False

        # Build backend
        self.log("Building backend...")
        os.chdir(install_path)
        if not self._run_command(["go", "run", "build.go", "build"], timeout=1200):
            return False

        # Build frontend
        self.log("Building frontend...")
        if not self._run_command(["npm", "install"], timeout=600):
            return False
        if not self._run_command(["npm", "run", "build"], timeout=1200):
            return False

        self.log(f"Grafana built successfully at {install_path}", "INFO")
        self.log(f"Start with: {install_path}/bin/grafana-server", "INFO")
        return True


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Install Grafana using various methods"
    )
    parser.add_argument(
        "method",
        choices=["package", "docker", "binary", "source"],
        help="Installation method"
    )
    parser.add_argument(
        "--version",
        help="Grafana version (default: latest stable)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=3000,
        help="Port for Docker installation (default: 3000)"
    )
    parser.add_argument(
        "--path",
        default="/opt/grafana",
        help="Installation path for binary/source (default: /opt/grafana)"
    )
    parser.add_argument(
        "--branch",
        default="main",
        help="Git branch for source installation (default: main)"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output"
    )
    parser.add_argument(
        "-y", "--yes",
        action="store_true",
        help="Automatic yes to prompts"
    )

    args = parser.parse_args()

    installer = GrafanaInstaller(verbose=args.verbose, auto_yes=args.yes)

    if args.method == "package":
        success = installer.install_package(version=args.version)
    elif args.method == "docker":
        success = installer.install_docker(version=args.version, port=args.port)
    elif args.method == "binary":
        success = installer.install_binary(version=args.version, install_path=args.path)
    elif args.method == "source":
        success = installer.install_source(install_path=args.path, branch=args.branch)
    else:
        print(f"Unknown method: {args.method}", file=sys.stderr)
        sys.exit(1)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
