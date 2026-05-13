"""Core alert rule datastructures and YAML serializer for Grafana unified alerting."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
import yaml


@dataclass
class AlertRule:
    uid: str
    title: str
    expr: str                          # PromQL / CloudWatch expression
    condition: str = "C"               # refId of the threshold condition
    for_duration: str = "5m"
    severity: str = "warning"          # critical | warning | info
    team: str = "noc"
    summary: str = ""
    description: str = ""
    datasource_uid: str = "prometheus"
    threshold_type: str = "gt"         # gt | lt | gte | lte
    threshold_value: float = 0
    no_data_state: str = "NoData"
    exec_err_state: str = "Alerting"
    labels: dict = field(default_factory=dict)
    annotations: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        extra_labels = {"severity": self.severity, "team": self.team, **self.labels}
        extra_annotations = {
            "summary": self.summary or self.title,
            "description": self.description,
            **self.annotations,
        }
        return {
            "uid": self.uid,
            "title": self.title,
            "condition": self.condition,
            "data": [
                {
                    "refId": "A",
                    "relativeTimeRange": {"from": 300, "to": 0},
                    "datasourceUid": self.datasource_uid,
                    "model": {
                        "expr": self.expr,
                        "refId": "A",
                        "intervalMs": 1000,
                        "maxDataPoints": 43200,
                    },
                },
                {
                    "refId": "B",
                    "relativeTimeRange": {"from": 300, "to": 0},
                    "datasourceUid": "__expr__",
                    "model": {
                        "refId": "B",
                        "type": "reduce",
                        "datasource": {"type": "__expr__", "uid": "__expr__"},
                        "conditions": [{"evaluator": {"params": [], "type": "gt"},
                                        "operator": {"type": "and"},
                                        "query": {"params": ["A"]},
                                        "reducer": {"params": [], "type": "last"},
                                        "type": "query"}],
                        "reducer": "last",
                        "expression": "A",
                    },
                },
                {
                    "refId": "C",
                    "relativeTimeRange": {"from": 300, "to": 0},
                    "datasourceUid": "__expr__",
                    "model": {
                        "refId": "C",
                        "type": "threshold",
                        "datasource": {"type": "__expr__", "uid": "__expr__"},
                        "conditions": [{
                            "evaluator": {"params": [self.threshold_value], "type": self.threshold_type},
                            "operator": {"type": "and"},
                            "query": {"params": ["B"]},
                            "reducer": {"params": [], "type": "last"},
                            "type": "query",
                        }],
                        "expression": "B",
                    },
                },
            ],
            "noDataState": self.no_data_state,
            "execErrState": self.exec_err_state,
            "for": self.for_duration,
            "labels": extra_labels,
            "annotations": extra_annotations,
        }


@dataclass
class AlertGroup:
    name: str
    folder: str
    interval: str = "1m"
    rules: list[AlertRule] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "orgId": 1,
            "name": self.name,
            "folder": self.folder,
            "interval": self.interval,
            "rules": [r.to_dict() for r in self.rules],
        }


def generate_rules_yaml(groups: list[AlertGroup], datasource_uid: str = "prometheus") -> str:
    """Serialize alert groups to Grafana provisioning YAML."""
    for g in groups:
        for r in g.rules:
            if r.datasource_uid == "prometheus":
                r.datasource_uid = datasource_uid
    payload = {"apiVersion": 1, "groups": [g.to_dict() for g in groups]}
    return yaml.dump(payload, default_flow_style=False, sort_keys=False, allow_unicode=True)
