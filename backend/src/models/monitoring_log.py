
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    DateTime,
    Identity,
    Index,
    Numeric,
    SmallInteger,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from src.database.connection import Base


class MonitoringLog(Base):
    __tablename__ = "monitoring_logs"

    __table_args__ = (
        UniqueConstraint(
            "record_hash",
            name="uq_monitoring_logs_record_hash",
        ),
        Index(
            "ix_monitoring_logs_observed_at",
            "observed_at",
        ),
        Index(
            "ix_monitoring_logs_service_observed_at",
            "service_id",
            "observed_at",
        ),
    )

    id: Mapped[int] = mapped_column(
        BigInteger,
        Identity(always=True),
        primary_key=True,
    )

    record_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    service_id: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    service_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    status_code: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
    )

    latency_ms: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 3),
        nullable=True,
    )

    agent: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    region: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    upload_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
