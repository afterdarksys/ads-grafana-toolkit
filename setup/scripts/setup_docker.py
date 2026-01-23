#!/usr/bin/env python3
"""
Docker Setup Script for Grafana
Handles Docker installation when packages are unavailable.
"""

import os
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional, Tuple


class DockerSetup:
    """Handles Docker installation and configuration."""

    def __init__(self, verbose: bool = False, auto_yes: bool = False):
        self.verbose = verbose
        self.auto_yes = auto_yes
        self.system = platform.system().lower()
        self.distro = self._detect_linux_distro()

    def log(self, message: str, level: str = "INFO"):
        """Print log message."""
        if self.verbose or level in ("WARN", "ERROR"):
            prefix = f"[{level}]"
            print(f"{prefix} {message}", file=sys.stderr if level == "ERROR" else sys.stdout)

    def _detect_linux_distro(self) -> Optional[str]:
        """Detect Linux distribution."""
        if self.system != "linux":
            return None

        # Try /etc/os-release first
        os_release_path = Path("/etc/os-release")
        if os_release_path.exists():
            with open(os_release_path) as f:
                for line in f:
                    if line.startswith("ID="):
                        distro = line.split("=")[1].strip().strip('"')
                        return distro.lower()

        # Fallback checks
        if Path("/etc/debian_version").exists():
            return "debian"
        elif Path("/etc/redhat-release").exists():
            return "rhel"
        elif Path("/etc/arch-release").exists():
            return "arch"

        return None

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

    def is_docker_installed(self) -> bool:
        """Check if Docker is already installed."""
        return shutil.which("docker") is not None

    def is_docker_running(self) -> bool:
        """Check if Docker daemon is running."""
        try:
            result = subprocess.run(
                ["docker", "info"],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, subprocess.SubprocessError):
            return False

    def check_docker_compose(self) -> Tuple[bool, Optional[str]]:
        """Check for docker-compose or docker compose plugin."""
        # Check for docker compose plugin (v2)
        try:
            result = subprocess.run(
                ["docker", "compose", "version"],
                capture_output=True,
                timeout=5
            )
            if result.returncode == 0:
                return True, "plugin"
        except (subprocess.TimeoutExpired, subprocess.SubprocessError):
            pass

        # Check for standalone docker-compose (v1)
        if shutil.which("docker-compose"):
            return True, "standalone"

        return False, None

    def install_docker(self) -> bool:
        """Install Docker based on the operating system."""
        self.log("Starting Docker installation...")

        if self.system == "linux":
            return self._install_docker_linux()
        elif self.system == "darwin":
            return self._install_docker_macos()
        else:
            self.log(f"Unsupported operating system: {self.system}", "ERROR")
            return False

    def _install_docker_linux(self) -> bool:
        """Install Docker on Linux."""
        if self.distro in ("ubuntu", "debian"):
            return self._install_docker_debian()
        elif self.distro in ("centos", "rhel", "fedora"):
            return self._install_docker_rhel()
        elif self.distro == "arch":
            return self._install_docker_arch()
        else:
            self.log(f"Unsupported Linux distribution: {self.distro}", "ERROR")
            self.log("Please install Docker manually: https://docs.docker.com/engine/install/")
            return False

    def _install_docker_debian(self) -> bool:
        """Install Docker on Debian/Ubuntu using official repository."""
        self.log("Installing Docker for Debian/Ubuntu...")

        commands = [
            # Remove old versions
            ["sudo", "apt-get", "remove", "-y", "docker", "docker-engine", "docker.io", "containerd", "runc"],

            # Update and install prerequisites
            ["sudo", "apt-get", "update"],
            ["sudo", "apt-get", "install", "-y", "ca-certificates", "curl", "gnupg", "lsb-release"],

            # Add Docker's official GPG key
            ["sudo", "install", "-m", "0755", "-d", "/etc/apt/keyrings"],
        ]

        for cmd in commands:
            if not self._run_command(cmd):
                return False

        # Download GPG key
        try:
            result = subprocess.run(
                ["curl", "-fsSL", "https://download.docker.com/linux/ubuntu/gpg"],
                capture_output=True,
                timeout=30
            )
            if result.returncode == 0:
                with tempfile.NamedTemporaryFile(mode='wb', delete=False) as f:
                    f.write(result.stdout)
                    gpg_file = f.name

                subprocess.run(
                    ["sudo", "gpg", "--dearmor", "-o", "/etc/apt/keyrings/docker.gpg"],
                    stdin=open(gpg_file, 'rb'),
                    timeout=10
                )
                os.unlink(gpg_file)
        except Exception as e:
            self.log(f"Failed to download GPG key: {e}", "ERROR")
            return False

        # Set up repository
        arch = subprocess.run(["dpkg", "--print-architecture"], capture_output=True, text=True).stdout.strip()
        distro = subprocess.run(["lsb_release", "-cs"], capture_output=True, text=True).stdout.strip()

        repo_line = f"deb [arch={arch} signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu {distro} stable"

        if not self._run_command(["sudo", "sh", "-c", f"echo '{repo_line}' > /etc/apt/sources.list.d/docker.list"]):
            return False

        # Install Docker Engine
        install_commands = [
            ["sudo", "apt-get", "update"],
            ["sudo", "apt-get", "install", "-y", "docker-ce", "docker-ce-cli", "containerd.io", "docker-buildx-plugin", "docker-compose-plugin"],
        ]

        for cmd in install_commands:
            if not self._run_command(cmd):
                return False

        return self._post_install_linux()

    def _install_docker_rhel(self) -> bool:
        """Install Docker on RHEL/CentOS/Fedora."""
        self.log("Installing Docker for RHEL/CentOS/Fedora...")

        commands = [
            # Remove old versions
            ["sudo", "yum", "remove", "-y", "docker", "docker-client", "docker-client-latest", "docker-common",
             "docker-latest", "docker-latest-logrotate", "docker-logrotate", "docker-engine"],

            # Install yum-utils
            ["sudo", "yum", "install", "-y", "yum-utils"],

            # Add Docker repository
            ["sudo", "yum-config-manager", "--add-repo", "https://download.docker.com/linux/centos/docker-ce.repo"],

            # Install Docker
            ["sudo", "yum", "install", "-y", "docker-ce", "docker-ce-cli", "containerd.io", "docker-buildx-plugin", "docker-compose-plugin"],
        ]

        for cmd in commands:
            if not self._run_command(cmd):
                return False

        return self._post_install_linux()

    def _install_docker_arch(self) -> bool:
        """Install Docker on Arch Linux."""
        self.log("Installing Docker for Arch Linux...")

        commands = [
            ["sudo", "pacman", "-Sy", "--noconfirm"],
            ["sudo", "pacman", "-S", "--noconfirm", "docker", "docker-compose"],
        ]

        for cmd in commands:
            if not self._run_command(cmd):
                return False

        return self._post_install_linux()

    def _post_install_linux(self) -> bool:
        """Post-installation steps for Linux."""
        self.log("Running post-installation steps...")

        # Start Docker service
        if not self._run_command(["sudo", "systemctl", "start", "docker"]):
            self.log("Failed to start Docker service", "WARN")

        # Enable Docker service
        if not self._run_command(["sudo", "systemctl", "enable", "docker"]):
            self.log("Failed to enable Docker service", "WARN")

        # Add current user to docker group
        import getpass
        username = getpass.getuser()

        if self.confirm(f"Add user '{username}' to docker group? (allows running docker without sudo)"):
            if self._run_command(["sudo", "usermod", "-aG", "docker", username]):
                self.log("User added to docker group. You may need to log out and back in for changes to take effect.", "INFO")
            else:
                self.log("Failed to add user to docker group", "WARN")

        return True

    def _install_docker_macos(self) -> bool:
        """Install Docker Desktop on macOS."""
        self.log("Installing Docker Desktop for macOS...")

        if not shutil.which("brew"):
            self.log("Homebrew is required to install Docker Desktop on macOS", "ERROR")
            self.log("Install Homebrew from https://brew.sh/ and try again")
            return False

        commands = [
            ["brew", "install", "--cask", "docker"],
        ]

        for cmd in commands:
            if not self._run_command(cmd):
                return False

        self.log("Docker Desktop installed. Please start it from Applications.", "INFO")
        return True

    def _run_command(self, cmd: list, check: bool = True) -> bool:
        """Run a shell command."""
        self.log(f"Running: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd,
                check=check,
                capture_output=not self.verbose,
                text=True,
                timeout=300
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

    def setup(self) -> bool:
        """Main setup method."""
        # Check if Docker is already installed
        if self.is_docker_installed():
            self.log("Docker is already installed.")

            if not self.is_docker_running():
                self.log("Docker is installed but not running.", "WARN")
                if self.confirm("Would you like to start Docker?"):
                    if self.system == "linux":
                        self._run_command(["sudo", "systemctl", "start", "docker"])
                    else:
                        self.log("Please start Docker Desktop manually.")

            # Check for docker-compose
            has_compose, compose_type = self.check_docker_compose()
            if has_compose:
                self.log(f"Docker Compose is available ({compose_type})")
            else:
                self.log("Docker Compose is not available", "WARN")
                if self.system == "linux" and self.confirm("Would you like to install Docker Compose plugin?"):
                    self._run_command(["sudo", "apt-get", "install", "-y", "docker-compose-plugin"])

            return True

        # Docker not installed
        self.log("Docker is not installed on this system.")

        if not self.confirm("Would you like to install Docker now?"):
            self.log("Docker installation cancelled.")
            return False

        return self.install_docker()


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Setup Docker for Grafana deployment"
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
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Only check if Docker is installed"
    )

    args = parser.parse_args()

    setup = DockerSetup(verbose=args.verbose, auto_yes=args.yes)

    if args.check_only:
        if setup.is_docker_installed():
            print("Docker is installed")
            if setup.is_docker_running():
                print("Docker is running")
            else:
                print("Docker is not running")
            sys.exit(0)
        else:
            print("Docker is not installed")
            sys.exit(1)

    success = setup.setup()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
