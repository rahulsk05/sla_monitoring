
import json
from datetime import date
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, MagicMock, patch

from src.handlers.logs_handler import (
    async_lambda_handler,
    parse_logs_filters,
)
from src.models.monitoring_log import MonitoringLog


class TestLogsHandler(IsolatedAsyncioTestCase):

    async def asyncSetUp(self) -> None:
        self.event = {
            "queryStringParameters": None,
            "requestContext": {
                "requestId": "test-request-id",
            },
        }

        self.session = MagicMock()
        self.session_context = MagicMock()
        self.session_context.__aenter__ = AsyncMock(
            return_value=self.session
        )
        self.session_context.__aexit__ = AsyncMock(
            return_value=None
        )

        self.session_factory_patcher = patch(
            "src.handlers.logs_handler.AsyncSessionLocal",
            return_value=self.session_context,
        )
        self.mock_session_factory = self.session_factory_patcher.start()
        self.addCleanup(self.session_factory_patcher.stop)

        self.service_patcher = patch(
            "src.handlers.logs_handler.MonitoringLogService"
        )
        self.mock_service_class = self.service_patcher.start()
        self.addCleanup(self.service_patcher.stop)

        self.service = self.mock_service_class.return_value
        self.service.get_monitoring_logs = AsyncMock()

    @staticmethod
    def create_log() -> MagicMock:
        log = MagicMock(spec=MonitoringLog)
        log.__table__ = MagicMock()
        log.__table__.columns = []
        return log

    # ---------------------------------------------------------
    # QUERY PARAMETER VALIDATION TESTS
    # ---------------------------------------------------------

    def test_parse_logs_filters_with_no_filters(self) -> None:
        result = parse_logs_filters({})

        self.assertEqual(
            result,
            (1, None, None, None, None, None),
        )

    def test_parse_logs_filters_with_single_date(self) -> None:
        result = parse_logs_filters({
            "date": "2026-11-24",
        })

        self.assertEqual(
            result,
            (
                1,
                date(2026, 11, 24),
                None,
                None,
                None,
                None,
            ),
        )

    def test_parse_logs_filters_with_date_range(self) -> None:
        result = parse_logs_filters({
            "start_date": "2026-11-20",
            "end_date": "2026-11-24",
        })

        self.assertEqual(
            result,
            (
                1,
                None,
                date(2026, 11, 20),
                date(2026, 11, 24),
                None,
                None,
            ),
        )

    def test_parse_logs_filters_with_service_and_agent(self) -> None:
        result = parse_logs_filters({
            "page": "2",
            "service_id": "svc-auth",
            "agent": "agent-1",
        })

        self.assertEqual(
            result,
            (2, None, None, None, "svc-auth", "agent-1"),
        )

    def test_parse_logs_filters_with_all_filters(self) -> None:
        result = parse_logs_filters({
            "page": "3",
            "start_date": "2026-11-20",
            "end_date": "2026-11-24",
            "service_id": "svc-auth",
            "agent": "agent-1",
        })

        self.assertEqual(
            result,
            (
                3,
                None,
                date(2026, 11, 20),
                date(2026, 11, 24),
                "svc-auth",
                "agent-1",
            ),
        )

    def test_parse_logs_filters_rejects_invalid_page(self) -> None:
        from src.core.exceptions import ApplicationError

        with self.assertRaises(ApplicationError):
            parse_logs_filters({"page": "abc"})

    def test_parse_logs_filters_rejects_zero_page(self) -> None:
        from src.core.exceptions import ApplicationError

        with self.assertRaises(ApplicationError):
            parse_logs_filters({"page": "0"})

    def test_parse_logs_filters_rejects_invalid_date(self) -> None:
        from src.core.exceptions import ApplicationError

        with self.assertRaises(ApplicationError):
            parse_logs_filters({"date": "24-11-2026"})

    def test_parse_logs_filters_rejects_date_and_range_together(
        self,
    ) -> None:
        from src.core.exceptions import ApplicationError

        with self.assertRaises(ApplicationError):
            parse_logs_filters({
                "date": "2026-11-24",
                "start_date": "2026-11-20",
                "end_date": "2026-11-24",
            })

    def test_parse_logs_filters_rejects_incomplete_date_range(
        self,
    ) -> None:
        from src.core.exceptions import ApplicationError

        with self.assertRaises(ApplicationError):
            parse_logs_filters({
                "start_date": "2026-11-20",
            })

    def test_parse_logs_filters_rejects_invalid_date_range(
        self,
    ) -> None:
        from src.core.exceptions import ApplicationError

        with self.assertRaises(ApplicationError):
            parse_logs_filters({
                "start_date": "2026-11-25",
                "end_date": "2026-11-20",
            })

    def test_parse_logs_filters_rejects_unknown_parameter(
        self,
    ) -> None:
        from src.core.exceptions import ApplicationError

        with self.assertRaises(ApplicationError):
            parse_logs_filters({
                "status_code": "500",
            })

    # ---------------------------------------------------------
    # LAMBDA HANDLER TESTS
    # ---------------------------------------------------------

    async def test_returns_logs_successfully(self) -> None:
        logs = [
            self.create_log(),
            self.create_log(),
        ]

        self.service.get_monitoring_logs.return_value = (
            logs,
            120,
        )

        response = await async_lambda_handler(
            self.event,
            None,
        )

        self.assertEqual(response["statusCode"], 200)

        body = json.loads(response["body"])

        self.assertTrue(body["success"])
        self.assertEqual(body["data"]["logs"], [{}, {}])
        self.assertEqual(
            body["data"]["pagination"],
            {
                "page": 1,
                "page_size": 50,
                "total_records": 120,
                "total_pages": 3,
            },
        )

        self.service.get_monitoring_logs.assert_awaited_once_with(
            page=1,
            date_filter=None,
            start_date=None,
            end_date=None,
            service_id=None,
            agent=None,
        )

    async def test_returns_logs_with_query_filters(self) -> None:
        self.event["queryStringParameters"] = {
            "page": "2",
            "start_date": "2026-11-20",
            "end_date": "2026-11-24",
            "service_id": "svc-auth",
            "agent": "agent-1",
        }

        self.service.get_monitoring_logs.return_value = (
            [],
            0,
        )

        response = await async_lambda_handler(
            self.event,
            None,
        )

        self.assertEqual(response["statusCode"], 200)

        self.service.get_monitoring_logs.assert_awaited_once_with(
            page=2,
            date_filter=None,
            start_date=date(2026, 11, 20),
            end_date=date(2026, 11, 24),
            service_id="svc-auth",
            agent="agent-1",
        )

    async def test_returns_empty_logs(self) -> None:
        self.service.get_monitoring_logs.return_value = (
            [],
            0,
        )

        response = await async_lambda_handler(
            self.event,
            None,
        )

        body = json.loads(response["body"])

        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(body["data"]["logs"], [])
        self.assertEqual(
            body["data"]["pagination"]["total_pages"],
            0,
        )

    async def test_returns_bad_request_for_invalid_query_parameters(
        self,
    ) -> None:
        self.event["queryStringParameters"] = {
            "page": "invalid",
        }

        response = await async_lambda_handler(
            self.event,
            None,
        )

        body = json.loads(response["body"])

        self.assertEqual(response["statusCode"], 400)
        self.assertFalse(body["success"])
        self.assertEqual(
            body["error"]["code"],
            "INVALID_QUERY_PARAMETERS",
        )

        self.service.get_monitoring_logs.assert_not_awaited()
        self.mock_session_factory.assert_not_called()

    async def test_returns_internal_server_error_on_database_error(
        self,
    ) -> None:
        self.service.get_monitoring_logs.side_effect = RuntimeError(
            "Database query failed"
        )

        response = await async_lambda_handler(
            self.event,
            None,
        )

        body = json.loads(response["body"])

        self.assertEqual(response["statusCode"], 500)
        self.assertFalse(body["success"])
        self.assertEqual(
            body["error"]["code"],
            "INTERNAL_SERVER_ERROR",
        )

    async def test_closes_session_after_successful_request(self) -> None:
        self.service.get_monitoring_logs.return_value = ([], 0)

        await async_lambda_handler(self.event, None)

        self.session_context.__aexit__.assert_awaited_once()


if __name__ == "__main__":
    import unittest

    unittest.main()
