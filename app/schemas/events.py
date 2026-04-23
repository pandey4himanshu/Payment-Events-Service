from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


SUPPORTED_EVENT_TYPES = {"payment_initiated", "payment_processed", "payment_failed", "settled"}


class EventIn(BaseModel):
    event_id: str = Field(..., min_length=1)
    event_type: str
    transaction_id: str = Field(..., min_length=1)
    merchant_id: str = Field(..., min_length=1)
    merchant_name: str = Field(..., min_length=1)
    amount: Decimal = Field(..., gt=0)
    currency: str = Field(..., min_length=3, max_length=8)
    timestamp: datetime

    model_config = ConfigDict(json_schema_extra={"example": {
        "event_id": "evt_001",
        "event_type": "payment_processed",
        "transaction_id": "txn_001",
        "merchant_id": "merchant_1",
        "merchant_name": "FreshBasket",
        "amount": 1200.50,
        "currency": "INR",
        "timestamp": "2026-01-08T12:11:58.085567+00:00",
    }})


class EventIngestResponse(BaseModel):
    inserted: bool
    duplicate: bool
    message: str
    transaction_id: str
    current_payment_status: str
    current_settlement_status: str
    reconciliation_status: str
