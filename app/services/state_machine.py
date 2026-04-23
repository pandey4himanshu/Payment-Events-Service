from __future__ import annotations

from collections import Counter

from app.models.entities import PaymentEvent


def derive_transaction_state(events: list[PaymentEvent]) -> tuple[str, str, str, str | None, int]:
    event_types = [event.event_type for event in events]
    counts = Counter(event_types)
    duplicate_event_count = max(len(events) - len(set((e.event_type, e.event_timestamp, str(e.amount)) for e in events)), 0)

    has_initiated = counts["payment_initiated"] > 0
    has_processed = counts["payment_processed"] > 0
    has_failed = counts["payment_failed"] > 0
    has_settled = counts["settled"] > 0

    if has_failed:
        payment_status = "failed"
    elif has_processed:
        payment_status = "processed"
    elif has_initiated:
        payment_status = "initiated"
    else:
        payment_status = "unknown"

    settlement_status = "settled" if has_settled else "pending"

    reasons: list[str] = []
    if has_processed and not has_settled:
        reasons.append("processed_not_settled")
    if has_failed and has_settled:
        reasons.append("settled_after_failure")
    if has_settled and not has_processed:
        reasons.append("settled_without_processed")
    if has_failed and has_processed:
        reasons.append("conflicting_terminal_payment_events")
    if duplicate_event_count > 0:
        reasons.append("duplicate_conflicting_events")

    if reasons:
        reconciliation_status = "discrepant"
    elif has_processed and has_settled:
        reconciliation_status = "matched"
    elif has_processed and not has_settled:
        reconciliation_status = "pending_settlement"
    elif has_failed:
        reconciliation_status = "closed_failed"
    else:
        reconciliation_status = "pending"

    discrepancy_reason = ",".join(reasons) if reasons else None
    return payment_status, settlement_status, reconciliation_status, discrepancy_reason, duplicate_event_count
