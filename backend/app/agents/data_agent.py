from sqlalchemy.orm import Session

from app.agents.document_agent import DocumentAgent
from app.agents.result import GroundedAgentResult
from app.models.company import User


class DataAgent:
    """Grounded numeric analysis over authorized current-version evidence."""

    @staticmethod
    async def run(
        db: Session,
        user: User,
        query: str,
        system_prompt: str,
        retrieval_query: str | None = None,
        previous_questions: list[str] | None = None,
    ) -> GroundedAgentResult:
        return await DocumentAgent.run(
            db,
            user,
            query,
            system_prompt,
            retrieval_query=retrieval_query,
            previous_questions=previous_questions,
            response_instruction=(
                "Answer using only the cited evidence. Show any arithmetic briefly, preserve units, "
                "and do not infer a metric that is absent from the evidence."
            ),
        )
