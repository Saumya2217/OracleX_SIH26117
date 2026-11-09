import pytest

from app.models.company import Company, User


def draft(client, headers, request_type="ACCESS_REQUEST", reviewer_id=None):
    fields = {"resource": "QA sandbox reports", "access_level": "VIEW", "business_reason": "Synthetic review only."}
    if request_type == "CONTROLLED_CHANGE":
        fields = {"affected_asset": "QA process", "proposed_change": "Update a QA checklist",
                  "business_reason": "Synthetic review only.", "impact_assessment": "No production impact",
                  "rollback_plan": "Restore the prior QA checklist"}
    result = client.post("/api/requests", headers=headers, json={
        "request_type": request_type, "title": "M07 reviewer journey QA", "description": "No real access or change.",
        "assigned_reviewer_id": reviewer_id, "payload": fields,
    })
    assert result.status_code == 201, result.text
    return result.json()


def transition(client, record, action, headers, **extra):
    return client.post(f"/api/requests/{record['id']}/{action}", headers=headers,
                       json={"expected_lock_version": record["lock_version"], **extra})


def test_reviewer_choices_are_minimal_active_company_scoped_and_exclude_requester(client, db_session, auth_headers):
    owner = db_session.query(User).filter_by(email="arya@novaworks.com").one()
    company = Company(name="Reviewer scope QA")
    db_session.add(company)
    db_session.flush()
    foreign = User(company_id=company.id, email="foreign-reviewer-qa@example.invalid",
                   full_name="Other company reviewer", hashed_password="not-a-login", is_admin=True)
    inactive = User(company_id=owner.company_id, email="inactive-reviewer-qa@example.invalid",
                    full_name="Inactive reviewer", hashed_password="not-a-login", is_admin=True, is_active=False)
    db_session.add_all([foreign, inactive])
    db_session.commit()
    headers = auth_headers(owner.email)
    choices = client.get("/api/requests/reviewers/eligible", headers=headers)
    assert choices.status_code == 200
    ids = {item["id"] for item in choices.json()}
    assert not {owner.id, foreign.id, inactive.id} & ids
    assert all(set(item) == {"id", "full_name", "job_title"} for item in choices.json())
    for invalid_id in [owner.id, foreign.id, inactive.id]:
        response = client.post("/api/requests", headers=headers, json={
            "request_type": "ACCESS_REQUEST", "title": "Invalid reviewer QA",
            "description": "Synthetic", "assigned_reviewer_id": invalid_id,
        })
        assert response.status_code == 422
    profile = client.get("/api/auth/me", headers=auth_headers("ashutosh@novaworks.com")).json()
    own_choices = client.get("/api/requests/reviewers/eligible", headers=auth_headers("ashutosh@novaworks.com")).json()
    assert profile["id"] not in {item["id"] for item in own_choices}
    private = draft(client, headers)
    assert client.get("/api/requests/reviewers/eligible", params={"request_id": private["id"]},
                      headers=auth_headers("krish@novaworks.com")).status_code == 404
    assert client.get("/api/requests/reviewers/eligible").status_code == 401


def test_reassignment_checks_actor_version_recipient_and_notifications(client, auth_headers):
    owner = auth_headers("arya@novaworks.com")
    first = auth_headers("ashutosh@novaworks.com")
    second = auth_headers("hetvi@novaworks.com")
    first_id = client.get("/api/auth/me", headers=first).json()["id"]
    second_id = client.get("/api/auth/me", headers=second).json()["id"]
    record = draft(client, owner, reviewer_id=first_id)
    submitted = transition(client, record, "submit", owner).json()
    assert transition(client, submitted, "assign", second, reviewer_id=second_id).status_code == 403
    assert transition(client, submitted, "assign", first, reviewer_id=first_id).status_code == 409
    reassigned_response = transition(client, submitted, "assign", first, reviewer_id=second_id)
    assert reassigned_response.status_code == 200, reassigned_response.text
    reassigned = reassigned_response.json()
    assert reassigned["assigned_reviewer_id"] == second_id
    assert reassigned["submitted_version_id"] == submitted["submitted_version_id"]
    assert len(reassigned["versions"]) == 1
    metadata = reassigned["timeline"][-1]["event_metadata"]
    assert metadata == {"reviewer_id": second_id, "previous_reviewer_id": first_id}
    assert transition(client, submitted, "assign", auth_headers("saumy@novaworks.com"), reviewer_id=first_id).status_code == 409
    assert transition(client, reassigned, "decision", first, submitted_version_id=reassigned["submitted_version_id"],
                      decision="REJECTED", reason="Old reviewer must be denied").status_code == 403
    for headers, expected in [(first, "REQUEST_REASSIGNED"), (second, "REQUEST_ASSIGNED"), (owner, "REQUEST_REVIEWER_CHANGED")]:
        inbox = client.get("/api/requests/notifications/inbox", headers=headers).json()
        assert any(item["request_id"] == record["id"] and item["notification_type"] == expected for item in inbox)


