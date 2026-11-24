
# CSV configuration

from decimal import Decimal


EXPECTED_CSV_COLUMNS = (
    "service_id",
    "service_name",
    "timestamp",
    "status_code",
    "latency",
    "latency_unit",
    "agent",
    "region",
)

MANDATORY_CSV_COLUMNS = (
    "service_id",
    "service_name",
    "timestamp",
    "status_code",
)


# Latency configuration

MILLISECONDS_UNITS = frozenset({
    "ms",
    "millisecond",
    "milliseconds",
})

SECONDS_UNITS = frozenset({
    "s",
    "sec",
    "second",
    "seconds",
})

LATENCY_PRECISION = Decimal("0.001")

PERCENTAGE_PRECISION = Decimal("0.001")


# HTTP status classification

SUCCESS_STATUS_MIN = 200
SUCCESS_STATUS_MAX = 299

FAILURE_STATUS_MIN = 500
FAILURE_STATUS_MAX = 599


# Database configuration

OVERALL_METRICS_ID = 1


# Upload configuration

UPLOAD_CHUNK_INSERT_SIZE = 1000

VALID_HTTP_STATUS_CODES = frozenset({
    # 1xx - Informational
    100, 101, 102, 103, 104,

    # 2xx - Success
    200, 201, 202, 203, 204, 205, 206,
    207, 208, 226,

    # 3xx - Redirection
    300, 301, 302, 303, 304, 305, 306,
    307, 308,

    # 4xx - Client Errors
    400, 401, 402, 403, 404, 405, 406,
    407, 408, 409, 410, 411, 412, 413,
    414, 415, 416, 417, 418, 421, 422,
    423, 424, 425, 426, 428, 429, 431,
    451,

    # 5xx - Server Errors
    500, 501, 502, 503, 504, 505, 506,
    507, 508, 510, 511,
})

MAX_CSV_FILE_SIZE_BYTES = 5 * 1024 * 1024

FILE_FIELD_NAME = "file"

LOGS_PAGE_SIZE = 50
