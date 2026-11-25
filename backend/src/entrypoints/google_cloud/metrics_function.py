
import asyncio
import json
import uuid

from flask import Request, Response, jsonify

from src.core.error_handler import handle_exception
from src.database.connection import AsyncSessionLocal
from src.models.overall_metric import OverallMetric
from src.models.service_metric import ServiceMetric
from src.services.metrics_service import MetricsService
from src.services.overall_metrics_service import OverallMetricsService
from src.services.service_metrics_service import ServiceMetricsService


def serialize_model(
    instance: OverallMetric | ServiceMetric,
) -> dict[str, object]:
    return {
        column.name: getattr(instance, column.name)
        for column in instance.__table__.columns
    }


def get_metrics(request: Request) -> Response | tuple[Response, int]:
    request_id = uuid.uuid4().hex

    try:
        if request.method != "GET":
            response = jsonify({
                "success": False,
                "error": {
                    "code": "METHOD_NOT_ALLOWED",
                    "message": "Only GET requests are allowed.",
                },
            })
            response.headers["Allow"] = "GET"
            return response, 405

        async def fetch_metrics() -> dict[str, object]:
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

                return {
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

        response_data = asyncio.run(fetch_metrics())

        response_body = {
            "success": True,
            "data": response_data,
        }

        return Response(
            json.dumps(response_body, default=str),
            status=200,
            mimetype="application/json",
        )

    except Exception as exception:
        status_code, error_response = handle_exception(
            exception,
            request_id,
        )

        return jsonify(error_response), status_code
