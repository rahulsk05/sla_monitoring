from datetime import datetime
from decimal import Decimal

import pytest

from src.utils.metrics_helpers import (
    calculate_availability,
    calculate_failure_metrics,
    is_failed_status,
    is_successful_status,
)


def test_status_classification():
    assert is_successful_status(200)
    assert is_successful_status(299)
    assert not is_successful_status(300)

    assert is_failed_status(500)
    assert is_failed_status(599)
    assert not is_failed_status(404)


def test_availability_calculation():
    result = calculate_availability(900, 100)

    assert result == Decimal("90.000")


def test_availability_with_no_eligible_checks():
    result = calculate_availability(0, 0)

    assert result == Decimal("0.000")


def test_failure_event_calculation():
    observations = [
        (datetime(2026, 11, 24, 10, 0), 500),
        (datetime(2026, 11, 24, 10, 15), 503),
        (datetime(2026, 11, 24, 10, 30), 500),
        (datetime(2026, 11, 24, 10, 45), 200),
    ]

    events, longest_duration = calculate_failure_metrics(observations)

    assert events == 1
    assert longest_duration == 2700


def test_ongoing_failure_event():
    observations = [
        (datetime(2026, 11, 24, 10, 0), 500),
        (datetime(2026, 11, 24, 10, 30), 999),
    ]

    events, longest_duration = calculate_failure_metrics(observations)

    assert events == 1
    assert longest_duration == 1800


def test_multiple_failure_events():
    observations = [
        (datetime(2026, 11, 24, 10, 0), 500),
        (datetime(2026, 11, 24, 10, 15), 200),
        (datetime(2026, 11, 24, 10, 30), 503),
        (datetime(2026, 11, 24, 10, 45), 200),
    ]

    events, longest_duration = calculate_failure_metrics(observations)

    assert events == 2
    assert longest_duration == 900

def test_calculate_availability_rejects_negative_counts():
    with pytest.raises(ValueError):
        calculate_availability(-1, 10)


def test_calculate_availability_rejects_negative_failed_count():
    with pytest.raises(ValueError):
        calculate_availability(10, -1)