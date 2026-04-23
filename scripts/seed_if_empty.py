from __future__ import annotations

import os

from sqlalchemy import func, select

from app.db.init_db import init_db
from app.db.session import SessionLocal
from app.models import PaymentEvent
from scripts.import_sample_events import main as import_main


def main() -> None:
    if os.getenv("AUTO_SEED_DATA", "false").lower() != "true":
        print("AUTO_SEED_DATA is not enabled; skipping seed check.")
        return

    init_db()
    with SessionLocal() as db:
        existing_events = db.scalar(select(func.count(PaymentEvent.id))) or 0

    if existing_events > 0:
        print(f"Database already contains {existing_events} events; skipping seed.")
        return

    print("Database is empty; importing sample dataset.")
    import_main()


if __name__ == "__main__":
    main()
