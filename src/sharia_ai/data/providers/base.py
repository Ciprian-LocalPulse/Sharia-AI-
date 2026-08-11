"""Provider abstraction for sourced financial data."""

from __future__ import annotations

from abc import ABC, abstractmethod

from sharia_ai.data.models import FinancialMetric


class FinancialDataProvider(ABC):
    """Implementations must return metrics with complete provenance."""

    @abstractmethod
    def get_metric(self, company_id: str, metric_name: str) -> FinancialMetric:
        raise NotImplementedError
