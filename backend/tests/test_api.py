import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app, engine
from app.models import BackgroundJob, Transaction, TransactionLabel
from app.security import create_access_token


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
    assert response.headers.get("X-Request-ID")


def test_ready(client: TestClient) -> None:
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


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

    tx_listing = client.get("/api/transactions?page=1&page_size=10&merchant=luxury", headers=headers)
    assert tx_listing.status_code == 200
    list_payload = tx_listing.json()
    assert "items" in list_payload
    assert list_payload["page"] == 1

    explanation = client.get(f"/api/explanations/{tx_id}", headers=headers)
    assert explanation.status_code == 200
    assert explanation.json()["top_factors"]
    assert explanation.json()["summary"]
    assert explanation.json()["ranked_contributions"]
    assert explanation.json()["narrative"]
    assert "direction" in explanation.json()["ranked_contributions"][0]
    assert "reason_codes" in explanation.json()

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
    assert queue_json["page"] == 1
    assert any(item["transaction_id"] == tx_id for item in queue_json["items"])

    assigned = client.post(
        f"/api/reviews/{tx_id}/assign",
        headers=headers,
        json={"assigned_to": "reviewer@meridian.ai", "note": "Assigning for priority queue"},
    )
    assert assigned.status_code == 200
    assert assigned.json()["assigned_to"] == "reviewer@meridian.ai"

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
    assert "assigned" in actions
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


def test_offline_model_evaluation(client: TestClient) -> None:
    headers = auth_headers(client, "admin@meridian.ai", "password123")
    for scenario in ["high_value_geo_attack", "card_testing_burst", "merchant_takeover"]:
        seeded = client.post(
            "/api/simulations/seed-scenarios",
            headers=headers,
            json={"scenario": scenario, "count": 20, "seed": 11},
        )
        assert seeded.status_code == 200

    with Session(bind=engine) as db:
        for index in range(12):
            tx = Transaction(
                amount=25 + index,
                merchant="local-store",
                country="US",
                card_last4=f"{3000 + index}",
            )
            db.add(tx)
            db.flush()
            db.add(TransactionLabel(transaction_id=tx.id, label="cleared", source="test_seed"))
        db.commit()

    evaluation = client.get("/api/models/evaluation", headers=headers)
    assert evaluation.status_code == 200
    payload = evaluation.json()
    assert payload["total_models"] >= 2
    assert payload["items"]
    first = payload["items"][0]
    assert "optimal_threshold" in first
    assert "brier_score" in first
    assert "cost_score" in first


def test_case_grouping_trends_and_ai_assist(client: TestClient) -> None:
    headers = auth_headers(client, "analyst@meridian.ai", "password123")
    seeded = client.post(
        "/api/simulations/seed-scenarios",
        headers=headers,
        json={"scenario": "high_value_geo_attack", "count": 8, "seed": 9},
    )
    assert seeded.status_code == 200
    tx_ids = seeded.json()["transaction_ids"]
    assert tx_ids

    for tx_id in tx_ids:
        scored = client.post("/api/scores", headers=headers, json={"transaction_id": tx_id})
        assert scored.status_code == 200

    groups = client.get("/api/cases/groups?status=all&limit=20", headers=headers)
    assert groups.status_code == 200
    payload = groups.json()
    assert payload["total_groups"] >= 1
    first_group = payload["items"][0]
    assert first_group["group_key"]

    summary = client.get(
        f"/api/cases/summary?group_key={first_group['group_key']}",
        headers=headers,
    )
    assert summary.status_code == 200
    assert summary.json()["summary"]

    suggestion = client.get(f"/api/reviews/{tx_ids[0]}/suggestion", headers=headers)
    assert suggestion.status_code == 200
    assert suggestion.json()["suggested_decision"] in {"approve", "review", "decline"}
    assert suggestion.json()["confidence"] >= 0

    trends = client.get("/api/metrics/trends", headers=headers)
    assert trends.status_code == 200
    trends_payload = trends.json()
    assert "fraud_trend" in trends_payload
    assert "top_risky_merchants" in trends_payload
    assert "top_risky_countries" in trends_payload

    audit_logs = client.get("/api/audit/logs?page=1&page_size=100", headers=headers)
    assert audit_logs.status_code == 200
    audit_payload = audit_logs.json()
    assert audit_payload["total"] >= 1
    if audit_payload["items"]:
        assert "@" in audit_payload["items"][0]["actor_email"]
        assert "***" in audit_payload["items"][0]["actor_email"]


