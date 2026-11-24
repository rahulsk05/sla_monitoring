import logging

from src.core.exceptions import ApplicationError

logger = logging.getLogger(__name__)


def handle_exception(
    exception: Exception,
    request_id: str,
) -> tuple[int, dict[str, object]]:
    """Convert application exceptions into safe API responses."""

    if isinstance(exception, ApplicationError):
        logger.warning(
            "Application error. Request ID: %s, Code: %s, Message: %s",
            request_id,
            exception.error_code,
            exception.message,
        )

        return exception.status_code, {
            "success": False,
            "error": {
                "code": exception.error_code,
                "message": exception.message,
            },
        }

    logger.exception(
        "Unexpected application error. Request ID: %s",
        request_id,
    )

    return 500, {
        "success": False,
        "error": {
            "code": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected error occurred.",
        },
    }
