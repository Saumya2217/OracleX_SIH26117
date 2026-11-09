import re
import json
import logging
from typing import Optional, Dict, Any, List
import httpx
from app.config import settings

logger = logging.getLogger("oraclex.ai")

class SovereignLLMClient:
    """
    Sovereign LLM Client designed for on-premise open-weight models.
    Communicates with the configured local Ollama daemon. A simulator is
    available only when explicitly enabled for disposable demonstrations/tests.
    """
    def __init__(self, base_url: str = settings.OLLAMA_BASE_URL, default_model: str = settings.OLLAMA_DEFAULT_MODEL):
        self.base_url = base_url.rstrip("/")
        self.default_model = default_model

    async def check_health(self) -> Dict[str, Any]:
        """Checks if local Ollama daemon is reachable and lists installed models."""
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                if resp.status_code == 200:
                    data = resp.json()
                    models = [name for m in data.get("models", []) if isinstance(name := m.get("name"), str) and name]
                    
                    exact_names = {name for name in models if name}
                    configured_available = self.default_model in exact_names
                    if ":" not in self.default_model:
                        configured_available = configured_available or f"{self.default_model}:latest" in exact_names
                    resolved_model = self.default_model if configured_available else None

                    return {
                        "status": "online" if configured_available else "model_missing",
                        "engine": "Ollama Local Daemon",
                        "provider": "Ollama",
                        "model": self.default_model,
                        "active_model": resolved_model,
                        "available_models": models,
                        "mode": "LIVE LOCAL INFERENCE" if configured_available else "MODEL_IMPORT_REQUIRED",
                        "sovereign_mode": "native",
                        "is_live_inference": configured_available,
                        "message": None if configured_available else (
                            f"Ollama is reachable, but configured model '{self.default_model}' is not installed."
                        ),
                    }
        except Exception:
            pass

        if settings.SIMULATED_AI_FALLBACK:
            return {
                "status": "simulated",
                "engine": "Demo response simulator",
                "provider": "Simulator",
                "model": None,
                "active_model": None,
                "available_models": [],
                "mode": "DEMO_ONLY",
                "is_live_inference": False,
            }
        return {
            "status": "unavailable",
            "engine": "Ollama",
            "provider": "Ollama",
            "model": self.default_model,
            "active_model": None,
            "available_models": [],
            "mode": "UNAVAILABLE",
            "is_live_inference": False,
            "message": "The local Ollama service is unreachable.",
        }

    async def generate_response(
        self,
        prompt: str,
        system_prompt: str,
        model: Optional[str] = None,
        context_chunks: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """Compatibility wrapper returning only the generated text."""
        response, _mode, _model = await self.generate_grounded_response(
            prompt=prompt,
            system_prompt=system_prompt,
            model=model,
            context_chunks=context_chunks,
        )
        return response

    async def generate_grounded_response(
        self,
        prompt: str,
        system_prompt: str,
        model: Optional[str] = None,
        context_chunks: Optional[List[Dict[str, Any]]] = None,
    ) -> tuple[str, str, Optional[str]]:
        """Return generated text with an explicit, reviewable generation mode."""
        target_model = model or self.default_model

        # Attempt call to local Ollama
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                payload = {
                    "model": target_model,
                    "prompt": prompt,
                    "system": system_prompt,
                    "stream": False,
                    "options": {"temperature": 0.2}
                }
                resp = await client.post(f"{self.base_url}/api/generate", json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    response_text = data.get("response", "").strip()
                    if response_text:
                        logger.info(f"Ollama live inference successful using {target_model}")
                        return response_text, "LOCAL_MODEL", target_model
        except Exception as e:
            logger.warning("Ollama call failed or is unavailable: %s", e)

        if settings.SIMULATED_AI_FALLBACK:
            return self._simulate_sovereign_reasoning(prompt, system_prompt, context_chunks), "DEMO_SIMULATION", None
        raise RuntimeError(f"Configured local model '{target_model}' is unavailable.")

    def _simulate_sovereign_reasoning(
        self,
        prompt: str,
        system_prompt: str,
        context_chunks: Optional[List[Dict[str, Any]]]
    ) -> str:
        """
        Generates realistic, strictly context-grounded answers.
        Never fabricates fictional company policies, roadmaps, or financial numbers.
        """
        query_lower = prompt.lower().strip()
        if "user query:" in query_lower:
            actual_query = query_lower.split("user query:")[1].split("\n")[0].strip()
        elif "\nquestion:" in query_lower:
            actual_query = query_lower.rsplit("\nquestion:", 1)[1].split("\n", 1)[0].strip()
        else:
            actual_query = query_lower

        # Handle basic greetings
        if actual_query in ["hello", "hi", "hey", "good morning", "good afternoon"]:
            return "Hello! How can I assist you with your work or company documents today?"

        # Check if authorized knowledge chunks were retrieved and actually match query terms
        if context_chunks and len(context_chunks) > 0:
            query_words = set(re.findall(r"\w+", actual_query))
            stop_words = {
                "what", "is", "the", "in", "to", "of", "and", "a", "for", "on", "with", "show",
                "me", "how", "are", "by", "our", "we", "us", "was", "were", "company", "corporate",
                "organization", "firm", "enterprise", "internal", "official", "tell"
            }
            meaningful_words = query_words - stop_words or query_words

            def score_chunk(c):
                content_words = re.findall(r"\w+", c.get("content", "").lower())
                return sum(1 for w in content_words if w in meaningful_words)

            sorted_chunks = sorted(context_chunks, key=score_chunk, reverse=True)
            top_score = score_chunk(sorted_chunks[0])

            if top_score > 0:
                top_source = sorted_chunks[0]
                content = top_source.get("content", "").strip()
                title = top_source.get("title", "Company Document")

                # Extract matching sections or paragraphs, prioritizing the most relevant paragraph
                paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]

                def score_para(p):
                    if "DOCUMENT REF:" in p or "CLASSIFICATION:" in p:
                        return 0
                    p_words = re.findall(r"\w+", p.lower())
                    return sum(1 for w in p_words if w in meaningful_words)

                sorted_paras = sorted(paragraphs, key=score_para, reverse=True)
                if sorted_paras and score_para(sorted_paras[0]) > 0:
                    concise_summary = sorted_paras[0]
                else:
                    concise_summary = "\n\n".join(paragraphs[:2]) if paragraphs else content[:500]

                return f"{concise_summary}\n\nSource: {title}"

        # OracleX is a company-evidence assistant. Ungrounded general answers
        # would blur that boundary and are intentionally refused.
        return "I don't have that information in the company's available data."

llm_client = SovereignLLMClient()
