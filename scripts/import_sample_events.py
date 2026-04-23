from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from sqlalchemy.orm import Session

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.db.init_db import init_db
from app.db.session import SessionLocal
from app.schemas.events import EventIn
from app.services.events import EventValidationError, ingest_event


DATA_PATH = Path(os.getenv("DATA_FILE", "data/sample_events.json"))


def main() -> None:
    if not DATA_PATH.exists():
        raise SystemExit(f"Missing dataset at {DATA_PATH}. Download it before running the import.")

    init_db()

    inserted = 0
    duplicates = 0
    rejected = 0

    with DATA_PATH.open("r", encoding="utf-8") as handle:
        payloads = json.load(handle)

    with SessionLocal() as db:
        for index, item in enumerate(payloads, start=1):
            try:
                _, duplicate = ingest_event(db, EventIn(**item), auto_commit=False)
                if duplicate:
                    duplicates += 1
                else:
                    inserted += 1
            except EventValidationError:
                rejected += 1
                db.rollback()
                continue

            if index % 500 == 0:
                db.commit()

        db.commit()

    print(
        json.dumps(
            {"inserted": inserted, "duplicates": duplicates, "rejected": rejected, "total": len(payloads)},
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
