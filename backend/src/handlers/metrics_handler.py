import asyncio
import json
from typing import Any

from src.core.error_handler import handle_exception
from src.database.connection import AsyncSessionLocal
from src.models.overall_metric import OverallMetric
from src.models.service_metric import ServiceMetric
from src.services.metrics_service import MetricsService
from src.services.overall_metrics_service import OverallMetricsService
from src.services.service_metrics_service import ServiceMetricsService


def get_request_id(
    event: dict[str, Any],
    context: object | None,
) -> str:
    request_id = getattr(context, "aws_request_id", None)

    if request_id:
        return request_id

    request_context = event.get("requestContext", {})

    if isinstance(request_context, dict):
        return request_context.get("requestId", "unknown")

    return "unknown"


def serialize_model(
    instance: OverallMetric | ServiceMetric,
) -> dict[str, object]:
    return {
        column.name: getattr(instance, column.name)
        for column in instance.__table__.columns
    }


async def async_lambda_handler(
    event: dict[str, Any],
    context: object | None,
) -> dict[str, Any]:
    request_id = get_request_id(event, context)

    try:
        async with AsyncSessionLocal() as session:
            overall_metrics_service = OverallMetricsService(session)
            service_metrics_service = ServiceMetricsService(session)

            metrics_service = MetricsService(
                overall_metrics_service=overall_metrics_service,
                service_metrics_service=service_metrics_service,
            )

            overall_metrics, service_metrics = (
                await metrics_service.get_dashboard_metrics()
            )

            response_data = {
                "overall": (
                    serialize_model(overall_metrics)
                    if overall_metrics is not None
                    else None
                ),
                "services": [
                    serialize_model(service_metric)
                    for service_metric in service_metrics
                ],
            }

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
            },
            "body": json.dumps(response_data_wrapper(response_data), default=str),
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


def response_data_wrapper(data: dict[str, object]) -> dict[str, object]:
    return {
        "success": True,
        "data": data,
    }


def lambda_handler(
    event: dict[str, Any],
    context: object | None,
) -> dict[str, Any]:
    return asyncio.run(async_lambda_handler(event, context))
