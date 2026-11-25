import asyncio
import uuid

from flask import Request, jsonify

from src.core.constants import FILE_FIELD_NAME
from src.core.error_handler import handle_exception
from src.core.exceptions import CSVValidationError
from src.database.connection import AsyncSessionLocal
from src.services.upload_service import UploadService


def upload_csv(request: Request):
    """Handle CSV uploads through Google Cloud Functions."""

    request_id = uuid.uuid4().hex

    try:
        if request.method != "POST":
            response, status_code = handle_method_not_allowed()
            return response, status_code

        uploaded_file = request.files.get(FILE_FIELD_NAME)

        if uploaded_file is None:
            raise CSVValidationError(
                "CSV file is missing. Upload a file using the 'file' field."
            )

        csv_content = uploaded_file.read()

        if not csv_content:
            raise CSVValidationError(
                "Uploaded CSV file is empty."
            )

        async def process_upload():
            async with AsyncSessionLocal() as session:
                upload_service = UploadService(session)

                return await upload_service.upload_csv(
                    csv_content
                )

        upload_result = asyncio.run(process_upload())

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

        return jsonify({
            "success": True,
            "data": response_data,
        }), 200

    except Exception as exception:
        status_code, error_response = handle_exception(
            exception,
            request_id,
        )

        return jsonify(error_response), status_code


def handle_method_not_allowed():
    """Return a consistent response for unsupported HTTP methods."""

    response = jsonify({
        "success": False,
        "error": {
            "code": "METHOD_NOT_ALLOWED",
            "message": "Only POST requests are allowed.",
        },
    })

    response.headers["Allow"] = "POST"

    return response, 405
