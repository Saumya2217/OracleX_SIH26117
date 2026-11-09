def test_team_delete_rejects_referenced_team_and_accepts_empty_team(client, auth_headers):
    headers = auth_headers("saumy@novaworks.com")
    departments = client.get("/api/company/departments", headers=headers).json()
    users = client.get("/api/users/", headers=headers).json()
    referenced_id = next(user["department_id"] for user in users if user.get("department_id"))
    assert any(department["id"] == referenced_id for department in departments)

    blocked = client.delete(f"/api/company/departments/{referenced_id}", headers=headers)
    assert blocked.status_code == 409
    assert "referenced" in blocked.json()["detail"]

    created = client.post("/api/company/departments", json={"name": "Temporary Empty Team", "code": "TEMP-EMPTY"}, headers=headers)
    assert created.status_code == 200
    deleted = client.delete(f"/api/company/departments/{created.json()['id']}", headers=headers)
    assert deleted.status_code == 200
    assert deleted.json() == {"status": "success", "deleted_id": created.json()["id"]}
