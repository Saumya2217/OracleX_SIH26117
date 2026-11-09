def test_company_registration_and_empty_knowledge_acceptance(empty_client):
    # 1. Register a new company (e.g. LensCraft Photography Studio)
    reg_payload = {
        "admin_name": "Elena Vance",
        "company_name": "LensCraft Studio",
        "industry": "Photography",
        "domain": "lenscraft.com",
        "admin_email": "elena@lenscraft.com",
        "password": "StudioPassword123!"
    }
    reg_resp = empty_client.post(
        "/api/auth/register-company",
        json=reg_payload,
        headers={"X-Setup-Token": "test-bootstrap-token-12345"},
    )
    assert reg_resp.status_code == 200
    token_data = reg_resp.json()
    assert "access_token" in token_data
    token = token_data["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Verify starter departments created based on Photography industry
    depts_resp = empty_client.get("/api/company/departments", headers=headers)
    assert depts_resp.status_code == 200
    dept_names = [d["name"] for d in depts_resp.json()]
    assert "Photography" in dept_names
    assert "Editing" in dept_names

    # 2. Acceptance Test: Empty Company Knowledge
    # Newly registered company has ZERO uploaded documents.
    docs_resp = empty_client.get("/api/knowledge/documents", headers=headers)
    assert docs_resp.status_code == 200
    assert len(docs_resp.json()) == 0

    # Ask for leave policy - MUST NOT FABRICATE
    query_resp = empty_client.post(
        "/api/agents/query",
        json={"message": "What is our company leave policy and vacation hours?"},
        headers=headers
    )
    assert query_resp.status_code == 200
    answer = query_resp.json()["answer"]
    assert "don't have enough authorized company evidence" in answer.lower()
    assert query_resp.json()["evidence_status"] == "INSUFFICIENT_EVIDENCE"

    # Generic questions also abstain: this assistant is grounded only in
    # authorized company evidence.
    general_resp = empty_client.post(
        "/api/agents/query",
        json={"message": "What is a balance sheet?"},
        headers=headers
    )
    assert general_resp.status_code == 200
    gen_answer = general_resp.json()["answer"]
    assert "don't have enough authorized company evidence" in gen_answer.lower()
    assert general_resp.json()["evidence_status"] == "INSUFFICIENT_EVIDENCE"
    assert general_resp.json()["citations"] == []

def test_department_crud(client, auth_headers):
    headers = auth_headers("saumy@novaworks.com")

    # Create Department
    create_resp = client.post("/api/company/departments", json={
        "name": "Customer Experience",
        "code": "CX",
        "description": "Customer support and experience operations"
    }, headers=headers)
    assert create_resp.status_code == 200
    dept_id = create_resp.json()["id"]

    # Update Department
    update_resp = client.put(f"/api/company/departments/{dept_id}", json={
        "name": "Customer Experience & Success"
    }, headers=headers)
    assert update_resp.status_code == 200
    assert update_resp.json()["name"] == "Customer Experience & Success"

    # Delete Department
    del_resp = client.delete(f"/api/company/departments/{dept_id}", headers=headers)
    assert del_resp.status_code == 200
    assert del_resp.json()["status"] == "success"

def test_document_upload_query_and_delete(client, auth_headers):
    headers = auth_headers("saumy@novaworks.com")

    # Upload test policy file
    test_content = b"TEST COMPANY TRAVEL POLICY\nEmployees travelling for company business are reimbursed up to $150 per diem for lodging."
    files = {"file": ("Travel_Policy_2026.txt", test_content, "text/plain")}
    data = {"title": "Company Travel Policy 2026", "clearance_level": 1, "is_company_wide": True}

    upload_resp = client.post("/api/knowledge/upload", files=files, data=data, headers=headers)
    assert upload_resp.status_code == 202
    upload = upload_resp.json()
    assert upload["job"]["state"] == "SUCCEEDED"
    doc_id = upload["document"]["id"]

    # Query about travel policy
    q_resp = client.post("/api/agents/query", json={"message": "What is the travel reimbursement per diem?"}, headers=headers)
    assert q_resp.status_code == 200
    assert "150" in q_resp.json()["answer"]

    # Delete the document
    del_resp = client.delete(f"/api/knowledge/documents/{doc_id}", headers=headers)
    assert del_resp.status_code == 200
    assert del_resp.json()["status"] == "success"

    # Verify document is gone from list
    list_resp = client.get("/api/knowledge/documents", headers=headers)
    assert all(d["id"] != doc_id for d in list_resp.json())
