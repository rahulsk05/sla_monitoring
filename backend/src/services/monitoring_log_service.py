
from collections.abc import Mapping, Sequence
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logger import get_logger
from src.models.monitoring_log import MonitoringLog
from src.repositories.monitoring_log_repository import (
    MonitoringLogRepository,
)


logger = get_logger(__name__)


class MonitoringLogService:
    """Handle monitoring log database operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.repository = MonitoringLogRepository(session)

    async def insert_monitoring_logs(
        self,
        records: Sequence[Mapping[str, object]],
    ) -> int:
        """Insert new monitoring records, ignoring existing duplicates."""

        return await self.repository.insert_monitoring_logs(records)

    async def get_all_monitoring_logs_for_metrics(
        self,
    ) -> list[dict[str, object]]:
        """Retrieve monitoring history required for metric calculations."""

        return await self.repository.get_all_monitoring_logs_for_metrics()

    async def get_monitoring_logs(
        self,
        page: int,
        date_filter: date | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        service_id: str | None = None,
        agent: str | None = None,
    ) -> tuple[list[MonitoringLog], int]:
        """Retrieve filtered and paginated monitoring logs."""

        return await self.repository.get_monitoring_logs(
            page=page,
            date_filter=date_filter,
            start_date=start_date,
            end_date=end_date,
            service_id=service_id,
            agent=agent,
        )
