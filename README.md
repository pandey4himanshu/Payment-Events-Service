# Setu Solutions Engineer Take-Home Assignment

A lightweight backend service for payment event ingestion, transaction retrieval, and reconciliation reporting.

This solution is intentionally practical and production-minded:

- idempotent event ingestion using unique `event_id`
- SQL-backed filtering, pagination, and aggregation
- discrepancy classification for ops teams
- local setup that works with SQLite
- deployment-ready configuration for Render or any similar platform

## Live Deployment

- Base URL: `https://payment-events-service.onrender.com`
- API Docs: `https://payment-events-service.onrender.com/docs`
- Health Check: `https://payment-events-service.onrender.com/health`

For the best reviewer experience, start with:

1. `GET /`
2. `GET /docs`
3. `GET /transactions?page=1&page_size=5`
4. `GET /reconciliation/summary?group_by=merchant`
5. `GET /reconciliation/discrepancies?page=1&page_size=5`

## Reviewer Quick Start

If you are reviewing the hosted service, you can validate the assignment quickly using the public deployment:

1. open `/docs`
2. verify `POST /events` accepts and deduplicates repeated `event_id`s
3. verify `GET /transactions` supports filters, pagination, and sorting
4. verify `GET /transactions/{transaction_id}` returns event history
5. verify reconciliation summary and discrepancy endpoints return populated results

If you want to run locally instead:

```bash
make demo-setup
make run
```

## Live Project Shape

- Framework: `FastAPI`
- Database: `SQLite` locally, any SQLAlchemy-supported SQL database in deployment
- ORM: `SQLAlchemy 2.x`
- Validation: `Pydantic`
- Testing: `pytest`
- Deployment artifact: `render.yaml`

## Architecture Overview

The service is organized into a few small layers:

- `app/routes`: API endpoints
- `app/schemas`: request and response contracts
- `app/models`: SQLAlchemy models
- `app/services`: event ingestion and reconciliation logic
- `app/db`: engine/session/init helpers
- `scripts`: sample-data import and dataset augmentation utilities
- `tests`: API-level verification

Flow:

1. `POST /events` validates an incoming payment lifecycle event.
2. The service checks whether `event_id` already exists.
3. If the event is new, it is stored in `payment_events`.
4. The corresponding transaction is created or updated.
5. Payment, settlement, and reconciliation states are derived from event history.
6. Operations APIs query the transaction table directly with SQL-backed filters and aggregations.

## Schema Design

### `merchants`

- `merchant_id` unique
- `merchant_name`

### `transactions`

- `transaction_id` unique
- `merchant_id` foreign key
- `amount`, `currency`
- `payment_status`
- `settlement_status`
- `reconciliation_status`
- `discrepancy_reason`
- `event_count`
- `duplicate_event_count`
- `first_event_at`, `last_event_at`

### `payment_events`

- `event_id` unique
- `event_type`
- `transaction_id` foreign key
- `merchant_id` foreign key
- `event_timestamp`
- `raw_payload`

## Indexing Strategy

The project includes indexes on the fields most likely to be queried:

- unique index on `payment_events.event_id`
- unique index on `transactions.transaction_id`
- index on `transactions.merchant_id`
- index on `transactions.payment_status`
- index on `transactions.settlement_status`
- index on `transactions.reconciliation_status`
- index on `transactions.last_event_at`
- composite index on `(merchant_id, last_event_at)`
- index on `payment_events(transaction_id, event_timestamp)`

This keeps list filters, transaction lookups, and reconciliation summaries efficient and SQL-driven.

## Idempotency Approach

Idempotency is handled through a unique constraint on `payment_events.event_id`.

- if an incoming `event_id` is new, the event is inserted and the transaction state is recomputed
- if the `event_id` already exists, the service returns a safe duplicate response and does not mutate transaction state
- event history is preserved for all unique events

Duplicate detection is visible in the API response through the `duplicate` flag.

## Reconciliation Logic

The service derives transaction state from stored events and classifies discrepancies using human-readable reasons:

- `processed_not_settled`
- `settled_after_failure`
- `settled_without_processed`
- `conflicting_terminal_payment_events`
- `duplicate_conflicting_events`

This makes the discrepancy endpoint more useful for operations teams than a generic boolean mismatch.

## API Documentation

### `POST /events`

Ingests a single lifecycle event:

- `payment_initiated`
- `payment_processed`
- `payment_failed`
- `settled`

Behavior:

- idempotent on `event_id`
- transaction state updates automatically
- returns duplicate metadata if re-submitted

Example payload:

```json
{
  "event_id": "evt_demo_1001",
  "event_type": "payment_initiated",
  "transaction_id": "txn_demo_1001",
  "merchant_id": "merchant_demo",
  "merchant_name": "OrbitCart",
  "amount": 1999.99,
  "currency": "INR",
  "timestamp": "2026-01-08T12:11:58.085567+00:00"
}
```

