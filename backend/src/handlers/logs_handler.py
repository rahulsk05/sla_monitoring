import asyncio
import json
import math
from datetime import date

from src.core.error_handler import handle_exception
from src.core.exceptions import ApplicationError
from src.database.connection import AsyncSessionLocal
from src.models.monitoring_log import MonitoringLog
from src.services.monitoring_log_service import MonitoringLogService


def get_request_id(
    event: dict[str, object],
    context: object | None,
) -> str:
    request_id = getattr(context, "aws_request_id", None)

    if request_id:
        return str(request_id)

    request_context = event.get("requestContext")

    if isinstance(request_context, dict):
        request_id = request_context.get("requestId")

        if isinstance(request_id, str):
            return request_id

    return "unknown"


def get_query_parameters(
    event: dict[str, object],
) -> dict[str, str]:
    raw_parameters = event.get("queryStringParameters")

    if raw_parameters is None:
        return {}

    if not isinstance(raw_parameters, dict):
        raise ApplicationError(
            message="Invalid query parameters.",
            error_code="INVALID_QUERY_PARAMETERS",
            status_code=400,
        )

    parameters: dict[str, str] = {}

    for key, value in raw_parameters.items():
        if value is None:
            continue

        if not isinstance(key, str) or not isinstance(value, str):
            raise ApplicationError(
                message="Invalid query parameters.",
                error_code="INVALID_QUERY_PARAMETERS",
                status_code=400,
            )

        parameters[key] = value.strip()

    return parameters


def parse_date_parameter(
    value: str | None,
    parameter_name: str,
) -> date | None:
    if value is None:
        return None

    try:
        return date.fromisoformat(value)
    except ValueError as exception:
        raise ApplicationError(
            message=(
                f"Invalid {parameter_name}. "
                "Expected date format: YYYY-MM-DD."
            ),
            error_code="INVALID_QUERY_PARAMETERS",
            status_code=400,
        ) from exception


def parse_logs_filters(
    parameters: dict[str, str],
) -> tuple[int, date | None, date | None, date | None, str | None, str | None]:
    allowed_parameters = {
        "page",
        "date",
        "start_date",
        "end_date",
        "service_id",
        "agent",
    }

    unexpected_parameters = set(parameters) - allowed_parameters

    if unexpected_parameters:
        raise ApplicationError(
            message=(
                "Unsupported query parameters: "
                + ", ".join(sorted(unexpected_parameters))
            ),
            error_code="INVALID_QUERY_PARAMETERS",
            status_code=400,
        )

    page_value = parameters.get("page", "1")

    try:
        page = int(page_value)
    except ValueError as exception:
        raise ApplicationError(
            message="Page must be a positive integer.",
            error_code="INVALID_QUERY_PARAMETERS",
            status_code=400,
        ) from exception

    if page < 1:
        raise ApplicationError(
            message="Page must be a positive integer.",
            error_code="INVALID_QUERY_PARAMETERS",
            status_code=400,
        )

    date_filter = parse_date_parameter(
        parameters.get("date"),
        "date",
    )
    start_date = parse_date_parameter(
        parameters.get("start_date"),
        "start_date",
    )
    end_date = parse_date_parameter(
        parameters.get("end_date"),
        "end_date",
    )

    if date_filter is not None and (
        start_date is not None or end_date is not None
    ):
        raise ApplicationError(
            message=(
                "Use either date or start_date and end_date, "
                "not both."
            ),
            error_code="INVALID_QUERY_PARAMETERS",
            status_code=400,
        )

    if (start_date is None) != (end_date is None):
        raise ApplicationError(
            message="Both start_date and end_date are required together.",
            error_code="INVALID_QUERY_PARAMETERS",
            status_code=400,
        )

    if (
        start_date is not None
        and end_date is not None
        and start_date > end_date
    ):
        raise ApplicationError(
            message="start_date cannot be later than end_date.",
            error_code="INVALID_QUERY_PARAMETERS",
            status_code=400,
        )

    service_id = parameters.get("service_id") or None
    agent = parameters.get("agent") or None

    return (
        page,
        date_filter,
        start_date,
        end_date,
        service_id,
        agent,
    )


def serialize_monitoring_log(
    log: MonitoringLog,
) -> dict[str, object]:
    return {
        column.name: getattr(log, column.name)
        for column in log.__table__.columns
    }


async def async_lambda_handler(
    event: dict[str, object],
    context: object | None,
) -> dict[str, object]:
    request_id = get_request_id(event, context)

    try:
        parameters = get_query_parameters(event)

        (
            page,
            date_filter,
            start_date,
            end_date,
            service_id,
            agent,
        ) = parse_logs_filters(parameters)

        async with AsyncSessionLocal() as session:
            monitoring_log_service = MonitoringLogService(session)

            logs, total_records = (
                await monitoring_log_service.get_monitoring_logs(
                    page=page,
                    date_filter=date_filter,
                    start_date=start_date,
                    end_date=end_date,
                    service_id=service_id,
                    agent=agent,
                )
            )

            response_data = {
                "logs": [
                    serialize_monitoring_log(log)
                    for log in logs
                ],
                "pagination": {
                    "page": page,
                    "page_size": 50,
                    "total_records": total_records,
                    "total_pages": math.ceil(total_records / 50),
                },
            }

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
            },
            "body": json.dumps(
                {
                    "success": True,
                    "data": response_data,
                },
                default=str,
            ),
        }

    except Exception as exception:
        status_code, error_response = handle_exception(
            exception,
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
    event: dict[str, object],
    context: object | None,
) -> dict[str, object]:
    return asyncio.run(async_lambda_handler(event, context))
