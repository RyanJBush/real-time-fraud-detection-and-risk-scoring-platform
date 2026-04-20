import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client


def auth_headers(client: TestClient, email: str, password: str) -> dict[str, str]:
    token = client.post("/api/auth/login", json={"email": email, "password": password}).json()[
        "access_token"
    ]
    return {"Authorization": f"Bearer {token}"}


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_login_and_me(client: TestClient) -> None:
    response = client.post(
        "/api/auth/login",
        json={"email": "admin@meridian.ai", "password": "password123"},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]

    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["role"] == "Admin"


def test_transaction_scoring_flow(client: TestClient) -> None:
    headers = auth_headers(client, "analyst@meridian.ai", "password123")

    created = client.post(
        "/api/transactions",
        headers=headers,
        json={"amount": 12000, "merchant": "luxury-goods", "country": "US", "card_last4": "1234"},
    )
    assert created.status_code == 200
    tx_id = created.json()["id"]

    scored = client.post("/api/scores", headers=headers, json={"transaction_id": tx_id})
    assert scored.status_code == 200
    scored_json = scored.json()
    assert scored_json["decision"] in {"decline", "review", "approve"}
    assert scored_json["reason_codes"]
    assert "model_version" in scored_json
    assert scored_json["threshold_approve_max"] == 0.4
    assert scored_json["threshold_review_max"] == 0.75

    fetched = client.get(f"/api/scores/{tx_id}", headers=headers)
    assert fetched.status_code == 200

    explanation = client.get(f"/api/explanations/{tx_id}", headers=headers)
    assert explanation.status_code == 200
    assert explanation.json()["top_factors"]
    assert explanation.json()["summary"]
    assert explanation.json()["ranked_contributions"]

    metrics = client.get("/api/metrics/summary", headers=headers)
    assert metrics.status_code == 200
    assert metrics.json()["scored_transactions"] >= 1
    assert "fraud_rate" in metrics.json()
    assert "blocked_fraud_value" in metrics.json()


def test_review_queue_and_override_flow(client: TestClient) -> None:
    headers = auth_headers(client, "analyst@meridian.ai", "password123")

    created = client.post(
        "/api/transactions",
        headers=headers,
        json={"amount": 15000, "merchant": "crypto-exchange", "country": "IR", "card_last4": "8888"},
    )
    assert created.status_code == 200
    tx_id = created.json()["id"]

    scored = client.post("/api/scores", headers=headers, json={"transaction_id": tx_id})
    assert scored.status_code == 200
    assert scored.json()["decision"] in {"review", "decline"}

    queue = client.get("/api/reviews/queue", headers=headers)
    assert queue.status_code == 200
    queue_json = queue.json()
    assert queue_json["total"] >= 1
    assert any(item["transaction_id"] == tx_id for item in queue_json["items"])

    override = client.post(
        f"/api/reviews/{tx_id}/decision",
        headers=headers,
        json={"final_decision": "approve", "note": "Validated as trusted customer"},
    )
    assert override.status_code == 200
    assert override.json()["status"] == "resolved"
    assert override.json()["final_decision"] == "approve"

    history = client.get(f"/api/reviews/{tx_id}/history", headers=headers)
    assert history.status_code == 200
    actions = [event["action"] for event in history.json()]
    assert "queued" in actions
    assert "override" in actions


def test_seeded_fraud_scenarios(client: TestClient) -> None:
    headers = auth_headers(client, "admin@meridian.ai", "password123")
    seeded = client.post(
        "/api/simulations/seed-scenarios",
        headers=headers,
        json={"scenario": "high_value_geo_attack", "count": 5, "seed": 7},
    )
    assert seeded.status_code == 200
    payload = seeded.json()
    assert payload["count"] == 5
    assert len(payload["transaction_ids"]) == 5

    for tx_id in payload["transaction_ids"]:
        scored = client.post("/api/scores", headers=headers, json={"transaction_id": tx_id})
        assert scored.status_code == 200

    metrics = client.get("/api/metrics/summary", headers=headers)
    assert metrics.status_code == 200
    assert metrics.json()["fraud_rate"] >= 0
