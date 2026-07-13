"""Points the OpenAI Agents SDK at OpenRouter instead of the OpenAI platform.

OpenRouter exposes an OpenAI-compatible Chat Completions endpoint, so the SDK works
unchanged once the default client targets it. Tracing is disabled because the SDK's
trace exporter uploads to the OpenAI platform, which this deployment does not use.
"""

from agents import set_default_openai_api, set_default_openai_client, set_tracing_disabled
from openai import AsyncOpenAI

from app.config import get_settings


def configure_model_provider() -> None:
    settings = get_settings()
    client = AsyncOpenAI(
        base_url=settings.openrouter_base_url,
        api_key=settings.openrouter_api_key or "missing-openrouter-api-key",
    )
    set_default_openai_client(client, use_for_tracing=False)
    # OpenRouter implements Chat Completions, not the OpenAI Responses API.
    set_default_openai_api("chat_completions")
    set_tracing_disabled(True)
