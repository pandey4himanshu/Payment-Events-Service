from __future__ import annotations

import json
import uuid
from copy import deepcopy
from pathlib import Path


SOURCE_PATH = Path("data/sample_events.json")
TARGET_PATH = Path("data/sample_events_augmented.json")


def main() -> None:
    if not SOURCE_PATH.exists():
        raise SystemExit(f"Missing source dataset at {SOURCE_PATH}")

    with SOURCE_PATH.open("r", encoding="utf-8") as handle:
        events = json.load(handle)

    if not events:
        raise SystemExit("Source dataset is empty")

    extra_events = []
    seed = deepcopy(events[0])

    duplicate = deepcopy(seed)
    extra_events.append(duplicate)

    conflict = deepcopy(seed)
    conflict["event_id"] = str(uuid.uuid4())
    conflict["transaction_id"] = "custom_conflict_txn"
    conflict["merchant_id"] = "merchant_custom"
    conflict["merchant_name"] = "OrbitCart"
    conflict["event_type"] = "payment_failed"
    extra_events.append(conflict)

    settlement = deepcopy(conflict)
    settlement["event_id"] = str(uuid.uuid4())
    settlement["event_type"] = "settled"
    extra_events.append(settlement)

    pending = deepcopy(conflict)
    pending["event_id"] = str(uuid.uuid4())
    pending["transaction_id"] = "custom_pending_txn"
    pending["event_type"] = "payment_processed"
    extra_events.append(pending)

    with TARGET_PATH.open("w", encoding="utf-8") as handle:
        json.dump(events + extra_events, handle, indent=2)

    print(f"Wrote {len(events) + len(extra_events)} events to {TARGET_PATH}")


if __name__ == "__main__":
    main()
