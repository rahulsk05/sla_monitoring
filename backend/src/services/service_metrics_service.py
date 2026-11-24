from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.constants import (
    LATENCY_PRECISION,
    SUCCESS_STATUS_MAX,
    SUCCESS_STATUS_MIN,
)
from src.core.logger import get_logger
from src.models.service_metric import ServiceMetric
from src.repositories.service_metrics_repository import ServiceMetricRepository
from src.utils.metrics_helpers import (
    calculate_availability,
    calculate_failure_metrics,
    is_failed_status,
)


logger = get_logger(__name__)


class ServiceMetricsService:
    def __init__(self, session: AsyncSession) -> None:
        self.repository = ServiceMetricRepository(session)
    """Calculate monitoring metrics independently for each service."""

    @staticmethod
    def _calculate_latency_metrics(
        service_records: pd.DataFrame,
    ) -> tuple[Decimal | None, Decimal | None, int]:
        """Calculate average and P95 latency from successful checks."""

        successful_mask = service_records["status_code"].between(
            SUCCESS_STATUS_MIN,
            SUCCESS_STATUS_MAX,
        )

        valid_latency_mask = (
            service_records["latency_ms"].notna()
            & (service_records["latency_ms"] >= 0)
        )

        latency_values = service_records.loc[
            successful_mask & valid_latency_mask,
            "latency_ms",
        ]

        sample_count = len(latency_values)

        if sample_count == 0:
            return None, None, 0

        precision = Decimal(LATENCY_PRECISION)

        average_latency = Decimal(
            str(latency_values.mean())
        ).quantize(
            precision,
            rounding=ROUND_HALF_UP,
        )

        p95_latency = Decimal(
            str(latency_values.quantile(0.95))
        ).quantize(
            precision,
            rounding=ROUND_HALF_UP,
        )

        return average_latency, p95_latency, sample_count

    @classmethod
    def calculate_metrics(
        cls,
        dataframe: pd.DataFrame,
    ) -> list[dict[str, object]]:
        """Calculate metrics for every service in the monitoring history."""

        if dataframe.empty:
            logger.info(
                "Service metrics calculation skipped: no monitoring records."
            )
            return []

        logger.info(
            "Starting service metrics calculation. Records: %d, Services: %d",
            len(dataframe),
            dataframe["service_id"].nunique(),
        )

        # Work on a copy so this service does not modify the caller's DataFrame.
        dataframe = dataframe.copy()

        dataframe["observed_at"] = pd.to_datetime(
            dataframe["observed_at"],
            utc=True,
        )

        dataframe["status_code"] = dataframe["status_code"].astype(int)

        dataframe["latency_ms"] = pd.to_numeric(
            dataframe["latency_ms"],
            errors="coerce",
        )

        # Sort observations before calculating failure events.
        dataframe = dataframe.sort_values(
            by=["service_id", "observed_at", "record_hash"],
            kind="stable",
        )

        calculated_at = datetime.now(timezone.utc)
        sla_threshold = Decimal(str(settings.sla_threshold))

        service_metrics: list[dict[str, object]] = []

        for service_id, service_records in dataframe.groupby(
            "service_id",
            sort=True,
        ):
            total_checks = len(service_records)

            successful_mask = service_records["status_code"].between(
                SUCCESS_STATUS_MIN,
                SUCCESS_STATUS_MAX,
            )

            failed_mask = service_records["status_code"].apply(
                is_failed_status
            )

            successful_checks = int(successful_mask.sum())
            failed_checks = int(failed_mask.sum())

            availability_eligible_checks = (
                successful_checks + failed_checks
            )

            availability_percentage = calculate_availability(
                successful_checks,
                failed_checks,
            )

            average_latency, p95_latency, latency_sample_count = (
                cls._calculate_latency_metrics(service_records)
            )

            observations = (
                (
                    observed_at.to_pydatetime(),
                    int(status_code),
                )
                for observed_at, status_code in zip(
                    service_records["observed_at"],
                    service_records["status_code"],
                )
            )

            failure_events, longest_failure_duration = (
                calculate_failure_metrics(observations)
            )

            meets_sla = availability_percentage >= sla_threshold

            service_name = str(service_records["service_name"].iloc[-1])

            service_metrics.append(
                {
                    "service_id": str(service_id),
                    "service_name": service_name,
                    "total_checks": total_checks,
                    "availability_eligible_checks": (
                        availability_eligible_checks
                    ),
                    "successful_checks": successful_checks,
                    "failed_checks": failed_checks,
                    "availability_percentage": availability_percentage,
                    "average_latency_ms": average_latency,
                    "p95_latency_ms": p95_latency,
                    "latency_sample_count": latency_sample_count,
                    "failure_events": failure_events,
                    "longest_failure_duration_seconds": (
                        longest_failure_duration
                    ),
                    "meets_sla": meets_sla,
                    "calculated_at": calculated_at,
                    "updated_at": calculated_at,
                }
            )

        logger.info(
            "Service metrics calculation completed. Services processed: %d",
            len(service_metrics),
        )

        return service_metrics

    async def calculate_and_save_metrics(
        self,
        dataframe: pd.DataFrame,
    ) -> list[dict[str, object]]:
        """Calculate and persist metrics for all services."""

        service_metrics = self.calculate_metrics(dataframe)

        await self.repository.upsert_service_metrics(
            service_metrics
        )

        logger.info(
            "Service metrics calculated and saved. Services: %d",
            len(service_metrics),
        )

        return service_metrics

    async def get_all_service_metrics(self) -> list[ServiceMetric]:
        return await self.repository.get_all_service_metrics()
