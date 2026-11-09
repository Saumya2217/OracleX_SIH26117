from app.agents.orchestrator import AIOrchestrator
from app.models.company import User


def test_conversation_persists_messages_runs_and_owner_boundary(client, auth_headers):
    owner = auth_headers("ashutosh@novaworks.com")
    other_user = auth_headers("hetvi@novaworks.com")
    first = client.post(
        "/api/agents/query",
        json={"message": "What is the critical airfoil chord tolerance specified in SOP-ENG-042?"},
        headers=owner,
    )
    assert first.status_code == 200, first.text
    first_data = first.json()
    assert first_data["conversation_id"]
    assert first_data["citations"]
    assert "retention_until" in client.get("/api/conversations", headers=owner).json()[0]

    second = client.post(
        "/api/agents/query",
        json={"message": "Summarize that again.", "conversation_id": first_data["conversation_id"]},
        headers=owner,
    )
    assert second.status_code == 200, second.text
    assert second.json()["evidence_status"] == "SUPPORTED"
    assert second.json()["citations"]

    detail = client.get(f"/api/conversations/{first_data['conversation_id']}", headers=owner)
    assert detail.status_code == 200
    messages = detail.json()["messages"]
    assert [message["sequence"] for message in messages] == [1, 2, 3, 4]
    assert [message["role"] for message in messages] == ["USER", "ASSISTANT", "USER", "ASSISTANT"]
    assert messages[1]["run"]["status"] == "COMPLETED"
    assert messages[1]["run"]["citations"]
    assert messages[1]["run"]["model_id"]
    assert messages[1]["run"]["prompt_version"] == "oraclex-agent-v1"
    assert "reasoning_trace" not in messages[1]["run"]
    assert "confidence" not in messages[1]["run"]

    assert client.get(f"/api/conversations/{first_data['conversation_id']}", headers=other_user).status_code == 404
    assert all(item["id"] != first_data["conversation_id"] for item in client.get("/api/conversations", headers=other_user).json())

    archived = client.patch(
        f"/api/conversations/{first_data['conversation_id']}",
        json={"status": "ARCHIVED"},
        headers=owner,
    )
    assert archived.status_code == 200
    assert all(item["id"] != first_data["conversation_id"] for item in client.get("/api/conversations", headers=owner).json())
    assert any(item["id"] == first_data["conversation_id"] for item in client.get("/api/conversations?include_archived=true", headers=owner).json())
    blocked = client.post(
        "/api/agents/query",
        json={"message": "Continue this conversation.", "conversation_id": first_data["conversation_id"]},
        headers=owner,
    )
    assert blocked.status_code == 409


def test_saved_answer_is_redacted_after_source_access_is_revoked(client, auth_headers, db_session):
    owner = auth_headers("ashutosh@novaworks.com")
    result = client.post(
        "/api/agents/query",
        json={"message": "What is the critical airfoil chord tolerance specified in SOP-ENG-042?"},
        headers=owner,
    ).json()
    assert result["citations"]

    user = db_session.query(User).filter(User.email == "ashutosh@novaworks.com").one()
    original_clearance = user.clearance_level
    user.clearance_level = 1
    db_session.commit()
    try:
        detail = client.get(f"/api/conversations/{result['conversation_id']}", headers=owner)
        assert detail.status_code == 200
        assistant = detail.json()["messages"][1]
        assert assistant["run"]["evidence_status"] == "ACCESS_REVOKED"
        assert assistant["run"]["citations"] == []
        assert "access" in assistant["content"].lower()
    finally:
        user = db_session.query(User).filter(User.email == "ashutosh@novaworks.com").one()
        user.clearance_level = original_clearance
        db_session.commit()


def test_failed_assistant_run_is_persisted(client, auth_headers, monkeypatch):
    owner = auth_headers("arya@novaworks.com")

    async def fail_run(**_kwargs):
        raise RuntimeError("simulated local inference outage")

    monkeypatch.setattr(AIOrchestrator, "process_query", fail_run)
    response = client.post("/api/agents/query", json={"message": "Test a saved failure."}, headers=owner)
    assert response.status_code == 503

    conversations = client.get("/api/conversations", headers=owner).json()
    failed_conversation = next(item for item in conversations if item["title"] == "Test a saved failure.")
    detail = client.get(f"/api/conversations/{failed_conversation['id']}", headers=owner).json()
    assert len(detail["messages"]) == 2
    assistant = detail["messages"][1]
    assert assistant["run"]["status"] == "FAILED"
    assert assistant["run"]["safe_error_message"]
    assert "simulated local inference outage" not in str(detail)
