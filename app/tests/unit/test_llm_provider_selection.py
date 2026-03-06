from __future__ import annotations

from app.api import deps


def test_get_llm_provider_returns_none_when_no_key(monkeypatch):
    # ensure cache doesn't leak across tests
    deps.get_llm_provider.cache_clear()

    monkeypatch.setattr(deps.settings, "llm_provider", "openai", raising=False)
    monkeypatch.setattr(deps.settings, "llm_api_key", "", raising=False)
    monkeypatch.setattr(deps.settings, "google_api_key", "", raising=False)

    assert deps.get_llm_provider() is None


def test_get_llm_provider_selects_google_when_configured(monkeypatch):
    deps.get_llm_provider.cache_clear()

    monkeypatch.setattr(deps.settings, "llm_provider", "google", raising=False)
    monkeypatch.setattr(deps.settings, "llm_api_key", "", raising=False)
    monkeypatch.setattr(deps.settings, "google_api_key", "test-key", raising=False)

    provider = deps.get_llm_provider()
    assert provider is not None
    assert provider.__class__.__name__ == "GoogleProvider"

