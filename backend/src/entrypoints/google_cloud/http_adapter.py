import base64
import uuid
from collections.abc import Callable, Mapping

from flask import Request, Response, make_response

from src.core.config import settings


LambdaHandler = Callable[..., object]

HttpHandler = Callable[
    [Request],
    Response | tuple[Response, int],
]


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


def handle_cors(
    request: Request,
    handler: HttpHandler,
) -> Response:
    """Apply CORS handling to a Google Cloud HTTP function."""

    allowed_origins = {
        origin.strip()
        for origin in settings.cors_allowed_origins.split(",")
        if origin.strip()
    }

    allowed_methods = {"GET", "POST"}
    allowed_headers = {"content-type", "authorization"}

    origin = request.headers.get("Origin")

    # Handle browser preflight requests.
    if request.method == "OPTIONS":
        if origin not in allowed_origins:
            return Response(status=403)

        requested_method = request.headers.get(
            "Access-Control-Request-Method",
            "",
        ).upper()

        if requested_method not in allowed_methods:
            return Response(status=405)

        requested_headers = {
            header.strip().lower()
            for header in request.headers.get(
                "Access-Control-Request-Headers",
                "",
            ).split(",")
            if header.strip()
        }

        if not requested_headers.issubset(allowed_headers):
            return Response(status=403)

        response = Response(status=204)

        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Methods"] = (
            "GET, POST, OPTIONS"
        )
        response.headers["Access-Control-Allow-Headers"] = (
            "Content-Type, Authorization"
        )
        response.headers["Access-Control-Max-Age"] = "600"

        response.vary.add("Origin")
        response.vary.add("Access-Control-Request-Method")
        response.vary.add("Access-Control-Request-Headers")

        return response

    # Execute the existing function for normal requests.
    response = make_response(handler(request))

    if origin in allowed_origins:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.vary.add("Origin")

    return response
