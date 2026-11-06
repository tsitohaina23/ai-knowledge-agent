"""Step 4 (generation): 100 % local, open-source LLM through LangChain + Ollama.

LLM_PROVIDER=none   -> extractive mode: no LLM at all, the API returns the best passages.
LLM_PROVIDER=ollama -> a local open-weights model served by Ollama (e.g. qwen2.5:3b).
No paid API, no data leaves the machine, so the cost per question is 0.
"""

from __future__ import annotations

from dataclasses import dataclass

from langchain_core.language_models.chat_models import BaseChatModel

from app.config import Settings


class LLMConfigError(RuntimeError):
    """Raised when the selected provider cannot be built."""


@dataclass
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def total(self) -> int:
        return self.input_tokens + self.output_tokens


def usage_from_message(msg) -> Usage:
    """LangChain normalises token usage across providers in `usage_metadata`."""
    meta = getattr(msg, "usage_metadata", None) or {}
    return Usage(int(meta.get("input_tokens", 0)), int(meta.get("output_tokens", 0)))


def build_chat_model(settings: Settings) -> BaseChatModel | None:
    if settings.llm_provider == "none":
        return None
    if settings.llm_provider == "ollama":
        try:
            from langchain_ollama import ChatOllama
        except ImportError as exc:  # pragma: no cover
            raise LLMConfigError("pip install langchain-ollama") from exc
        return ChatOllama(
            model=settings.resolved_model,
            base_url=settings.ollama_base_url,
            temperature=settings.llm_temperature,
            num_predict=settings.llm_max_tokens,
            client_kwargs={"timeout": settings.llm_timeout_s},
        )
    raise LLMConfigError(f"Unknown LLM_PROVIDER '{settings.llm_provider}'")
