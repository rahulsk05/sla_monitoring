
from io import BytesIO
from uuid import uuid4

from src.services.cleaning_service import CleaningService


def test_cleaning_service_basic():

    csv_content = b"""service_id,service_name,timestamp,status_code,latency,latency_unit,agent,region
svc-auth,Auth Service,2026-11-01T10:00:00Z,200,0.5,seconds,agent-1,ap-south-1
svc-auth,Auth Service,2026-11-01T10:00:00Z,200,0.5,seconds,agent-1,ap-south-1
svc-payments,Payments Service,2026-11-01T10:15:00+05:30,500,250,milliseconds,agent-2,ap-south-1
svc-notify,Notify Service,1793527200,200,,,agent-3,ap-south-1
svc-search,Search Service,2026-11-01T10:30:00Z,200,-10,milliseconds,agent-4,ap-south-1
,Invalid Service,2026-11-01T10:30:00Z,200,100,milliseconds,agent-5,ap-south-1
svc-reports,Reports Service,2026-11-01T10:45:00Z,999,150,milliseconds,agent-6,ap-south-1
"""

    result = CleaningService.clean_csv(
        BytesIO(csv_content),
        uuid4(),
    )

    summary = result.summary

    assert summary.total_source_rows == 7
    assert summary.accepted_rows == 2
    assert summary.partially_accepted_rows == 2
    assert summary.rejected_rows == 2
    assert summary.duplicate_rows == 1

    assert len(result.records) == 4

    # Seconds converted into milliseconds.
    assert result.records[0]["latency_ms"] == 500

    # Invalid latency is retained as None.
    assert result.records[-1]["latency_ms"] is None

def test_invalid_http_status_code_is_rejected():

    row = {
        "service_id": "svc-reports",
        "service_name": "Reports Service",
        "timestamp": "2026-11-01T10:45:00Z",
        "status_code": "999",
        "latency": "150",
        "latency_unit": "milliseconds",
        "agent": "agent-6",
        "region": "ap-south-1",
    }

    record, partially_accepted = CleaningService.clean_row(
        row,
        uuid4(),
    )

    assert record is None
    assert partially_accepted is False