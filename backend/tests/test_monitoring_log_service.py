
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, MagicMock

from sqlalchemy.ext.asyncio import AsyncSession

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


if __name__ == "__main__":
    import unittest
    unittest.main()
