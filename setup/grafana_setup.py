#!/usr/bin/env python3
"""
Grafana Setup Orchestration Script
Main entry point for Grafana installation and configuration.
Supports multiple modes: automated, step-by-step, play, run.
"""

import argparse
import json
import os
import subprocess
import sys
import time
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any
from enum import Enum


class Color:
    """ANSI color codes for terminal output."""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


class SetupMode(Enum):
    """Setup execution modes."""
    AUTOMATED = "automated"      # Run everything automatically
    STEP_BY_STEP = "step-by-step"  # Show each step, wait for confirmation
    PLAY = "play"                # Run with pauses, no confirmation needed
    RUN = "run"                  # Just execute, minimal output


class GrafanaSetup:
    """Orchestrates the complete Grafana setup process."""

    def __init__(self, mode: SetupMode, config_path: Optional[str] = None, verbose: bool = False):
        self.mode = mode
        self.verbose = verbose
        self.config = self._load_config(config_path)
        self.scripts_dir = Path(__file__).parent / "scripts"
        self.templates_dir = Path(__file__).parent / "templates"
        self.steps_completed = []
        self.steps_failed = []

    def _load_config(self, config_path: Optional[str] = None) -> Dict[str, Any]:
        """Load configuration file."""
        if config_path is None:
            config_path = Path(__file__).parent / "config" / "setup_config.yaml"
        else:
            config_path = Path(config_path)

        if not config_path.exists():
            self.log("Configuration file not found, using defaults", "WARN")
            return {}

        try:
            with open(config_path) as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            self.log(f"Failed to load config: {e}", "ERROR")
            return {}

    def log(self, message: str, level: str = "INFO"):
        """Print formatted log message."""
        if not self.verbose and level == "DEBUG":
            return

        colors = {
            "INFO": Color.BLUE,
            "SUCCESS": Color.GREEN,
            "WARN": Color.YELLOW,
            "ERROR": Color.RED,
            "STEP": Color.CYAN,
            "DEBUG": Color.END
        }

        color = colors.get(level, Color.END)
        timestamp = time.strftime("%H:%M:%S")

        if level in ("ERROR", "WARN"):
            output = sys.stderr
        else:
            output = sys.stdout

        print(f"{color}[{timestamp}] [{level}]{Color.END} {message}", file=output)

    def header(self, message: str):
        """Print section header."""
        print(f"\n{Color.BOLD}{Color.HEADER}{'=' * 70}{Color.END}")
        print(f"{Color.BOLD}{Color.HEADER}{message.center(70)}{Color.END}")
        print(f"{Color.BOLD}{Color.HEADER}{'=' * 70}{Color.END}\n")

    def confirm(self, message: str, default: bool = False) -> bool:
        """Ask user for confirmation."""
        if self.mode in (SetupMode.AUTOMATED, SetupMode.PLAY, SetupMode.RUN):
            return True

        suffix = "[Y/n]" if default else "[y/N]"
        while True:
            response = input(f"{Color.CYAN}{message} {suffix}:{Color.END} ").strip().lower()

            if not response:
                return default

            if response in ("y", "yes"):
                return True
            elif response in ("n", "no"):
                return False
            else:
                print("Please answer 'y' or 'n'")

    def pause(self, duration: Optional[float] = None):
        """Pause execution."""
        if self.mode == SetupMode.RUN:
            return

        if self.mode == SetupMode.STEP_BY_STEP:
            input(f"\n{Color.YELLOW}Press Enter to continue...{Color.END}")
        elif self.mode == SetupMode.PLAY:
            pause_time = duration or self.config.get("interactive", {}).get("pause_duration", 2)
            time.sleep(pause_time)

    def run_script(self, script_name: str, args: List[str] = None, capture: bool = False) -> tuple:
        """Run a setup script."""
        script_path = self.scripts_dir / script_name

        if not script_path.exists():
            self.log(f"Script not found: {script_path}", "ERROR")
            return False, None

        cmd = [sys.executable, str(script_path)]
        if args:
            cmd.extend(args)

        # Add verbose flag if in verbose mode
        if self.verbose and "-v" not in cmd:
            cmd.append("-v")

        # Add auto-yes flag if in automated modes
        if self.mode in (SetupMode.AUTOMATED, SetupMode.PLAY, SetupMode.RUN):
            if "-y" not in cmd and "--yes" not in cmd:
                cmd.append("-y")

        self.log(f"Running: {' '.join(cmd)}", "DEBUG")

        try:
            result = subprocess.run(
                cmd,
                capture_output=capture,
                text=True,
                timeout=600
            )
            return result.returncode == 0, result.stdout if capture else None
        except subprocess.TimeoutExpired:
            self.log("Script timed out", "ERROR")
            return False, None
        except Exception as e:
            self.log(f"Error running script: {e}", "ERROR")
            return False, None

    def step_audit_system(self) -> bool:
        """Step 0: Audit entire monitoring stack."""
        self.header("STEP 0: System Audit (Optional)")

        if not self.confirm("Run full monitoring stack audit? (Grafana, Prometheus, Graphite, MySQL, etc.)", default=False):
            self.log("Skipping system audit", "INFO")
            return True

        self.log("Auditing monitoring stack...", "STEP")
        success, _ = self.run_script("audit_monitoring_stack.py", ["-v"])

        if not success:
            self.log("Audit failed, continuing anyway...", "WARN")

        self.pause()
        return True

    def step_detect_grafana(self) -> bool:
        """Step 1: Detect existing Grafana installations."""
        self.header("STEP 1: Detecting Existing Grafana Installations")

        self.log("Scanning system for Grafana...", "STEP")

        success, output = self.run_script("detect_grafana.py", ["-f", "json"], capture=True)

        if success and output:
            try:
                installations = json.loads(output)
                if installations:
                    self.log(f"Found {len(installations)} existing installation(s):", "SUCCESS")
                    for inst in installations:
                        print(f"  - {inst['type']}: {inst.get('path', 'N/A')}")
                        if inst.get('running'):
                            print(f"    Status: {Color.GREEN}Running{Color.END}")
                            if inst.get('url'):
                                print(f"    URL: {inst['url']}")

                    if self.confirm("Use existing installation?", default=True):
                        self.log("Using existing Grafana installation", "INFO")
                        return True

                    if not self.confirm("Continue with new installation?", default=False):
                        self.log("Setup cancelled by user", "WARN")
                        sys.exit(0)
                else:
                    self.log("No existing Grafana installations found", "INFO")
            except json.JSONDecodeError:
                self.log("Failed to parse detection results", "WARN")

        self.pause()
        return True

    def step_setup_docker(self) -> bool:
        """Step 2: Setup Docker if needed."""
        self.header("STEP 2: Docker Setup")

        # Check if Docker installation is needed
        install_method = self.config.get("installation", {}).get("preferred_method", "docker")

        if install_method != "docker":
            self.log(f"Skipping Docker setup (preferred method: {install_method})", "INFO")
            return True

        self.log("Checking Docker installation...", "STEP")

        success, _ = self.run_script("setup_docker.py", ["--check-only"], capture=True)

        if success:
            self.log("Docker is already installed and running", "SUCCESS")
        else:
            self.log("Docker needs to be installed", "WARN")

            if not self.confirm("Install Docker now?", default=True):
                self.log("Docker installation skipped", "WARN")
                return False

            success, _ = self.run_script("setup_docker.py")

            if not success:
                self.log("Docker installation failed", "ERROR")
                return False

            self.log("Docker installed successfully", "SUCCESS")

        self.pause()
        return True

    def step_install_grafana(self) -> bool:
        """Step 3: Install Grafana."""
        self.header("STEP 3: Grafana Installation")

        install_config = self.config.get("installation", {})
        method = install_config.get("preferred_method", "docker")
        version = install_config.get("version", "")

        self.log(f"Installing Grafana via {method}...", "STEP")

        args = [method]

        if version:
            args.extend(["--version", version])

        # Add method-specific arguments
        if method == "docker":
            docker_config = self.config.get("docker", {})
            port = docker_config.get("port", 3000)
            args.extend(["--port", str(port)])

        elif method in ("binary", "source"):
            install_path = install_config.get("install_path", "/opt/grafana")
            args.extend(["--path", install_path])

        success, _ = self.run_script("install_grafana.py", args)

        if not success:
            self.log(f"Installation via {method} failed", "ERROR")

            # Try fallback methods
            fallback_order = install_config.get("fallback_order", [])
            for fallback_method in fallback_order:
                if fallback_method == method:
                    continue

                self.log(f"Trying fallback method: {fallback_method}", "WARN")
                args = [fallback_method]

                if version:
                    args.extend(["--version", version])

                success, _ = self.run_script("install_grafana.py", args)

                if success:
                    self.log(f"Installation via {fallback_method} succeeded", "SUCCESS")
                    break
            else:
                self.log("All installation methods failed", "ERROR")
                return False

        self.log("Grafana installed successfully", "SUCCESS")
        self.pause()
        return True

    def step_configure_grafana(self) -> bool:
        """Step 4: Configure Grafana."""
        self.header("STEP 4: Grafana Configuration")

        self.log("Grafana configuration is handled during installation", "INFO")
        self.log("Default credentials: admin / admin", "INFO")
        self.log("You will be prompted to change the password on first login", "INFO")

        self.pause()
        return True

    def step_setup_datasources(self) -> bool:
        """Step 5: Setup datasources."""
        self.header("STEP 5: Datasource Configuration")

        datasource_config = self.config.get("datasources", {})

        if not datasource_config.get("enabled", True):
            self.log("Datasource provisioning is disabled", "INFO")
            return True

        self.log("Datasource provisioning will be available after Grafana starts", "INFO")
        self.log("You can manually configure datasources at http://localhost:3000/datasources", "INFO")

        self.pause()
        return True

    def step_health_check(self) -> bool:
        """Step 6: Perform health check."""
        self.header("STEP 6: Health Check")

        health_config = self.config.get("health_checks", {})

        if not health_config.get("enabled", True):
            self.log("Health checks are disabled", "INFO")
            return True

        self.log("Waiting for Grafana to start...", "STEP")

        timeout = health_config.get("timeout", 60)
        retry_interval = health_config.get("retry_interval", 5)
        expected_status = health_config.get("expected_status", 200)

        import urllib.request
        import urllib.error

        start_time = time.time()
        url = "http://localhost:3000/api/health"

        while time.time() - start_time < timeout:
            try:
                response = urllib.request.urlopen(url, timeout=5)
                if response.status == expected_status:
                    self.log("Grafana is healthy and responding", "SUCCESS")
                    return True
            except (urllib.error.URLError, urllib.error.HTTPError, OSError):
                pass

            time.sleep(retry_interval)

        self.log("Health check timed out", "WARN")
        self.log("Grafana may still be starting up", "INFO")
        return True

    def step_post_install(self) -> bool:
        """Step 7: Post-installation tasks."""
        self.header("STEP 7: Post-Installation")

        post_config = self.config.get("post_install", {})

        if post_config.get("show_guide", True):
            self.show_getting_started()

        self.log("Setup complete!", "SUCCESS")
        self.pause()
        return True

    def show_getting_started(self):
        """Show getting started guide."""
        print(f"\n{Color.BOLD}{Color.GREEN}Getting Started with Grafana:{Color.END}\n")

        print(f"{Color.CYAN}1. Access Grafana:{Color.END}")
        print(f"   Open your browser: http://localhost:3000")
        print(f"   Default login: admin / admin\n")

        print(f"{Color.CYAN}2. Add a datasource:{Color.END}")
        print(f"   Navigate to Configuration > Data Sources")
        print(f"   Click 'Add data source' and select your data source type\n")

        print(f"{Color.CYAN}3. Create a dashboard:{Color.END}")
        print(f"   Use the toolkit to generate dashboards:")
        print(f"   $ ads-grafana-toolkit wizard")
        print(f"   $ ads-grafana-toolkit templates create node-exporter -d Prometheus\n")

        print(f"{Color.CYAN}4. Import generated dashboard:{Color.END}")
        print(f"   In Grafana, go to Dashboards > Import")
        print(f"   Upload your generated JSON file\n")

    def show_summary(self):
        """Show setup summary."""
        self.header("Setup Summary")

        if self.steps_completed:
            print(f"{Color.GREEN}Completed steps:{Color.END}")
            for step in self.steps_completed:
                print(f"  ✓ {step}")

        if self.steps_failed:
            print(f"\n{Color.RED}Failed steps:{Color.END}")
            for step in self.steps_failed:
                print(f"  ✗ {step}")

        print()

    def run(self) -> bool:
        """Run the complete setup process."""
        self.header("Grafana Setup - ads-grafana-toolkit")

        print(f"Mode: {Color.BOLD}{self.mode.value}{Color.END}")
        print(f"Configuration: {self.config.get('installation', {}).get('preferred_method', 'docker')}")
        print()

        steps = [
            ("System Audit", self.step_audit_system),
            ("Detect Grafana", self.step_detect_grafana),
            ("Setup Docker", self.step_setup_docker),
            ("Install Grafana", self.step_install_grafana),
            ("Configure Grafana", self.step_configure_grafana),
            ("Setup Datasources", self.step_setup_datasources),
            ("Health Check", self.step_health_check),
            ("Post-Install", self.step_post_install),
        ]

        for step_name, step_func in steps:
            try:
                success = step_func()

                if success:
                    self.steps_completed.append(step_name)
                else:
                    self.steps_failed.append(step_name)

                    if self.config.get("automated", {}).get("fail_fast", True):
                        self.log(f"Setup failed at step: {step_name}", "ERROR")
                        break

            except KeyboardInterrupt:
                self.log("\nSetup interrupted by user", "WARN")
                break
            except Exception as e:
                self.log(f"Error in step '{step_name}': {e}", "ERROR")
                self.steps_failed.append(step_name)

                if self.config.get("automated", {}).get("fail_fast", True):
                    break

        self.show_summary()

        return len(self.steps_failed) == 0


