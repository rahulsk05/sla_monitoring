
from datetime import date, datetime, time, timedelta, timezone
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.constants import LOGS_PAGE_SIZE
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

    def configure_paginated_query(
        self,
        records: list[MonitoringLog],
        total_records: int,
    ) -> None:
        count_result = MagicMock()
        count_result.scalar_one.return_value = total_records

        logs_result = MagicMock()
        logs_result.scalars.return_value.all.return_value = records

        self.session.execute.side_effect = [
            count_result,
            logs_result,
        ]

    def get_compiled_query(self, execution_index: int) -> tuple[str, dict[str, object]]:
        statement = self.session.execute.await_args_list[
            execution_index
        ].args[0]

        compiled_statement = statement.compile(
            dialect=postgresql.dialect()
        )

        return str(compiled_statement), compiled_statement.params

    # ---------------------------------------------------------
    # INSERT TESTS
    # ---------------------------------------------------------

    async def test_insert_monitoring_logs(self) -> None:
        records = [
            self.create_record(1),
            self.create_record(2),
        ]

        result = MagicMock()
        result.scalars.return_value.all.return_value = [
            "hash-1",
            "hash-2",
        ]
        self.session.execute.return_value = result

        with patch(
            "src.repositories.monitoring_log_repository.insert"
        ) as mock_insert:
            statement = MagicMock()
            mock_insert.return_value.values.return_value = statement
            statement.on_conflict_do_nothing.return_value = statement
            statement.returning.return_value = statement

            inserted_count = await self.repository.insert_monitoring_logs(
                records
            )

            self.assertEqual(inserted_count, 2)

            mock_insert.assert_called_once_with(MonitoringLog)
            mock_insert.return_value.values.assert_called_once_with(records)
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
        result.scalars.return_value.all.return_value = [
            "hash-1",
            "hash-2",
        ]
        self.session.execute.return_value = result

        with patch(
            "src.repositories.monitoring_log_repository.insert"
        ) as mock_insert:
            statement = MagicMock()
            mock_insert.return_value.values.return_value = statement
            statement.on_conflict_do_nothing.return_value = statement
            statement.returning.return_value = statement

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
            MagicMock(),
            MagicMock(),
            MagicMock(),
        ]

        results[0].scalars.return_value.all.return_value = [
            "hash-0",
            "hash-1",
        ]
        results[1].scalars.return_value.all.return_value = [
            "hash-2",
            "hash-3",
        ]
        results[2].scalars.return_value.all.return_value = [
            "hash-4",
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
            statement.returning.return_value = statement

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
    # METRICS RETRIEVAL TESTS
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

    # ---------------------------------------------------------
    # PAGINATED LOG RETRIEVAL TESTS
    # ---------------------------------------------------------

    async def test_get_monitoring_logs_returns_first_page(self) -> None:
        expected_logs = [
            MagicMock(spec=MonitoringLog)
            for _ in range(LOGS_PAGE_SIZE)
        ]

        self.configure_paginated_query(
            records=expected_logs,
            total_records=120,
        )

        logs, total_records = await self.repository.get_monitoring_logs(
            page=1,
        )

        self.assertEqual(logs, expected_logs)
        self.assertEqual(total_records, 120)
        self.assertEqual(len(logs), LOGS_PAGE_SIZE)
        self.assertEqual(self.session.execute.await_count, 2)

        query, params = self.get_compiled_query(1)

        self.assertIn("LIMIT", query.upper())
        self.assertIn("OFFSET", query.upper())
        self.assertIn(LOGS_PAGE_SIZE, params.values())
        self.assertIn(0, params.values())

    async def test_get_monitoring_logs_applies_second_page_offset(
        self,
    ) -> None:
        expected_logs = [
            MagicMock(spec=MonitoringLog)
            for _ in range(LOGS_PAGE_SIZE)
        ]

        self.configure_paginated_query(
            records=expected_logs,
            total_records=120,
        )

        logs, total_records = await self.repository.get_monitoring_logs(
            page=2,
        )

        self.assertEqual(logs, expected_logs)
        self.assertEqual(total_records, 120)

        query, params = self.get_compiled_query(1)

        self.assertIn("LIMIT", query.upper())
        self.assertIn("OFFSET", query.upper())
        self.assertIn(LOGS_PAGE_SIZE, params.values())

    async def test_get_monitoring_logs_filters_by_single_date(
        self,
    ) -> None:
        selected_date = date(2026, 11, 24)

        self.configure_paginated_query(
            records=[],
            total_records=0,
        )

        logs, total_records = await self.repository.get_monitoring_logs(
            page=1,
            date_filter=selected_date,
        )

        self.assertEqual(logs, [])
        self.assertEqual(total_records, 0)

        query, params = self.get_compiled_query(0)

        expected_start = datetime.combine(
            selected_date,
            time.min,
            tzinfo=timezone.utc,
        )
        expected_end = expected_start + timedelta(days=1)

        self.assertIn("observed_at >=", query)
        self.assertIn("observed_at <", query)
        self.assertIn(expected_start, params.values())
        self.assertIn(expected_end, params.values())

    async def test_get_monitoring_logs_filters_by_date_range(
        self,
    ) -> None:
        start_date = date(2026, 11, 20)
        end_date = date(2026, 11, 24)

        self.configure_paginated_query(
            records=[],
            total_records=0,
        )

        await self.repository.get_monitoring_logs(
            page=1,
            start_date=start_date,
            end_date=end_date,
        )

        query, params = self.get_compiled_query(0)

        expected_start = datetime.combine(
            start_date,
            time.min,
            tzinfo=timezone.utc,
        )
        expected_end = datetime.combine(
            end_date + timedelta(days=1),
            time.min,
            tzinfo=timezone.utc,
        )

        self.assertIn("observed_at >=", query)
        self.assertIn("observed_at <", query)
        self.assertIn(expected_start, params.values())
        self.assertIn(expected_end, params.values())

    async def test_get_monitoring_logs_filters_by_service_id(
        self,
    ) -> None:
        self.configure_paginated_query(
            records=[],
            total_records=0,
        )

        await self.repository.get_monitoring_logs(
            page=1,
            service_id="svc-auth",
        )

        query, params = self.get_compiled_query(0)

        self.assertIn("service_id", query)
        self.assertIn("svc-auth", params.values())

    async def test_get_monitoring_logs_filters_by_agent(
        self,
    ) -> None:
        self.configure_paginated_query(
            records=[],
            total_records=0,
        )

        await self.repository.get_monitoring_logs(
            page=1,
            agent="agent-1",
        )

        query, params = self.get_compiled_query(0)

        self.assertIn("agent", query)
        self.assertIn("agent-1", params.values())

    async def test_get_monitoring_logs_combines_all_filters(
        self,
    ) -> None:
        selected_date = date(2026, 11, 24)

        self.configure_paginated_query(
            records=[],
            total_records=0,
        )

        await self.repository.get_monitoring_logs(
            page=1,
            date_filter=selected_date,
            service_id="svc-auth",
            agent="agent-1",
        )

        query, params = self.get_compiled_query(0)

        self.assertIn("observed_at >=", query)
        self.assertIn("observed_at <", query)
        self.assertIn("service_id", query)
        self.assertIn("agent", query)

        self.assertIn("svc-auth", params.values())
        self.assertIn("agent-1", params.values())

    async def test_get_monitoring_logs_without_filters_returns_all_paginated(
        self,
    ) -> None:
        expected_logs = [
            MagicMock(spec=MonitoringLog)
            for _ in range(10)
        ]

        self.configure_paginated_query(
            records=expected_logs,
            total_records=10,
        )

        logs, total_records = await self.repository.get_monitoring_logs(
            page=1,
        )

        self.assertEqual(logs, expected_logs)
        self.assertEqual(total_records, 10)

        count_query, _ = self.get_compiled_query(0)
        logs_query, _ = self.get_compiled_query(1)

        self.assertNotIn("WHERE", count_query.upper())
        self.assertNotIn("WHERE", logs_query.upper())
        self.assertIn("LIMIT", logs_query.upper())
        self.assertIn("OFFSET", logs_query.upper())

    async def test_get_monitoring_logs_returns_empty_results(
        self,
    ) -> None:
        self.configure_paginated_query(
            records=[],
            total_records=0,
        )

        logs, total_records = await self.repository.get_monitoring_logs(
            page=1,
            service_id="unknown-service",
        )

        self.assertEqual(logs, [])
        self.assertEqual(total_records, 0)

    async def test_get_monitoring_logs_orders_by_observed_at_and_id(
        self,
    ) -> None:
        self.configure_paginated_query(
            records=[],
            total_records=0,
        )

        await self.repository.get_monitoring_logs(page=1)

        query, _ = self.get_compiled_query(1)

        self.assertIn("ORDER BY", query.upper())
        self.assertIn("observed_at DESC", query)
        self.assertIn("id DESC", query)

    async def test_get_monitoring_logs_propagates_database_error(
        self,
    ) -> None:
        self.session.execute.side_effect = RuntimeError(
            "Database query failed"
        )

        with self.assertRaisesRegex(
            RuntimeError,
            "Database query failed",
        ):
            await self.repository.get_monitoring_logs(page=1)

        self.session.execute.assert_awaited_once()


if __name__ == "__main__":
    import unittest

    unittest.main()
