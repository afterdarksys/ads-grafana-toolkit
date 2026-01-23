#!/usr/bin/env python3
"""
Grafonnet/Jsonnet Support
Auto-installs Jsonnet and provides conversion utilities.
"""

import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path
from typing import Optional, Dict, Any


class JsonnetSupport:
    """Handles Jsonnet/Grafonnet integration."""

    JSONNET_VERSION = "0.20.0"
    GRAFONNET_VERSION = "main"

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.system = platform.system().lower()
        self.jsonnet_bin = None
        self.grafonnet_path = None

    def log(self, message: str, level: str = "INFO"):
        """Log message."""
        if self.verbose or level in ("ERROR", "WARN"):
            print(f"[{level}] {message}", file=sys.stderr if level == "ERROR" else sys.stdout)

    def check_jsonnet(self) -> bool:
        """Check if jsonnet is available."""
        # Check for go-jsonnet
        if shutil.which("jsonnet"):
            self.jsonnet_bin = "jsonnet"
            self.log("Found jsonnet binary")
            return True

        # Check for _jsonnet Python module
        try:
            import _jsonnet
            self.jsonnet_bin = "python"
            self.log("Found Python jsonnet module")
            return True
        except ImportError:
            pass

        return False

    def install_jsonnet(self) -> bool:
        """Install jsonnet automatically."""
        self.log("Installing jsonnet...")

        # Try pip install first (easiest)
        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "jsonnet"],
                check=True,
                capture_output=not self.verbose,
                timeout=300
            )
            self.log("Installed jsonnet via pip")
            self.jsonnet_bin = "python"
            return True
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            self.log("pip install failed, trying binary installation", "WARN")

        # Try binary installation
        if self.system == "linux":
            return self._install_jsonnet_linux()
        elif self.system == "darwin":
            return self._install_jsonnet_macos()
        else:
            self.log(f"Unsupported platform: {self.system}", "ERROR")
            return False

    def _install_jsonnet_linux(self) -> bool:
        """Install jsonnet on Linux."""
        arch = platform.machine()
        if arch == "x86_64":
            arch = "amd64"
        elif arch == "aarch64":
            arch = "arm64"

        url = f"https://github.com/google/go-jsonnet/releases/download/v{self.JSONNET_VERSION}/go-jsonnet_{self.JSONNET_VERSION}_linux_{arch}.tar.gz"

        try:
            self.log(f"Downloading from {url}")
            with tempfile.TemporaryDirectory() as tmpdir:
                archive_path = Path(tmpdir) / "jsonnet.tar.gz"
                urllib.request.urlretrieve(url, archive_path)

                # Extract
                subprocess.run(
                    ["tar", "xzf", str(archive_path), "-C", tmpdir],
                    check=True,
                    timeout=30
                )

                # Install to user bin
                user_bin = Path.home() / ".local" / "bin"
                user_bin.mkdir(parents=True, exist_ok=True)

                shutil.copy(Path(tmpdir) / "jsonnet", user_bin / "jsonnet")
                os.chmod(user_bin / "jsonnet", 0o755)

                self.jsonnet_bin = str(user_bin / "jsonnet")
                self.log(f"Installed jsonnet to {self.jsonnet_bin}")
                return True
        except Exception as e:
            self.log(f"Binary installation failed: {e}", "ERROR")
            return False

    def _install_jsonnet_macos(self) -> bool:
        """Install jsonnet on macOS."""
        if shutil.which("brew"):
            try:
                subprocess.run(
                    ["brew", "install", "jsonnet"],
                    check=True,
                    capture_output=not self.verbose,
                    timeout=300
                )
                self.jsonnet_bin = "jsonnet"
                return True
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
                pass

        # Fallback to binary
        url = f"https://github.com/google/go-jsonnet/releases/download/v{self.JSONNET_VERSION}/go-jsonnet_{self.JSONNET_VERSION}_darwin_amd64.tar.gz"

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                archive_path = Path(tmpdir) / "jsonnet.tar.gz"
                urllib.request.urlretrieve(url, archive_path)

                subprocess.run(
                    ["tar", "xzf", str(archive_path), "-C", tmpdir],
                    check=True,
                    timeout=30
                )

                user_bin = Path.home() / ".local" / "bin"
                user_bin.mkdir(parents=True, exist_ok=True)

                shutil.copy(Path(tmpdir) / "jsonnet", user_bin / "jsonnet")
                os.chmod(user_bin / "jsonnet", 0o755)

                self.jsonnet_bin = str(user_bin / "jsonnet")
                return True
        except Exception as e:
            self.log(f"Installation failed: {e}", "ERROR")
            return False

    def setup_grafonnet(self) -> bool:
        """Download and setup Grafonnet library."""
        self.log("Setting up Grafonnet library...")

        grafonnet_dir = Path.home() / ".grafonnet"
        grafonnet_dir.mkdir(exist_ok=True)

        lib_dir = grafonnet_dir / "grafonnet-lib"

        if lib_dir.exists():
            self.log("Grafonnet library already exists")
            self.grafonnet_path = str(lib_dir)
            return True

        # Clone grafonnet
        try:
            subprocess.run(
                ["git", "clone", "https://github.com/grafana/grafonnet-lib.git", str(lib_dir)],
                check=True,
                capture_output=not self.verbose,
                timeout=120
            )
            self.grafonnet_path = str(lib_dir)
            self.log(f"Grafonnet installed to {self.grafonnet_path}")
            return True
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            self.log(f"Failed to clone grafonnet: {e}", "ERROR")
            return False

    def convert_jsonnet(self, input_file: str, output_file: Optional[str] = None) -> bool:
        """Convert Jsonnet file to JSON."""
        input_path = Path(input_file)

        if not input_path.exists():
            self.log(f"Input file not found: {input_file}", "ERROR")
            return False

        if output_file is None:
            output_file = input_path.with_suffix(".json")

        self.log(f"Converting {input_file} -> {output_file}")

        try:
            if self.jsonnet_bin == "python":
                # Use Python module
                import _jsonnet
                with open(input_path) as f:
                    jsonnet_code = f.read()

                jpaths = [str(Path(input_file).parent)]
                if self.grafonnet_path:
                    jpaths.append(self.grafonnet_path)

                result = _jsonnet.evaluate_file(
                    str(input_path),
                    jpathdir=jpaths
                )

                with open(output_file, 'w') as f:
                    # Parse and re-format to ensure valid JSON
                    data = json.loads(result)
                    json.dump(data, f, indent=2)

            else:
                # Use binary
                cmd = [self.jsonnet_bin]

                # Add library paths
                if self.grafonnet_path:
                    cmd.extend(["-J", self.grafonnet_path])
                cmd.extend(["-J", str(Path(input_file).parent)])

                cmd.extend(["-o", output_file, input_file])

                subprocess.run(
                    cmd,
                    check=True,
                    capture_output=not self.verbose,
                    timeout=60
                )

            self.log(f"Conversion successful: {output_file}", "INFO")
            return True

        except Exception as e:
            self.log(f"Conversion failed: {e}", "ERROR")
            return False

    def create_example(self, output_file: str = "example_dashboard.jsonnet"):
        """Create example Grafonnet dashboard."""
        example = '''// Example Grafonnet Dashboard
local grafana = import 'grafonnet/grafana.libsonnet';
local dashboard = grafana.dashboard;
local row = grafana.row;
local prometheus = grafana.prometheus;
local template = grafana.template;
local graphPanel = grafana.graphPanel;

dashboard.new(
  'Example Dashboard',
  tags=['example', 'auto-generated'],
  editable=true,
  time_from='now-6h',
  refresh='30s',
)
.addTemplate(
  template.datasource(
    'datasource',
    'prometheus',
    'Prometheus',
    hide='',
  )
)
.addRow(
  row.new(title='System Metrics')
  .addPanel(
    graphPanel.new(
      'CPU Usage',
      datasource='$datasource',
      format='percent',
    )
    .addTarget(
      prometheus.target(
        'avg(rate(node_cpu_seconds_total{mode!="idle"}[5m])) * 100',
        legendFormat='CPU Usage',
      )
    )
  )
  .addPanel(
    graphPanel.new(
      'Memory Usage',
      datasource='$datasource',
      format='bytes',
    )
    .addTarget(
      prometheus.target(
        'node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes',
        legendFormat='Used Memory',
      )
    )
  )
)
'''
        with open(output_file, 'w') as f:
            f.write(example)

        self.log(f"Created example: {output_file}")

    def setup(self) -> bool:
        """Complete setup of Jsonnet and Grafonnet."""
        # Check if already installed
        if self.check_jsonnet():
            self.log("Jsonnet is already available")
        else:
            if not self.install_jsonnet():
                self.log("Failed to install jsonnet", "ERROR")
                return False

        # Setup Grafonnet
        if not self.setup_grafonnet():
            self.log("Failed to setup Grafonnet", "WARN")
            self.log("You can still use jsonnet without Grafonnet library", "INFO")

        return True


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Jsonnet/Grafonnet support for Grafana dashboards"
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # Setup command
    setup_parser = subparsers.add_parser("setup", help="Install Jsonnet and Grafonnet")
    setup_parser.add_argument("-v", "--verbose", action="store_true")

    # Convert command
    convert_parser = subparsers.add_parser("convert", help="Convert Jsonnet to JSON")
    convert_parser.add_argument("input", help="Input .jsonnet file")
    convert_parser.add_argument("-o", "--output", help="Output .json file")
    convert_parser.add_argument("-v", "--verbose", action="store_true")

    # Example command
    example_parser = subparsers.add_parser("example", help="Create example Grafonnet dashboard")
    example_parser.add_argument("-o", "--output", default="example_dashboard.jsonnet")
    example_parser.add_argument("-v", "--verbose", action="store_true")

    args = parser.parse_args()

    support = JsonnetSupport(verbose=args.verbose)

    if args.command == "setup":
        success = support.setup()
        sys.exit(0 if success else 1)

    elif args.command == "convert":
        # Ensure setup first
        if not support.check_jsonnet():
            print("Jsonnet not found. Running setup...")
            if not support.setup():
                sys.exit(1)

        success = support.convert_jsonnet(args.input, args.output)
        sys.exit(0 if success else 1)

    elif args.command == "example":
        # Ensure setup first
        if not support.check_jsonnet():
            if not support.setup():
                sys.exit(1)

        support.create_example(args.output)
        print(f"Example created: {args.output}")
        print(f"Convert with: python3 {sys.argv[0]} convert {args.output}")


if __name__ == "__main__":
    main()
