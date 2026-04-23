from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel

from app.schemas.transactions import TransactionListItem


class ReconciliationSummaryItem(BaseModel):
    group_key: str
    transaction_count: int
    total_amount: Decimal
    matched_count: int
    pending_settlement_count: int
    discrepant_count: int
    failed_count: int


class ReconciliationSummaryResponse(BaseModel):
    group_by: str
    items: list[ReconciliationSummaryItem]


class DiscrepancyListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[TransactionListItem]
