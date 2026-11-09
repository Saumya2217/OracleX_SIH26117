from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.schemas.agent import AgentCitation


@dataclass
class GroundedAgentResult:
    answer: str
    evidence_status: str
    generation_mode: str
    model_id: str | None = None
    citations: list[AgentCitation] = field(default_factory=list)
    context_chunks: list[dict[str, Any]] = field(default_factory=list)
