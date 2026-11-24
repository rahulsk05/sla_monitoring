from collections.abc import Mapping, Sequence

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.constants import UPLOAD_CHUNK_INSERT_SIZE
from src.core.logger import get_logger
from src.models.monitoring_log import MonitoringLog


logger = get_logger(__name__)


class MonitoringLogRepository:
    """Database operations for monitoring logs."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def insert_monitoring_logs(
        self,
        records: Sequence[Mapping[str, object]],
    ) -> int:
        """
        Bulk insert monitoring records.

        Existing records with the same record_hash are ignored.

        Returns:
            Number of newly inserted records.
        """

        if not records:
            logger.info("Monitoring log insertion skipped: no records provided.")
            return 0

        inserted_count = 0

        for start_index in range(
            0,
            len(records),
            UPLOAD_CHUNK_INSERT_SIZE,
        ):
            batch = [
                dict(record)
                for record in records[
                    start_index:start_index + UPLOAD_CHUNK_INSERT_SIZE
                ]
            ]

            statement = insert(MonitoringLog).values(batch)

            statement = statement.on_conflict_do_nothing(
                index_elements=[MonitoringLog.record_hash],
            )

            result = await self.session.execute(statement)

            inserted_count += result.rowcount or 0

        duplicate_count = len(records) - inserted_count

        logger.info(
            (
                "Monitoring log insertion completed. "
                "Submitted: %d, Inserted: %d, Existing duplicates: %d"
            ),
            len(records),
            inserted_count,
            duplicate_count,
        )

        return inserted_count

    async def get_all_monitoring_logs_for_metrics(
        self,
    ) -> list[dict[str, object]]:
        """Retrieve monitoring history required for metrics calculation."""

        statement = select(
            MonitoringLog.record_hash,
            MonitoringLog.service_id,
            MonitoringLog.service_name,
            MonitoringLog.observed_at,
            MonitoringLog.status_code,
            MonitoringLog.latency_ms,
        )

        result = await self.session.execute(statement)

        records: list[dict[str, object]] = [
            dict(row)
            for row in result.mappings().all()
        ]

        logger.info(
            "Retrieved %d monitoring records for metrics calculation.",
            len(records),
        )

        return records
