from __future__ import annotations


def sample_event(**overrides: str) -> dict:
    payload = {
        "event_id": "evt_001",
        "event_type": "payment_initiated",
        "transaction_id": "txn_001",
        "merchant_id": "merchant_1",
        "merchant_name": "FreshBasket",
        "amount": 1200.50,
        "currency": "INR",
        "timestamp": "2026-01-08T12:11:58.085567+00:00",
    }
    payload.update(overrides)
    return payload


def test_event_ingestion_is_idempotent(client) -> None:
    first = client.post("/events", json=sample_event())
    assert first.status_code == 201
    assert first.json()["duplicate"] is False

    duplicate = client.post("/events", json=sample_event())
    assert duplicate.status_code == 200
    assert duplicate.json()["duplicate"] is True


def test_transaction_detail_contains_event_history(client) -> None:
    client.post("/events", json=sample_event())
    client.post("/events", json=sample_event(event_id="evt_002", event_type="payment_processed"))
    client.post("/events", json=sample_event(event_id="evt_003", event_type="settled"))

    response = client.get("/transactions/txn_001")
    assert response.status_code == 200
    data = response.json()
    assert data["payment_status"] == "processed"
    assert data["settlement_status"] == "settled"
    assert len(data["event_history"]) == 3


def test_discrepancies_endpoint_returns_failed_then_settled_cases(client) -> None:
    client.post("/events", json=sample_event(transaction_id="txn_bad", event_id="evt_010", event_type="payment_failed"))
    client.post("/events", json=sample_event(transaction_id="txn_bad", event_id="evt_011", event_type="settled"))

    response = client.get("/reconciliation/discrepancies")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["discrepancy_reason"] is not None
