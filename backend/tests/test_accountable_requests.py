import pytest


def _create_purchase(client, headers, reviewer_id=None, *, complete=True):
    fields = {
        "item": "Encrypted backup appliance",
        "quantity": 1,
        "estimated_cost": 4800,
        "currency": "USD",
        "vendor": "Local Systems Ltd",
        "business_reason": "Replace the unsupported backup target.",
    } if complete else {"item": "Encrypted backup appliance"}
    response = client.post(
        "/api/requests",
        json={
            "request_type": "PURCHASE_REQUEST",
            "title": "Replace backup appliance",
            "description": "Purchase request for an on-premises encrypted backup target.",
            "risk_level": "HIGH",
            "assigned_reviewer_id": reviewer_id,
            "payload": fields,
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_request_versions_submission_decision_and_stale_write_protection(client, auth_headers):
    requester = auth_headers("arya@novaworks.com")
    reviewer = auth_headers("ashutosh@novaworks.com")
    reviewer_profile = client.get("/api/auth/me", headers=reviewer).json()
    draft = _create_purchase(client, requester, reviewer_profile["id"], complete=False)

    incomplete = client.post(
        f"/api/requests/{draft['id']}/submit",
        json={"expected_lock_version": draft["lock_version"]},
        headers=requester,
    )
    assert incomplete.status_code == 422
    assert "required fields" in incomplete.json()["detail"]

    updated_response = client.patch(
        f"/api/requests/{draft['id']}",
        json={
            "expected_lock_version": draft["lock_version"],
            "description": "Approved replacement for the unsupported backup target.",
            "payload": {
                "item": "Encrypted backup appliance",
                "quantity": 1,
                "estimated_cost": 4800,
                "currency": "USD",
                "vendor": "Local Systems Ltd",
                "business_reason": "Replace the unsupported backup target.",
            },
        },
        headers=requester,
    )
    assert updated_response.status_code == 200, updated_response.text
    updated = updated_response.json()
    assert len(updated["versions"]) == 2
    assert updated["versions"][0]["payload"]["fields"] == {"item": "Encrypted backup appliance"}

    stale_edit = client.patch(
        f"/api/requests/{draft['id']}",
        json={"expected_lock_version": draft["lock_version"], "title": "Stale title"},
        headers=requester,
    )
    assert stale_edit.status_code == 409

    submitted_response = client.post(
        f"/api/requests/{draft['id']}/submit",
        json={"expected_lock_version": updated["lock_version"]},
        headers=requester,
    )
    assert submitted_response.status_code == 200, submitted_response.text
    submitted = submitted_response.json()
    assert submitted["status"] == "ASSIGNED"
    assert submitted["submitted_version_id"] == updated["current_version_id"]

    wrong_version = client.post(
        f"/api/requests/{draft['id']}/decision",
        json={
            "expected_lock_version": submitted["lock_version"],
            "submitted_version_id": updated["versions"][0]["id"],
            "decision": "APPROVED",
            "reason": "This version is not the submitted version.",
        },
        headers=reviewer,
    )
    assert wrong_version.status_code == 409

    other_reviewer = client.post(
        f"/api/requests/{draft['id']}/decision",
        json={
            "expected_lock_version": submitted["lock_version"],
            "submitted_version_id": submitted["submitted_version_id"],
            "decision": "APPROVED", "reason": "An unassigned reviewer must not decide this request.",
        }, headers=auth_headers("hetvi@novaworks.com"),
    )
    assert other_reviewer.status_code == 403

    decided_response = client.post(
        f"/api/requests/{draft['id']}/decision",
        json={
            "expected_lock_version": submitted["lock_version"],
            "submitted_version_id": submitted["submitted_version_id"],
            "decision": "APPROVED",
            "reason": "The replacement is necessary and within the approved budget.",
        },
        headers=reviewer,
    )
    assert decided_response.status_code == 200, decided_response.text
    decided = decided_response.json()
    assert decided["decision_reason"].startswith("The replacement")

    duplicate_decision = client.post(
        f"/api/requests/{draft['id']}/decision",
        json={
            "expected_lock_version": submitted["lock_version"],
            "submitted_version_id": submitted["submitted_version_id"],
            "decision": "REJECTED",
            "reason": "A duplicate decision must be rejected.",
        },
        headers=reviewer,
    )
    assert duplicate_decision.status_code == 409

    fulfilled_response = client.post(
        f"/api/requests/{draft['id']}/fulfill",
        json={"expected_lock_version": decided["lock_version"], "notes": "Purchase order PO-2048 was issued."},
        headers=reviewer,
    )
    assert fulfilled_response.status_code == 200
    fulfilled = fulfilled_response.json()
    assert fulfilled["status"] == "COMPLETED"
    assert [event["event_type"] for event in fulfilled["timeline"]][-3:] == ["SUBMITTED", "DECIDED", "FULFILLED"]

    duplicate_fulfillment = client.post(
        f"/api/requests/{draft['id']}/fulfill",
        json={"expected_lock_version": fulfilled["lock_version"], "notes": "Duplicate fulfillment attempt."},
        headers=reviewer,
    )
    assert duplicate_fulfillment.status_code == 409


def test_request_visibility_notifications_and_cancellation_are_recipient_scoped(client, auth_headers):
    requester = auth_headers("jidnyasa@novaworks.com")
    reviewer = auth_headers("hetvi@novaworks.com")
    unrelated = auth_headers("krish@novaworks.com")
    reviewer_profile = client.get("/api/auth/me", headers=reviewer).json()
    draft = _create_purchase(client, requester, reviewer_profile["id"])

    assert client.get(f"/api/requests/{draft['id']}", headers=unrelated).status_code == 404
    submitted_response = client.post(
        f"/api/requests/{draft['id']}/submit",
        json={"expected_lock_version": draft["lock_version"]},
        headers=requester,
    )
    assert submitted_response.status_code == 200, submitted_response.text
    submitted = submitted_response.json()

    reviewer_notifications = client.get("/api/requests/notifications/inbox", headers=reviewer)
    assert reviewer_notifications.status_code == 200, reviewer_notifications.text
    matching = [item for item in reviewer_notifications.json() if item["request_id"] == draft["id"]]
    assert len(matching) == 1
    assert matching[0]["deep_link"].endswith(draft["id"])
    unrelated_notifications = client.get("/api/requests/notifications/inbox", headers=unrelated).json()
    assert all(item["request_id"] != draft["id"] for item in unrelated_notifications)

    marked = client.post(f"/api/requests/notifications/{matching[0]['id']}/read", headers=reviewer)
    assert marked.status_code == 200
    assert marked.json()["read_at"] is not None
    assert client.post(f"/api/requests/notifications/{matching[0]['id']}/read", headers=unrelated).status_code == 404

    cancelled = client.post(
        f"/api/requests/{draft['id']}/cancel",
        json={"expected_lock_version": submitted["lock_version"], "reason": "The replacement is no longer required."},
        headers=requester,
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "CANCELLED"


def test_invalid_draft_fields_return_safe_422_and_preserve_saved_version(client, auth_headers):
    headers = auth_headers("arya@novaworks.com")
    invalid = client.post("/api/requests", headers=headers, json={
        "request_type": "PURCHASE_REQUEST", "title": "Invalid QA currency",
        "description": "Synthetic validation fixture", "payload": {"currency": "ZZ"},
    })
    assert invalid.status_code == 422
    error = invalid.json()["detail"][0]
    assert error["loc"] == ["body", "payload", "currency"]
    assert error["msg"] == "Use a three-letter currency code, such as USD."
    assert "input" not in error and "ctx" not in error

    draft = _create_purchase(client, headers)
    rejected = client.patch(f"/api/requests/{draft['id']}", headers=headers, json={
        "expected_lock_version": draft["lock_version"], "payload": {"quantity": 0},
    })
    assert rejected.status_code == 422
    retained = client.get(f"/api/requests/{draft['id']}", headers=headers).json()
    assert retained["current_version_id"] == draft["current_version_id"]
    assert retained["lock_version"] == draft["lock_version"]
    assert retained["current_payload"] == draft["current_payload"]


@pytest.mark.parametrize("field", ["title", "description"])
def test_blank_request_basics_are_rejected(client, auth_headers, field):
    body = {"request_type": "ACCESS_REQUEST", "title": "QA", "description": "Synthetic fixture"}
    body[field] = "   "
    response = client.post("/api/requests", headers=auth_headers("arya@novaworks.com"), json=body)
    assert response.status_code == 422


def test_blank_submission_and_decision_reasons_are_rejected(client, auth_headers):
    owner = auth_headers("arya@novaworks.com")
    reviewer = auth_headers("ashutosh@novaworks.com")
    draft = _create_purchase(client, owner)
    changed = client.patch(f"/api/requests/{draft['id']}", headers=owner, json={
        "expected_lock_version": draft["lock_version"],
        "payload": {**draft["current_payload"], "business_reason": "   "},
    }).json()
    blocked = client.post(f"/api/requests/{draft['id']}/submit", headers=owner,
                          json={"expected_lock_version": changed["lock_version"]})
    assert blocked.status_code == 422
    assert "business_reason" in blocked.json()["detail"]
    for action, extra in [
        ("decision", {"reason": "   ", "decision": "APPROVED", "submitted_version_id": draft["current_version_id"]}),
        ("fulfill", {"notes": "   "}),
        ("cancel", {"reason": "   "}),
    ]:
        response = client.post(f"/api/requests/{draft['id']}/{action}", headers=reviewer,
                               json={"expected_lock_version": changed["lock_version"], **extra})
        assert response.status_code == 422
