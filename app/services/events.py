from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.entities import Merchant, PaymentEvent, Transaction
from app.schemas.events import EventIn, SUPPORTED_EVENT_TYPES
from app.services.state_machine import derive_transaction_state


class EventValidationError(ValueError):
    pass


def _normalize_timestamp(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _get_or_create_merchant(db: Session, payload: EventIn) -> Merchant:
    merchant = db.scalar(select(Merchant).where(Merchant.merchant_id == payload.merchant_id))
    if merchant is None:
        merchant = Merchant(merchant_id=payload.merchant_id, merchant_name=payload.merchant_name)
        db.add(merchant)
        db.flush()
    elif merchant.merchant_name != payload.merchant_name:
        merchant.merchant_name = payload.merchant_name
    return merchant


def _get_or_create_transaction(db: Session, payload: EventIn, merchant: Merchant) -> Transaction:
    normalized_timestamp = _normalize_timestamp(payload.timestamp)
    transaction = db.scalar(
        select(Transaction)
        .where(Transaction.transaction_id == payload.transaction_id)
        .options(selectinload(Transaction.events))
    )
    if transaction is None:
        transaction = Transaction(
            transaction_id=payload.transaction_id,
            merchant_id=merchant.id,
            amount=payload.amount,
            currency=payload.currency,
            first_event_at=normalized_timestamp,
            last_event_at=normalized_timestamp,
        )
        db.add(transaction)
        db.flush()
        db.refresh(transaction)
    else:
        transaction.merchant_id = merchant.id
        transaction.amount = payload.amount
        transaction.currency = payload.currency
        transaction.first_event_at = min(_normalize_timestamp(transaction.first_event_at), normalized_timestamp)
        transaction.last_event_at = max(_normalize_timestamp(transaction.last_event_at), normalized_timestamp)
    return transaction


def ingest_event(db: Session, payload: EventIn, auto_commit: bool = True) -> tuple[Transaction, bool]:
    if payload.event_type not in SUPPORTED_EVENT_TYPES:
        raise EventValidationError(f"Unsupported event_type '{payload.event_type}'.")

    existing_event = db.scalar(select(PaymentEvent).where(PaymentEvent.event_id == payload.event_id))
    if existing_event is not None:
        transaction = db.scalar(
            select(Transaction)
            .where(Transaction.id == existing_event.transaction_id)
            .options(selectinload(Transaction.merchant), selectinload(Transaction.events))
        )
        if transaction is None:
            raise EventValidationError("Duplicate event points to a missing transaction.")
        return transaction, True

    merchant = _get_or_create_merchant(db, payload)
    transaction = _get_or_create_transaction(db, payload, merchant)

    event = PaymentEvent(
        event_id=payload.event_id,
        event_type=payload.event_type,
        transaction_id=transaction.id,
        merchant_id=merchant.id,
        amount=payload.amount,
        currency=payload.currency,
        event_timestamp=_normalize_timestamp(payload.timestamp),
        raw_payload=payload.model_dump(mode="json"),
    )
    db.add(event)
    db.flush()

    transaction = db.scalar(
        select(Transaction)
        .where(Transaction.id == transaction.id)
        .options(selectinload(Transaction.merchant), selectinload(Transaction.events))
    )
    if transaction is None:
        raise EventValidationError("Transaction missing after event insert.")

    transaction_events = db.scalars(
        select(PaymentEvent).where(PaymentEvent.transaction_id == transaction.id).order_by(PaymentEvent.event_timestamp)
    ).all()

    payment_status, settlement_status, reconciliation_status, discrepancy_reason, duplicate_event_count = derive_transaction_state(
        transaction_events
    )
    transaction.payment_status = payment_status
    transaction.settlement_status = settlement_status
    transaction.reconciliation_status = reconciliation_status
    transaction.discrepancy_reason = discrepancy_reason
    transaction.event_count = len(transaction_events)
    transaction.duplicate_event_count = duplicate_event_count
    transaction.first_event_at = min(_normalize_timestamp(event.event_timestamp) for event in transaction_events)
    transaction.last_event_at = max(_normalize_timestamp(event.event_timestamp) for event in transaction_events)

    if auto_commit:
        db.commit()
        db.refresh(transaction)
    else:
        db.flush()
    return transaction, False
