"""Small LLM provider layer: OpenAI-compatible APIs, Anthropic, and an offline mock.

Standard library only (urllib).

Environment variables
---------------------
LISTING_PROVIDER    mock | openai | openrouter | groq | ollama | lmstudio | openai-compatible | anthropic  (default: mock)
LISTING_MODEL       model name for the chosen provider
LISTING_BASE_URL    override base URL for OpenAI-compatible servers (vLLM, Together, a proxy, ...)
LISTING_API_KEY / OPENAI_API_KEY    key for OpenAI-compatible endpoints
ANTHROPIC_API_KEY   key for Anthropic
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass


class ProviderError(RuntimeError):
    pass


@dataclass
class Prompt:
    system: str
    user: str


def _post(url: str, payload: dict, headers: dict[str, str], timeout: float = 120.0) -> dict:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")[:500]
        raise ProviderError(f"HTTP {e.code} from {url}: {body}") from e
    except urllib.error.URLError as e:
        raise ProviderError(f"Cannot reach {url}: {e.reason}") from e


class OpenAICompatible:
    """OpenAI, OpenRouter, Groq, Ollama (/v1), LM Studio, vLLM, ..."""

    name = "openai"
    is_mock = False

    def __init__(self, model: str, api_key: str | None, base_url: str = "https://api.openai.com/v1"):
        self.model = model
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    def build_payload(self, prompt: Prompt, max_tokens: int = 2500) -> dict:
        return {
            "model": self.model,
            "messages": [{"role": "system", "content": prompt.system}, {"role": "user", "content": prompt.user}],
            "temperature": 0.4,
            "max_tokens": max_tokens,
            "response_format": {"type": "json_object"},
        }

    def complete(self, prompt: Prompt, max_tokens: int = 2500) -> str:
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        payload = self.build_payload(prompt, max_tokens)
        try:
            data = _post(f"{self.base_url}/chat/completions", payload, headers)
        except ProviderError as e:
            # Some local / third-party servers reject response_format; retry once without it.
            if "response_format" not in str(e) and "HTTP 400" not in str(e):
                raise
            payload.pop("response_format", None)
            data = _post(f"{self.base_url}/chat/completions", payload, headers)
        try:
            return data["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError, TypeError) as e:
            raise ProviderError(f"Unexpected response: {str(data)[:300]}") from e


class Anthropic:
    name = "anthropic"
    is_mock = False

    def __init__(self, model: str, api_key: str | None, base_url: str = "https://api.anthropic.com"):
        if not api_key:
            raise ProviderError("ANTHROPIC_API_KEY is not set")
        self.model = model
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    def build_payload(self, prompt: Prompt, max_tokens: int = 2500) -> dict:
        return {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": 0.4,
            "system": prompt.system,
            "messages": [{"role": "user", "content": prompt.user}],
        }

    def complete(self, prompt: Prompt, max_tokens: int = 2500) -> str:
        data = _post(
            f"{self.base_url}/v1/messages",
            self.build_payload(prompt, max_tokens),
            {"x-api-key": self.api_key, "anthropic-version": "2023-06-01"},
        )
        try:
            return "".join(b.get("text", "") for b in data["content"] if b.get("type") == "text")
        except (KeyError, TypeError) as e:
            raise ProviderError(f"Unexpected response: {str(data)[:300]}") from e


class Mock:
    """Offline, deterministic stand-in. It does not call any model.

    ``write_listing`` detects it and uses the built-in bilingual template writer instead. Output is always
    labelled ``written_by = "mock (template writer, no LLM)"``.
    """

    name = "mock"
    model = "template"
    is_mock = True

    def complete(self, prompt: Prompt, max_tokens: int = 2500) -> str:  # pragma: no cover - never used
        raise ProviderError("The mock provider does not generate text; the template writer is used instead.")


_OPENAI_BASES = {
    "openai": "https://api.openai.com/v1",
    "openrouter": "https://openrouter.ai/api/v1",
    "groq": "https://api.groq.com/openai/v1",
    "ollama": "http://localhost:11434/v1",
    "lmstudio": "http://localhost:1234/v1",
}

_DEFAULT_MODELS = {
    "openai": "gpt-4o-mini",
    "openrouter": "openai/gpt-4o-mini",
    "groq": "llama-3.3-70b-versatile",
    "ollama": "qwen2.5:7b",
    "lmstudio": "local-model",
    "openai-compatible": "gpt-4o-mini",
}

PROVIDERS = ["mock", *list(_OPENAI_BASES), "openai-compatible", "anthropic"]


def get_provider(provider: str | None = None, model: str | None = None):
    provider = (provider or os.getenv("LISTING_PROVIDER") or "mock").strip().lower()
    model = model or os.getenv("LISTING_MODEL")
    if provider == "mock":
        return Mock()
    if provider in _OPENAI_BASES or provider == "openai-compatible":
        base = os.getenv("LISTING_BASE_URL") or _OPENAI_BASES.get(provider, _OPENAI_BASES["openai"])
        key = os.getenv("LISTING_API_KEY") or os.getenv("OPENAI_API_KEY")
        local = provider in {"ollama", "lmstudio"} or "localhost" in base or "127.0.0.1" in base
        if not key and not local:
            raise ProviderError("Set LISTING_API_KEY (or OPENAI_API_KEY) for this provider")
        p = OpenAICompatible(model or _DEFAULT_MODELS[provider], key, base)
        p.name = provider
        return p
    if provider == "anthropic":
        return Anthropic(model or "claude-sonnet-4-5", os.getenv("ANTHROPIC_API_KEY"))
    raise ProviderError(f"Unknown provider: {provider!r} (use {', '.join(PROVIDERS)})")
