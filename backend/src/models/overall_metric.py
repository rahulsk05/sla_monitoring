
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Integer,
    Numeric,
    SmallInteger,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from src.database.connection import Base


class OverallMetric(Base):
    __tablename__ = "overall_metrics"

    __table_args__ = (
        CheckConstraint(
            "id = 1",
            name="ck_overall_metrics_single_record",
        ),
    )

    id: Mapped[int] = mapped_column(
        SmallInteger,
        primary_key=True,
    )

    total_checks: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        server_default=text("0"),
    )

    availability_eligible_checks: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        server_default=text("0"),
    )

    successful_checks: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        server_default=text("0"),
    )

    failed_checks: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        server_default=text("0"),
    )

    availability_percentage: Mapped[Decimal] = mapped_column(
        Numeric(6, 3),
        nullable=False,
        server_default=text("0"),
    )

    services_below_sla: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("0"),
    )

    total_failure_events: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("0"),
    )

    longest_failure_duration_seconds: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        server_default=text("0"),
    )

    sla_threshold_percentage: Mapped[Decimal] = mapped_column(
        Numeric(5, 3),
        nullable=False,
        server_default=text("99.900"),
    )

    calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
