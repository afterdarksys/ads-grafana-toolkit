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
