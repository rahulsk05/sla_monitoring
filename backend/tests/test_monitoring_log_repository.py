
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy.ext.asyncio import AsyncSession

from src.models.monitoring_log import MonitoringLog
from src.repositories.monitoring_log_repository import (
    MonitoringLogRepository,
)


class TestMonitoringLogRepository(IsolatedAsyncioTestCase):

    async def asyncSetUp(self) -> None:
        self.session = AsyncMock(spec=AsyncSession)
        self.repository = MonitoringLogRepository(self.session)

    @staticmethod
    def create_record(record_id: int) -> dict[str, object]:
        return {
            "record_hash": f"hash-{record_id}",
            "service_id": "svc-auth",
            "service_name": "Auth Service",
            "observed_at": "2026-11-01T10:00:00Z",
            "status_code": 200,
            "latency_ms": 125.500,
            "agent": "agent-1",
            "region": "ap-south-1",
            "upload_id": "test-upload-id",
        }

    # ---------------------------------------------------------
    # INSERT TESTS
    # ---------------------------------------------------------

    async def test_insert_monitoring_logs(self) -> None:
        records = [
            self.create_record(1),
            self.create_record(2),
        ]

        result = MagicMock()
        result.rowcount = 2
        self.session.execute.return_value = result

        with patch(
            "src.repositories.monitoring_log_repository.insert"
        ) as mock_insert:
            statement = MagicMock()
            mock_insert.return_value.values.return_value = statement
            statement.on_conflict_do_nothing.return_value = statement

            inserted_count = await self.repository.insert_monitoring_logs(
                records
            )

            self.assertEqual(inserted_count, 2)

            mock_insert.assert_called_once_with(MonitoringLog)
            mock_insert.return_value.values.assert_called_once_with(
                records
            )
            statement.on_conflict_do_nothing.assert_called_once()

            self.session.execute.assert_awaited_once_with(statement)

    async def test_insert_monitoring_logs_with_empty_list(self) -> None:
        inserted_count = await self.repository.insert_monitoring_logs([])

        self.assertEqual(inserted_count, 0)
        self.session.execute.assert_not_awaited()

    async def test_insert_monitoring_logs_skips_existing_duplicates(
        self,
    ) -> None:
        records = [
            self.create_record(1),
            self.create_record(2),
            self.create_record(3),
        ]

        result = MagicMock()
        result.rowcount = 2
        self.session.execute.return_value = result

        with patch(
            "src.repositories.monitoring_log_repository.insert"
        ) as mock_insert:
            statement = MagicMock()
            mock_insert.return_value.values.return_value = statement
            statement.on_conflict_do_nothing.return_value = statement

            inserted_count = await self.repository.insert_monitoring_logs(
                records
            )

            self.assertEqual(inserted_count, 2)
            self.assertEqual(len(records) - inserted_count, 1)

            mock_insert.assert_called_once_with(MonitoringLog)
            self.session.execute.assert_awaited_once_with(statement)

    async def test_insert_monitoring_logs_uses_batches(self) -> None:
        records = [
            self.create_record(index)
            for index in range(5)
        ]

        results = [
            MagicMock(rowcount=2),
            MagicMock(rowcount=2),
            MagicMock(rowcount=1),
        ]

        self.session.execute.side_effect = results

        with (
            patch(
                "src.repositories.monitoring_log_repository.insert"
            ) as mock_insert,
            patch(
                "src.repositories.monitoring_log_repository.UPLOAD_CHUNK_INSERT_SIZE",
                2,
            ),
        ):
            statement = MagicMock()
            mock_insert.return_value.values.return_value = statement
            statement.on_conflict_do_nothing.return_value = statement

            inserted_count = await self.repository.insert_monitoring_logs(
                records
            )

            self.assertEqual(inserted_count, 5)
            self.assertEqual(mock_insert.call_count, 3)
            self.assertEqual(mock_insert.return_value.values.call_count, 3)
            self.assertEqual(self.session.execute.await_count, 3)

    async def test_insert_monitoring_logs_propagates_database_error(
        self,
    ) -> None:
        self.session.execute.side_effect = RuntimeError(
            "Database write failed"
        )

        with self.assertRaisesRegex(
            RuntimeError,
            "Database write failed",
        ):
            await self.repository.insert_monitoring_logs(
                [self.create_record(1)]
            )

        self.session.execute.assert_awaited_once()

    # ---------------------------------------------------------
    # GET TESTS
    # ---------------------------------------------------------

    async def test_get_all_monitoring_logs_for_metrics_returns_records(
        self,
    ) -> None:
        expected_records = [
            {
                "record_hash": "hash-001",
                "service_id": "svc-auth",
                "service_name": "Auth Service",
                "observed_at": "2026-11-01T10:00:00Z",
                "status_code": 200,
                "latency_ms": 125.500,
            },
            {
                "record_hash": "hash-002",
                "service_id": "svc-payments",
                "service_name": "Payments Service",
                "observed_at": "2026-11-01T10:05:00Z",
                "status_code": 500,
                "latency_ms": 250.000,
            },
        ]

        mappings_result = MagicMock()
        mappings_result.all.return_value = expected_records

        query_result = MagicMock()
        query_result.mappings.return_value = mappings_result

        self.session.execute.return_value = query_result

        records = await (
            self.repository.get_all_monitoring_logs_for_metrics()
        )

        self.assertEqual(records, expected_records)
        self.assertEqual(len(records), 2)

        self.session.execute.assert_awaited_once()

    async def test_get_all_monitoring_logs_for_metrics_returns_empty_list(
        self,
    ) -> None:
        mappings_result = MagicMock()
        mappings_result.all.return_value = []

        query_result = MagicMock()
        query_result.mappings.return_value = mappings_result

        self.session.execute.return_value = query_result

        records = await (
            self.repository.get_all_monitoring_logs_for_metrics()
        )

        self.assertEqual(records, [])
        self.session.execute.assert_awaited_once()

    async def test_get_all_monitoring_logs_for_metrics_propagates_error(
        self,
    ) -> None:
        self.session.execute.side_effect = RuntimeError(
            "Database query failed"
        )

        with self.assertRaisesRegex(
            RuntimeError,
            "Database query failed",
        ):
            await self.repository.get_all_monitoring_logs_for_metrics()

        self.session.execute.assert_awaited_once()
