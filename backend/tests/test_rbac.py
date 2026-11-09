def test_rbac_clearance_filtering(client, auth_headers):
    headers_director = auth_headers("saumy@novaworks.com")
    
    docs_resp = client.get("/api/knowledge/documents", headers=headers_director)
    assert docs_resp.status_code == 200
    docs = docs_resp.json()
    doc_titles = [d["title"] for d in docs]
    # Director should see Restricted Level 4 doc
    assert any("RESTRICTED" in t for t in doc_titles)

    headers_operator = auth_headers("krish@novaworks.com")

    docs_op_resp = client.get("/api/knowledge/documents", headers=headers_operator)
    assert docs_op_resp.status_code == 200
    op_docs = docs_op_resp.json()
    op_titles = [d["title"] for d in op_docs]
    # Operator must NOT see Level 4 doc
    assert not any("RESTRICTED" in t for t in op_titles)
    # Operator should see Public Handbook
    assert any("Handbook" in t or "HR-001" in t for t in op_titles)

def test_direct_restricted_access_denied(client, auth_headers):
    # Director finds the restricted doc ID
    docs = client.get("/api/knowledge/documents", headers=auth_headers("saumy@novaworks.com")).json()
    restricted_doc = next(d for d in docs if "RESTRICTED" in d["title"])
    restricted_id = restricted_doc["id"]

    # Operator attempts to read the restricted doc
    resp = client.get(f"/api/knowledge/documents/{restricted_id}", headers=auth_headers("krish@novaworks.com"))
    assert resp.status_code == 403
    assert "Clearance Violation" in resp.json()["detail"]
