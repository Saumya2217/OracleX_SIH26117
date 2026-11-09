from __future__ import annotations

from sqlalchemy.orm import Session

from app.agents.llm_client import llm_client
from app.agents.result import GroundedAgentResult
from app.models.company import User
from app.schemas.agent import AgentCitation
from app.services.retrieval import RetrievalService, expanded_query_tokens


ABSTENTION = "I don't have enough authorized company evidence to answer that question."


def _citation(candidate: dict) -> AgentCitation:
    return AgentCitation(
        document_id=candidate["document_id"],
        version_id=candidate["version_id"],
        chunk_id=candidate["chunk_id"],
        chunk_index=candidate["chunk_index"],
        title=candidate["title"],
        filename=candidate["filename"],
        page_number=candidate.get("page_number"),
        section_index=candidate.get("section_index"),
        sheet_name=candidate.get("sheet_name"),
        row_range=candidate.get("row_range"),
        source_type=candidate["source_type"],
        location_label=candidate["location_label"],
        excerpt=candidate["content"][:320].strip(),
        source_path=(
            f"/api/knowledge/documents/{candidate['document_id']}"
            f"/versions/{candidate['version_id']}/source"
        ),
    )


def _extractive_answer(query: str, candidates: list[dict]) -> str:
    tokens = expanded_query_tokens(query)
    ranked_lines: list[tuple[int, int, str]] = []
    for candidate_index, candidate in enumerate(candidates):
        for line_index, line in enumerate(candidate["content"].splitlines()):
            cleaned = line.strip(" •\t")
            if not cleaned:
                continue
            line_tokens = expanded_query_tokens(cleaned)
            score = len(tokens.intersection(line_tokens))
            if score:
                ranked_lines.append((score, -(candidate_index * 1000 + line_index), cleaned))
    ranked_lines.sort(reverse=True)
    selected: list[str] = []
    for _score, _position, line in ranked_lines:
        if line not in selected:
            selected.append(line)
        if len(selected) == 3:
            break
    if not selected:
        selected = [candidates[0]["content"][:600].strip()]
    return "\n".join(selected) + "\n\nThe local language model is unavailable, so this is an extractive answer from the cited source."


class DocumentAgent:
    """Answer only from authorized, current, immutable company evidence."""

    @staticmethod
    async def run(
        db: Session,
        user: User,
        query: str,
        system_prompt: str,
        response_instruction: str | None = None,
        retrieval_query: str | None = None,
        previous_questions: list[str] | None = None,
    ) -> GroundedAgentResult:
        search_query = retrieval_query or query
        candidates = RetrievalService.retrieve(db, user, search_query, limit=5, mode="hybrid")
        if not candidates:
            return GroundedAgentResult(
                answer=ABSTENTION,
                evidence_status="INSUFFICIENT_EVIDENCE",
                generation_mode="NONE",
            )

        citations = [_citation(candidate) for candidate in candidates]
        evidence = []
        for index, candidate in enumerate(candidates, 1):
            evidence.append(
                f"[S{index}] {candidate['title']} — {candidate['location_label']} "
                f"(version {candidate['version_id']})\n{candidate['content']}"
            )
        instruction = response_instruction or "Answer the question concisely using only the evidence."
        history = ""
        if previous_questions:
            history = "PREVIOUS USER QUESTIONS IN THIS CONVERSATION:\n" + "\n".join(
                f"- {item}" for item in previous_questions[-2:]
            ) + "\n\n"
        prompt = (
            history
            + "AUTHORIZED CURRENT-VERSION COMPANY EVIDENCE:\n\n"
            + "\n\n".join(evidence)
            + f"\n\nQUESTION: {query}\n"
            + instruction
            + " Cite supporting statements with [S1], [S2], and so on. If the evidence does not support the answer, abstain."
        )
        try:
            answer, generation_mode, model_id = await llm_client.generate_grounded_response(
                prompt=prompt,
                system_prompt=system_prompt,
                context_chunks=candidates,
            )
        except RuntimeError:
            answer = _extractive_answer(search_query, candidates)
            generation_mode = "EXTRACTIVE"
            model_id = None

        return GroundedAgentResult(
            answer=answer,
            evidence_status="SUPPORTED",
            generation_mode=generation_mode,
            model_id=model_id,
            citations=citations,
            context_chunks=candidates,
        )
