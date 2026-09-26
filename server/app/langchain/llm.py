from langchain.agents import create_agent
from langchain.chat_models import init_chat_model

from app.core.logging import logger
from app.langchain.tools import get_tools
from app.types import Context
from app.utils.prompts import SYSTEM_PROMPT

AVAILABLE_MODELS: dict[str, dict] = {
    "qwen3:4b": {
        "model": "qwen3:4b",
        "model_provider": "ollama",
        "temperature": 0.0,
        "display_name": "Qwen 3 4B",
        "description": "Fast, lightweight model for quick responses.",
    },
    "qwen2.5:1.5b": {
        "model": "qwen2.5:1.5b",
        "model_provider": "ollama",
        "temperature": 0.0,
        "display_name": "Qwen 2.5 1.5B",
        "description": "Ultra-light model for simple tasks.",
    },
}

DEFAULT_MODEL = "qwen3:4b"

AVAILABLE_RAG_STRATEGIES: dict[str, dict] = {
    "basic": {
        "id": "basic",
        "display_name": "Basic RAG",
        "description": "Standard vector similarity search (top-k chunks from Pinecone).",
    },
    "corrective": {
        "id": "corrective",
        "display_name": "Corrective RAG (CRAG)",
        "description": "Evaluates retrieved chunks for relevance and falls back to web search if relevance is low.",
    },
    "adaptive_gate": {
        "id": "adaptive_gate",
        "display_name": "Adaptive Retrieval Gate",
        "description": "Uses an LLM gate to dynamically decide whether and how much context to retrieve based on the query.",
    },
}

DEFAULT_RAG_STRATEGY = "basic"

llm_cache: dict[str, object] = {}
agent_cache: dict[str, object] = {}

# ---------------------------------------------------------------------------------


def get_llm(llm_model: str | None = None):
    """Return an initialized base chat model for the given model slug (cached)."""
    selected_llm = llm_model or DEFAULT_MODEL

    if selected_llm not in AVAILABLE_MODELS:
        selected_llm = DEFAULT_MODEL
        logger.warning("Unknown model '%s', falling back to '%s'", selected_llm, DEFAULT_MODEL)

    if selected_llm not in llm_cache:
        model_data = AVAILABLE_MODELS[selected_llm]
        llm = init_chat_model(
            model=model_data["model"],
            model_provider=model_data["model_provider"],
            temperature=model_data.get("temperature", 0.0),
        )
        llm_cache[selected_llm] = llm

    return llm_cache[selected_llm]


def get_agent(llm_model: str | None = None):
    """Return an agent executor for the given model slug (cached)."""
    selected_llm = llm_model or DEFAULT_MODEL

    if selected_llm not in AVAILABLE_MODELS:
        selected_llm = DEFAULT_MODEL
        logger.warning("Unknown model '%s', falling back to '%s'", selected_llm, DEFAULT_MODEL)

    if selected_llm not in agent_cache:
        llm = get_llm(selected_llm)
        agent_cache[selected_llm] = create_agent(
            model=llm,
            tools=get_tools(),
            system_prompt=SYSTEM_PROMPT,
            context_schema=Context,
        )
        logger.info("Agent created for model '%s'", selected_llm)

    return agent_cache[selected_llm]


def list_models() -> list[dict]:
    return [
        {
            "model": model_name,
            "display_name": model_data["display_name"],
            "description": model_data["description"],
            "provider": model_data["model_provider"],
        }
        for model_name, model_data in AVAILABLE_MODELS.items()
    ]


def list_rag_strategies() -> list[dict]:
    return list(AVAILABLE_RAG_STRATEGIES.values())
