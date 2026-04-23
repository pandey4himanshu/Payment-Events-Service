from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.db.session import get_db
from app.models.entities import Merchant, Transaction
from app.routes.transactions import _build_transaction_item
from app.schemas.reconciliation import DiscrepancyListResponse, ReconciliationSummaryItem, ReconciliationSummaryResponse


router = APIRouter(prefix="/reconciliation", tags=["reconciliation"])
settings = get_settings()


@router.get("/summary", response_model=ReconciliationSummaryResponse)
def reconciliation_summary(
    group_by: str = Query("merchant"),
    merchant_id: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    db: Session = Depends(get_db),
) -> ReconciliationSummaryResponse:
    if group_by == "merchant":
        group_expr = Merchant.merchant_name
    elif group_by == "status":
        group_expr = Transaction.reconciliation_status
    elif group_by == "date":
        group_expr = func.date(Transaction.last_event_at)
    else:
        raise HTTPException(status_code=400, detail="group_by must be one of: merchant, status, date")

    query = (
        select(
            group_expr.label("group_key"),
            func.count(Transaction.id).label("transaction_count"),
            func.coalesce(func.sum(Transaction.amount), 0).label("total_amount"),
            func.sum(case((Transaction.reconciliation_status == "matched", 1), else_=0)).label("matched_count"),
            func.sum(case((Transaction.reconciliation_status == "pending_settlement", 1), else_=0)).label("pending_settlement_count"),
            func.sum(case((Transaction.reconciliation_status == "discrepant", 1), else_=0)).label("discrepant_count"),
            func.sum(case((Transaction.payment_status == "failed", 1), else_=0)).label("failed_count"),
        )
        .join(Merchant, Transaction.merchant_id == Merchant.id)
        .group_by(group_expr)
        .order_by(group_expr)
    )

    if merchant_id:
        query = query.where(Merchant.merchant_id == merchant_id)
    if date_from:
        query = query.where(Transaction.last_event_at >= date_from)
    if date_to:
        query = query.where(Transaction.last_event_at <= date_to)

    rows = db.execute(query).all()
    items = [
        ReconciliationSummaryItem(
            group_key=str(row.group_key),
            transaction_count=row.transaction_count,
            total_amount=row.total_amount,
            matched_count=row.matched_count,
            pending_settlement_count=row.pending_settlement_count,
            discrepant_count=row.discrepant_count,
            failed_count=row.failed_count,
        )
        for row in rows
    ]
    return ReconciliationSummaryResponse(group_by=group_by, items=items)


@router.get("/discrepancies", response_model=DiscrepancyListResponse)
def reconciliation_discrepancies(
    merchant_id: str | None = None,
    discrepancy_reason: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(settings.default_page_size, ge=1, le=settings.max_page_size),
    db: Session = Depends(get_db),
) -> DiscrepancyListResponse:
    base_query = (
        select(Transaction)
        .options(selectinload(Transaction.merchant))
        .where(Transaction.reconciliation_status == "discrepant")
    )
    count_query = select(func.count(Transaction.id)).where(Transaction.reconciliation_status == "discrepant")

    if merchant_id:
        clause = Transaction.merchant.has(merchant_id=merchant_id)
        base_query = base_query.where(clause)
        count_query = count_query.where(clause)
    if discrepancy_reason:
        clause = Transaction.discrepancy_reason.contains(discrepancy_reason)
        base_query = base_query.where(clause)
        count_query = count_query.where(clause)
    if date_from:
        clause = Transaction.last_event_at >= date_from
        base_query = base_query.where(clause)
        count_query = count_query.where(clause)
    if date_to:
        clause = Transaction.last_event_at <= date_to
        base_query = base_query.where(clause)
        count_query = count_query.where(clause)

    base_query = base_query.order_by(Transaction.last_event_at.desc()).offset((page - 1) * page_size).limit(page_size)

    items = db.scalars(base_query).all()
    total = db.scalar(count_query) or 0
    return DiscrepancyListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=[_build_transaction_item(item) for item in items],
    )
