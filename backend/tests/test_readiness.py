import asyncio

from app.agents.llm_client import SovereignLLMClient


def test_liveness_is_independent_of_dependencies(client):
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json()["status"] == "live"


def test_readiness_reports_each_component(client):
    response = client.get("/health/ready")
    payload = response.json()

    assert response.status_code in {200, 503}
    assert set(payload["checks"]) == {
        "database",
        "migrations",
        "storage",
        "index",
        "model",
        "worker",
    }
    assert payload["checks"]["worker"]["status"] == "not_required"


def test_reachable_ollama_without_configured_model_is_not_live_inference(monkeypatch):
    class Response:
        status_code = 200

        @staticmethod
        def json():
            return {"models": [{"name": "some-other-model:1b"}]}

    class Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def get(self, _url):
            return Response()

    monkeypatch.setattr("app.agents.llm_client.httpx.AsyncClient", lambda **_kwargs: Client())
    status = asyncio.run(SovereignLLMClient(default_model="approved-model:1b").check_health())

    assert status["status"] == "model_missing"
    assert status["active_model"] is None
    assert status["is_live_inference"] is False
