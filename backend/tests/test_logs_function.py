from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest
from flask import Flask, request

from src.entrypoints.google_cloud import logs_function


@pytest.fixture
def client():
    app = Flask(__name__)

    def logs_route():
        return logs_function.get_logs(request)

    app.add_url_rule(
        "/logs",
        view_func=logs_route,
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
        logs_function,
        "AsyncSessionLocal",
        MagicMock(return_value=mock_session_context),
    )

    return mock_session


def mock_log():
    log = MagicMock()
    log.__table__ = MagicMock()
    log.__table__.columns = []
    return log


def test_get_logs_success(client, monkeypatch):
    mock_database_session(monkeypatch)

    logs = [mock_log(), mock_log()]

    mock_service = MagicMock()
    mock_service.get_monitoring_logs = AsyncMock(
        return_value=(logs, 2)
    )

    monkeypatch.setattr(
        logs_function,
        "MonitoringLogService",
        MagicMock(return_value=mock_service),
    )

    response = client.get("/logs")

    assert response.status_code == 200
    assert response.get_json() == {
        "success": True,
        "data": {
            "logs": [{}, {}],
            "pagination": {
                "page": 1,
                "page_size": 50,
                "total_records": 2,
                "total_pages": 1,
            },
        },
    }

    mock_service.get_monitoring_logs.assert_awaited_once_with(
        page=1,
        date_filter=None,
        start_date=None,
        end_date=None,
        service_id=None,
        agent=None,
    )


def test_get_logs_with_query_filters(client, monkeypatch):
    mock_database_session(monkeypatch)

    mock_service = MagicMock()
    mock_service.get_monitoring_logs = AsyncMock(
        return_value=([], 0)
    )

    monkeypatch.setattr(
        logs_function,
        "MonitoringLogService",
        MagicMock(return_value=mock_service),
    )

    response = client.get(
        "/logs?page=2&start_date=2026-11-20"
        "&end_date=2026-11-21&service_id=service-1&agent=agent-1"
    )

    assert response.status_code == 200

    mock_service.get_monitoring_logs.assert_awaited_once_with(
        page=2,
        date_filter=None,
        start_date=date(2026, 11, 20),
        end_date=date(2026, 11, 21),
        service_id="service-1",
        agent="agent-1",
    )


def test_get_logs_with_single_date_filter(client, monkeypatch):
    mock_database_session(monkeypatch)

    mock_service = MagicMock()
    mock_service.get_monitoring_logs = AsyncMock(
        return_value=([], 0)
    )

    monkeypatch.setattr(
        logs_function,
        "MonitoringLogService",
        MagicMock(return_value=mock_service),
    )

    response = client.get("/logs?date=2026-11-20")

    assert response.status_code == 200

    mock_service.get_monitoring_logs.assert_awaited_once_with(
        page=1,
        date_filter=date(2026, 11, 20),
        start_date=None,
        end_date=None,
        service_id=None,
        agent=None,
    )


@pytest.mark.parametrize(
    "query_string",
    [
        "page=0",
        "page=-1",
        "page=abc",
        "date=invalid-date",
        "start_date=2026-11-20",
        "end_date=2026-11-21",
        "date=2026-11-20&start_date=2026-11-20&end_date=2026-11-21",
        "start_date=2026-11-22&end_date=2026-11-20",
        "unknown=value",
    ],
)
def test_get_logs_rejects_invalid_query_parameters(
    client,
    query_string,
):
    response = client.get(f"/logs?{query_string}")

    assert response.status_code == 400
    assert response.get_json()["success"] is False
    assert response.get_json()["error"]["code"] == (
        "INVALID_QUERY_PARAMETERS"
    )


def test_get_logs_returns_empty_results(client, monkeypatch):
    mock_database_session(monkeypatch)

    mock_service = MagicMock()
    mock_service.get_monitoring_logs = AsyncMock(
        return_value=([], 0)
    )

    monkeypatch.setattr(
        logs_function,
        "MonitoringLogService",
        MagicMock(return_value=mock_service),
    )

    response = client.get("/logs")

    assert response.status_code == 200
    assert response.get_json()["data"]["logs"] == []
    assert response.get_json()["data"]["pagination"]["total_pages"] == 0


def test_get_logs_rejects_non_get_method(client):
    response = client.post("/logs")

    assert response.status_code == 405
    assert response.get_json()["error"]["code"] == "METHOD_NOT_ALLOWED"
    assert response.headers["Allow"] == "GET"


def test_get_logs_handles_unexpected_exception(
    client,
    monkeypatch,
):
    mock_database_session(monkeypatch)

    mock_service = MagicMock()
    mock_service.get_monitoring_logs = AsyncMock(
        side_effect=RuntimeError("Database connection failed")
    )

    monkeypatch.setattr(
        logs_function,
        "MonitoringLogService",
        MagicMock(return_value=mock_service),
    )

    response = client.get("/logs")

    assert response.status_code == 500
    assert response.get_json()["success"] is False
    assert response.get_json()["error"]["code"] == (
        "INTERNAL_SERVER_ERROR"
    )
