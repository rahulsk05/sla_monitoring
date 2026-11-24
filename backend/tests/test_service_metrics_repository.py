
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy.ext.asyncio import AsyncSession

from src.models.service_metric import ServiceMetric
from src.repositories.service_metrics_repository import (
    ServiceMetricRepository,
)


class TestServiceMetricRepository(IsolatedAsyncioTestCase):

    async def asyncSetUp(self) -> None:
        self.session = AsyncMock(spec=AsyncSession)
        self.repository = ServiceMetricRepository(self.session)

    
    async def test_upsert_service_metrics(self) -> None:
        metrics = [
            {
                "service_id": "svc-auth",
                "service_name": "Auth Service",
                "total_checks": 100,
                "availability_eligible_checks": 100,
                "successful_checks": 99,
                "failed_checks": 1,
                "availability_percentage": 99.000,
                "average_latency_ms": 120.000,
                "p95_latency_ms": 180.000,
                "latency_sample_count": 99,
                "failure_events": 1,
                "longest_failure_duration_seconds": 60,
                "meets_sla": False,
                "calculated_at": None,
                "updated_at": None,
            }
        ]

        with patch(
            "src.repositories.service_metrics_repository.insert"
        ) as mock_insert:

            # Mock SQLAlchemy statement.
            statement = MagicMock()

            # insert().values() returns the statement.
            mock_insert.return_value.values.return_value = statement

            statement.excluded = MagicMock()
            statement.on_conflict_do_update.return_value = statement

            await self.repository.upsert_service_metrics(metrics)

            mock_insert.assert_called_once()

            mock_insert.return_value.values.assert_called_once_with(
                metrics
            )

            statement.on_conflict_do_update.assert_called_once()

            self.session.execute.assert_awaited_once_with(statement)


    async def test_upsert_service_metrics_with_multiple_services(
        self,
    ) -> None:
        metrics = [
            {"service_id": "svc-auth"},
            {"service_id": "svc-payments"},
        ]

        with patch(
            "src.repositories.service_metrics_repository.insert"
        ) as mock_insert:
            statement = mock_insert.return_value
            statement.excluded = AsyncMock()
            statement.on_conflict_do_update.return_value = statement

            await self.repository.upsert_service_metrics(metrics)

            self.assertEqual(mock_insert.call_args.args[0], ServiceMetric)
            self.assertEqual(
                len(mock_insert.return_value.values.call_args.args[0]),
                2,
            )
            self.session.execute.assert_awaited_once()

    async def test_upsert_service_metrics_with_empty_list(self) -> None:
        await self.repository.upsert_service_metrics([])

        self.session.execute.assert_not_awaited()

    async def test_upsert_service_metrics_propagates_database_error(
        self,
    ) -> None:
        self.session.execute.side_effect = RuntimeError(
            "Database write failed"
        )

        with self.assertRaisesRegex(
            RuntimeError,
            "Database write failed",
        ):
            await self.repository.upsert_service_metrics(
                [{"service_id": "svc-auth"}]
            )

        self.session.execute.assert_awaited_once()
