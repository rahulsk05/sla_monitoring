
import base64
import json

from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from src.core.exceptions import CSVValidationError
from src.handlers.upload_handler import (
    async_lambda_handler,
    extract_csv_content,
)
from src.services.upload_service import UploadResult


class TestUploadHandler(IsolatedAsyncioTestCase):

    def setUp(self) -> None:
        self.csv_content = (
            b"service_id,service_name,timestamp,status_code\n"
            b"svc-auth,Authentication,2026-11-24T10:00:00Z,200"
        )

        self.context = MagicMock()
        self.context.aws_request_id = "test-request-id"

        self.event = {
            "body": self.csv_content.decode("utf-8"),
            "isBase64Encoded": False,
        }

        self.upload_result = UploadResult(
            upload_id=uuid4(),
            total_source_rows=10,
            accepted_rows=6,
            partially_accepted_rows=2,
            rejected_rows=1,
            duplicate_rows=1,
            inserted_rows=8,
            service_count=5,
        )

    def create_session_context(self) -> MagicMock:
        """Create a mocked asynchronous database session context."""

        session = MagicMock()

        session_context = MagicMock()
        session_context.__aenter__ = AsyncMock(
            return_value=session
        )
        session_context.__aexit__ = AsyncMock(
            return_value=False
        )

        return session_context

    def test_extract_plain_text_csv(self) -> None:
        csv_content = extract_csv_content(self.event)

        self.assertEqual(csv_content, self.csv_content)

    def test_extract_base64_encoded_csv(self) -> None:
        encoded_content = base64.b64encode(
            self.csv_content
        ).decode("utf-8")

        event = {
            "body": encoded_content,
            "isBase64Encoded": True,
        }

        csv_content = extract_csv_content(event)

        self.assertEqual(csv_content, self.csv_content)

    async def test_missing_request_body(self) -> None:
        event = {
            "body": None,
            "isBase64Encoded": False,
        }

        response = await async_lambda_handler(
            event,
            self.context,
        )

        self.assertEqual(response["statusCode"], 400)

        response_body = json.loads(response["body"])

        self.assertFalse(response_body["success"])
        self.assertEqual(
            response_body["error"]["code"],
            "INVALID_CSV",
        )

    async def test_invalid_base64_content(self) -> None:
        event = {
            "body": "invalid-base64-content!!!",
            "isBase64Encoded": True,
        }

        response = await async_lambda_handler(
            event,
            self.context,
        )

        self.assertEqual(response["statusCode"], 400)

        response_body = json.loads(response["body"])

        self.assertFalse(response_body["success"])
        self.assertEqual(
            response_body["error"]["code"],
            "INVALID_CSV",
        )

    async def test_successful_upload(self) -> None:
        session_context = self.create_session_context()

        with (
            patch(
                "src.handlers.upload_handler.AsyncSessionLocal",
                return_value=session_context,
            ),
            patch(
                "src.handlers.upload_handler.UploadService"
            ) as mock_upload_service,
        ):
            mock_service_instance = mock_upload_service.return_value

            mock_service_instance.upload_csv = AsyncMock(
                return_value=self.upload_result
            )

            response = await async_lambda_handler(
                self.event,
                self.context,
            )

        self.assertEqual(response["statusCode"], 200)

        response_body = json.loads(response["body"])

        self.assertTrue(response_body["success"])

        data = response_body["data"]

        self.assertEqual(
            data["upload_id"],
            str(self.upload_result.upload_id),
        )
        self.assertEqual(data["total_source_rows"], 10)
        self.assertEqual(data["accepted_rows"], 6)
        self.assertEqual(data["partially_accepted_rows"], 2)
        self.assertEqual(data["rejected_rows"], 1)
        self.assertEqual(data["duplicate_rows"], 1)
        self.assertEqual(data["inserted_rows"], 8)
        self.assertEqual(data["service_count"], 5)

        mock_service_instance.upload_csv.assert_awaited_once_with(
            self.csv_content
        )

        session_context.__aenter__.assert_awaited_once()
        session_context.__aexit__.assert_awaited_once()

    async def test_application_exception_response(self) -> None:
        session_context = self.create_session_context()

        with (
            patch(
                "src.handlers.upload_handler.AsyncSessionLocal",
                return_value=session_context,
            ),
            patch(
                "src.handlers.upload_handler.UploadService"
            ) as mock_upload_service,
        ):
            mock_service_instance = mock_upload_service.return_value

            mock_service_instance.upload_csv = AsyncMock(
                side_effect=CSVValidationError(
                    "Invalid CSV structure."
                )
            )

            response = await async_lambda_handler(
                self.event,
                self.context,
            )

        self.assertEqual(response["statusCode"], 400)

        response_body = json.loads(response["body"])

        self.assertFalse(response_body["success"])
        self.assertEqual(
            response_body["error"]["code"],
            "INVALID_CSV",
        )
        self.assertEqual(
            response_body["error"]["message"],
            "Invalid CSV structure.",
        )

    async def test_unexpected_exception_response(self) -> None:
        session_context = self.create_session_context()

        with (
            patch(
                "src.handlers.upload_handler.AsyncSessionLocal",
                return_value=session_context,
            ),
            patch(
                "src.handlers.upload_handler.UploadService"
            ) as mock_upload_service,
        ):
            mock_service_instance = mock_upload_service.return_value

            mock_service_instance.upload_csv = AsyncMock(
                side_effect=RuntimeError(
                    "Database connection failed."
                )
            )

            response = await async_lambda_handler(
                self.event,
                self.context,
            )

        self.assertEqual(response["statusCode"], 500)

        response_body = json.loads(response["body"])

        self.assertFalse(response_body["success"])
        self.assertEqual(
            response_body["error"]["code"],
            "INTERNAL_SERVER_ERROR",
        )
        self.assertEqual(
            response_body["error"]["message"],
            "An unexpected error occurred.",
        )


if __name__ == "__main__":
    import unittest
    unittest.main()