def test_feature_service_and_rules_management(client: TestClient) -> None:
    admin_headers = auth_headers(client, "admin@meridian.ai", "password123")

    created = client.post(
        "/api/transactions",
        headers=admin_headers,
        json={"amount": 2200, "merchant": "marketplace", "country": "US", "card_last4": "4321"},
    )
    assert created.status_code == 200
    tx_id = created.json()["id"]

    feature_snapshot = client.get(f"/api/features/{tx_id}", headers=admin_headers)
    assert feature_snapshot.status_code == 200
    snapshot_payload = feature_snapshot.json()
    assert snapshot_payload["transaction_id"] == tx_id
    assert "velocity_1h" in snapshot_payload["features"]

    refresh = client.post("/api/features/refresh?window_hours=24", headers=admin_headers)
    assert refresh.status_code == 200
    refresh_payload = refresh.json()
    assert refresh_payload["window_hours"] == 24
    assert refresh_payload["job_id"] >= 1
    assert refresh_payload["status"] == "queued"

    job = client.get(f"/api/jobs/{refresh_payload['job_id']}", headers=admin_headers)
    assert job.status_code == 200
    assert job.json()["job_type"] == "feature_refresh"
    assert job.json()["status"] in {"queued", "running", "completed"}
    assert job.json()["attempts"] >= 1

    jobs = client.get("/api/jobs?job_type=feature_refresh", headers=admin_headers)
    assert jobs.status_code == 200
    assert jobs.json()["total"] >= 1

    summary = client.get("/api/jobs/summary", headers=admin_headers)
    assert summary.status_code == 200
    assert summary.json()["total"] >= 1

    retry = client.post(f"/api/jobs/{refresh_payload['job_id']}/retry", headers=admin_headers)
    assert retry.status_code == 200
    retry_payload = retry.json()
    assert retry_payload["retried_from_job_id"] == refresh_payload["job_id"]
    assert retry_payload["new_job_id"] >= 1

    retried_job = client.get(f"/api/jobs/{retry_payload['new_job_id']}", headers=admin_headers)
    assert retried_job.status_code == 200
    assert retried_job.json()["parent_job_id"] == refresh_payload["job_id"]
    assert retried_job.json()["attempts"] >= 2

    rule_name = f"rule_test_{uuid.uuid4().hex[:8]}"
    created_rule = client.post(
        "/api/rules",
        headers=admin_headers,
        json={"name": rule_name, "condition": "velocity_1h >= 4", "action": "review"},
    )
    assert created_rule.status_code == 200
    rule_id = created_rule.json()["id"]

    patched = client.patch(
        f"/api/rules/{rule_id}",
        headers=admin_headers,
        json={"condition": "velocity_1h >= 3", "action": "decline"},
    )
    assert patched.status_code == 200
    assert patched.json()["action"] == "decline"

    listed = client.get("/api/rules", headers=admin_headers)
    assert listed.status_code == 200
    assert any(row["id"] == rule_id for row in listed.json())

    logs = client.get("/api/audit/logs?action=rule_update", headers=admin_headers)
    assert logs.status_code == 200
    assert logs.json()["total"] >= 1


def test_auth_and_role_guards(client: TestClient) -> None:
    invalid_login = client.post(
        "/api/auth/login",
        json={"email": "admin@meridian.ai", "password": "wrong-password"},
    )
    assert invalid_login.status_code == 401
    assert invalid_login.json()["detail"] == "Invalid credentials"

    bad_token = client.get("/api/auth/me", headers={"Authorization": "Bearer not-a-token"})
    assert bad_token.status_code == 401

    unknown_token = create_access_token("missing-user@meridian.ai")
    unknown_user = client.get("/api/auth/me", headers={"Authorization": f"Bearer {unknown_token}"})
    assert unknown_user.status_code == 401

    viewer_headers = auth_headers(client, "viewer@meridian.ai", "password123")
    forbidden = client.post(
        "/api/transactions",
        headers=viewer_headers,
        json={"amount": 100, "merchant": "bookshop", "country": "US", "card_last4": "1000"},
    )
    assert forbidden.status_code == 403


def test_not_found_and_validation_paths(client: TestClient) -> None:
    headers = auth_headers(client, "admin@meridian.ai", "password123")

    assert client.get("/api/transactions/999999", headers=headers).status_code == 404
    assert client.get("/api/scores/999999", headers=headers).status_code == 404
    assert client.post("/api/scores", headers=headers, json={"transaction_id": 999999}).status_code == 404
    assert client.get("/api/explanations/999999", headers=headers).status_code == 404
    assert client.get("/api/reviews/999999/history", headers=headers).status_code == 404
    assert client.get("/api/cases/summary?group_key=does-not-exist", headers=headers).status_code == 404
    assert client.get("/api/reviews/999999/suggestion", headers=headers).status_code == 404
    assert client.get("/api/jobs/999999", headers=headers).status_code == 404
    assert client.post("/api/jobs/999999/retry", headers=headers).status_code == 404


def test_retry_non_refresh_job_returns_400(client: TestClient) -> None:
    headers = auth_headers(client, "admin@meridian.ai", "password123")
    with Session(bind=engine) as db:
        job = BackgroundJob(
            job_type="other_job",
            status="completed",
            attempts=1,
            metadata_json="{}",
            result_json="{}",
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        job_id = job.id

    retry = client.post(f"/api/jobs/{job_id}/retry", headers=headers)
    assert retry.status_code == 400
    assert retry.json()["detail"] == "Only feature_refresh jobs are retryable"


def test_duplicate_rule_and_missing_rule_update(client: TestClient) -> None:
    headers = auth_headers(client, "admin@meridian.ai", "password123")
    rule_name = f"rule_test_{uuid.uuid4().hex[:8]}"
    created = client.post(
        "/api/rules",
        headers=headers,
        json={"name": rule_name, "condition": "amount > 10", "action": "review"},
    )
    assert created.status_code == 200

    duplicate = client.post(
        "/api/rules",
        headers=headers,
        json={"name": rule_name, "condition": "amount > 99", "action": "decline"},
    )
    assert duplicate.status_code == 400
    assert duplicate.json()["detail"] == "Rule with this name already exists"

    missing = client.patch(
        "/api/rules/999999",
        headers=headers,
        json={"condition": "amount > 25"},
    )
    assert missing.status_code == 404
    assert missing.json()["detail"] == "Rule not found"
