
from collections.abc import Mapping, Sequence

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logger import get_logger
from src.models.service_metric import ServiceMetric


logger = get_logger(__name__)


class ServiceMetricRepository:
    """Database operations for service-level metrics."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def upsert_service_metrics(
        self,
        metrics: Sequence[Mapping[str, object]],
    ) -> None:
        """Insert or update metrics for multiple services."""

        if not metrics:
            logger.info(
                "Service metrics upsert skipped: no metrics provided."
            )
            return

        records = [dict(metric) for metric in metrics]

        statement = insert(ServiceMetric).values(records)

        update_fields = (
            "service_name",
            "total_checks",
            "availability_eligible_checks",
            "successful_checks",
            "failed_checks",
            "availability_percentage",
            "average_latency_ms",
            "p95_latency_ms",
            "latency_sample_count",
            "failure_events",
            "longest_failure_duration_seconds",
            "meets_sla",
            "calculated_at",
            "updated_at",
        )

        statement = statement.on_conflict_do_update(
            index_elements=[ServiceMetric.service_id],
            set_={
                field: getattr(statement.excluded, field)
                for field in update_fields
            },
        )

        await self.session.execute(statement)

        logger.info(
            "Service metrics upsert completed successfully. Services: %d",
            len(records),
        )

    async def get_all_service_metrics(
        self,
    ) -> list[ServiceMetric]:
        """Retrieve all service-level metrics."""

        statement = (
            select(ServiceMetric)
            .order_by(ServiceMetric.service_id.asc())
        )

        result = await self.session.execute(statement)

        service_metrics = list(result.scalars().all())

        logger.info(
            "Retrieved service metrics. Services: %d",
            len(service_metrics),
        )

        return service_metrics
