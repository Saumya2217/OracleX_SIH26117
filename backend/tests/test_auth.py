def test_login_success(client):
    response = client.post("/api/auth/login", json={
        "email": "saumy@novaworks.com",
        "password": "password123"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "saumy@novaworks.com"
    assert data["user"]["clearance_level"] == 4

def test_login_normalizes_email(client):
    response = client.post("/api/auth/login", json={
        "email": "  SAUMY@NOVAWORKS.COM  ",
        "password": "password123"
    })
    assert response.status_code == 200
    assert response.json()["user"]["email"] == "saumy@novaworks.com"

def test_login_invalid_password(client):
    response = client.post("/api/auth/login", json={
        "email": "saumy@novaworks.com",
        "password": "wrongpassword"
    })
    assert response.status_code == 401

def test_protected_endpoint_requires_token(client):
    response = client.get("/api/auth/me")
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"

def test_demo_and_seed_routes_are_absent(client):
    assert client.post("/api/auth/demo-switch/ARYA").status_code == 404
    assert client.post("/api/company/seed").status_code == 404

def test_bootstrap_requires_token_and_runs_once(empty_client):
    payload = {
        "admin_name": "Initial Admin",
        "company_name": "Example Company",
        "industry": "General Business Operations",
        "domain": "example.internal",
        "admin_email": "admin@example.internal",
        "password": "StrongPassword123!"
    }
    assert empty_client.post("/api/auth/register-company", json=payload).status_code == 401

    response = empty_client.post(
        "/api/auth/register-company",
        json=payload,
        headers={"X-Setup-Token": "test-bootstrap-token-12345"},
    )
    assert response.status_code == 200, response.text

    repeated = empty_client.post(
        "/api/auth/register-company",
        json={**payload, "admin_email": "second@example.internal"},
        headers={"X-Setup-Token": "test-bootstrap-token-12345"},
    )
    assert repeated.status_code == 409
