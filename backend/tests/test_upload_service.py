
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.constants import MAX_CSV_FILE_SIZE_BYTES
from src.core.exceptions import CSVFileTooLargeError, CSVValidationError
from src.services.cleaning_service import (
    CleaningResult,
    CleaningSummary,
)
from src.services.upload_service import UploadService


class TestUploadService(IsolatedAsyncioTestCase):

    def setUp(self) -> None:
        self.session = MagicMock(spec=AsyncSession)
        self.session.begin = AsyncMock()
        self.session.commit = AsyncMock()
        self.session.rollback = AsyncMock()
        self.session.in_transaction = MagicMock(return_value=True)

        self.upload_service = UploadService(self.session)

        # Mock dependent services.
        self.upload_service.monitoring_log_service = MagicMock()
        self.upload_service.service_metrics_service = MagicMock()
        self.upload_service.overall_metrics_service = MagicMock()

        self.upload_service.monitoring_log_service.insert_monitoring_logs = (
            AsyncMock(return_value=1)
        )

        self.upload_service.monitoring_log_service.get_all_monitoring_logs_for_metrics = (
            AsyncMock(
                return_value=[
                    {
                        "record_hash": "hash-1",
                        "service_id": "service-1",
                        "service_name": "Service One",
                        "observed_at": "2026-11-20T10:00:00+00:00",
                        "status_code": 200,
                        "latency_ms": 150.0,
                    },
                    {
                        "record_hash": "hash-2",
                        "service_id": "service-1",
                        "service_name": "Service One",
                        "observed_at": "2026-11-20T10:01:00+00:00",
                        "status_code": 500,
                        "latency_ms": None,
                    },
                ]
            )
        )

        self.service_metrics = [
            {
                "service_id": "service-1",
                "service_name": "Service One",
                "total_checks": 2,
                "meets_sla": True,
            }
        ]

        self.upload_service.service_metrics_service.calculate_and_save_metrics = (
            AsyncMock(return_value=self.service_metrics)
        )

        self.upload_service.overall_metrics_service.calculate_and_save_metrics = (
            AsyncMock(return_value={"total_checks": 2})
        )

        self.cleaning_result = CleaningResult(
            records=[
                {
                    "record_hash": "hash-1",
                    "service_id": "service-1",
                    "service_name": "Service One",
                },
                {
                    "record_hash": "hash-2",
                    "service_id": "service-1",
                    "service_name": "Service One",
                },
            ],
            summary=CleaningSummary(
                total_source_rows=4,
                accepted_rows=1,
                partially_accepted_rows=1,
                rejected_rows=1,
                duplicate_rows=1,
            ),
        )

        self.csv_content = b"service_id,service_name,timestamp,status_code"

    async def test_upload_csv_success(self) -> None:
        with patch(
            "src.services.upload_service.CleaningService.clean_csv",
            return_value=self.cleaning_result,
        ) as mock_clean_csv:

            result = await self.upload_service.upload_csv(
                self.csv_content
            )

        # Verify cleaning.
        mock_clean_csv.assert_called_once()

        # Verify transaction lifecycle.
        self.session.begin.assert_awaited_once()
        self.session.commit.assert_awaited_once()
        self.session.rollback.assert_not_awaited()

        # Verify monitoring log operations.
        self.upload_service.monitoring_log_service.insert_monitoring_logs.assert_awaited_once()
        self.upload_service.monitoring_log_service.get_all_monitoring_logs_for_metrics.assert_awaited_once()

        # Verify metrics services.
        self.upload_service.service_metrics_service.calculate_and_save_metrics.assert_awaited_once()
        self.upload_service.overall_metrics_service.calculate_and_save_metrics.assert_awaited_once()

        # Verify upload result.
        self.assertEqual(result.total_source_rows, 4)
        self.assertEqual(result.accepted_rows, 1)
        self.assertEqual(result.partially_accepted_rows, 1)
        self.assertEqual(result.rejected_rows, 1)

        # One duplicate within the CSV and one existing DB record.
        self.assertEqual(result.duplicate_rows, 2)

        self.assertEqual(result.inserted_rows, 1)
        self.assertEqual(result.service_count, 1)
        self.assertIsNotNone(result.upload_id)

    async def test_upload_csv_rejects_file_larger_than_5mb(self) -> None:
        oversized_content = (
            b"x" * (MAX_CSV_FILE_SIZE_BYTES + 1)
        )

        with patch(
            "src.services.upload_service.CleaningService.clean_csv"
        ) as mock_clean_csv:

            with self.assertRaises(CSVFileTooLargeError):
                await self.upload_service.upload_csv(
                    oversized_content
                )

        mock_clean_csv.assert_not_called()

        self.session.begin.assert_not_awaited()
        self.session.commit.assert_not_awaited()
        self.session.rollback.assert_not_awaited()

    async def test_upload_csv_accepts_file_exactly_5mb(self) -> None:
        csv_content = b"x" * MAX_CSV_FILE_SIZE_BYTES

        with patch(
            "src.services.upload_service.CleaningService.clean_csv",
            return_value=self.cleaning_result,
        ) as mock_clean_csv:

            await self.upload_service.upload_csv(csv_content)

        mock_clean_csv.assert_called_once()
        self.session.commit.assert_awaited_once()

    async def test_upload_csv_raises_validation_error(self) -> None:
        with patch(
            "src.services.upload_service.CleaningService.clean_csv",
            side_effect=CSVValidationError(
                "Invalid CSV structure."
            ),
        ):

            with self.assertRaises(CSVValidationError):
                await self.upload_service.upload_csv(
                    self.csv_content
                )

        # Cleaning failed before transaction started.
        self.session.begin.assert_not_awaited()
        self.session.commit.assert_not_awaited()
        self.session.rollback.assert_not_awaited()

    async def test_upload_csv_rolls_back_when_log_insertion_fails(
        self,
    ) -> None:
        self.upload_service.monitoring_log_service.insert_monitoring_logs.side_effect = (
            RuntimeError("Database insertion failed.")
        )

        with patch(
            "src.services.upload_service.CleaningService.clean_csv",
            return_value=self.cleaning_result,
        ):

            with self.assertRaises(RuntimeError):
                await self.upload_service.upload_csv(
                    self.csv_content
                )

        self.session.begin.assert_awaited_once()
        self.session.commit.assert_not_awaited()
        self.session.rollback.assert_awaited_once()

    async def test_upload_csv_rolls_back_when_history_retrieval_fails(
        self,
    ) -> None:
        self.upload_service.monitoring_log_service.get_all_monitoring_logs_for_metrics.side_effect = (
            RuntimeError("History retrieval failed.")
        )

        with patch(
            "src.services.upload_service.CleaningService.clean_csv",
            return_value=self.cleaning_result,
        ):

            with self.assertRaises(RuntimeError):
                await self.upload_service.upload_csv(
                    self.csv_content
                )

        self.session.commit.assert_not_awaited()
        self.session.rollback.assert_awaited_once()

    async def test_upload_csv_rolls_back_when_service_metrics_fail(
        self,
    ) -> None:
        self.upload_service.service_metrics_service.calculate_and_save_metrics.side_effect = (
            RuntimeError("Service metrics update failed.")
        )

        with patch(
            "src.services.upload_service.CleaningService.clean_csv",
            return_value=self.cleaning_result,
        ):

            with self.assertRaises(RuntimeError):
                await self.upload_service.upload_csv(
                    self.csv_content
                )

        self.session.commit.assert_not_awaited()
        self.session.rollback.assert_awaited_once()

    async def test_upload_csv_rolls_back_when_overall_metrics_fail(
        self,
    ) -> None:
        self.upload_service.overall_metrics_service.calculate_and_save_metrics.side_effect = (
            RuntimeError("Overall metrics update failed.")
        )

        with patch(
            "src.services.upload_service.CleaningService.clean_csv",
            return_value=self.cleaning_result,
        ):

            with self.assertRaises(RuntimeError):
                await self.upload_service.upload_csv(
                    self.csv_content
                )

        self.session.commit.assert_not_awaited()
        self.session.rollback.assert_awaited_once()

    async def test_upload_csv_rolls_back_when_commit_fails(
        self,
    ) -> None:
        self.session.commit.side_effect = RuntimeError(
            "Database commit failed."
        )

        with patch(
            "src.services.upload_service.CleaningService.clean_csv",
            return_value=self.cleaning_result,
        ):

            with self.assertRaises(RuntimeError):
                await self.upload_service.upload_csv(
                    self.csv_content
                )

        self.session.commit.assert_awaited_once()
        self.session.rollback.assert_awaited_once()


if __name__ == "__main__":
    import unittest
    unittest.main()
