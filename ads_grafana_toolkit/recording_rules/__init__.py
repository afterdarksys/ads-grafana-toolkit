"""Prometheus recording rules generator — extract PromQL from dashboard templates."""
from ads_grafana_toolkit.recording_rules.generator import (
    generate_recording_rules_yaml,
    recording_rules_for_template,
)

__all__ = ["generate_recording_rules_yaml", "recording_rules_for_template"]
