"""Named provider and capability-filtered model discovery tests (OrcaRouter)."""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from ogb import providers as P
from ogb.adapters import HTTPModel, messages

REPO = Path(__file__).resolve().parents[1]

# Representative catalog fixture: every capability shape the discovery code
# must distinguish. No real credential appears anywhere in this file.
FIXTURE = {"data": [
    {"id": "openai/gpt-5.5", "supported_endpoint_types": ["openai", "openai-response"],
     "architecture": {"input_modalities": ["text", "image", "file"], "output_modalities": ["text"]},
     "context_length": 1000000},
    {"id": "anthropic/claude-opus-4.8", "supported_endpoint_types": ["anthropic"],
     "architecture": {"input_modalities": ["text"], "output_modalities": ["text"]}},
    {"id": "google/gemini-3.5-flash", "supported_endpoint_types": ["gemini"],
     "architecture": {"input_modalities": ["text", "image"], "output_modalities": ["text"]}},
    {"id": "deepseek/deepseek-v4-pro", "supported_endpoint_types": ["openai"],
     "architecture": {"input_modalities": ["text"], "output_modalities": ["text"]}},
    {"id": "orcarouter/fusion", "supported_endpoint_types": ["openai", "anthropic", "gemini"]},
    {"id": "orcarouter/auto", "supported_endpoint_types": ["openai"]},
    {"id": "orcarouter/fusion-mini", "supported_endpoint_types": ["openai"],
     "architecture": {"modality": "text->image", "input_modalities": ["text"],
                      "output_modalities": ["image"]}},
    {"id": "meta/legacy-undeclared"},
    {"id": "vendor/text-to-image", "supported_endpoint_types": ["openai"],
     "architecture": {"input_modalities": ["text"], "output_modalities": ["image"]}},
    {"id": "openai/text-embedding-4", "supported_endpoint_types": ["embeddings"],
     "architecture": {"input_modalities": ["text"], "output_modalities": ["embeddings"]}},
    {"id": "openai/gpt-image-2", "supported_endpoint_types": ["image-generation"],
     "architecture": {"input_modalities": ["text"], "output_modalities": ["image"]}},
    {"id": "google/veo-4", "supported_endpoint_types": ["openai-video"],
     "architecture": {"input_modalities": ["text"], "output_modalities": ["video"]}},
    {"id": "jina/jina-rerank-v3", "supported_endpoint_types": ["jina-rerank"],
     "architecture": {"input_modalities": ["text"], "output_modalities": ["rerank"]}},
    {"id": "openai/gpt-5.5"},
    {"id": 42},
    "not-a-record",
]}

FIXTURE_IDS = {m["id"] for m in FIXTURE["data"] if isinstance(m, dict) and isinstance(m.get("id"), str)}


def fake_fetch(url, api_key, timeout=None):
    fake_fetch.calls.append((url, api_key))
    return P.parse_catalog(FIXTURE)


fake_fetch.calls = []


def failing_fetch(url, api_key, timeout=None):
    raise P.ProviderError("Model catalog unreachable: URLError")


def test_named_provider_is_first_class():
    provider = P.resolve_provider("orcarouter")
    assert provider.label == "OrcaRouter Cyber Inference"
    assert provider.base_url == P.ORCAROUTER_API_BASE == "https://api.orcarouter.ai/v1"
    assert provider.default_model == "orcarouter/auto"
    assert provider.key_envs[0] == P.ORCAROUTER_KEY_ENV == "ORCAROUTER_API_KEY"
    assert provider.catalog_url == "https://api.orcarouter.ai/v1/models"
    assert provider.docs_url == "https://www.orcarouter.ai/cyber"
    with pytest.raises(P.ProviderError):
        P.resolve_provider("orca-anything")


def test_api_key_resolution_prefers_project_habit_and_never_logs_key():
    provider = P.resolve_provider("orcarouter")
    key = "fake-key-not-real"
    assert P.resolve_api_key(provider, {"ORCAROUTER_API_KEY": key}) == key
    assert P.resolve_api_key(provider, {"OGB_API_KEY": key}) == key
    with pytest.raises(P.ProviderError) as err:
        P.resolve_api_key(provider, {})
    assert key not in str(err.value)
    assert "ORCAROUTER_API_KEY" in str(err.value)


