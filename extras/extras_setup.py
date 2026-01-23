#!/usr/bin/env python3
"""
Extras Setup Orchestrator
Unified setup and usage guide for all extra features.
"""

import os
import subprocess
import sys
from pathlib import Path


class ExtrasSetup:
    """Orchestrates setup and provides guidance for extra features."""

    def __init__(self):
        self.extras_dir = Path(__file__).parent
        self.scripts = {
            "jsonnet": self.extras_dir / "jsonnet_support.py",
            "promql": self.extras_dir / "promql_builder.py",
            "writers": self.extras_dir / "writers_toolkit.py",
        }

    def print_header(self, text: str):
        """Print section header."""
        print(f"\n{'='*70}")
        print(f"{text.center(70)}")
        print(f"{'='*70}\n")

    def show_menu(self):
        """Show main menu."""
        self.print_header("GRAFANA TOOLKIT - EXTRAS")

        print("Available features:")
        print()
        print("1. Jsonnet/Grafonnet Support")
        print("   - Convert Jsonnet to Grafana JSON")
        print("   - Use Grafonnet library for programmatic dashboards")
        print("   - Auto-installs dependencies")
        print()
        print("2. PromQL Query Builder")
        print("   - Interactive query builder")
        print("   - Query templates for common metrics")
        print("   - Validation against Prometheus")
        print()
        print("3. Writers Toolkit")
        print("   - Export dashboards to Markdown/HTML/JSON")
        print("   - Generate documentation")
        print("   - Create reports")
        print()
        print("4. Setup All Features")
        print("   - Install all dependencies")
        print("   - Run initial setup")
        print()
        print("5. Show Quick Start Guide")
        print()
        print("0. Exit")
        print()

    def setup_jsonnet(self):
        """Setup Jsonnet/Grafonnet."""
        self.print_header("Setting up Jsonnet/Grafonnet")

        print("Installing Jsonnet and downloading Grafonnet library...")
        result = subprocess.run(
            [sys.executable, str(self.scripts["jsonnet"]), "setup", "-v"],
            check=False
        )

        if result.returncode == 0:
            print("\n✓ Jsonnet setup complete!")
            print("\nQuick start:")
            print(f"  {sys.executable} {self.scripts['jsonnet']} example")
            print(f"  {sys.executable} {self.scripts['jsonnet']} convert example_dashboard.jsonnet")
        else:
            print("\n✗ Setup failed. Check error messages above.")

        input("\nPress Enter to continue...")

    def setup_promql(self):
        """Setup PromQL builder."""
        self.print_header("PromQL Query Builder")

        print("No setup required!")
        print("\nQuick start:")
        print(f"  {sys.executable} {self.scripts['promql']} interactive")
        print(f"  {sys.executable} {self.scripts['promql']} template cpu_usage")

        input("\nPress Enter to continue...")

    def setup_writers(self):
        """Setup Writers Toolkit."""
        self.print_header("Writers Toolkit")

        print("No setup required!")
        print("\nQuick start:")
        print(f"  {sys.executable} {self.scripts['writers']} dashboard.json -f markdown")
        print(f"  {sys.executable} {self.scripts['writers']} dashboard.json -f html")

        input("\nPress Enter to continue...")

    def setup_all(self):
        """Setup all features."""
        self.print_header("Setting up all features")

        self.setup_jsonnet()
        self.setup_promql()
        self.setup_writers()

        print("\n✓ All features are ready!")
        input("\nPress Enter to continue...")

    def show_quick_start(self):
        """Show quick start guide."""
        self.print_header("QUICK START GUIDE")

        print("""
1. JSONNET/GRAFONNET

   Setup:
   $ python3 extras/jsonnet_support.py setup

   Create example:
   $ python3 extras/jsonnet_support.py example

   Convert to JSON:
   $ python3 extras/jsonnet_support.py convert example_dashboard.jsonnet

   Use with main toolkit:
   $ ads-grafana-toolkit convert example_dashboard.json

2. PROMQL QUERY BUILDER

   Interactive mode:
   $ python3 extras/promql_builder.py interactive

   Use template:
   $ python3 extras/promql_builder.py template cpu_usage

   Validate query:
   $ python3 extras/promql_builder.py validate 'up{job="node"}'

3. WRITERS TOOLKIT

   Export to Markdown:
   $ python3 extras/writers_toolkit.py dashboard.json -f markdown

   Export to HTML:
   $ python3 extras/writers_toolkit.py dashboard.json -f html

   Fetch from Grafana:
   $ python3 extras/writers_toolkit.py DASHBOARD_UID --fetch \\
       --grafana-url http://localhost:3000 \\
       --api-key YOUR_API_KEY

COMBINED WORKFLOW:

  1. Build query:
     $ python3 extras/promql_builder.py template cpu_usage > query.txt

  2. Create dashboard with Jsonnet:
     $ python3 extras/jsonnet_support.py example
     $ python3 extras/jsonnet_support.py convert example_dashboard.jsonnet

  3. Import to Grafana:
     $ ads-grafana-toolkit convert example_dashboard.json

  4. Generate docs:
     $ python3 extras/writers_toolkit.py example_dashboard.json -f html

See individual tool --help for more options.
""")

        input("\nPress Enter to continue...")

    def run(self):
        """Run the interactive menu."""
        while True:
            self.show_menu()

            try:
                choice = input("Select option (0-5): ").strip()

                if choice == "0":
                    print("\nGoodbye!")
                    break
                elif choice == "1":
                    self.setup_jsonnet()
                elif choice == "2":
                    self.setup_promql()
                elif choice == "3":
                    self.setup_writers()
                elif choice == "4":
                    self.setup_all()
                elif choice == "5":
                    self.show_quick_start()
                else:
                    print("\nInvalid choice. Please try again.")
                    input("Press Enter to continue...")

            except KeyboardInterrupt:
                print("\n\nInterrupted. Goodbye!")
                break
            except Exception as e:
                print(f"\nError: {e}")
                input("Press Enter to continue...")


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Extras Setup - Configure and use additional features"
    )

    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Non-interactive mode (just show quick start)"
    )

    args = parser.parse_args()

    setup = ExtrasSetup()

    if args.non_interactive:
        setup.show_quick_start()
    else:
        setup.run()


if __name__ == "__main__":
    main()
