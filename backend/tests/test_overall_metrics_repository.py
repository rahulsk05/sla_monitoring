
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy.ext.asyncio import AsyncSession

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

            # Mock the SQLAlchemy INSERT statement.
            statement = MagicMock()

            # Configure insert().values() to return our statement.
            mock_insert.return_value.values.return_value = statement

            # Mock the excluded fields used during upsert.
            statement.excluded = MagicMock()

            # Configure the upsert operation.
            statement.on_conflict_do_update.return_value = statement

            await self.repository.upsert_overall_metrics(metrics)

            # Verify INSERT construction.
            mock_insert.assert_called_once()

            mock_insert.return_value.values.assert_called_once_with(
                metrics
            )

            # Verify ON CONFLICT DO UPDATE.
            statement.on_conflict_do_update.assert_called_once()

            # Verify database execution.
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
