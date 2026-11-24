import json
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, MagicMock, patch

from src.handlers.metrics_handler import async_lambda_handler
from src.models.overall_metric import OverallMetric
from src.models.service_metric import ServiceMetric


class TestMetricsHandler(IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.event = {
            "requestContext": {
                "requestId": "test-request-id",
            },
        }
        self.context = None

        self.session = MagicMock()
        self.session_context = MagicMock()
        self.session_context.__aenter__ = AsyncMock(
            return_value=self.session
        )
        self.session_context.__aexit__ = AsyncMock(
            return_value=None
        )

        self.session_factory_patcher = patch(
            "src.handlers.metrics_handler.AsyncSessionLocal",
            return_value=self.session_context,
        )
        self.mock_session_factory = self.session_factory_patcher.start()
        self.addCleanup(self.session_factory_patcher.stop)

    @patch("src.handlers.metrics_handler.MetricsService")
    @patch("src.handlers.metrics_handler.ServiceMetricsService")
    @patch("src.handlers.metrics_handler.OverallMetricsService")
    async def test_returns_dashboard_metrics_successfully(
        self,
        mock_overall_service: MagicMock,
        mock_service_service: MagicMock,
        mock_metrics_service: MagicMock,
    ) -> None:
        overall_metrics = MagicMock(spec=OverallMetric)
        service_metric = MagicMock(spec=ServiceMetric)

        overall_metrics.__table__ = MagicMock()
        service_metric.__table__ = MagicMock()

        overall_metrics.__table__.columns = []
        service_metric.__table__.columns = []

        metrics_service_instance = mock_metrics_service.return_value
        metrics_service_instance.get_dashboard_metrics = AsyncMock(
            return_value=(overall_metrics, [service_metric])
        )

        response = await async_lambda_handler(
            self.event,
            self.context,
        )

        self.assertEqual(response["statusCode"], 200)

        body = json.loads(response["body"])
        self.assertTrue(body["success"])
        self.assertEqual(body["data"]["overall"], {})
        self.assertEqual(body["data"]["services"], [{}])

        self.mock_session_factory.assert_called_once()
        metrics_service_instance.get_dashboard_metrics.assert_awaited_once()

    @patch("src.handlers.metrics_handler.MetricsService")
    @patch("src.handlers.metrics_handler.ServiceMetricsService")
    @patch("src.handlers.metrics_handler.OverallMetricsService")
    async def test_returns_null_when_overall_metrics_not_found(
        self,
        mock_overall_service: MagicMock,
        mock_service_service: MagicMock,
        mock_metrics_service: MagicMock,
    ) -> None:
        metrics_service_instance = mock_metrics_service.return_value
        metrics_service_instance.get_dashboard_metrics = AsyncMock(
            return_value=(None, [])
        )

        response = await async_lambda_handler(
            self.event,
            self.context,
        )

        body = json.loads(response["body"])

        self.assertEqual(response["statusCode"], 200)
        self.assertIsNone(body["data"]["overall"])
        self.assertEqual(body["data"]["services"], [])

    @patch("src.handlers.metrics_handler.MetricsService")
    @patch("src.handlers.metrics_handler.ServiceMetricsService")
    @patch("src.handlers.metrics_handler.OverallMetricsService")
    async def test_returns_internal_server_error_on_unexpected_error(
        self,
        mock_overall_service: MagicMock,
        mock_service_service: MagicMock,
        mock_metrics_service: MagicMock,
    ) -> None:
        metrics_service_instance = mock_metrics_service.return_value
        metrics_service_instance.get_dashboard_metrics = AsyncMock(
            side_effect=RuntimeError("Database error")
        )

        response = await async_lambda_handler(
            self.event,
            self.context,
        )

        body = json.loads(response["body"])

        self.assertEqual(response["statusCode"], 500)
        self.assertFalse(body["success"])
        self.assertEqual(
            body["error"]["code"],
            "INTERNAL_SERVER_ERROR",
        )

    @patch("src.handlers.metrics_handler.MetricsService")
    @patch("src.handlers.metrics_handler.ServiceMetricsService")
    @patch("src.handlers.metrics_handler.OverallMetricsService")
    async def test_closes_session_after_successful_request(
        self,
        mock_overall_service: MagicMock,
        mock_service_service: MagicMock,
        mock_metrics_service: MagicMock,
    ) -> None:
        metrics_service_instance = mock_metrics_service.return_value
        metrics_service_instance.get_dashboard_metrics = AsyncMock(
            return_value=(None, [])
        )

        await async_lambda_handler(self.event, self.context)

        self.session_context.__aexit__.assert_awaited_once()


if __name__ == "__main__":
    import unittest

    unittest.main()
