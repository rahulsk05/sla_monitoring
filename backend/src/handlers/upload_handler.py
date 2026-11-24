
import asyncio
import base64
import binascii
import json

from collections.abc import Mapping
from email import policy
from email.parser import BytesParser

from src.core.constants import FILE_FIELD_NAME, MAX_CSV_FILE_SIZE_BYTES
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


def get_content_type(
    event: Mapping[str, object],
) -> str:
    """Extract the Content-Type header from the API Gateway event."""

    headers = event.get("headers")

    if not isinstance(headers, Mapping):
        return ""

    for key, value in headers.items():
        if (
            isinstance(key, str)
            and key.lower() == "content-type"
            and isinstance(value, str)
        ):
            return value

    return ""


def decode_request_body(
    event: Mapping[str, object],
) -> bytes:
    """Decode the API Gateway request body."""

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
                "Invalid Base64-encoded request body."
            ) from exc

    return body.encode("utf-8")


def extract_multipart_file(
    request_body: bytes,
    content_type: str,
) -> bytes:
    """Extract the CSV file from a multipart/form-data request."""

    if "\r" in content_type or "\n" in content_type:
        raise CSVValidationError(
            "Invalid multipart Content-Type header."
        )

    message_bytes = (
        f"Content-Type: {content_type}\r\n"
        "MIME-Version: 1.0\r\n"
        "\r\n"
    ).encode("ascii") + request_body

    message = BytesParser(
        policy=policy.default,
    ).parsebytes(message_bytes)

    if not message.is_multipart():
        raise CSVValidationError(
            "Invalid multipart file upload request."
        )

    uploaded_files: list[bytes] = []

    for part in message.iter_parts():
        field_name = part.get_param(
            "name",
            header="content-disposition",
        )

        if field_name != FILE_FIELD_NAME:
            continue

        filename = part.get_filename()

        if not filename:
            raise CSVValidationError(
                "Uploaded CSV file is missing a filename."
            )

        file_content = part.get_payload(decode=True)

        if not isinstance(file_content, bytes):
            raise CSVValidationError(
                "Unable to read the uploaded CSV file."
            )

        uploaded_files.append(file_content)

    if len(uploaded_files) != 1:
        raise CSVValidationError(
            "Exactly one CSV file must be uploaded using the 'file' field."
        )

    return uploaded_files[0]


def extract_csv_content(
    event: Mapping[str, object],
) -> bytes:
    """Extract CSV content from raw or multipart API Gateway requests."""

    request_body = decode_request_body(event)
    content_type = get_content_type(event)

    if content_type.lower().startswith("multipart/form-data"):
        csv_content = extract_multipart_file(
            request_body,
            content_type,
        )
    else:
        # Preserve support for raw CSV requests.
        csv_content = request_body

    if not csv_content:
        raise CSVValidationError(
            "Uploaded CSV file is empty."
        )

    if len(csv_content) > MAX_CSV_FILE_SIZE_BYTES:
        raise CSVValidationError(
            "CSV file size must not exceed 5 MB."
        )

    return csv_content


async def async_lambda_handler(
    event: Mapping[str, object],
    context: object,
) -> dict[str, object]:
    """Handle CSV upload requests asynchronously."""

    request_id = get_request_id(event, context)

    try:
        # Extract and validate the uploaded CSV content.
        csv_content = extract_csv_content(event)

        # Create a fresh database session for this invocation.
        async with AsyncSessionLocal() as session:

            upload_service = UploadService(session)

            upload_result = await upload_service.upload_csv(
                csv_content
            )

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
