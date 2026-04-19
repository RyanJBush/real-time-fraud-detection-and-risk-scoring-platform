def test_ingestion_scoring_and_explanation_pipeline(client):
    payload = {
        "account_id": "acct_100",
        "merchant_id": "mrc_200",
        "amount": 3425.50,
        "currency": "USD",
        "channel": "wire",
    }

    ingest_response = client.post("/api/v1/transactions/ingest", json=payload)
    assert ingest_response.status_code == 200
    ingest_data = ingest_response.json()
    assert ingest_data["transaction_id"] > 0
    assert ingest_data["decision"]["decision"] in {"approve", "review", "decline"}
    assert "high_amount" in ingest_data["decision"]["rule_flags"]

    tx_id = ingest_data["transaction_id"]

    score_response = client.post("/api/v1/scoring", json={"transaction_id": tx_id})
    assert score_response.status_code == 200
    score_data = score_response.json()
    assert score_data["transaction_id"] == tx_id
    assert 0.0 <= score_data["risk_score"] <= 1.0

    explanation_response = client.get(f"/api/v1/explanations/{tx_id}")
    assert explanation_response.status_code == 200
    explanation_data = explanation_response.json()
    assert explanation_data["transaction_id"] == tx_id
    assert len(explanation_data["top_features"]) == 3


def test_not_found_for_unknown_transaction(client):
    score_response = client.post("/api/v1/scoring", json={"transaction_id": 999})
    assert score_response.status_code == 404

    explanation_response = client.get("/api/v1/explanations/999")
    assert explanation_response.status_code == 404
