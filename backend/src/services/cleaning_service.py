import hashlib
import json
import re

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import IO
from uuid import UUID

import pandas as pd

from src.core.config import settings
from src.core.constants import (
    EXPECTED_CSV_COLUMNS,
    LATENCY_PRECISION,
    MILLISECONDS_UNITS,
    SECONDS_UNITS,
    VALID_HTTP_STATUS_CODES,
)
from src.core.exceptions import CSVValidationError
from src.core.logger import get_logger


logger = get_logger(__name__)


@dataclass
class CleaningSummary:
    total_source_rows: int = 0
    accepted_rows: int = 0
    partially_accepted_rows: int = 0
    rejected_rows: int = 0
    duplicate_rows: int = 0


@dataclass
class CleaningResult:
    records: list[dict[str, object]]
    summary: CleaningSummary


class CleaningService:
    """Validate and normalize uploaded CSV monitoring records."""

    @staticmethod
    def generate_record_hash(row: Mapping[str, str]) -> str:
        """
        Generate a deterministic SHA-256 fingerprint
        using all eight original CSV fields.
        """

        original_values = [
            row[column]
            for column in EXPECTED_CSV_COLUMNS
        ]

        serialized = json.dumps(
            original_values,
            ensure_ascii=False,
            separators=(",", ":"),
        )

        return hashlib.sha256(
            serialized.encode("utf-8")
        ).hexdigest()

    @staticmethod
    def normalize_timestamp(value: str) -> datetime | None:
        """
        Convert supported timestamps into UTC-aware datetime.
        Supports ISO timestamps and Unix epoch seconds.
        """

        value = value.strip()

        if not value:
            return None

        try:
            if re.fullmatch(r"[+-]?\d+", value):
                timestamp = pd.to_datetime(
                    int(value),
                    unit="s",
                    utc=True,
                    errors="coerce",
                )
            else:
                timestamp = pd.to_datetime(
                    value,
                    utc=True,
                    errors="coerce",
                )

            if pd.isna(timestamp):
                return None

            return timestamp.to_pydatetime()

        except (ValueError, OverflowError, TypeError):
            return None

    @staticmethod
    def normalize_status_code(value: str) -> int | None:
        """
        Validate against registered HTTP status codes.

        Invalid or unregistered status codes return None.
        """

        try:
            status_code = int(value.strip())

            if status_code not in VALID_HTTP_STATUS_CODES:
                return None

            return status_code

        except (ValueError, TypeError):
            return None

    @staticmethod
    def normalize_latency(
        latency: str,
        latency_unit: str,
    ) -> Decimal | None:
        """
        Normalize valid nonnegative latency into milliseconds.
        Invalid latency is represented as None.
        """

        if not latency.strip():
            return None

        try:
            value = Decimal(latency.strip())

            if not value.is_finite() or value < 0:
                return None

            unit = latency_unit.strip().lower()

            if unit in SECONDS_UNITS:
                value *= Decimal("1000")

            elif unit not in MILLISECONDS_UNITS:
                return None

            return value.quantize(
                Decimal(LATENCY_PRECISION),
                rounding=ROUND_HALF_UP,
            )

        except (InvalidOperation, ValueError):
            return None

    @staticmethod
    def clean_row(
        row: Mapping[str, str],
        upload_id: UUID,
    ) -> tuple[dict[str, object] | None, bool]:
        """
        Validate and normalize one CSV row.

        Returns:
            Cleaned record and partially accepted flag.
        """

        service_id = row["service_id"].strip()
        service_name = row["service_name"].strip()

        observed_at = CleaningService.normalize_timestamp(
            row["timestamp"]
        )

        status_code = CleaningService.normalize_status_code(
            row["status_code"]
        )

        # Reject rows with invalid mandatory fields.
        if (
            not service_id
            or not service_name
            or observed_at is None
            or status_code is None
        ):
            return None, False

        latency_ms = CleaningService.normalize_latency(
            row["latency"],
            row["latency_unit"],
        )

        record: dict[str, object] = {
            "record_hash": CleaningService.generate_record_hash(row),
            "service_id": service_id,
            "service_name": service_name,
            "observed_at": observed_at,
            "status_code": status_code,
            "latency_ms": latency_ms,
            "agent": row["agent"].strip() or None,
            "region": row["region"].strip() or None,
            "upload_id": upload_id,
        }

        partially_accepted = latency_ms is None

        return record, partially_accepted

    @staticmethod
    def clean_csv(
        file: str | Path | IO[bytes],
        upload_id: UUID,
    ) -> CleaningResult:
        """
        Read, validate and clean CSV records in chunks.

        File-level validation errors reject the upload.
        Invalid individual rows are counted as rejected rows.
        """

        logger.info(
            "Starting CSV cleaning. Upload ID: %s",
            upload_id,
        )

        summary = CleaningSummary()
        cleaned_records: list[dict[str, object]] = []

        # Tracks fingerprints across all CSV chunks.
        seen_hashes: set[str] = set()

        try:
            # Validate CSV headers without loading the entire file.
            headers = pd.read_csv(
                file,
                dtype=str,
                keep_default_na=False,
                encoding="utf-8-sig",
                nrows=0,
            )

            if headers.columns.has_duplicates:
                raise CSVValidationError(
                    "CSV contains duplicate column names."
                )

            actual_columns = set(headers.columns)
            expected_columns = set(EXPECTED_CSV_COLUMNS)

            if actual_columns != expected_columns:
                missing = sorted(
                    expected_columns - actual_columns
                )

                unexpected = sorted(
                    actual_columns - expected_columns
                )

                raise CSVValidationError(
                    f"Invalid CSV structure. "
                    f"Missing columns: {missing}. "
                    f"Unexpected columns: {unexpected}."
                )

            # Reset file pointer before chunk processing.
            if hasattr(file, "seek"):
                file.seek(0)

            # Read CSV in chunks to control memory consumption.
            reader = pd.read_csv(
                file,
                dtype=str,
                keep_default_na=False,
                encoding="utf-8-sig",
                chunksize=settings.csv_chunk_size,
            )

            for chunk in reader:
                for row_data in chunk.to_dict(orient="records"):
                    summary.total_source_rows += 1

                    record, partially_accepted = (
                        CleaningService.clean_row(
                            row_data,
                            upload_id,
                        )
                    )

                    if record is None:
                        summary.rejected_rows += 1
                        continue

                    record_hash = str(record["record_hash"])

                    # Detect duplicates across different chunks.
                    if record_hash in seen_hashes:
                        summary.duplicate_rows += 1
                        continue

                    seen_hashes.add(record_hash)
                    cleaned_records.append(record)

                    if partially_accepted:
                        summary.partially_accepted_rows += 1
                    else:
                        summary.accepted_rows += 1

        except CSVValidationError:
            raise

        except (
            pd.errors.EmptyDataError,
            pd.errors.ParserError,
            UnicodeDecodeError,
            ValueError,
        ) as exc:
            raise CSVValidationError(
                f"Unable to process CSV file: {exc}"
            ) from exc

        result = CleaningResult(
            records=cleaned_records,
            summary=summary,
        )

        logger.info(
            (
                "CSV cleaning completed. Upload ID: %s, "
                "Source rows: %d, Accepted: %d, "
                "Partially accepted: %d, Rejected: %d, "
                "Duplicates: %d"
            ),
            upload_id,
            summary.total_source_rows,
            summary.accepted_rows,
            summary.partially_accepted_rows,
            summary.rejected_rows,
            summary.duplicate_rows,
        )

        return result
