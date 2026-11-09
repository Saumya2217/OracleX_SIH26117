def test_model_health_requires_sign_in_and_reports_missing_model(client, monkeypatch, auth_headers):
    async def missing_model():
        return {
            "status": "model_missing",
            "engine": "Ollama Local Daemon",
            "provider": "Ollama",
            "model": "approved-model:1b",
            "active_model": None,
            "available_models": ["another-model:1b"],
            "mode": "MODEL_IMPORT_REQUIRED",
            "is_live_inference": False,
            "message": "The configured model is not installed.",
        }

    monkeypatch.setattr("app.api.agents.llm_client.check_health", missing_model)
    assert client.get("/api/agents/health").status_code == 401
    response = client.get("/api/agents/health", headers=auth_headers("saumy@novaworks.com"))
    assert response.status_code == 200
    assert response.json()["status"] == "model_missing"
    assert response.json()["is_live_inference"] is False


def test_feedback_response_identifies_persisted_record(client, db_session, auth_headers):
    from app.models.adaptation import FeedbackRecord

    response = client.post(
        "/api/agents/feedback",
        headers=auth_headers("saumy@novaworks.com"),
        json={"query_text": "Where is the leave policy?", "agent_response": "Synthetic answer", "rating": -1},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "recorded"
    assert db_session.get(FeedbackRecord, response.json()["feedback_id"]) is not None
