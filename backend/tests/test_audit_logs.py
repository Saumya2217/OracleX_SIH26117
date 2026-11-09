from datetime import datetime

from app.models.company import User
from app.services.audit_service import record_audit_event


def test_audit_log_generation_and_integrity(client, db_session, auth_headers):
    user = db_session.query(User).filter(User.email == "saumy@novaworks.com").one()
    record_audit_event(db_session, company_id=user.company_id, action="AUDIT_INTEGRITY_TEST", resource_type="test", user=user)
    headers = auth_headers("saumy@novaworks.com")

    # Fetch logs
    logs_resp = client.get("/api/audit/logs", headers=headers)
    assert logs_resp.status_code == 200
    logs = logs_resp.json()
    assert len(logs) > 0
    
    first_log = logs[0]
    assert "integrity_hash" in first_log
    assert len(first_log["integrity_hash"]) == 64  # SHA-256 length

    # Verify the explicitly limited per-record checksum scope.
    integrity_resp = client.get("/api/audit/verify-integrity", headers=headers)
    assert integrity_resp.status_code == 200
    integrity_data = integrity_resp.json()
    assert integrity_data["status"] == "CHECKSUMS_VALID"
    assert "deletion and reordering are not detected" in integrity_data["scope"]
    assert integrity_data["total_records_checked"] > 0
    assert len(integrity_data["tampered_records"]) == 0


def test_audit_requires_permission(client, auth_headers):
    response = client.get("/api/audit/logs", headers=auth_headers("krish@novaworks.com"))
    assert response.status_code == 403


def test_audit_cursor_keeps_equal_timestamp_records_without_duplicates(client, db_session, auth_headers):
    user = db_session.query(User).filter(User.email == "saumy@novaworks.com").one()
    records = [
        record_audit_event(db_session, company_id=user.company_id, action="M07_CURSOR_TEST", resource_type="test", user=user)
        for _ in range(3)
    ]
    for record in records:
        record.timestamp = datetime(2026, 1, 1)
    db_session.commit()

    headers = auth_headers("saumy@novaworks.com")
    first = client.get("/api/audit/logs", params={"action": "M07_CURSOR_TEST", "limit": 2}, headers=headers)
    assert first.status_code == 200
    first_items = first.json()
    assert len(first_items) == 2
    last = first_items[-1]
    second = client.get(
        "/api/audit/logs",
        params={"action": "M07_CURSOR_TEST", "limit": 2, "before_timestamp": last["timestamp"], "before_id": last["id"]},
        headers=headers,
    )
    assert second.status_code == 200
    assert len(second.json()) == 1
    assert len({item["id"] for item in first_items + second.json()}) == 3
    incomplete = client.get("/api/audit/logs", params={"before_id": last["id"]}, headers=headers)
    assert incomplete.status_code == 422
