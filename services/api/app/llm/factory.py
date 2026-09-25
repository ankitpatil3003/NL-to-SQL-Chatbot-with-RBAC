"""Build the LLM router from settings."""

import logging

from app.core.config import Settings
from app.llm.anthropic_provider import AnthropicProvider
from app.llm.base import Provider
from app.llm.bedrock_converse import BedrockConverseProvider
from app.llm.openai_compat import OpenAICompatProvider
from app.llm.router import LLMRouter, Target

log = logging.getLogger(__name__)

TASKS = ("sql", "router", "rewrite", "answer", "title")


def build_providers(settings: Settings) -> dict[str, Provider]:
    providers: dict[str, Provider] = {}
    if settings.openrouter_api_key:
        providers["openrouter"] = OpenAICompatProvider(
            "openrouter",
            "https://openrouter.ai/api/v1",
            settings.openrouter_api_key,
            timeout_s=settings.llm_timeout_s,
            # Attribution headers OpenRouter recommends; usage.include returns per-call cost.
            extra_headers={"HTTP-Referer": settings.public_url, "X-Title": "NovaPharma Analytics"},
            extra_body={"usage": {"include": True}},
        )
    if settings.anthropic_api_key:
        providers["anthropic"] = AnthropicProvider(
            settings.anthropic_api_key, timeout_s=settings.llm_timeout_s
        )
    if settings.bedrock_region:
        providers["bedrock"] = AnthropicProvider.bedrock(
            settings.bedrock_region, timeout_s=settings.llm_timeout_s
        )
        providers["bedrock-converse"] = BedrockConverseProvider(
            settings.bedrock_region, timeout_s=settings.llm_timeout_s
        )
    return providers


def build_router(settings: Settings) -> LLMRouter | None:
    """None when no configured provider can serve the default chain (the API still runs; the
    chat endpoint then reports that the assistant isn't configured)."""
    providers = build_providers(settings)
    chains: dict[str, list[Target]] = {}
    for task, spec in [("default", settings.llm_chain), *settings.llm_task_chains().items()]:
        targets = [Target.parse(s) for s in spec.split(",") if s.strip()]
        usable = [t for t in targets if t.provider in providers]
        for skipped in (t for t in targets if t.provider not in providers):
            log.warning(
                "LLM chain %r: skipping %s (%s is not configured)", task, skipped, skipped.provider
            )
        if usable:
            chains[task] = usable
    if "default" not in chains:
        log.warning("no usable LLM provider configured; the assistant is disabled")
        return None
    return LLMRouter(providers, chains)