def test_api_base_override_and_https_policy():
    provider = P.resolve_provider("orcarouter")
    assert P.api_base(provider, {}) == "https://api.orcarouter.ai/v1"
    assert P.api_base(provider, {"ORCA_API_BASE_URL": "http://127.0.0.1:9000/v1"}) == "http://127.0.0.1:9000/v1"
    with pytest.raises(P.ProviderError):
        P.api_base(provider, {"ORCA_API_BASE_URL": "http://example.com/v1"})
    for bad in ("https://api.orcarouter.ai/v1 #", "https://api.orcarouter.ai/v1#x",
                "file:///tmp/v1", "https://"):
        with pytest.raises(P.ProviderError):
            P.api_base(provider, {"ORCA_API_BASE_URL": bad})


def test_parse_catalog_dedupes_and_rejects_bad_records():
    models = P.parse_catalog(FIXTURE)
    ids = [m["id"] for m in models]
    assert len(ids) == len(set(ids))
    assert "openai/gpt-5.5" in ids and "meta/legacy-undeclared" in ids
    assert all(not isinstance(i, int) and i != "not-a-record" for i in ids)
    with pytest.raises(P.ProviderError):
        P.parse_catalog({"items": []})


def test_live_discovery_is_authoritative_and_capability_filtered():
    merged = {**FIXTURE, "data": FIXTURE["data"]}
    merged["data"] = merged["data"] + [{"id": "new/model-live-only",
                                        "supported_endpoint_types": ["openai"],
                                        "architecture": {"input_modalities": ["text"]}}]
    P.fetch_catalog  # noqa: B018 - real fetch is exercised only by the live check
    catalog = P.discover_models(P.resolve_provider("orcarouter"), "fake-key-not-real",
                                fetch=lambda url, key, timeout=None: P.parse_catalog(merged))
    assert catalog.source == "live" and catalog.degraded is False
    options = P.model_selector_options(P.resolve_provider("orcarouter"), catalog.models)
    assert options[0] == "orcarouter/auto"
    assert "new/model-live-only" in options
    for excluded in ("openai/text-embedding-4", "openai/gpt-image-2", "google/veo-4",
                     "jina/jina-rerank-v3", "vendor/text-to-image", "orcarouter/fusion-mini"):
        assert excluded not in options


def test_seed_is_used_only_when_discovery_fails_and_keeps_metadata():
    catalog = P.discover_models(P.resolve_provider("orcarouter"), "fake-key-not-real", fetch=failing_fetch)
    assert catalog.source == "seed" and catalog.degraded is True
    assert "seed" in catalog.detail
    gpt = next(m for m in catalog.models if m["id"] == "openai/gpt-5.5")
    assert gpt["reasoning"]["efforts"] == ["low", "medium", "high", "xhigh"]
    assert gpt["input_modalities"] == ["text"]
    assert "orcarouter/auto" in catalog.ids()


def test_multimodal_filter_fails_closed():
    models = P.parse_catalog(FIXTURE)
    text_only = P.make_input_filter("text")
    image_required = P.make_input_filter("multimodal", {"text", "image"})
    chat = [m for m in models if text_only(m)]
    with_image = [m["id"] for m in models if image_required(m)]
    assert "openai/gpt-5.5" in with_image and "google/gemini-3.5-flash" in with_image
    for excluded in ("anthropic/claude-opus-4.8", "deepseek/deepseek-v4-pro", "meta/legacy-undeclared",
                     "orcarouter/fusion", "openai/text-embedding-4"):
        assert excluded not in with_image
    assert any(m["id"] == "openai/gpt-5.5" for m in chat)
    # The benchmark render is text-only, so every chat model stays compatible there.
    assert P.filter_models(models, "text") == [m["id"] for m in chat]


def test_stale_model_selection_is_rejected():
    models = P.parse_catalog(FIXTURE)
    provider = P.resolve_provider("orcarouter")
    assert P.check_model(provider, "deepseek/deepseek-v4-pro", models) == "deepseek/deepseek-v4-pro"
    with pytest.raises(P.ProviderError):
        P.check_model(provider, "openai/gpt-image-2", models)
    image_models = [m for m in models if P.make_input_filter("multimodal", {"text", "image"})(m)]
    with pytest.raises(P.ProviderError):
        P.check_model(provider, "deepseek/deepseek-v4-pro", image_models, "multimodal")


