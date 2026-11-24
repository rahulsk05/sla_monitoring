
from dataclasses import dataclass
from io import BytesIO
from uuid import UUID, uuid4

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.constants import MAX_CSV_FILE_SIZE_BYTES
from src.core.exceptions import CSVFileTooLargeError
from src.core.logger import get_logger
from src.services.cleaning_service import CleaningService
from src.services.monitoring_log_service import MonitoringLogService
from src.services.overall_metrics_service import OverallMetricsService
from src.services.service_metrics_service import ServiceMetricsService


logger = get_logger(__name__)


@dataclass
class UploadResult:
    upload_id: UUID
    total_source_rows: int
    accepted_rows: int
    partially_accepted_rows: int
    rejected_rows: int
    duplicate_rows: int
    inserted_rows: int
    service_count: int


class UploadService:
    """Orchestrate CSV uploads and monitoring metric updates."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

        self.monitoring_log_service = MonitoringLogService(
            session
        )
        self.service_metrics_service = ServiceMetricsService(
            session
        )
        self.overall_metrics_service = OverallMetricsService(
            session
        )

    async def upload_csv(
        self,
        csv_content: bytes,
    ) -> UploadResult:
        """Process a CSV upload and update dashboard metrics."""

        upload_id = uuid4()
        file_size = len(csv_content)

        logger.info(
            "Starting CSV upload. Upload ID: %s, File size: %d bytes",
            upload_id,
            file_size,
        )

        # Validate actual decoded file size before CSV processing.
        if file_size > MAX_CSV_FILE_SIZE_BYTES:
            logger.warning(
                "CSV upload rejected: file exceeds 5 MB. "
                "Upload ID: %s, File size: %d bytes",
                upload_id,
                file_size,
            )
            raise CSVFileTooLargeError()

        # Clean and validate the CSV before starting the transaction.
        cleaning_result = CleaningService.clean_csv(
            BytesIO(csv_content),
            upload_id,
        )

        logger.info(
            "CSV cleaning completed. Upload ID: %s, Valid records: %d",
            upload_id,
            len(cleaning_result.records),
        )

        transaction_started = False

        try:
            # Explicitly begin the database transaction.
            await self.session.begin()
            transaction_started = True

            # 1. Insert new monitoring records.
            inserted_count = (
                await self.monitoring_log_service.insert_monitoring_logs(
                    cleaning_result.records
                )
            )

            # 2. Retrieve complete monitoring history.
            monitoring_records = (
                await self.monitoring_log_service
                .get_all_monitoring_logs_for_metrics()
            )

            monitoring_dataframe = pd.DataFrame(
                monitoring_records,
                columns=[
                    "record_hash",
                    "service_id",
                    "service_name",
                    "observed_at",
                    "status_code",
                    "latency_ms",
                ],
            )

            # 3. Calculate and save service-level metrics.
            service_metrics = (
                await self.service_metrics_service
                .calculate_and_save_metrics(
                    monitoring_dataframe
                )
            )

            # 4. Calculate and save overall metrics.
            await self.overall_metrics_service.calculate_and_save_metrics(
                monitoring_dataframe,
                service_metrics,
            )

            # 5. Commit all database changes.
            await self.session.commit()
            transaction_started = False

            logger.info(
                "CSV upload transaction committed successfully. "
                "Upload ID: %s",
                upload_id,
            )

        except Exception:
            # Roll back only the transaction started by this service.
            if (
                transaction_started
                and self.session.in_transaction()
            ):
                try:
                    await self.session.rollback()
                    logger.info(
                        "Database transaction rolled back. "
                        "Upload ID: %s",
                        upload_id,
                    )
                except Exception:
                    logger.exception(
                        "Database transaction rollback failed. "
                        "Upload ID: %s",
                        upload_id,
                    )

            logger.exception(
                "CSV upload failed. Upload ID: %s",
                upload_id,
            )
            raise

        # Build the response only after a successful commit.
        summary = cleaning_result.summary

        existing_duplicate_count = (
            len(cleaning_result.records) - inserted_count
        )

        total_duplicate_count = (
            summary.duplicate_rows + existing_duplicate_count
        )

        result = UploadResult(
            upload_id=upload_id,
            total_source_rows=summary.total_source_rows,
            accepted_rows=summary.accepted_rows,
            partially_accepted_rows=summary.partially_accepted_rows,
            rejected_rows=summary.rejected_rows,
            duplicate_rows=total_duplicate_count,
            inserted_rows=inserted_count,
            service_count=len(service_metrics),
        )

        logger.info(
            "CSV upload completed successfully. "
            "Upload ID: %s, Inserted: %d, Duplicates: %d, "
            "Services: %d",
            upload_id,
            inserted_count,
            total_duplicate_count,
            len(service_metrics),
        )

        return result
