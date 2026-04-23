from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class MerchantOut(BaseModel):
    merchant_id: str
    merchant_name: str

    model_config = ConfigDict(from_attributes=True)


class EventHistoryOut(BaseModel):
    event_id: str
    event_type: str
    amount: Decimal
    currency: str
    event_timestamp: datetime
    ingested_at: datetime
    raw_payload: dict

    model_config = ConfigDict(from_attributes=True)


class TransactionListItem(BaseModel):
    transaction_id: str
    merchant_id: str
    merchant_name: str
    amount: Decimal
    currency: str
    payment_status: str
    settlement_status: str
    reconciliation_status: str
    discrepancy_reason: str | None
    event_count: int
    duplicate_event_count: int
    first_event_at: datetime
    last_event_at: datetime


class PaginatedTransactions(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[TransactionListItem]


class TransactionDetailOut(BaseModel):
    transaction_id: str
    amount: Decimal
    currency: str
    payment_status: str
    settlement_status: str
    reconciliation_status: str
    discrepancy_reason: str | None
    event_count: int
    duplicate_event_count: int
    first_event_at: datetime
    last_event_at: datetime
    merchant: MerchantOut
    event_history: list[EventHistoryOut]
