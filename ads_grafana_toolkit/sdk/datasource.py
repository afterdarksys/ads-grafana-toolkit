"""Datasource configuration for Grafana dashboards."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Datasource:
    """Represents a Grafana datasource reference."""

    name: str
    type: str = "prometheus"
    uid: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to Grafana datasource reference format."""
        if self.uid:
            return {"type": self.type, "uid": self.uid}
        return {"type": self.type, "uid": self.name}

    @classmethod
    def prometheus(cls, name: str = "Prometheus") -> Datasource:
        """Create a Prometheus datasource reference."""
        return cls(name=name, type="prometheus")

    @classmethod
    def mysql(cls, name: str = "MySQL") -> Datasource:
        """Create a MySQL datasource reference."""
        return cls(name=name, type="mysql")

    @classmethod
    def postgres(cls, name: str = "PostgreSQL") -> Datasource:
        """Create a PostgreSQL datasource reference."""
        return cls(name=name, type="postgres")

    @classmethod
    def influxdb(cls, name: str = "InfluxDB") -> Datasource:
        """Create an InfluxDB datasource reference."""
        return cls(name=name, type="influxdb")

    @classmethod
    def elasticsearch(cls, name: str = "Elasticsearch") -> Datasource:
        """Create an Elasticsearch datasource reference."""
        return cls(name=name, type="elasticsearch")

    @classmethod
    def loki(cls, name: str = "Loki") -> Datasource:
        """Create a Loki datasource reference."""
        return cls(name=name, type="loki")

    @classmethod
    def cloudwatch(cls, name: str = "CloudWatch") -> Datasource:
        """Create a CloudWatch datasource reference."""
        return cls(name=name, type="cloudwatch")

    @classmethod
    def graphite(cls, name: str = "Graphite") -> Datasource:
        """Create a Graphite datasource reference."""
        return cls(name=name, type="graphite")

    @classmethod
    def tempo(cls, name: str = "Tempo") -> Datasource:
        """Create a Tempo datasource reference."""
        return cls(name=name, type="tempo")

    @classmethod
    def azure_monitor(cls, name: str = "Azure Monitor") -> Datasource:
        """Create an Azure Monitor datasource reference."""
        return cls(name=name, type="grafana-azure-monitor-datasource")

    @classmethod
    def cloud_monitoring(cls, name: str = "Google Cloud Monitoring") -> Datasource:
        """Create a GCP Cloud Monitoring (Stackdriver) datasource reference."""
        return cls(name=name, type="stackdriver")

    @classmethod
    def influxdb2(cls, name: str = "InfluxDB v2") -> Datasource:
        """Create an InfluxDB v2 (Flux) datasource reference."""
        return cls(name=name, type="influxdb")

    @classmethod
    def snmp(cls, name: str = "Prometheus-SNMP") -> Datasource:
        """Create a Prometheus datasource reference for SNMP exporter metrics."""
        return cls(name=name, type="prometheus")

    @classmethod
    def telegraf(cls, name: str = "InfluxDB-Telegraf") -> Datasource:
        """Create an InfluxDB datasource reference for Telegraf output."""
        return cls(name=name, type="influxdb")
