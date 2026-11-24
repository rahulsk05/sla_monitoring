
from datetime import date
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, MagicMock

from sqlalchemy.ext.asyncio import AsyncSession

from src.models.monitoring_log import MonitoringLog
from src.services.monitoring_log_service import MonitoringLogService


class TestMonitoringLogService(IsolatedAsyncioTestCase):

    def setUp(self) -> None:
        self.session = MagicMock(spec=AsyncSession)
        self.service = MonitoringLogService(self.session)

        self.service.repository = MagicMock()
        self.service.repository.insert_monitoring_logs = AsyncMock()
        self.service.repository.get_all_monitoring_logs_for_metrics = (
            AsyncMock()
        )
        self.service.repository.get_monitoring_logs = AsyncMock()

        self.records = [
            {
                "record_hash": "hash-1",
                "service_id": "service-1",
                "service_name": "Service One",
                "status_code": 200,
            },
            {
                "record_hash": "hash-2",
                "service_id": "service-1",
                "service_name": "Service One",
                "status_code": 500,
            },
        ]

    # ---------------------------------------------------------
    # INSERT TESTS
    # ---------------------------------------------------------

    async def test_insert_monitoring_logs(self) -> None:
        self.service.repository.insert_monitoring_logs.return_value = 2

        inserted_count = await self.service.insert_monitoring_logs(
            self.records
        )

        self.assertEqual(inserted_count, 2)

        self.service.repository.insert_monitoring_logs.assert_awaited_once_with(
            self.records
        )

    async def test_insert_monitoring_logs_with_empty_records(self) -> None:
        self.service.repository.insert_monitoring_logs.return_value = 0

        inserted_count = await self.service.insert_monitoring_logs([])

        self.assertEqual(inserted_count, 0)

        self.service.repository.insert_monitoring_logs.assert_awaited_once_with(
            []
        )

    async def test_insert_monitoring_logs_propagates_repository_error(
        self,
    ) -> None:
        self.service.repository.insert_monitoring_logs.side_effect = (
            RuntimeError("Database insertion failed.")
        )

        with self.assertRaises(RuntimeError):
            await self.service.insert_monitoring_logs(self.records)

        self.service.repository.insert_monitoring_logs.assert_awaited_once_with(
            self.records
        )

    # ---------------------------------------------------------
    # METRICS RETRIEVAL TESTS
    # ---------------------------------------------------------

    async def test_get_all_monitoring_logs_for_metrics(self) -> None:
        expected_records = [
            {
                "record_hash": "hash-1",
                "service_id": "service-1",
                "service_name": "Service One",
                "observed_at": "2026-11-20T10:00:00+00:00",
                "status_code": 200,
                "latency_ms": 150.0,
            }
        ]

        (
            self.service.repository
            .get_all_monitoring_logs_for_metrics
            .return_value
        ) = expected_records

        result = await self.service.get_all_monitoring_logs_for_metrics()

        self.assertEqual(result, expected_records)

        (
            self.service.repository
            .get_all_monitoring_logs_for_metrics
            .assert_awaited_once_with()
        )

    async def test_get_all_monitoring_logs_propagates_repository_error(
        self,
    ) -> None:
        (
            self.service.repository
            .get_all_monitoring_logs_for_metrics
            .side_effect
        ) = RuntimeError("Database retrieval failed.")

        with self.assertRaises(RuntimeError):
            await self.service.get_all_monitoring_logs_for_metrics()

        (
            self.service.repository
            .get_all_monitoring_logs_for_metrics
            .assert_awaited_once_with()
        )

    # ---------------------------------------------------------
    # PAGINATED LOG RETRIEVAL TESTS
    # ---------------------------------------------------------

    async def test_get_monitoring_logs(self) -> None:
        expected_logs = [
            MagicMock(spec=MonitoringLog),
            MagicMock(spec=MonitoringLog),
        ]

        self.service.repository.get_monitoring_logs.return_value = (
            expected_logs,
            120,
        )

        result = await self.service.get_monitoring_logs(page=1)

        self.assertIs(result[0], expected_logs)
        self.assertEqual(result[1], 120)

        self.service.repository.get_monitoring_logs.assert_awaited_once_with(
            page=1,
            date_filter=None,
            start_date=None,
            end_date=None,
            service_id=None,
            agent=None,
        )

    async def test_get_monitoring_logs_with_single_date(self) -> None:
        selected_date = date(2026, 11, 24)

        expected_logs = [MagicMock(spec=MonitoringLog)]

        self.service.repository.get_monitoring_logs.return_value = (
            expected_logs,
            1,
        )

        result = await self.service.get_monitoring_logs(
            page=1,
            date_filter=selected_date,
        )

        self.assertEqual(result, (expected_logs, 1))

        self.service.repository.get_monitoring_logs.assert_awaited_once_with(
            page=1,
            date_filter=selected_date,
            start_date=None,
            end_date=None,
            service_id=None,
            agent=None,
        )

    async def test_get_monitoring_logs_with_date_range(self) -> None:
        start_date = date(2026, 11, 20)
        end_date = date(2026, 11, 24)

        self.service.repository.get_monitoring_logs.return_value = ([], 0)

        result = await self.service.get_monitoring_logs(
            page=1,
            start_date=start_date,
            end_date=end_date,
        )

        self.assertEqual(result, ([], 0))

        self.service.repository.get_monitoring_logs.assert_awaited_once_with(
            page=1,
            date_filter=None,
            start_date=start_date,
            end_date=end_date,
            service_id=None,
            agent=None,
        )

    async def test_get_monitoring_logs_with_service_and_agent_filters(
        self,
    ) -> None:
        expected_logs = [MagicMock(spec=MonitoringLog)]

        self.service.repository.get_monitoring_logs.return_value = (
            expected_logs,
            1,
        )

        result = await self.service.get_monitoring_logs(
            page=2,
            service_id="svc-auth",
            agent="agent-1",
        )

        self.assertEqual(result, (expected_logs, 1))

        self.service.repository.get_monitoring_logs.assert_awaited_once_with(
            page=2,
            date_filter=None,
            start_date=None,
            end_date=None,
            service_id="svc-auth",
            agent="agent-1",
        )

    async def test_get_monitoring_logs_returns_empty_result(self) -> None:
        self.service.repository.get_monitoring_logs.return_value = ([], 0)

        result = await self.service.get_monitoring_logs(page=1)

        self.assertEqual(result, ([], 0))

    async def test_get_monitoring_logs_propagates_repository_error(
        self,
    ) -> None:
        self.service.repository.get_monitoring_logs.side_effect = (
            RuntimeError("Database retrieval failed.")
        )

        with self.assertRaisesRegex(
            RuntimeError,
            "Database retrieval failed.",
        ):
            await self.service.get_monitoring_logs(page=1)

        self.service.repository.get_monitoring_logs.assert_awaited_once_with(
            page=1,
            date_filter=None,
            start_date=None,
            end_date=None,
            service_id=None,
            agent=None,
        )


if __name__ == "__main__":
    import unittest

    unittest.main()
