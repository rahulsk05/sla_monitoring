from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, MagicMock

from src.models.overall_metric import OverallMetric
from src.models.service_metric import ServiceMetric
from src.services.metrics_service import MetricsService
from src.services.overall_metrics_service import OverallMetricsService
from src.services.service_metrics_service import ServiceMetricsService


class TestMetricsService(IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.overall_metrics_service = MagicMock(
            spec=OverallMetricsService
        )
        self.service_metrics_service = MagicMock(
            spec=ServiceMetricsService
        )

        self.overall_metrics_service.get_overall_metrics = AsyncMock()
        self.service_metrics_service.get_all_service_metrics = AsyncMock()

        self.metrics_service = MetricsService(
            overall_metrics_service=self.overall_metrics_service,
            service_metrics_service=self.service_metrics_service,
        )

    async def test_get_dashboard_metrics_returns_both_metric_results(
        self,
    ) -> None:
        overall_metrics = MagicMock(spec=OverallMetric)
        service_metrics = [
            MagicMock(spec=ServiceMetric),
            MagicMock(spec=ServiceMetric),
        ]

        self.overall_metrics_service.get_overall_metrics.return_value = (
            overall_metrics
        )
        self.service_metrics_service.get_all_service_metrics.return_value = (
            service_metrics
        )

        result = await self.metrics_service.get_dashboard_metrics()

        self.assertEqual(result, (overall_metrics, service_metrics))
        self.overall_metrics_service.get_overall_metrics.assert_awaited_once()
        self.service_metrics_service.get_all_service_metrics.assert_awaited_once()

    async def test_get_dashboard_metrics_when_overall_metrics_not_found(
        self,
    ) -> None:
        service_metrics = [MagicMock(spec=ServiceMetric)]

        self.overall_metrics_service.get_overall_metrics.return_value = None
        self.service_metrics_service.get_all_service_metrics.return_value = (
            service_metrics
        )

        result = await self.metrics_service.get_dashboard_metrics()

        self.assertEqual(result, (None, service_metrics))

    async def test_get_dashboard_metrics_when_no_service_metrics_exist(
        self,
    ) -> None:
        overall_metrics = MagicMock(spec=OverallMetric)

        self.overall_metrics_service.get_overall_metrics.return_value = (
            overall_metrics
        )
        self.service_metrics_service.get_all_service_metrics.return_value = []

        result = await self.metrics_service.get_dashboard_metrics()

        self.assertEqual(result, (overall_metrics, []))

    async def test_get_dashboard_metrics_propagates_overall_metrics_error(
        self,
    ) -> None:
        self.overall_metrics_service.get_overall_metrics.side_effect = (
            RuntimeError("Database error")
        )

        with self.assertRaisesRegex(RuntimeError, "Database error"):
            await self.metrics_service.get_dashboard_metrics()

        self.service_metrics_service.get_all_service_metrics.assert_not_awaited()

    async def test_get_dashboard_metrics_propagates_service_metrics_error(
        self,
    ) -> None:
        self.overall_metrics_service.get_overall_metrics.return_value = None
        self.service_metrics_service.get_all_service_metrics.side_effect = (
            RuntimeError("Database error")
        )

        with self.assertRaisesRegex(RuntimeError, "Database error"):
            await self.metrics_service.get_dashboard_metrics()


if __name__ == "__main__":
    import unittest

    unittest.main()