### `GET /transactions`

Supports:

- filtering by `merchant_id`
- filtering by `payment_status`
- filtering by `settlement_status`
- filtering by `reconciliation_status`
- filtering by `date_from` and `date_to`
- pagination via `page` and `page_size`
- sorting via `sort_by` and `sort_order`

### `GET /transactions/{transaction_id}`

Returns:

- transaction details
- merchant details
- current derived state
- ordered event history

### `GET /reconciliation/summary`

Supports grouping by:

- `merchant`
- `date`
- `status`

Returns aggregated counts and amount totals.

### `GET /reconciliation/discrepancies`

Returns transactions with inconsistent payment and settlement state, including `discrepancy_reason`.

## Hosted API Smoke Test

The deployed service can be checked with these URLs:

- `GET https://payment-events-service.onrender.com/`
- `GET https://payment-events-service.onrender.com/health`
- `GET https://payment-events-service.onrender.com/docs`
- `GET https://payment-events-service.onrender.com/transactions?page=1&page_size=5`
- `GET https://payment-events-service.onrender.com/reconciliation/summary?group_by=merchant`
- `GET https://payment-events-service.onrender.com/reconciliation/discrepancies?page=1&page_size=5`

## Local Setup

### 1. Create a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment

```bash
cp .env.example .env
```

Default local database:

```env
DATABASE_URL=sqlite:///./setu.db
```

### 4. Download sample data

```bash
mkdir -p data
curl -s https://raw.githubusercontent.com/SetuHQ/hiring-assignments/main/solutions-engineer/sample_events.json -o data/sample_events.json
```

### 5. Import the sample events

```bash
PYTHONPATH=. python scripts/import_sample_events.py
```

For a cleaner demo or reviewer setup, use:

```bash
make seed
```

### 6. Run the API

```bash
uvicorn app.main:app --reload
```

Or:

```bash
make run
```

Interactive docs:

- `http://127.0.0.1:8000/docs`

## Postman Collection

The repository includes `postman_collection.json` covering:

- health
- event ingestion
- transaction listing
- transaction detail
- reconciliation summary
- discrepancy listing

To use the deployed service in Postman, set:

```text
base_url = https://payment-events-service.onrender.com
```

## Dataset Notes

The base dataset comes from the Setu assignment repository:

- `data/sample_events.json`

An additional helper script is included to produce a slightly more distinctive demo dataset with a few custom discrepancy scenarios:

```bash
PYTHONPATH=. python scripts/generate_custom_events.py
```

That script writes:

- `data/sample_events_augmented.json`

To import the augmented file instead of the base sample:

```bash
DATA_FILE=data/sample_events_augmented.json PYTHONPATH=. python scripts/import_sample_events.py
```

Or:

```bash
make seed-augmented
```

## Testing

Run:

```bash
pytest
```

Or:

```bash
make test
```

## Reviewer-Friendly Commands

If you want the happy path to look polished in the README or live demo, use:

```bash
make demo-setup
make run
```

This keeps the main workflow simple and avoids exposing implementation details like `PYTHONPATH=.` during the walkthrough.

The test suite currently validates:

- idempotent duplicate event handling
- transaction detail with ordered event history
- discrepancy detection for invalid settlement flow

## Deployment

The repository includes `render.yaml` for easy deployment on Render.

Recommended deployment path:

1. create a Render Postgres instance in the same region as the web service
2. create a new web service from this repository
3. set `DATABASE_URL` to the Postgres internal URL
4. set `AUTO_SEED_DATA=true`
5. deploy the service

On first start, the service can automatically import the sample dataset if the database is empty.

Current public deployment:

- `https://payment-events-service.onrender.com`

For a stronger production deployment, use Postgres in the hosted environment rather than SQLite.

## Assumptions And Tradeoffs

- I kept the service synchronous because the workload is DB-centric and the assignment values clarity over complexity.
- I used SQLAlchemy models plus derived transaction state rather than a full event-sourcing framework.
- SQLite is the local default for a zero-friction review experience.
- The service is already compatible with stronger SQL backends through `DATABASE_URL`.
- Authentication was intentionally left out because it was not required in the prompt.

## What I Would Improve With More Time

- add Alembic migration history instead of relying on `create_all`
- add bulk ingestion endpoint for faster dataset loading
- support richer reconciliation windows and SLA-based delayed settlement rules
- add structured logging and request IDs
- add Docker Compose with Postgres for an even closer production setup

## AI Usage Disclosure

AI was used to accelerate scaffolding, documentation refinement, and implementation support.

All schema choices, event-state rules, discrepancy logic, and final code were reviewed and adapted manually for this submission.
