import asyncio
import base64
import binascii
import json

from collections.abc import Mapping

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.error_handler import handle_exception
from src.core.exceptions import CSVValidationError
from src.database.connection import AsyncSessionLocal
from src.services.upload_service import UploadService


def get_request_id(
    event: Mapping[str, object],
    context: object,
) -> str:
    """Extract the Lambda or API Gateway request ID."""

    lambda_request_id = getattr(
        context,
        "aws_request_id",
        None,
    )

    if isinstance(lambda_request_id, str) and lambda_request_id:
        return lambda_request_id

    request_context = event.get("requestContext")

    if isinstance(request_context, Mapping):
        request_id = request_context.get("requestId")

        if isinstance(request_id, str) and request_id:
            return request_id

    return "unknown"


def extract_csv_content(
    event: Mapping[str, object],
) -> bytes:
    """Extract and decode CSV content from the API Gateway event."""

    body = event.get("body")

    if not isinstance(body, str):
        raise CSVValidationError(
            "CSV file content is missing or invalid."
        )

    is_base64_encoded = event.get("isBase64Encoded", False)

    if not isinstance(is_base64_encoded, bool):
        raise CSVValidationError(
            "Invalid request body encoding information."
        )

    if is_base64_encoded:
        try:
            return base64.b64decode(
                body,
                validate=True,
            )
        except (binascii.Error, ValueError) as exc:
            raise CSVValidationError(
                "Invalid Base64-encoded CSV content."
            ) from exc

    return body.encode("utf-8")


async def async_lambda_handler(
    event: Mapping[str, object],
    context: object,
) -> dict[str, object]:
    """Handle CSV upload requests asynchronously."""

    request_id = get_request_id(event, context)

    try:
        # Extract and decode CSV content.
        csv_content = extract_csv_content(event)

        # Create a fresh database session for this invocation.
        async with AsyncSessionLocal() as session:

            upload_service = UploadService(session)

            upload_result = await upload_service.upload_csv(
                csv_content
            )

        # Build the successful API response.
        response_data = {
            "upload_id": str(upload_result.upload_id),
            "total_source_rows": upload_result.total_source_rows,
            "accepted_rows": upload_result.accepted_rows,
            "partially_accepted_rows": (
                upload_result.partially_accepted_rows
            ),
            "rejected_rows": upload_result.rejected_rows,
            "duplicate_rows": upload_result.duplicate_rows,
            "inserted_rows": upload_result.inserted_rows,
            "service_count": upload_result.service_count,
        }

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
            },
            "body": json.dumps({
                "success": True,
                "data": response_data,
            }),
        }

    except Exception as exc:
        status_code, error_response = handle_exception(
            exc,
            request_id,
        )

        return {
            "statusCode": status_code,
            "headers": {
                "Content-Type": "application/json",
            },
            "body": json.dumps(error_response),
        }


def lambda_handler(
    event: Mapping[str, object],
    context: object,
) -> dict[str, object]:
    """Synchronous AWS Lambda entry point."""

    return asyncio.run(
        async_lambda_handler(event, context)
    )
