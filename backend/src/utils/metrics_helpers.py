
from collections.abc import Iterable
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

from src.core.constants import (
    FAILURE_STATUS_MAX,
    FAILURE_STATUS_MIN,
    PERCENTAGE_PRECISION,
    SUCCESS_STATUS_MAX,
    SUCCESS_STATUS_MIN,
)


def is_successful_status(status_code: int) -> bool:
    """Return True when the status code represents a successful check."""

    return SUCCESS_STATUS_MIN <= status_code <= SUCCESS_STATUS_MAX


def is_failed_status(status_code: int) -> bool:
    """Return True when the status code represents a failed check."""

    return FAILURE_STATUS_MIN <= status_code <= FAILURE_STATUS_MAX


def calculate_availability(
    successful_checks: int,
    failed_checks: int,
) -> Decimal:
    """Calculate availability percentage using eligible checks only."""

    if successful_checks < 0 or failed_checks < 0:
        raise ValueError("Check counts cannot be negative.")

    eligible_checks = successful_checks + failed_checks
    precision = Decimal(PERCENTAGE_PRECISION)

    if eligible_checks == 0:
        return Decimal("0").quantize(precision)

    availability = (
        Decimal(successful_checks)
        / Decimal(eligible_checks)
        * Decimal("100")
    )

    return availability.quantize(
        precision,
        rounding=ROUND_HALF_UP,
    )


def calculate_failure_metrics(
    observations: Iterable[tuple[datetime, int]],
) -> tuple[int, int]:
    """
    Calculate the number of failure events and longest event duration.

    Observations must already be sorted by timestamp and record_hash.

    Returns:
        Number of failure events and longest failure duration in seconds.
    """

    failure_events = 0
    longest_failure_duration = 0

    failure_started_at: datetime | None = None
    last_observed_at: datetime | None = None

    for observed_at, status_code in observations:
        last_observed_at = observed_at

        if is_failed_status(status_code):
            if failure_started_at is None:
                failure_started_at = observed_at
                failure_events += 1

        elif is_successful_status(status_code):
            if failure_started_at is not None:
                duration = int(
                    (observed_at - failure_started_at).total_seconds()
                )

                longest_failure_duration = max(
                    longest_failure_duration,
                    duration,
                )

                failure_started_at = None

    # Account for a failure event still active at the last observation.
    if failure_started_at is not None and last_observed_at is not None:
        duration = int(
            (last_observed_at - failure_started_at).total_seconds()
        )

        longest_failure_duration = max(
            longest_failure_duration,
            duration,
        )

    return failure_events, longest_failure_duration
