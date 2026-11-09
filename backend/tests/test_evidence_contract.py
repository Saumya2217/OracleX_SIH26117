def test_unsupported_image_input_is_explicit(client, auth_headers):
    response = client.post(
        "/api/agents/query",
        json={"message": "Inspect this component", "image_base64": "ZmFrZQ=="},
        headers=auth_headers("saumy@novaworks.com"),
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["evidence_status"] == "UNSUPPORTED_INPUT"
    assert payload["generation_mode"] == "NONE"
    assert payload["citations"] == []


def test_unanswerable_company_question_abstains_without_citations(client, auth_headers):
    response = client.post(
        "/api/agents/query",
        json={"message": "What is the employee stock option vesting schedule?"},
        headers=auth_headers("krish@novaworks.com"),
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["evidence_status"] == "INSUFFICIENT_EVIDENCE"
    assert payload["generation_mode"] == "NONE"
    assert payload["citations"] == []


def test_current_source_download_is_authorized_and_historical_source_is_not(client, auth_headers):
    admin_headers = auth_headers("saumy@novaworks.com")
    upload = client.post(
        "/api/knowledge/upload",
        files={"file": ("evidence-v1.txt", b"Evidence source version one with code alpha-771.", "text/plain")},
        data={"title": "Evidence download fixture", "clearance_level": 1, "is_company_wide": True},
        headers=admin_headers,
    ).json()
    document_id = upload["document"]["id"]
    first_version = upload["version"]["id"]
    replacement = client.post(
        f"/api/knowledge/documents/{document_id}/versions",
        files={"file": ("evidence-v2.txt", b"Evidence source version two with code beta-992.", "text/plain")},
        headers=admin_headers,
    ).json()
    current_version = replacement["version"]["id"]
    employee_headers = auth_headers("krish@novaworks.com")

    current = client.get(
        f"/api/knowledge/documents/{document_id}/versions/{current_version}/source",
        headers=employee_headers,
    )
    historical = client.get(
        f"/api/knowledge/documents/{document_id}/versions/{first_version}/source",
        headers=employee_headers,
    )
    assert current.status_code == 200
    assert current.content == b"Evidence source version two with code beta-992."
    assert historical.status_code == 403


def test_offline_model_failure_uses_labelled_extractive_answer(client, auth_headers, monkeypatch):
    monkeypatch.setattr(settings, "SIMULATED_AI_FALLBACK", False)
    response = client.post(
        "/api/agents/query",
        json={"message": "How many annual vacation leave days are provided?"},
        headers=auth_headers("krish@novaworks.com"),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["evidence_status"] == "SUPPORTED"
    assert payload["generation_mode"] == "EXTRACTIVE"
    assert payload["model_id"] is None
    assert payload["citations"]
    assert "extractive answer" in payload["answer"].lower()


def test_source_download_rejects_insufficient_clearance(client, auth_headers, db_session):
    document = db_session.query(Document).filter(Document.title.like("Executive Board Expansion%")).one()
    response = client.get(
        f"/api/knowledge/documents/{document.id}/versions/{document.current_version_id}/source",
        headers=auth_headers("krish@novaworks.com"),
    )
    assert response.status_code == 403


def test_source_download_detects_retained_file_tampering(client, auth_headers, db_session):
    headers = auth_headers("saumy@novaworks.com")
    upload_response = client.post(
        "/api/knowledge/upload",
        files={"file": ("integrity.txt", b"Original retained source content.", "text/plain")},
        data={"title": "Retained source integrity fixture", "clearance_level": 1, "is_company_wide": True},
        headers=headers,
    )
    assert upload_response.status_code == 202
    upload = upload_response.json()
    version = db_session.get(DocumentVersion, upload["version"]["id"])
    assert version is not None
    Path(version.storage_key).write_bytes(b"Tampered retained source content.")

    response = client.get(
        f"/api/knowledge/documents/{upload['document']['id']}/versions/{version.id}/source",
        headers=headers,
    )
    assert response.status_code == 409
    assert "integrity check" in response.json()["detail"].lower()
from pathlib import Path

from app.config import settings
from app.models.knowledge import Document, DocumentVersion