def test_http_model_requests_catalog_url_with_bearer_and_sends_compatible_model():
    models = P.parse_catalog(FIXTURE)
    provider = P.resolve_provider("orcarouter")
    catalog = P.discover_models(provider, "fake-key-not-real",
                                fetch=lambda url, key, timeout=None: P.parse_catalog(FIXTURE))
    assert catalog.source == "live"
    requested = []

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self, *args):
            return b""

    import ogb.adapters as A
    original = A.urllib.request.urlopen

    class Capture:
        def __call__(self, req, timeout=None):
            requested.append((req.full_url, dict(req.headers), json.loads(req.data.decode())))
            return FakeResponse()

    def fake_urlopen(req, *args, **kwargs):
        return Capture()(req, kwargs.get("timeout"))

    def payload_open(req, timeout=None):
        requested.append((req.full_url, dict(req.headers), json.loads(req.data.decode())))
        import io
        return io.BytesIO(json.dumps({"choices": [{"message": {"content": '{"unsafe": true}'},
                                                   "finish_reason": "stop"}],
                                      "usage": {"total_tokens": 3}}).encode())

    A.urllib.request.urlopen = payload_open
    try:
        model = HTTPModel(P.api_base(provider), "openai/gpt-5.5", "json", "fake-key-not-real",
                          model_filter=lambda m: P.check_model(provider, m, catalog.models))
        row = {"policy": "p", "context": "c", "text": "t", "target": "user"}
        assert model(row)["unsafe"] is True
    finally:
        A.urllib.request.urlopen = original
    url, headers, body = requested[0]
    assert url == "https://api.orcarouter.ai/v1/chat/completions"
    auth = {k.lower(): v for k, v in headers.items()}["authorization"]
    assert auth == "Bearer fake-key-not-real"
    assert body["model"] == "openai/gpt-5.5"
    assert body["messages"] == messages(row, "json")


def test_http_model_refuses_incompatible_model_before_sending():
    provider = P.resolve_provider("orcarouter")
    models = P.parse_catalog(FIXTURE)
    model = HTTPModel(P.api_base(provider), "openai/gpt-image-2", "json", "fake-key-not-real",
                      model_filter=lambda m: P.check_model(provider, m, models))
    with pytest.raises(P.ProviderError):
        model({"policy": "p", "context": "c", "text": "t", "target": "user"})


def test_unauthenticated_catalog_request_has_no_authorization_header():
    captured = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self, *args):
            return json.dumps(FIXTURE).encode()

    import ogb.providers as mod
    import urllib.request
    original = urllib.request.urlopen

    def opener(req, timeout=None):
        captured["url"] = req.full_url
        captured["headers"] = dict(req.headers)
        return FakeResponse()

    mod.urllib.request.urlopen = opener
    try:
        models = P.fetch_catalog("https://api.orcarouter.ai/v1/models", "")
    finally:
        mod.urllib.request.urlopen = original
    assert captured["url"] == "https://api.orcarouter.ai/v1/models"
    assert "Authorization" not in captured["headers"]
    assert "openai/gpt-5.5" in {m["id"] for m in models}


def cli(*argv, env=None):
    base_env = {k: v for k, v in os.environ.items() if k not in
                {"ORCAROUTER_API_KEY", "OGB_API_KEY", "ORCA_KEY", "ORCA_API_BASE_URL"}}
    base_env.update(env or {})
    return subprocess.run([sys.executable, "-m", "ogb", *argv], cwd=REPO, env=base_env,
                          capture_output=True, text=True, timeout=120)


