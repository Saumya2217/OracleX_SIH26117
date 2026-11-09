def test_employee_cannot_modify_another_users_task(client, auth_headers):
    owner_headers = auth_headers("krish@novaworks.com")
    created = client.post(
        "/api/workflows/tasks",
        json={"title": "Owner-only task", "priority": "MEDIUM", "status": "TODO"},
        headers=owner_headers,
    )
    assert created.status_code == 200, created.text

    response = client.patch(
        f"/api/workflows/tasks/{created.json()['id']}",
        json={"status": "COMPLETED"},
        headers=auth_headers("arya@novaworks.com"),
    )
    assert response.status_code == 403


def test_task_assignee_must_be_active_and_in_company(client, auth_headers):
    response = client.post(
        "/api/workflows/tasks",
        json={
            "title": "Invalid assignment",
            "assigned_to_id": "outside-company-user",
            "priority": "HIGH",
            "status": "TODO",
        },
        headers=auth_headers("ashutosh@novaworks.com"),
    )
    assert response.status_code == 422
