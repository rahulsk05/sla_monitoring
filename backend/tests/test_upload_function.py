from io import BytesIO
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from flask import Flask, request

from src.core.exceptions import CSVValidationError
from src.entrypoints.google_cloud import upload_function
from src.services.upload_service import UploadResult


@pytest.fixture
def client():
    app = Flask(__name__)

    def upload_route():
        return upload_function.upload_csv(request)

    app.add_url_rule(
        "/upload",
        view_func=upload_route,
        methods=["GET", "POST", "PUT"],
    )

    return app.test_client()


@pytest.fixture
def upload_result():
    return UploadResult(
        upload_id=uuid4(),
        total_source_rows=10,
        accepted_rows=7,
        partially_accepted_rows=1,
        rejected_rows=1,
        duplicate_rows=1,
        inserted_rows=7,
        service_count=3,
    )


def mock_database_session(monkeypatch):
    session = MagicMock()

    session_context = MagicMock()
    session_context.__aenter__ = AsyncMock(
        return_value=session
    )
    session_context.__aexit__ = AsyncMock(
        return_value=None
    )

    monkeypatch.setattr(
        upload_function,
        "AsyncSessionLocal",
        lambda: session_context,
    )

    return session


def test_upload_rejects_unsupported_http_method(client):
    response = client.get("/upload")

    assert response.status_code == 405
    assert response.headers["Allow"] == "POST"
    assert response.get_json() == {
        "success": False,
        "error": {
            "code": "METHOD_NOT_ALLOWED",
            "message": "Only POST requests are allowed.",
        },
    }


def test_upload_rejects_missing_file(client):
    response = client.post("/upload")

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "INVALID_CSV"


def test_upload_rejects_empty_file(client):
    response = client.post(
        "/upload",
        data={
            "file": (
                BytesIO(b""),
                "empty.csv",
            )
        },
    )

    assert response.status_code == 400
    assert response.get_json()["error"]["code"] == "INVALID_CSV"


def test_upload_success(
    client,
    monkeypatch,
    upload_result,
):
    session = mock_database_session(monkeypatch)

    upload_service = MagicMock()
    upload_service.upload_csv = AsyncMock(
        return_value=upload_result
    )

    upload_service_class = MagicMock(
        return_value=upload_service
    )

    monkeypatch.setattr(
        upload_function,
        "UploadService",
        upload_service_class,
    )

    csv_content = b"service_id,status_code\nservice-1,200\n"

    response = client.post(
        "/upload",
        data={
            "file": (
                BytesIO(csv_content),
                "monitoring.csv",
            )
        },
    )

    response_data = response.get_json()

    assert response.status_code == 200
    assert response_data["success"] is True

    assert response_data["data"] == {
        "upload_id": str(upload_result.upload_id),
        "total_source_rows": 10,
        "accepted_rows": 7,
        "partially_accepted_rows": 1,
        "rejected_rows": 1,
        "duplicate_rows": 1,
        "inserted_rows": 7,
        "service_count": 3,
    }

    upload_service.upload_csv.assert_awaited_once_with(
        csv_content
    )

    upload_service_class.assert_called_once_with(session)


def test_upload_handles_csv_validation_error(
    client,
    monkeypatch,
):
    mock_database_session(monkeypatch)

    upload_service = MagicMock()
    upload_service.upload_csv = AsyncMock(
        side_effect=CSVValidationError(
            "Invalid CSV structure."
        )
    )

    monkeypatch.setattr(
        upload_function,
        "UploadService",
        MagicMock(return_value=upload_service),
    )

    response = client.post(
        "/upload",
        data={
            "file": (
                BytesIO(b"invalid,csv"),
                "invalid.csv",
            )
        },
    )

    assert response.status_code == 400
    assert response.get_json() == {
        "success": False,
        "error": {
            "code": "INVALID_CSV",
            "message": "Invalid CSV structure.",
        },
    }


def test_upload_handles_unexpected_error(
    client,
    monkeypatch,
):
    mock_database_session(monkeypatch)

    upload_service = MagicMock()
    upload_service.upload_csv = AsyncMock(
        side_effect=RuntimeError("Database failure")
    )

    monkeypatch.setattr(
        upload_function,
        "UploadService",
        MagicMock(return_value=upload_service),
    )

    response = client.post(
        "/upload",
        data={
            "file": (
                BytesIO(b"service_id,status_code\nservice-1,200\n"),
                "monitoring.csv",
            )
        },
    )

    assert response.status_code == 500
    assert response.get_json()["error"]["code"] == (
        "INTERNAL_SERVER_ERROR"
    )
