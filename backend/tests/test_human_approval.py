def _complete_controlled_change(client, headers, request):
    response = client.patch(
        f"/api/requests/{request['id']}",
        json={
            "expected_lock_version": request["lock_version"],
            "payload": {
                "affected_asset": "Turbine Part #A-402",
                "proposed_change": "Change the tolerance limit to +/-0.009 mm.",
                "business_reason": "Validate a controlled production exception.",
                "impact_assessment": "May affect fatigue performance and inspection limits.",
                "rollback_plan": "Restore the approved baseline tolerance and quarantine the batch.",
            },
        },
        headers=headers,
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_agent_action_creates_reviewable_draft_and_separate_fulfillment(client, auth_headers):
    requester = auth_headers("arya@novaworks.com")
    reviewer = auth_headers("ashutosh@novaworks.com")

    response = client.post(
        "/api/agents/query",
        json={"message": "I need to modify the tolerance limit on Turbine Part #A-402 to +/-0.009 mm"},
        headers=requester,
    )
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["requires_review"] is True
    assert result["execution_status"] == "DRAFT_CREATED"
    assert result["request_id"]
    assert "draft" in result["answer"].lower()
    assert "requires_approval" not in result

    draft_response = client.get(f"/api/requests/{result['request_id']}", headers=requester)
    assert draft_response.status_code == 200
    draft = draft_response.json()
    assert draft["request_type"] == "CONTROLLED_CHANGE"
    assert draft["status"] == "DRAFT"
    assert draft["source_context"]["conversation_id"] == result["conversation_id"]

    draft = _complete_controlled_change(client, requester, draft)
    submitted = client.post(
        f"/api/requests/{draft['id']}/submit",
        json={"expected_lock_version": draft["lock_version"]},
        headers=requester,
    )
    assert submitted.status_code == 200, submitted.text
    submitted_data = submitted.json()
    assert submitted_data["status"] == "SUBMITTED"
    assert submitted_data["submitted_version_id"] == submitted_data["current_version_id"]

    decided = client.post(
        f"/api/requests/{draft['id']}/decision",
        json={
            "expected_lock_version": submitted_data["lock_version"],
            "submitted_version_id": submitted_data["submitted_version_id"],
            "decision": "APPROVED",
            "reason": "The impact and rollback controls are sufficient for this exception.",
        },
        headers=reviewer,
    )
    assert decided.status_code == 200, decided.text
    approved = decided.json()
    assert approved["status"] == "APPROVED"
    assert approved["fulfilled_at"] is None

    fulfilled = client.post(
        f"/api/requests/{draft['id']}/fulfill",
        json={
            "expected_lock_version": approved["lock_version"],
            "notes": "The controlled change was recorded and the production owner was notified.",
        },
        headers=reviewer,
    )
    assert fulfilled.status_code == 200, fulfilled.text
    assert fulfilled.json()["status"] == "COMPLETED"


def test_requester_cannot_self_review(client, auth_headers):
    requester = auth_headers("ashutosh@novaworks.com")
    created = client.post(
        "/api/requests",
        json={
            "request_type": "ACCESS_REQUEST",
            "title": "Temporary finance workspace access",
            "description": "Access is required for a cross-department review.",
            "risk_level": "MEDIUM",
            "payload": {
                "resource": "Finance planning workspace",
                "access_level": "VIEW",
                "business_reason": "Review quarterly product spend.",
            },
        },
        headers=requester,
    )
    assert created.status_code == 201, created.text
    draft = created.json()
    submitted_response = client.post(
        f"/api/requests/{draft['id']}/submit",
        json={"expected_lock_version": draft["lock_version"]},
        headers=requester,
    )
    assert submitted_response.status_code == 200, submitted_response.text
    submitted = submitted_response.json()

    self_review = client.post(
        f"/api/requests/{draft['id']}/decision",
        json={
            "expected_lock_version": submitted["lock_version"],
            "submitted_version_id": submitted["submitted_version_id"],
            "decision": "APPROVED",
            "reason": "A requester must not decide their own request.",
        },
        headers=requester,
    )
    assert self_review.status_code == 403

    invalid_decision = client.post(
        f"/api/requests/{draft['id']}/decision",
        json={
            "expected_lock_version": submitted["lock_version"],
            "submitted_version_id": submitted["submitted_version_id"],
            "decision": "BANANA",
            "reason": "Invalid state transition.",
        },
        headers=auth_headers("saumy@novaworks.com"),
    )
    assert invalid_decision.status_code == 422
