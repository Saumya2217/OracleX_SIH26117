from pathlib import Path

from app.config import settings


def test_upload_requires_capability(client, auth_headers):
    response = client.post(
        "/api/knowledge/upload",
        files={"file": ("notes.txt", b"Authorized information for testing.", "text/plain")},
        data={"title": "Notes", "clearance_level": 1, "is_company_wide": True},
        headers=auth_headers("krish@novaworks.com"),
    )
    assert response.status_code == 403


def test_upload_uses_generated_contained_path_and_rejects_duplicate(client, auth_headers):
    headers = auth_headers("saumy@novaworks.com")
    content = b"Unique upload containment fixture with enough searchable text."
    request_args = {
        "files": {"file": ("../outside.txt", content, "text/plain")},
        "data": {"title": "Contained upload", "clearance_level": 1, "is_company_wide": True},
        "headers": headers,
    }

    first = client.post("/api/knowledge/upload", **request_args)
    assert first.status_code == 202, first.text
    document = first.json()["document"]
    assert document["filename"] == "outside.txt"

    upload_root = Path(settings.UPLOAD_DIR).resolve()
    assert not (upload_root.parent / "outside.txt").exists()
    stored = list((upload_root / document["company_id"] / document["id"] / "versions").glob("*/original/source.txt"))
    assert len(stored) == 1

    second = client.post("/api/knowledge/upload", **request_args)
    assert second.status_code == 409

    deleted = client.delete(f"/api/knowledge/documents/{document['id']}", headers=headers)
    assert deleted.status_code == 200
    assert not stored[0].exists()


def test_upload_rejects_unsupported_and_ambiguous_audience(client, auth_headers):
    headers = auth_headers("saumy@novaworks.com")
    unsupported = client.post(
        "/api/knowledge/upload",
        files={"file": ("payload.exe", b"not executable", "application/octet-stream")},
        data={"title": "Unsupported", "clearance_level": 1, "is_company_wide": True},
        headers=headers,
    )
    assert unsupported.status_code == 415

    missing_department = client.post(
        "/api/knowledge/upload",
        files={"file": ("department.txt", b"Department content.", "text/plain")},
        data={"title": "Department only", "clearance_level": 1, "is_company_wide": False},
        headers=headers,
    )
    assert missing_department.status_code == 422