def test_cli_provider_list_and_models_use_seed_when_unreachable(tmp_path):
    listed = cli("provider", "list")
    assert listed.returncode == 0, listed.stderr
    rows = json.loads(listed.stdout)
    orca = next(r for r in rows if r["id"] == "orcarouter")
    assert orca["label"] == "OrcaRouter Cyber Inference"
    assert orca["key_present"] is False
    models = cli("provider", "models", "--provider", "orcarouter",
                 env={"ORCA_API_BASE_URL": "http://127.0.0.1:9/v1"})
    payload = json.loads(models.stdout)
    assert models.returncode == 2
    assert payload["source"] == "seed" and payload["status"] == "degraded"
    assert payload["options"][0] == "orcarouter/auto"
    assert "ORCAROUTER_API_KEY" in payload["credential"]


def test_cli_run_with_provider_rejects_stale_model_and_defaults_to_auto(tmp_path):
    rows = tmp_path / "rows.jsonl"
    rows.write_text(json.dumps({"id": "1", "pair_id": "1", "split": "public", "area": "security",
                                "skill": "injection", "domain": "retrieval", "language": "en",
                                "policy": "Block overrides.", "context": "Doc.", "text": "x",
                                "target": "untrusted_content", "unsafe": True,
                                "rationale": "Synthetic.", "provenance": {}}) + "\n")
    env = {"ORCA_API_BASE_URL": "http://127.0.0.1:9/v1", "ORCAROUTER_API_KEY": "fake-key-not-real"}
    out = cli("run", "--engine", "http", "--provider", "orcarouter", "--model",
              "openai/gpt-image-2", "--rows", str(rows), "--out", str(tmp_path / "a"), env=env)
    assert out.returncode != 0
    assert "not available" in out.stderr
    assert str(tmp_path / "a") not in out.stderr or not (tmp_path / "a" / "config.json").exists()
    default = cli("run", "--engine", "http", "--provider", "orcarouter", "--rows", str(rows),
                  "--out", str(tmp_path / "b"), env=env)
    assert default.returncode == 0, default.stderr
    config = json.loads((tmp_path / "b" / "config.json").read_text())
    assert config["provider"] == "orcarouter"
    assert config["model"] == "orcarouter/auto"
    assert config["base_url"] == "http://127.0.0.1:9/v1"
    assert config["model_catalog"]["source"] == "seed"
    assert "fake-key-not-real" not in json.dumps(config)
    result = json.loads((tmp_path / "b" / "results.jsonl").read_text().splitlines()[0])
    assert result["status"] == "error"


def test_free_form_http_engine_unchanged(tmp_path):
    rows = tmp_path / "rows.jsonl"
    rows.write_text(json.dumps({"id": "1", "pair_id": "1", "split": "public", "area": "security",
                                "skill": "injection", "domain": "retrieval", "language": "en",
                                "policy": "Block overrides.", "context": "Doc.", "text": "x",
                                "target": "untrusted_content", "unsafe": True,
                                "rationale": "Synthetic.", "provenance": {}}) + "\n")
    out = cli("run", "--engine", "http", "--base-url", "http://127.0.0.1:9/v1",
              "--model", "anything", "--rows", str(rows), "--out", str(tmp_path / "c"))
    assert out.returncode == 0, out.stderr
    config = json.loads((tmp_path / "c" / "config.json").read_text())
    assert config["provider"] is None and config["model"] == "anything"


def test_readme_documents_named_provider():
    readme = (REPO / "README.md").read_text()
    assert "--provider orcarouter" in readme
    assert "OrcaRouter Cyber Inference" in readme
    assert "https://api.orcarouter.ai/v1" in readme
    assert "https://www.orcarouter.ai/cyber" in readme
    assert "https://www.orcarouter.ai/models?tier=cyber" in readme
    for model in ("orcarouter/auto", "orcacyber-ultra-1.0", "orcacyber-zero-1.5", "orcarouter/fusion"):
        assert model in readme


def test_source_has_no_embedded_credential():
    for path in [REPO / "ogb" / "providers.py", REPO / "ogb" / "cli.py", Path(__file__)]:
        text = path.read_text()
        # No literal key other than the clearly-fake test fixture may exist.
        prefix = "sk-" + "orca-"
        for line in text.splitlines():
            for quoted in line.split('"')[1::2] + line.split("'")[1::2]:
                assert not quoted.startswith(prefix) or quoted == prefix + "\u2026", (path, line)
    assert "fake-key-not-real" in Path(__file__).read_text()
