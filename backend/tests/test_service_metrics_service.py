from datetime import datetime, timezone
from decimal import Decimal
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.service_metrics_service import ServiceMetricsService


def create_record(
    service_id: str,
    observed_at: datetime,
    status_code: int,
    record_hash: str,
    latency_ms: float | None = None,
) -> dict[str, object]:
    return {
        "service_id": service_id,
        "service_name": service_id,
        "observed_at": observed_at,
        "status_code": status_code,
        "record_hash": record_hash,
        "latency_ms": latency_ms,
    }


def create_dataframe(
    records: list[dict[str, object]],
) -> pd.DataFrame:
    return pd.DataFrame.from_records(records)


# ---------------------------------------------------------
# Service metrics calculation tests
# ---------------------------------------------------------


def test_calculate_metrics_for_multiple_services():
    records = [
        create_record(
            "svc-auth",
            datetime(2026, 11, 24, 10, 0, tzinfo=timezone.utc),
            500, "a",
        ),
        create_record(
            "svc-auth",
            datetime(2026, 11, 24, 10, 15, tzinfo=timezone.utc),
            503, "b",
        ),
        create_record(
            "svc-auth",
            datetime(2026, 11, 24, 10, 30, tzinfo=timezone.utc),
            500, "c",
        ),
        create_record(
            "svc-auth",
            datetime(2026, 11, 24, 10, 45, tzinfo=timezone.utc),
            200, "d", 150,
        ),
        create_record(
            "svc-auth",
            datetime(2026, 11, 24, 11, 0, tzinfo=timezone.utc),
            200, "e", 250,
        ),
        create_record(
            "svc-notify",
            datetime(2026, 11, 24, 10, 0, tzinfo=timezone.utc),
            200, "f", 200,
        ),
        create_record(
            "svc-notify",
            datetime(2026, 11, 24, 10, 15, tzinfo=timezone.utc),
            999, "g", 1000,
        ),
    ]

    dataframe = create_dataframe(records)

    results = ServiceMetricsService.calculate_metrics(dataframe)

    assert len(results) == 2

    auth_metrics = next(
        item for item in results if item["service_id"] == "svc-auth"
    )

    assert auth_metrics["total_checks"] == 5
    assert auth_metrics["successful_checks"] == 2
    assert auth_metrics["failed_checks"] == 3
    assert auth_metrics["availability_percentage"] == Decimal("40.000")
    assert auth_metrics["failure_events"] == 1
    assert auth_metrics["longest_failure_duration_seconds"] == 2700
    assert auth_metrics["average_latency_ms"] == Decimal("200.000")
    assert auth_metrics["p95_latency_ms"] == Decimal("245.000")
    assert auth_metrics["latency_sample_count"] == 2
    assert auth_metrics["meets_sla"] is False

    notify_metrics = next(
        item for item in results if item["service_id"] == "svc-notify"
    )

    assert notify_metrics["total_checks"] == 2
    assert notify_metrics["successful_checks"] == 1
    assert notify_metrics["failed_checks"] == 0
    assert notify_metrics["availability_percentage"] == Decimal("100.000")
    assert notify_metrics["latency_sample_count"] == 1
    assert notify_metrics["average_latency_ms"] == Decimal("200.000")
    assert notify_metrics["meets_sla"] is True


def test_service_with_no_valid_latency_samples():
    records = [
        create_record(
            "svc-auth",
            datetime(2026, 11, 24, 10, 0, tzinfo=timezone.utc),
            200, "a", None,
        ),
    ]

    dataframe = create_dataframe(records)

    results = ServiceMetricsService.calculate_metrics(dataframe)

    assert results[0]["average_latency_ms"] is None
    assert results[0]["p95_latency_ms"] is None
    assert results[0]["latency_sample_count"] == 0


def test_empty_monitoring_history():
    dataframe = pd.DataFrame()

    results = ServiceMetricsService.calculate_metrics(dataframe)

    assert results == []


