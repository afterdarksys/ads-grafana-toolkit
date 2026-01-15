"""Base class for dashboard templates."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Union

from ads_grafana_toolkit.sdk.dashboard import Dashboard
from ads_grafana_toolkit.sdk.datasource import Datasource


@dataclass
class TemplateVariable:
    """A variable that users can customize in the template."""

    name: str
    description: str
    default: str = ""
    required: bool = False
    choices: list[str] = field(default_factory=list)


@dataclass
class DashboardTemplate(ABC):
    """Base class for dashboard templates."""

    name: str
    description: str
    category: str
    tags: list[str] = field(default_factory=list)
    variables: list[TemplateVariable] = field(default_factory=list)

    @abstractmethod
    def create(
        self,
        datasource: Union[Datasource, str],
        **kwargs,
    ) -> Dashboard:
        """Create a dashboard from this template."""
        pass

    def _resolve_datasource(self, datasource: Union[Datasource, str]) -> Datasource:
        """Convert datasource string to Datasource object if needed."""
        if isinstance(datasource, str):
            return Datasource(name=datasource, type="prometheus")
        return datasource

    def _substitute_vars(self, text: str, variables: dict[str, str]) -> str:
        """Substitute template variables in text."""
        result = text
        for key, value in variables.items():
            result = result.replace(f"${{{key}}}", value)
            result = result.replace(f"${key}", value)
        return result
