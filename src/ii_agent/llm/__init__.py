from ii_agent.llm.base import LLMClient
from ii_agent.llm.openai import OpenAIDirectClient
from ii_agent.llm.anthropic import AnthropicDirectClient
from ii_agent.llm.chutes_openai import ChutesOpenAIClient
from ii_agent.llm.openrouter_openai import OpenRouterOpenAIClient
from ii_agent.llm.moonshot import MoonshotDirectClient


def get_client(client_name: str, **kwargs) -> LLMClient:
    """Get a client for a given client name."""
    if client_name == "anthropic-direct":
        return AnthropicDirectClient(**kwargs)
    elif client_name == "openai-direct":
        return OpenAIDirectClient(**kwargs)
    elif client_name == "chutes-openai":
        return ChutesOpenAIClient(**kwargs)
    elif client_name == "openrouter-openai":
        return OpenRouterOpenAIClient(**kwargs)
    elif client_name == "moonshot-direct":
        return MoonshotDirectClient(**kwargs)
    else:
        raise ValueError(f"Unknown client name: {client_name}")


__all__ = [
    "LLMClient",
    "OpenAIDirectClient",
    "AnthropicDirectClient",
    "ChutesOpenAIClient",
    "OpenRouterOpenAIClient",
    "get_client",
]
