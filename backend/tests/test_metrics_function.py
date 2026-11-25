
from unittest.mock import AsyncMock, MagicMock

import pytest
from flask import Flask, request

from src.entrypoints.google_cloud import metrics_function


@pytest.fixture
def client():
    app = Flask(__name__)

    def metrics_route():
        return metrics_function.get_metrics(request)

    app.add_url_rule(
        "/metrics",
        view_func=metrics_route,
        methods=["GET", "POST", "PUT"],
    )

    return app.test_client()


def mock_database_session(monkeypatch):
    mock_session = MagicMock()
    mock_session_context = MagicMock()

    mock_session_context.__aenter__ = AsyncMock(
        return_value=mock_session
    )
    mock_session_context.__aexit__ = AsyncMock(
        return_value=None
    )

    monkeypatch.setattr(
        metrics_function,
        "AsyncSessionLocal",
        MagicMock(return_value=mock_session_context),
    )

    return mock_session


def test_get_metrics_success(client, monkeypatch):
    mock_session = mock_database_session(monkeypatch)

    overall_metric = MagicMock()
    overall_metric.__table__ = MagicMock()
    overall_metric.__table__.columns = []

    service_metric = MagicMock()
    service_metric.__table__ = MagicMock()
    service_metric.__table__.columns = []

    mock_metrics_service = MagicMock()
    mock_metrics_service.get_dashboard_metrics = AsyncMock(
        return_value=(
            overall_metric,
            [service_metric],
        )
    )

    monkeypatch.setattr(
        metrics_function,
        "OverallMetricsService",
        MagicMock(return_value=MagicMock()),
    )
    monkeypatch.setattr(
        metrics_function,
        "ServiceMetricsService",
        MagicMock(return_value=MagicMock()),
    )
    monkeypatch.setattr(
        metrics_function,
        "MetricsService",
        MagicMock(return_value=mock_metrics_service),
    )

    response = client.get("/metrics")

    assert response.status_code == 200
    assert response.get_json() == {
        "success": True,
        "data": {
            "overall": {},
            "services": [{}],
        },
    }

    mock_metrics_service.get_dashboard_metrics.assert_awaited_once()


def test_get_metrics_returns_null_overall_when_missing(
    client,
    monkeypatch,
):
    mock_database_session(monkeypatch)

    mock_metrics_service = MagicMock()
    mock_metrics_service.get_dashboard_metrics = AsyncMock(
        return_value=(None, [])
    )

    monkeypatch.setattr(
        metrics_function,
        "OverallMetricsService",
        MagicMock(return_value=MagicMock()),
    )
    monkeypatch.setattr(
        metrics_function,
        "ServiceMetricsService",
        MagicMock(return_value=MagicMock()),
    )
    monkeypatch.setattr(
        metrics_function,
        "MetricsService",
        MagicMock(return_value=mock_metrics_service),
    )

    response = client.get("/metrics")

    assert response.status_code == 200
    assert response.get_json() == {
        "success": True,
        "data": {
            "overall": None,
            "services": [],
        },
    }


def test_get_metrics_rejects_non_get_method(client):
    response = client.post("/metrics")

    assert response.status_code == 405
    assert response.get_json()["error"]["code"] == "METHOD_NOT_ALLOWED"
    assert response.headers["Allow"] == "GET"


def test_get_metrics_handles_unexpected_exception(
    client,
    monkeypatch,
):
    mock_database_session(monkeypatch)

    mock_metrics_service = MagicMock()
    mock_metrics_service.get_dashboard_metrics = AsyncMock(
        side_effect=RuntimeError("Database connection failed")
    )

    monkeypatch.setattr(
        metrics_function,
        "OverallMetricsService",
        MagicMock(return_value=MagicMock()),
    )
    monkeypatch.setattr(
        metrics_function,
        "ServiceMetricsService",
        MagicMock(return_value=MagicMock()),
    )
    monkeypatch.setattr(
        metrics_function,
        "MetricsService",
        MagicMock(return_value=mock_metrics_service),
    )

    response = client.get("/metrics")

    assert response.status_code == 500
    assert response.get_json()["success"] is False
    assert response.get_json()["error"]["code"] == "INTERNAL_SERVER_ERROR"
