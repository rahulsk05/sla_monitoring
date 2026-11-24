
from collections.abc import Mapping, Sequence
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.constants import LOGS_PAGE_SIZE, UPLOAD_CHUNK_INSERT_SIZE
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
            logger.info(
                "Monitoring log insertion skipped: no records provided."
            )
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
            ).returning(
                MonitoringLog.record_hash
            )

            result = await self.session.execute(statement)

            # RETURNING provides only records that were actually inserted.
            batch_inserted_count = len(result.scalars().all())

            inserted_count += batch_inserted_count

            logger.debug(
                "Monitoring log batch processed. "
                "Batch size: %d, Inserted: %d",
                len(batch),
                batch_inserted_count,
            )

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

    async def get_monitoring_logs(
        self,
        page: int,
        date_filter: date | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        service_id: str | None = None,
        agent: str | None = None,
    ) -> tuple[list[MonitoringLog], int]:
        """Retrieve a filtered, paginated list of monitoring logs."""

        filters = []

        if date_filter is not None:
            start_datetime = datetime.combine(
                date_filter,
                time.min,
                tzinfo=timezone.utc,
            )
            end_datetime = start_datetime + timedelta(days=1)

            filters.extend([
                MonitoringLog.observed_at >= start_datetime,
                MonitoringLog.observed_at < end_datetime,
            ])

        elif start_date is not None and end_date is not None:
            start_datetime = datetime.combine(
                start_date,
                time.min,
                tzinfo=timezone.utc,
            )
            end_datetime = datetime.combine(
                end_date + timedelta(days=1),
                time.min,
                tzinfo=timezone.utc,
            )

            filters.extend([
                MonitoringLog.observed_at >= start_datetime,
                MonitoringLog.observed_at < end_datetime,
            ])

        if service_id is not None:
            filters.append(MonitoringLog.service_id == service_id)

        if agent is not None:
            filters.append(MonitoringLog.agent == agent)

        count_statement = (
            select(func.count())
            .select_from(MonitoringLog)
            .where(*filters)
        )

        count_result = await self.session.execute(count_statement)
        total_records = count_result.scalar_one()

        offset = (page - 1) * LOGS_PAGE_SIZE

        logs_statement = (
            select(MonitoringLog)
            .where(*filters)
            .order_by(
                MonitoringLog.observed_at.desc(),
                MonitoringLog.id.desc(),
            )
            .offset(offset)
            .limit(LOGS_PAGE_SIZE)
        )

        logs_result = await self.session.execute(logs_statement)
        logs = list(logs_result.scalars().all())

        logger.info(
            "Retrieved monitoring logs. Page: %d, Records: %d, Total: %d",
            page,
            len(logs),
            total_records,
        )

        return logs, total_records
