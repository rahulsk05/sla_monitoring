from decimal import Decimal
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.overall_metrics_service import OverallMetricsService


def create_record(status_code: int) -> dict[str, object]:
    return {
        "service_id": "svc-auth",
        "service_name": "Authentication",
        "status_code": status_code,
    }


def create_service_metric(
    service_id: str,
    meets_sla: bool,
    failure_events: int,
    longest_duration: int,
) -> dict[str, object]:
    return {
        "service_id": service_id,
        "meets_sla": meets_sla,
        "failure_events": failure_events,
        "longest_failure_duration_seconds": longest_duration,
    }


# ---------------------------------------------------------
# Overall metrics calculation tests
# ---------------------------------------------------------


def test_calculate_overall_metrics():
    records = (
        [create_record(200) for _ in range(800)]
        + [create_record(500) for _ in range(100)]
        + [create_record(999) for _ in range(20)]
    )

    dataframe = pd.DataFrame.from_records(records)

    service_metrics = [
        create_service_metric("svc-auth", False, 3, 2700),
        create_service_metric("svc-notify", True, 2, 600),
        create_service_metric("svc-payments", False, 1, 1200),
    ]

    result = OverallMetricsService.calculate_metrics(
        dataframe,
        service_metrics,
    )

    assert result["id"] == 1
    assert result["total_checks"] == 920
    assert result["availability_eligible_checks"] == 900
    assert result["successful_checks"] == 800
    assert result["failed_checks"] == 100
    assert result["availability_percentage"] == Decimal("88.889")
    assert result["services_below_sla"] == 2
    assert result["total_failure_events"] == 6
    assert result["longest_failure_duration_seconds"] == 2700
    assert result["sla_threshold_percentage"] == Decimal("99.9")


def test_empty_monitoring_history():
    dataframe = pd.DataFrame()

    result = OverallMetricsService.calculate_metrics(
        dataframe,
        [],
    )

    assert result["total_checks"] == 0
    assert result["availability_eligible_checks"] == 0
    assert result["successful_checks"] == 0
    assert result["failed_checks"] == 0
    assert result["availability_percentage"] == Decimal("0.000")
    assert result["services_below_sla"] == 0
    assert result["total_failure_events"] == 0
    assert result["longest_failure_duration_seconds"] == 0


def test_all_services_meet_sla():
    records = [
        create_record(200),
        create_record(200),
    ]

    dataframe = pd.DataFrame.from_records(records)

    service_metrics = [
        create_service_metric("svc-auth", True, 0, 0),
        create_service_metric("svc-notify", True, 0, 0),
    ]

    result = OverallMetricsService.calculate_metrics(
        dataframe,
        service_metrics,
    )

    assert result["services_below_sla"] == 0
    assert result["total_failure_events"] == 0
    assert result["longest_failure_duration_seconds"] == 0


# ---------------------------------------------------------
# Overall metrics calculation and persistence tests
# ---------------------------------------------------------


class TestOverallMetricsPersistence(IsolatedAsyncioTestCase):

    def setUp(self) -> None:
        self.session = MagicMock(spec=AsyncSession)

        self.service = OverallMetricsService(self.session)

        # Mock the repository to avoid database access.
        self.service.repository = MagicMock()
        self.service.repository.upsert_overall_metrics = AsyncMock()

        self.dataframe = pd.DataFrame.from_records(
            [
                create_record(200),
                create_record(500),
            ]
        )

        self.service_metrics = [
            create_service_metric(
                "svc-auth",
                False,
                1,
                300,
            ),
            create_service_metric(
                "svc-notify",
                True,
                0,
                0,
            ),
        ]

        self.expected_metrics = {
            "id": 1,
            "total_checks": 2,
            "availability_eligible_checks": 2,
            "successful_checks": 1,
            "failed_checks": 1,
            "availability_percentage": Decimal("50.000"),
            "services_below_sla": 1,
            "total_failure_events": 1,
            "longest_failure_duration_seconds": 300,
            "sla_threshold_percentage": Decimal("99.9"),
        }

    async def test_calculate_and_save_metrics(self) -> None:
        with patch.object(
            self.service,
            "calculate_metrics",
            return_value=self.expected_metrics,
        ) as mock_calculate:

            result = await self.service.calculate_and_save_metrics(
                self.dataframe,
                self.service_metrics,
            )

        # Verify existing calculation method is reused.
        mock_calculate.assert_called_once_with(
            self.dataframe,
            self.service_metrics,
        )

        # Verify calculated metrics are persisted.
        self.service.repository.upsert_overall_metrics.assert_awaited_once_with(
            self.expected_metrics
        )

        # Verify calculated metrics are returned.
        self.assertEqual(result, self.expected_metrics)

    async def test_calculation_failure_prevents_repository_call(
        self,
    ) -> None:
        with patch.object(
            self.service,
            "calculate_metrics",
            side_effect=ValueError(
                "Overall metrics calculation failed."
            ),
        ):

            with self.assertRaises(ValueError):
                await self.service.calculate_and_save_metrics(
                    self.dataframe,
                    self.service_metrics,
                )

        self.service.repository.upsert_overall_metrics.assert_not_awaited()

    async def test_repository_failure_propagates(self) -> None:
        self.service.repository.upsert_overall_metrics.side_effect = (
            RuntimeError("Overall metrics persistence failed.")
        )

        with patch.object(
            self.service,
            "calculate_metrics",
            return_value=self.expected_metrics,
        ):

            with self.assertRaises(RuntimeError):
                await self.service.calculate_and_save_metrics(
                    self.dataframe,
                    self.service_metrics,
                )

        self.service.repository.upsert_overall_metrics.assert_awaited_once_with(
            self.expected_metrics
        )


if __name__ == "__main__":
    import unittest
    unittest.main()
