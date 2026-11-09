from datetime import timedelta

from app.config import settings
from app.models.knowledge import Document, DocumentChunk, DocumentVersion, IngestionJob, OutboxEvent, utcnow
from app.services.ingestion import IngestionService
from app.services.vector_store import vector_store_service


def upload_text(client, headers, title: str, filename: str, content: bytes):
    response = client.post(
        "/api/knowledge/upload",
        files={"file": (filename, content, "text/plain")},
        data={"title": title, "clearance_level": 1, "is_company_wide": True},
        headers=headers,
    )
    assert response.status_code == 202, response.text
    return response.json()


def test_version_replacement_keeps_only_current_version_searchable(client, auth_headers, db_session):
    headers = auth_headers("saumy@novaworks.com")
    initial = upload_text(
        client,
        headers,
        "Version lifecycle fixture",
        "version-one.txt",
        b"Version lifecycle record. The zephyrlattice approval threshold is 417 units.",
    )
    assert initial["job"]["state"] == "SUCCEEDED"
    document_id = initial["document"]["id"]
    first_version_id = initial["version"]["id"]
    assert vector_store_service.version_chunk_count(first_version_id) == 1

    replacement = client.post(
        f"/api/knowledge/documents/{document_id}/versions",
        files={"file": ("version-two.txt", b"Version lifecycle record. The zephyrlattice approval threshold is now 913 units.", "text/plain")},
        headers=headers,
    )
    assert replacement.status_code == 202, replacement.text
    payload = replacement.json()
    second_version_id = payload["version"]["id"]
    assert payload["version"]["version_number"] == 2
    assert payload["document"]["current_version_id"] == second_version_id
    assert vector_store_service.version_chunk_count(first_version_id) == 0
    assert vector_store_service.version_chunk_count(second_version_id) == 1

    first_version = db_session.get(DocumentVersion, first_version_id)
    assert first_version.status == "SUPERSEDED"
    chunks = client.get(f"/api/knowledge/documents/{document_id}/chunks", headers=headers)
    assert chunks.status_code == 200
    assert "913" in chunks.json()[0]["content"]
    assert "417" not in chunks.json()[0]["content"]

    employee_headers = auth_headers("krish@novaworks.com")
    current_chunks = client.get(
        f"/api/knowledge/documents/{document_id}/versions/{second_version_id}/chunks",
        headers=employee_headers,
    )
    historical_chunks = client.get(
        f"/api/knowledge/documents/{document_id}/versions/{first_version_id}/chunks",
        headers=employee_headers,
    )
    assert current_chunks.status_code == 200
    assert historical_chunks.status_code == 403


def test_archive_restore_and_reconcile_rebuild_index(client, auth_headers):
    headers = auth_headers("saumy@novaworks.com")
    uploaded = upload_text(
        client,
        headers,
        "Recovery fixture",
        "recovery.txt",
        b"Recovery fixture source with the distinct term heliocentricledger and retention code 602.",
    )
    document = uploaded["document"]
    version_id = uploaded["version"]["id"]

    archived = client.post(f"/api/knowledge/documents/{document['id']}/archive", headers=headers)
    assert archived.status_code == 200
    assert archived.json()["status"] == "ARCHIVED"
    assert vector_store_service.version_chunk_count(version_id) == 0

    restored = client.post(f"/api/knowledge/documents/{document['id']}/restore", headers=headers)
    assert restored.status_code == 200
    assert restored.json()["status"] == "INDEXED"
    assert vector_store_service.version_chunk_count(version_id) == 1

    vector_store_service.delete_version_chunks(version_id)
    report = client.post("/api/knowledge/admin/reconcile?repair=true", headers=headers)
    assert report.status_code == 200, report.text
    issue = next(item for item in report.json()["issues"] if item["version_id"] == version_id)
    assert issue["code"] == "INDEX_COUNT_MISMATCH"
    assert issue["repaired"] is True
    assert vector_store_service.version_chunk_count(version_id) == 1


