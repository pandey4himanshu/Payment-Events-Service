from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.events import EventIn, EventIngestResponse
from app.services.events import EventValidationError, ingest_event


router = APIRouter(prefix="/events", tags=["events"])


@router.post("", response_model=EventIngestResponse, status_code=status.HTTP_201_CREATED)
def create_event(payload: EventIn, response: Response, db: Session = Depends(get_db)) -> EventIngestResponse:
    try:
        transaction, duplicate = ingest_event(db, payload)
    except EventValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    response.status_code = status.HTTP_200_OK if duplicate else status.HTTP_201_CREATED
    message = "Duplicate event ignored safely." if duplicate else "Event ingested successfully."

    return EventIngestResponse(
        inserted=not duplicate,
        duplicate=duplicate,
        message=message,
        transaction_id=transaction.transaction_id,
        current_payment_status=transaction.payment_status,
        current_settlement_status=transaction.settlement_status,
        reconciliation_status=transaction.reconciliation_status,
    )