def test_same_timestamp_records_are_sorted_deterministically():
    timestamp = datetime(2026, 11, 24, 10, 0, tzinfo=timezone.utc)

    failure_record = create_record(
        "svc-auth", timestamp, 500, "a",
    )

    success_record = create_record(
        "svc-auth", timestamp, 200, "b", 100,
    )

    later_failure_record = create_record(
        "svc-auth",
        datetime(2026, 11, 24, 10, 1, tzinfo=timezone.utc),
        500,
        "c",
    )

    records = [
        later_failure_record,
        success_record,
        failure_record,
    ]

    dataframe = create_dataframe(records)

    results = ServiceMetricsService.calculate_metrics(dataframe)

    assert results[0]["failure_events"] == 2
    assert results[0]["longest_failure_duration_seconds"] == 0


# ---------------------------------------------------------
# Service metrics calculation and persistence tests
# ---------------------------------------------------------


class TestServiceMetricsPersistence(IsolatedAsyncioTestCase):

    def setUp(self) -> None:
        self.session = MagicMock(spec=AsyncSession)

        self.service = ServiceMetricsService(self.session)

        # Mock the repository to avoid database access.
        self.service.repository = MagicMock()
        self.service.repository.upsert_service_metrics = AsyncMock()

        self.dataframe = create_dataframe(
            [
                create_record(
                    "svc-auth",
                    datetime(
                        2026, 11, 24, 10, 0,
                        tzinfo=timezone.utc,
                    ),
                    200,
                    "hash-1",
                    150,
                ),
            ]
        )

        self.expected_metrics = [
            {
                "service_id": "svc-auth",
                "service_name": "svc-auth",
                "total_checks": 1,
                "availability_eligible_checks": 1,
                "successful_checks": 1,
                "failed_checks": 0,
                "availability_percentage": Decimal("100.000"),
                "average_latency_ms": Decimal("150.000"),
                "p95_latency_ms": Decimal("150.000"),
                "latency_sample_count": 1,
                "failure_events": 0,
                "longest_failure_duration_seconds": 0,
                "meets_sla": True,
            }
        ]

    async def test_calculate_and_save_metrics(self) -> None:
        with patch.object(
            self.service,
            "calculate_metrics",
            return_value=self.expected_metrics,
        ) as mock_calculate:

            result = await self.service.calculate_and_save_metrics(
                self.dataframe
            )

        # Verify existing calculation method is reused.
        mock_calculate.assert_called_once_with(self.dataframe)

        # Verify calculated metrics are persisted.
        self.service.repository.upsert_service_metrics.assert_awaited_once_with(
            self.expected_metrics
        )

        # Verify calculated metrics are returned.
        self.assertEqual(result, self.expected_metrics)

    async def test_calculate_and_save_metrics_with_empty_result(
        self,
    ) -> None:
        with patch.object(
            self.service,
            "calculate_metrics",
            return_value=[],
        ) as mock_calculate:

            result = await self.service.calculate_and_save_metrics(
                pd.DataFrame()
            )

        mock_calculate.assert_called_once()

        self.service.repository.upsert_service_metrics.assert_awaited_once_with(
            []
        )

        self.assertEqual(result, [])

    async def test_calculation_failure_prevents_repository_call(
        self,
    ) -> None:
        with patch.object(
            self.service,
            "calculate_metrics",
            side_effect=ValueError("Metrics calculation failed."),
        ):

            with self.assertRaises(ValueError):
                await self.service.calculate_and_save_metrics(
                    self.dataframe
                )

        self.service.repository.upsert_service_metrics.assert_not_awaited()

    async def test_repository_failure_propagates(self) -> None:
        self.service.repository.upsert_service_metrics.side_effect = (
            RuntimeError("Service metrics persistence failed.")
        )

        with patch.object(
            self.service,
            "calculate_metrics",
            return_value=self.expected_metrics,
        ):

            with self.assertRaises(RuntimeError):
                await self.service.calculate_and_save_metrics(
                    self.dataframe
                )

        self.service.repository.upsert_service_metrics.assert_awaited_once_with(
            self.expected_metrics
        )


if __name__ == "__main__":
    import unittest
    unittest.main()
