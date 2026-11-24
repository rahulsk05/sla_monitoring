
from collections.abc import Mapping

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logger import get_logger
from src.models.overall_metric import OverallMetric


logger = get_logger(__name__)


class OverallMetricRepository:
    """Database operations for overall dashboard metrics."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def upsert_overall_metrics(
        self,
        metrics: Mapping[str, object],
    ) -> None:
        """Insert or update the overall metrics record."""

        statement = insert(OverallMetric).values(dict(metrics))

        update_fields = (
            "total_checks",
            "availability_eligible_checks",
            "successful_checks",
            "failed_checks",
            "availability_percentage",
            "services_below_sla",
            "total_failure_events",
            "longest_failure_duration_seconds",
            "sla_threshold_percentage",
            "calculated_at",
            "updated_at",
        )

        statement = statement.on_conflict_do_update(
            index_elements=[OverallMetric.id],
            set_={
                field: getattr(statement.excluded, field)
                for field in update_fields
            },
        )

        await self.session.execute(statement)

        logger.info("Overall metrics upsert completed successfully.")

    async def get_overall_metrics(
        self,
    ) -> OverallMetric | None:
        """Retrieve the overall dashboard metrics record."""

        statement = select(OverallMetric).where(
            OverallMetric.id == 1
        )

        result = await self.session.execute(statement)

        metrics = result.scalar_one_or_none()

        if metrics is None:
            logger.info("Overall metrics record not found.")
            return None

        logger.info("Overall metrics record retrieved successfully.")

        return metrics
