import base64
import uuid
from collections.abc import Callable, Mapping

from flask import Request, Response


LambdaHandler = Callable[..., object]


def create_lambda_event(request: Request) -> dict[str, object]:
    """Convert a Google Cloud HTTP request into a Lambda-compatible event."""

    request_body = request.get_data(cache=False)

    headers = {
        key.lower(): value
        for key, value in request.headers.items()
    }

    return {
        "body": base64.b64encode(request_body).decode("ascii"),
        "isBase64Encoded": True,
        "headers": headers,
        "queryStringParameters": request.args.to_dict(flat=True),
        "requestContext": {
            "requestId": uuid.uuid4().hex,
        },
    }


def create_http_response(
    lambda_response: object,
) -> Response:
    """Convert a Lambda-compatible response into a Flask HTTP response."""

    if not isinstance(lambda_response, Mapping):
        return Response(
            response="Invalid handler response.",
            status=500,
            content_type="text/plain",
        )

    status_code = lambda_response.get("statusCode", 500)
    headers = lambda_response.get("headers", {})
    body = lambda_response.get("body", "")

    if (
        not isinstance(status_code, int)
        or isinstance(status_code, bool)
        or not 100 <= status_code <= 599
    ):
        status_code = 500

    response_headers: dict[str, str] = {}

    if isinstance(headers, Mapping):
        response_headers = {
            key: value
            for key, value in headers.items()
            if isinstance(key, str) and isinstance(value, str)
        }

    if not isinstance(body, str):
        body = ""

    return Response(
        response=body,
        status=status_code,
        headers=response_headers,
    )


def handle_http_request(
    request: Request,
    handler: LambdaHandler,
) -> Response:
    """Adapt a Google Cloud HTTP request to an existing application handler."""

    event = create_lambda_event(request)

    lambda_response = handler(
        event,
        None,
    )

    return create_http_response(lambda_response)
