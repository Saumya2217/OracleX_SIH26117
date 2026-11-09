def test_vector_search_authorized(client, auth_headers):
    headers = auth_headers("saumy@novaworks.com")

    resp = client.post(
        "/api/knowledge/search",
        json={"query": "turbine blade machining tolerance coolant", "limit": 3},
        headers=headers
    )
    assert resp.status_code == 200
    results = resp.json()
    assert len(results) > 0
    top_result = results[0]
    assert "content" in top_result
    assert top_result["similarity_score"] >= 0.0

def test_vector_search_clearance_filtering(client, auth_headers):
    # Operator searching for classified executive terms
    headers = auth_headers("krish@novaworks.com")

    resp = client.post(
        "/api/knowledge/search",
        json={"query": "strategic defense capital expenditure compensation", "limit": 5},
        headers=headers
    )
    assert resp.status_code == 200
    results = resp.json()
    # Level 4 documents must be omitted from Operator results
    for r in results:
        assert r["clearance_level"] <= 1
