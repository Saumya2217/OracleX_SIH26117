import asyncio

import pytest
from pydantic import ValidationError

from app.agents.llm_client import SovereignLLMClient
from app.config import Settings, settings


def test_security_configuration_rejects_unsafe_defaults():
    with pytest.raises(ValidationError):
        Settings(SECRET_KEY="short")

    with pytest.raises(ValidationError):
        Settings(
            SECRET_KEY="a-valid-test-key-with-at-least-32-characters",
            ALLOWED_ORIGINS=["*"],
        )

    with pytest.raises(ValidationError):
        Settings(
            SECRET_KEY="a-valid-test-key-with-at-least-32-characters",
            DEMO_MODE=False,
            DEMO_SEED_ON_STARTUP=True,
        )


def test_model_failure_is_visible_when_simulation_is_disabled():
    original = settings.SIMULATED_AI_FALLBACK
    settings.SIMULATED_AI_FALLBACK = False
    client = SovereignLLMClient(base_url="http://127.0.0.1:9", default_model="missing-model")
    try:
        health = asyncio.run(client.check_health())
        assert health["status"] == "unavailable"
        with pytest.raises(RuntimeError, match="missing-model"):
            asyncio.run(client.generate_response("Question", "System"))
    finally:
        settings.SIMULATED_AI_FALLBACK = original
