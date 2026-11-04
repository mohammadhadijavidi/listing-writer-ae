import json

import pytest

from listing_writer_ae import providers as pv


def test_default_is_mock(monkeypatch):
    monkeypatch.delenv("LISTING_PROVIDER", raising=False)
    p = pv.get_provider()
    assert p.name == "mock" and p.is_mock


def test_openai_requires_key(monkeypatch):
    for k in ("LISTING_API_KEY", "OPENAI_API_KEY", "LISTING_BASE_URL"):
        monkeypatch.delenv(k, raising=False)
    with pytest.raises(pv.ProviderError):
        pv.get_provider("openai")


def test_local_servers_need_no_key(monkeypatch):
    for k in ("LISTING_API_KEY", "OPENAI_API_KEY", "LISTING_BASE_URL"):
        monkeypatch.delenv(k, raising=False)
    p = pv.get_provider("ollama")
    assert p.base_url == "http://localhost:11434/v1" and p.api_key is None
    assert pv.get_provider("lmstudio").base_url.endswith(":1234/v1")


def test_env_configuration(monkeypatch):
    monkeypatch.setenv("LISTING_PROVIDER", "openrouter")
    monkeypatch.setenv("LISTING_API_KEY", "k")
    monkeypatch.setenv("LISTING_MODEL", "some/model")
    p = pv.get_provider()
    assert p.name == "openrouter" and p.model == "some/model" and p.base_url == "https://openrouter.ai/api/v1"
    monkeypatch.setenv("LISTING_BASE_URL", "http://127.0.0.1:9000/v1/")
    assert pv.get_provider("openai-compatible").base_url == "http://127.0.0.1:9000/v1"


def test_anthropic_requires_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(pv.ProviderError):
        pv.get_provider("anthropic")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "x")
    assert pv.get_provider("anthropic").name == "anthropic"


def test_unknown_provider():
    with pytest.raises(pv.ProviderError):
        pv.get_provider("nope")


def test_openai_payload_and_parsing(monkeypatch):
    seen = {}

    def fake_post(url, payload, headers, timeout=120.0):
        seen.update(url=url, payload=payload, headers=headers)
        return {"choices": [{"message": {"content": "{}"}}]}

    monkeypatch.setattr(pv, "_post", fake_post)
    p = pv.OpenAICompatible("m", "key", "https://x/v1")
    assert p.complete(pv.Prompt("sys", "user")) == "{}"
    assert seen["url"] == "https://x/v1/chat/completions"
    assert seen["headers"]["Authorization"] == "Bearer key"
    assert seen["payload"]["messages"][0] == {"role": "system", "content": "sys"}
    assert seen["payload"]["response_format"] == {"type": "json_object"}


def test_openai_retries_without_response_format(monkeypatch):
    calls = []

    def fake_post(url, payload, headers, timeout=120.0):
        calls.append(dict(payload))
        if "response_format" in payload:
            raise pv.ProviderError("HTTP 400 from x: response_format not supported")
        return {"choices": [{"message": {"content": "ok"}}]}

    monkeypatch.setattr(pv, "_post", fake_post)
    assert pv.OpenAICompatible("m", None, "http://localhost:1/v1").complete(pv.Prompt("s", "u")) == "ok"
    assert len(calls) == 2 and "response_format" not in calls[1]


def test_anthropic_payload_and_parsing(monkeypatch):
    seen = {}

    def fake_post(url, payload, headers, timeout=120.0):
        seen.update(url=url, payload=payload, headers=headers)
        return {"content": [{"type": "text", "text": "a"}, {"type": "text", "text": "b"}]}

    monkeypatch.setattr(pv, "_post", fake_post)
    p = pv.Anthropic("claude-x", "k")
    assert p.complete(pv.Prompt("sys", "u")) == "ab"
    assert seen["url"].endswith("/v1/messages") and seen["headers"]["x-api-key"] == "k"
    assert seen["payload"]["system"] == "sys"


def test_unexpected_response(monkeypatch):
    monkeypatch.setattr(pv, "_post", lambda *a, **k: {"weird": json.dumps({})})
    with pytest.raises(pv.ProviderError):
        pv.OpenAICompatible("m", "k").complete(pv.Prompt("s", "u"))
