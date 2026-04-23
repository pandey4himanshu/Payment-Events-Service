from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import asc, desc, func, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.db.session import get_db
from app.models.entities import Transaction
from app.schemas.transactions import (
    EventHistoryOut,
    MerchantOut,
    PaginatedTransactions,
    TransactionDetailOut,
    TransactionListItem,
)


router = APIRouter(prefix="/transactions", tags=["transactions"])
settings = get_settings()

SORTABLE_FIELDS = {
    "last_event_at": Transaction.last_event_at,
    "first_event_at": Transaction.first_event_at,
    "amount": Transaction.amount,
    "payment_status": Transaction.payment_status,
}


def _build_transaction_item(transaction: Transaction) -> TransactionListItem:
    return TransactionListItem(
        transaction_id=transaction.transaction_id,
        merchant_id=transaction.merchant.merchant_id,
        merchant_name=transaction.merchant.merchant_name,
        amount=transaction.amount,
        currency=transaction.currency,
        payment_status=transaction.payment_status,
        settlement_status=transaction.settlement_status,
        reconciliation_status=transaction.reconciliation_status,
        discrepancy_reason=transaction.discrepancy_reason,
        event_count=transaction.event_count,
        duplicate_event_count=transaction.duplicate_event_count,
        first_event_at=transaction.first_event_at,
        last_event_at=transaction.last_event_at,
    )


@router.get("", response_model=PaginatedTransactions)
def list_transactions(
    merchant_id: str | None = None,
    payment_status: str | None = None,
    settlement_status: str | None = None,
    reconciliation_status: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(settings.default_page_size, ge=1, le=settings.max_page_size),
    sort_by: str = Query("last_event_at"),
    sort_order: str = Query("desc"),
    db: Session = Depends(get_db),
) -> PaginatedTransactions:
    sort_column = SORTABLE_FIELDS.get(sort_by)
    if sort_column is None:
        raise HTTPException(status_code=400, detail=f"Unsupported sort_by value '{sort_by}'.")

    query = select(Transaction).options(selectinload(Transaction.merchant))
    count_query = select(func.count(Transaction.id))

    filters = []
    if merchant_id:
        filters.append(Transaction.merchant.has(merchant_id=merchant_id))
    if payment_status:
        filters.append(Transaction.payment_status == payment_status)
    if settlement_status:
        filters.append(Transaction.settlement_status == settlement_status)
    if reconciliation_status:
        filters.append(Transaction.reconciliation_status == reconciliation_status)
    if date_from:
        filters.append(Transaction.last_event_at >= date_from)
    if date_to:
        filters.append(Transaction.last_event_at <= date_to)

    for clause in filters:
        query = query.where(clause)
        count_query = count_query.where(clause)

    ordering = desc(sort_column) if sort_order.lower() == "desc" else asc(sort_column)
    query = query.order_by(ordering).offset((page - 1) * page_size).limit(page_size)

    items = db.scalars(query).all()
    total = db.scalar(count_query) or 0

    return PaginatedTransactions(
        total=total,
        page=page,
        page_size=page_size,
        items=[_build_transaction_item(transaction) for transaction in items],
    )


@router.get("/{transaction_id}", response_model=TransactionDetailOut)
def get_transaction_detail(transaction_id: str, db: Session = Depends(get_db)) -> TransactionDetailOut:
    transaction = db.scalar(
        select(Transaction)
        .where(Transaction.transaction_id == transaction_id)
        .options(selectinload(Transaction.merchant), selectinload(Transaction.events))
    )
    if transaction is None:
        raise HTTPException(status_code=404, detail="Transaction not found.")

    merchant = MerchantOut(
        merchant_id=transaction.merchant.merchant_id,
        merchant_name=transaction.merchant.merchant_name,
    )
    event_history = [
        EventHistoryOut(
            event_id=event.event_id,
            event_type=event.event_type,
            amount=event.amount,
            currency=event.currency,
            event_timestamp=event.event_timestamp,
            ingested_at=event.ingested_at,
            raw_payload=event.raw_payload,
        )
        for event in transaction.events
    ]

    return TransactionDetailOut(
        transaction_id=transaction.transaction_id,
        amount=transaction.amount,
        currency=transaction.currency,
        payment_status=transaction.payment_status,
        settlement_status=transaction.settlement_status,
        reconciliation_status=transaction.reconciliation_status,
        discrepancy_reason=transaction.discrepancy_reason,
        event_count=transaction.event_count,
        duplicate_event_count=transaction.duplicate_event_count,
        first_event_at=transaction.first_event_at,
        last_event_at=transaction.last_event_at,
        merchant=merchant,
        event_history=event_history,
    )
