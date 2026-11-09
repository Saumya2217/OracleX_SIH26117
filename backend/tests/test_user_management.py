def test_list_and_manage_users(client, auth_headers):
    headers = auth_headers("saumy@novaworks.com")

    # 1. List users
    resp = client.get("/api/users/", headers=headers)
    assert resp.status_code == 200
    users = resp.json()
    names = [u["full_name"] for u in users]
    assert "Saumy Jain" in names
    assert "Ashutosh Tandel" in names
    assert "Arya Khetalpar" in names

    # 2. Find Arya and update job title
    arya = next(u for u in users if u["email"] == "arya@novaworks.com")
    update_resp = client.put(f"/api/users/{arya['id']}", json={"job_title": "Senior Creative Lead"}, headers=headers)
    assert update_resp.status_code == 200
    assert update_resp.json()["job_title"] == "Senior Creative Lead"

    # 3. Toggle status
    status_resp = client.patch(f"/api/users/{arya['id']}/status", headers=headers)
    assert status_resp.status_code == 200
    assert status_resp.json()["is_active"] is False

    # Restore status
    status_resp2 = client.patch(f"/api/users/{arya['id']}/status", headers=headers)
    assert status_resp2.status_code == 200
    assert status_resp2.json()["is_active"] is True


def test_final_active_admin_is_protected(client, auth_headers):
    headers = auth_headers("saumy@novaworks.com")
    current = client.get("/api/auth/me", headers=headers).json()
    response = client.patch(f"/api/users/{current['id']}/status", headers=headers)
    assert response.status_code == 409


def test_user_relationships_must_belong_to_company(client, auth_headers):
    response = client.post(
        "/api/users/",
        json={
            "email": "new.user@example.internal",
            "full_name": "New User",
            "password": "StrongPassword123!",
            "clearance_level": 1,
            "department_id": "outside-company-department",
        },
        headers=auth_headers("saumy@novaworks.com"),
    )
    assert response.status_code == 422