@pytest.mark.parametrize("request_type,decision", [("ACCESS_REQUEST", "REJECTED"), ("CONTROLLED_CHANGE", "APPROVED")])
def test_access_change_exact_version_terminal_journeys(client, auth_headers, request_type, decision):
    owner = auth_headers("arya@novaworks.com")
    reviewer = auth_headers("ashutosh@novaworks.com")
    reviewer_id = client.get("/api/auth/me", headers=reviewer).json()["id"]
    record = draft(client, owner, request_type, reviewer_id)
    saved = client.patch(f"/api/requests/{record['id']}", headers=owner, json={
        "expected_lock_version": record["lock_version"], "assigned_reviewer_id": None,
    }).json()
    assert saved["versions"][-1]["payload"]["assigned_reviewer_id"] is None
    assert saved["versions"][0]["payload"]["assigned_reviewer_id"] == reviewer_id
    submitted = transition(client, saved, "submit", owner).json()
    assert submitted["status"] == "SUBMITTED"
    assigned_response = transition(client, submitted, "assign", reviewer, reviewer_id=reviewer_id)
    assert assigned_response.status_code == 200
    assigned = assigned_response.json()
    decided = transition(client, assigned, "decision", reviewer,
                         submitted_version_id=submitted["submitted_version_id"], decision=decision, reason="Synthetic decision only.")
    assert decided.status_code == 200, decided.text
    decided = decided.json()
    assert decided["submitted_version_id"] == saved["current_version_id"]
    assert decided["status"] == decision
    assert transition(client, decided, "cancel", owner, reason="Cannot cancel a terminal decision").status_code == 409
    completed = transition(client, decided, "fulfill", reviewer, notes="Synthetic QA record; no real action.")
    assert completed.status_code == (409 if decision == "REJECTED" else 200)
    assert any(item["request_id"] == record["id"] and item["notification_type"] == "REQUEST_DECIDED"
               for item in client.get("/api/requests/notifications/inbox", headers=owner).json())


@pytest.mark.parametrize("assigned", [False, True])
def test_submitted_or_assigned_owner_cancellation_blocks_later_decision(client, auth_headers, assigned):
    owner = auth_headers("arya@novaworks.com")
    reviewer = auth_headers("ashutosh@novaworks.com")
    reviewer_id = client.get("/api/auth/me", headers=reviewer).json()["id"]
    record = draft(client, owner, reviewer_id=reviewer_id if assigned else None)
    submitted = transition(client, record, "submit", owner).json()
    assert submitted["status"] == ("ASSIGNED" if assigned else "SUBMITTED")
    cancelled = transition(client, submitted, "cancel", owner, reason="Synthetic cancellation only.")
    assert cancelled.status_code == 200
    cancelled = cancelled.json()
    assert cancelled["timeline"][-1]["reason"] == "Synthetic cancellation only."
    assert transition(client, cancelled, "decision", reviewer, decision="APPROVED", reason="Late decision",
                      submitted_version_id=submitted["submitted_version_id"]).status_code == 409


@pytest.mark.parametrize("revocation", ["inactive", "permission"])
def test_submit_rechecks_reviewer_eligibility_without_changing_saved_version(client, db_session, auth_headers, revocation):
    owner = auth_headers("arya@novaworks.com")
    reviewer = db_session.query(User).filter_by(email="ashutosh@novaworks.com").one()
    record = draft(client, owner, reviewer_id=reviewer.id)
    original_active, original_role = reviewer.is_active, reviewer.role_id
    try:
        if revocation == "inactive":
            reviewer.is_active = False
        else:
            reviewer.role_id = None
        db_session.commit()
        response = transition(client, record, "submit", owner)
        assert response.status_code == 422
        retained = client.get(f"/api/requests/{record['id']}", headers=owner).json()
        assert retained["status"] == "DRAFT"
        assert retained["lock_version"] == record["lock_version"]
        assert retained["current_version_id"] == record["current_version_id"]
        assert retained["submitted_version_id"] is None
    finally:
        reviewer.is_active, reviewer.role_id = original_active, original_role
        db_session.commit()