def main():
    parser = argparse.ArgumentParser(
        description="Grafana Setup - Complete installation and configuration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Automated installation with defaults
  %(prog)s --automated

  # Step-by-step with confirmations
  %(prog)s --step-by-step

  # Run with pauses but no confirmations
  %(prog)s --play

  # Quick run with minimal output
  %(prog)s --run

  # Use custom configuration
  %(prog)s --automated --config my_config.yaml

  # Verbose output
  %(prog)s --automated --verbose
        """
    )

    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument(
        "--automated",
        action="store_const",
        const=SetupMode.AUTOMATED,
        dest="mode",
        help="Run fully automated (no confirmations)"
    )
    mode_group.add_argument(
        "--step-by-step",
        action="store_const",
        const=SetupMode.STEP_BY_STEP,
        dest="mode",
        help="Run step-by-step with confirmations"
    )
    mode_group.add_argument(
        "--play",
        action="store_const",
        const=SetupMode.PLAY,
        dest="mode",
        help="Run with pauses, no confirmations"
    )
    mode_group.add_argument(
        "--run",
        action="store_const",
        const=SetupMode.RUN,
        dest="mode",
        help="Quick run, minimal output"
    )

    parser.add_argument(
        "-c", "--config",
        help="Path to configuration file"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output"
    )

    args = parser.parse_args()

    setup = GrafanaSetup(
        mode=args.mode,
        config_path=args.config,
        verbose=args.verbose
    )

    success = setup.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
