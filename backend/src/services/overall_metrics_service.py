from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from decimal import Decimal

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.constants import OVERALL_METRICS_ID
from src.core.logger import get_logger
from src.models.overall_metric import OverallMetric
from src.repositories.overall_metrics_repository import OverallMetricRepository
from src.utils.metrics_helpers import (
    calculate_availability,
    is_failed_status,
    is_successful_status,
)


logger = get_logger(__name__)


class OverallMetricsService:
    def __init__(self, session: AsyncSession) -> None:
        self.repository = OverallMetricRepository(session)

    """Calculate dashboard-wide metrics from monitoring history."""

    @staticmethod
    def calculate_metrics(
        dataframe: pd.DataFrame,
        service_metrics: Sequence[Mapping[str, object]],
    ) -> dict[str, object]:
        """Calculate and return a single overall metrics record."""

        logger.info(
            "Starting overall metrics calculation. Records: %d, Services: %d",
            len(dataframe),
            len(service_metrics),
        )

        calculated_at = datetime.now(timezone.utc)

        if dataframe.empty:
            total_checks = 0
            successful_checks = 0
            failed_checks = 0
        else:
            status_codes = dataframe["status_code"].astype(int)

            total_checks = len(dataframe)

            successful_checks = int(
                status_codes.map(is_successful_status).sum()
            )

            failed_checks = int(
                status_codes.map(is_failed_status).sum()
            )

        availability_eligible_checks = (
            successful_checks + failed_checks
        )

        availability_percentage = calculate_availability(
            successful_checks,
            failed_checks,
        )

        services_below_sla = sum(
            not bool(metric["meets_sla"])
            for metric in service_metrics
        )

        total_failure_events = sum(
            int(metric["failure_events"])
            for metric in service_metrics
        )

        longest_failure_duration = max(
            (
                int(metric["longest_failure_duration_seconds"])
                for metric in service_metrics
            ),
            default=0,
        )

        overall_metrics: dict[str, object] = {
            "id": OVERALL_METRICS_ID,
            "total_checks": total_checks,
            "availability_eligible_checks": availability_eligible_checks,
            "successful_checks": successful_checks,
            "failed_checks": failed_checks,
            "availability_percentage": availability_percentage,
            "services_below_sla": services_below_sla,
            "total_failure_events": total_failure_events,
            "longest_failure_duration_seconds": (
                longest_failure_duration
            ),
            "sla_threshold_percentage": Decimal(
                str(settings.sla_threshold)
            ),
            "calculated_at": calculated_at,
            "updated_at": calculated_at,
        }

        logger.info(
            (
                "Overall metrics calculation completed. "
                "Total checks: %d, Successful: %d, Failed: %d, "
                "Availability: %s%%, Services below SLA: %d"
            ),
            total_checks,
            successful_checks,
            failed_checks,
            availability_percentage,
            services_below_sla,
        )

        return overall_metrics

    async def calculate_and_save_metrics(
        self,
        dataframe: pd.DataFrame,
        service_metrics: Sequence[Mapping[str, object]],
    ) -> dict[str, object]:
        """Calculate and persist overall dashboard metrics."""

        overall_metrics = self.calculate_metrics(
            dataframe,
            service_metrics,
        )

        await self.repository.upsert_overall_metrics(
            overall_metrics
        )

        logger.info(
            "Overall dashboard metrics calculated and saved."
        )

        return overall_metrics

    async def get_overall_metrics(self) -> OverallMetric | None:
        return await self.repository.get_overall_metrics()