def test_expired_worker_lease_requeues_without_duplicate_chunks(client, auth_headers, db_session, monkeypatch):
    monkeypatch.setattr(settings, "INGESTION_INLINE_FOR_TESTS", False)
    headers = auth_headers("saumy@novaworks.com")
    queued = upload_text(
        client,
        headers,
        "Interrupted worker fixture",
        "worker-recovery.txt",
        b"Worker recovery content with unique reference windwardmatrix 884.",
    )
    job_id = queued["job"]["id"]
    job = db_session.get(IngestionJob, job_id)
    job.state = "PROCESSING"
    job.attempt_count = 1
    job.lease_owner = "dead-worker"
    job.lease_expires_at = utcnow() - timedelta(seconds=1)
    db_session.commit()

    assert IngestionService.release_expired_leases(db_session) == 1
    db_session.refresh(job)
    assert job.state == "RETRYABLE"
    assert job.error_code == "WORKER_LEASE_EXPIRED"

    claimed = IngestionService.claim_next_job(db_session, "replacement-worker")
    assert claimed == job_id
    assert IngestionService.process_job(db_session, job_id, "replacement-worker") is True
    assert IngestionService.process_job(db_session, job_id, "replacement-worker") is False
    assert db_session.query(DocumentChunk).filter(DocumentChunk.version_id == job.version_id).count() == 1
    assert vector_store_service.version_chunk_count(job.version_id) == 1


def test_failed_signature_is_safe_and_retryable(client, auth_headers):
    headers = auth_headers("saumy@novaworks.com")
    response = client.post(
        "/api/knowledge/upload",
        files={"file": ("misleading.pdf", b"This is plain text, not a PDF.", "application/pdf")},
        data={"title": "Invalid PDF fixture", "clearance_level": 1, "is_company_wide": True},
        headers=headers,
    )
    assert response.status_code == 202, response.text
    payload = response.json()
    assert payload["document"]["status"] == "FAILED"
    assert payload["version"]["status"] == "FAILED"
    assert payload["job"]["state"] == "RETRYABLE"
    assert payload["job"]["error_code"] == "TYPE_MISMATCH"
    assert "valid PDF signature" in payload["job"]["safe_error_message"]


def test_vector_failure_never_marks_document_ready(client, auth_headers, monkeypatch):
    headers = auth_headers("saumy@novaworks.com")

    def fail_index(*_args, **_kwargs):
        raise RuntimeError("simulated index outage")

    monkeypatch.setattr(vector_store_service, "index_chunks", fail_index)
    payload = upload_text(
        client,
        headers,
        "Index outage fixture",
        "index-outage.txt",
        b"Index outage fixture with unique term resolutecarbon 492.",
    )
    assert payload["document"]["status"] == "FAILED"
    assert payload["document"]["current_version_id"] is None
    assert payload["version"]["status"] == "FAILED"
    assert payload["job"]["state"] == "RETRYABLE"
    assert payload["job"]["error_code"] == "PROCESSING_ERROR"


def test_invalid_utf8_text_is_rejected_without_partial_content(client, auth_headers):
    headers = auth_headers("saumy@novaworks.com")
    response = client.post(
        "/api/knowledge/upload",
        files={"file": ("invalid-utf8.txt", b"valid prefix \xff\xfe invalid content", "text/plain")},
        data={"title": "Invalid UTF-8 fixture", "clearance_level": 1, "is_company_wide": True},
        headers=headers,
    )
    assert response.status_code == 202
    payload = response.json()
    assert payload["document"]["status"] == "FAILED"
    assert payload["job"]["error_code"] == "PARSER_REJECTED"
    assert payload["version"]["chunk_count"] == 0


def test_upload_job_and_outbox_are_committed_together(client, auth_headers, db_session, monkeypatch):
    monkeypatch.setattr(settings, "INGESTION_INLINE_FOR_TESTS", False)
    headers = auth_headers("saumy@novaworks.com")
    queued = upload_text(
        client,
        headers,
        "Outbox fixture",
        "outbox.txt",
        b"Transactional outbox fixture with unique reference northboundquartz 177.",
    )
    document_id = queued["document"]["id"]
    version_id = queued["version"]["id"]
    assert db_session.get(Document, document_id) is not None
    assert db_session.get(DocumentVersion, version_id) is not None
    assert db_session.get(IngestionJob, queued["job"]["id"]) is not None
    event = db_session.query(OutboxEvent).filter(OutboxEvent.aggregate_id == version_id).one()
    assert event.payload["job_id"] == queued["job"]["id"]
    assert event.state == "PENDING"
