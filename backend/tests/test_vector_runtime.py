from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.config import Settings, settings
from app.services.vector_store import VectorStoreService, vector_store_service
from app.workers.ingestion import run_once


def test_production_requires_server_and_valid_port():
    with pytest.raises(ValidationError, match="Production requires CHROMA_HOST"):
        Settings(TESTING=False, ENVIRONMENT="production", CHROMA_HOST=None)
    with pytest.raises(ValidationError, match="CHROMA_PORT"):
        Settings(CHROMA_PORT=0)
    valid = Settings(TESTING=False, ENVIRONMENT="production", CHROMA_HOST="chroma")
    assert valid.CHROMA_HOST == "chroma"


def test_server_client_routes_to_configured_owner(monkeypatch):
    called = {}
    collection = object()

    def client(**kwargs):
        called.update(kwargs)
        return SimpleNamespace(get_or_create_collection=lambda **_: collection)

    monkeypatch.setattr(settings, "CHROMA_HOST", "private-chroma")
    monkeypatch.setattr(settings, "CHROMA_PORT", 8123)
    monkeypatch.setattr(settings, "CHROMA_SSL", True)
    monkeypatch.setattr("app.services.vector_store.chromadb.HttpClient", client)
    store = VectorStoreService()
    assert store.collection is collection
    assert (called["host"], called["port"], called["ssl"]) == ("private-chroma", 8123, True)


def test_worker_refuses_shared_embedded_storage(monkeypatch):
    monkeypatch.setattr(settings, "TESTING", False)
    monkeypatch.setattr(settings, "CHROMA_HOST", None)
    with pytest.raises(RuntimeError, match="requires CHROMA_HOST"):
        run_once("must-not-claim-a-job")


def test_search_outage_is_503_without_internal_error_details(client, auth_headers, monkeypatch):
    def fail_query(**_kwargs):
        raise RuntimeError("private index location and diagnostic text")

    monkeypatch.setattr(vector_store_service.collection, "query", fail_query)
    response = client.post(
        "/api/knowledge/search", json={"query": "leave", "limit": 5},
        headers=auth_headers("saumy@novaworks.com"),
    )
    assert response.status_code == 503
    assert response.json() == {"detail": "Document search is temporarily unavailable. Please retry."}
