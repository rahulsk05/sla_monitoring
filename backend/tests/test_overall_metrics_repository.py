from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy.ext.asyncio import AsyncSession

from src.models.overall_metric import OverallMetric
from src.repositories.overall_metrics_repository import (
    OverallMetricRepository,
)


class TestOverallMetricRepository(IsolatedAsyncioTestCase):

    async def asyncSetUp(self) -> None:
        self.session = AsyncMock(spec=AsyncSession)
        self.repository = OverallMetricRepository(self.session)

    async def test_upsert_executes_statement(self) -> None:
        metrics = {
            "id": 1,
            "total_checks": 1000,
            "availability_eligible_checks": 990,
            "successful_checks": 980,
            "failed_checks": 10,
            "availability_percentage": 98.990,
            "services_below_sla": 2,
            "total_failure_events": 5,
            "longest_failure_duration_seconds": 120,
            "sla_threshold_percentage": 99.900,
            "calculated_at": None,
            "updated_at": None,
        }

        with patch(
            "src.repositories.overall_metrics_repository.insert"
        ) as mock_insert:

            statement = MagicMock()
            mock_insert.return_value.values.return_value = statement

            statement.excluded = MagicMock()
            statement.on_conflict_do_update.return_value = statement

            await self.repository.upsert_overall_metrics(metrics)

            mock_insert.assert_called_once()
            mock_insert.return_value.values.assert_called_once_with(
                metrics
            )
            statement.on_conflict_do_update.assert_called_once()

            self.session.execute.assert_awaited_once_with(statement)

    async def test_upsert_propagates_database_error(self) -> None:
        self.session.execute.side_effect = RuntimeError(
            "Database write failed"
        )

        with self.assertRaisesRegex(
            RuntimeError,
            "Database write failed",
        ):
            await self.repository.upsert_overall_metrics({"id": 1})

        self.session.execute.assert_awaited_once()

    async def test_get_overall_metrics_returns_record(self) -> None:
        expected_metrics = MagicMock(spec=OverallMetric)

        result = MagicMock()
        result.scalar_one_or_none.return_value = expected_metrics

        self.session.execute.return_value = result

        metrics = await self.repository.get_overall_metrics()

        self.assertIs(metrics, expected_metrics)
        self.session.execute.assert_awaited_once()

    async def test_get_overall_metrics_returns_none_when_not_found(
        self,
    ) -> None:
        result = MagicMock()
        result.scalar_one_or_none.return_value = None

        self.session.execute.return_value = result

        metrics = await self.repository.get_overall_metrics()

        self.assertIsNone(metrics)
        self.session.execute.assert_awaited_once()

    async def test_get_overall_metrics_propagates_database_error(
        self,
    ) -> None:
        self.session.execute.side_effect = RuntimeError(
            "Database query failed"
        )

        with self.assertRaisesRegex(
            RuntimeError,
            "Database query failed",
        ):
            await self.repository.get_overall_metrics()

        self.session.execute.assert_awaited_once()


if __name__ == "__main__":
    import unittest
    unittest.main()
