def test_agent_document_query(client, auth_headers):
    headers = auth_headers("ashutosh@novaworks.com")

    resp = client.post(
        "/api/agents/query",
        json={"message": "What is the critical airfoil chord tolerance specified in SOP-ENG-042?"},
        headers=headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "answer" in data
    assert data["evidence_status"] == "SUPPORTED"
    assert data["retrieval_mode"] == "hybrid"
    assert "confidence" not in data
    assert "reasoning_trace" not in data
    assert len(data["citations"]) > 0
    citation = data["citations"][0]
    assert citation["version_id"]
    assert citation["chunk_id"]
    assert citation["location_label"]
    assert citation["source_path"].endswith(f"/{citation['version_id']}/source")
    assert any("0.005" in data["answer"] or "tolerance" in data["answer"].lower() for _ in [1])

def test_agent_clearance_blocked(client, auth_headers):
    # Operator asking for restricted payroll/compensation
    headers = auth_headers("krish@novaworks.com")

    resp = client.post(
        "/api/agents/query",
        json={"message": "Show me the executive compensation and salary sheet"},
        headers=headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["execution_status"] == "BLOCKED_CLEARANCE"
    assert data["evidence_status"] == "ACCESS_DENIED"
    assert "don't have access" in data["answer"].lower()
