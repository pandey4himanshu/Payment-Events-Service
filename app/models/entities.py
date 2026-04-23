from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Merchant(Base):
    __tablename__ = "merchants"

    id: Mapped[int] = mapped_column(primary_key=True)
    merchant_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    merchant_name: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    transactions: Mapped[list["Transaction"]] = relationship(back_populates="merchant")
    events: Mapped[list["PaymentEvent"]] = relationship(back_populates="merchant")


class Transaction(Base): 
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    transaction_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    merchant_id: Mapped[int] = mapped_column(ForeignKey("merchants.id"), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    currency: Mapped[str] = mapped_column(String(8))
    payment_status: Mapped[str] = mapped_column(String(32), index=True, default="unknown")
    settlement_status: Mapped[str] = mapped_column(String(32), index=True, default="pending")
    reconciliation_status: Mapped[str] = mapped_column(String(32), index=True, default="pending")
    discrepancy_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    event_count: Mapped[int] = mapped_column(default=0)
    duplicate_event_count: Mapped[int] = mapped_column(default=0)
    first_event_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    last_event_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    merchant: Mapped["Merchant"] = relationship(back_populates="transactions")
    events: Mapped[list["PaymentEvent"]] = relationship(
        back_populates="transaction",
        order_by="PaymentEvent.event_timestamp",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_transactions_merchant_last_event", "merchant_id", "last_event_at"),
    )


class PaymentEvent(Base):
    __tablename__ = "payment_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    transaction_id: Mapped[int] = mapped_column(ForeignKey("transactions.id"), index=True)
    merchant_id: Mapped[int] = mapped_column(ForeignKey("merchants.id"), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    currency: Mapped[str] = mapped_column(String(8))
    event_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    raw_payload: Mapped[dict] = mapped_column(JSON)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    transaction: Mapped["Transaction"] = relationship(back_populates="events")
    merchant: Mapped["Merchant"] = relationship(back_populates="events")

    __table_args__ = (
        UniqueConstraint("event_id", name="uq_payment_events_event_id"),
        Index("ix_payment_events_transaction_timestamp", "transaction_id", "event_timestamp"),
    )
