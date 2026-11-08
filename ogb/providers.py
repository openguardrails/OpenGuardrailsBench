"""Named model providers and capability-filtered model discovery.

The HTTP engine in :mod:`ogb.adapters` speaks the OpenAI chat-completions wire
format. :data:`PROVIDERS` names the providers a submission can select with
``python -m ogb run --provider <id>``; the free-form ``--engine http
--base-url/--model/--adapter`` path is unchanged for every other server.

Model lists are never hand-written guesses: for OrcaRouter the live catalog is
``GET <api_base>/models`` and the cold-start seed is a small, verified subset
with explicit capability metadata. Live discovery is authoritative; the seed is
only used, clearly labelled, when discovery fails.
"""
import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Optional

ORCAROUTER_API_BASE = "https://api.orcarouter.ai/v1"
ORCAROUTER_KEY_ENV = "ORCAROUTER_API_KEY"
ORCAROUTER_KEY_FALLBACK_ENVS = ("OGB_API_KEY", "ORCA_KEY")
CATALOG_TIMEOUT = 20
CATALOG_MAX_BYTES = 4 * 1024 * 1024
CATALOG_MAX_ITEMS = 2000
# Endpoint types the OpenAI-compatible chat path in ogb.adapters can speak.
TEXT_ENDPOINT_TYPES = frozenset({"openai", "anthropic", "gemini", "openai-response"})
NON_TEXT_ENDPOINT_TYPES = frozenset({"image-generation", "openai-video", "jina-rerank",
                                     "embeddings", "audio"})

TEXT = "text"
MULTIMODAL = "multimodal"
CAPABILITIES = (TEXT, MULTIMODAL)
# Modalities the benchmark render (policy/context/target as plain text) uploads.
ACTIVE_INPUT_MODALITIES = frozenset({TEXT})

# Verified cold-start seed (outage fallback only, never merged into live results).
# Source: GET https://api.orcarouter.ai/v1/models?capability=chat, verified
# 2026-11-08. Text-only models carry no extra modalities; GPT-5.5 keeps the
# reasoning-effort ladder this repository reports for it.
SEED_MODELS = (
    {"id": "openai/gpt-5.5", "input_modalities": [TEXT], "context_length": 1000000,
     "reasoning": {"efforts": ["low", "medium", "high", "xhigh"]}},
    {"id": "anthropic/claude-opus-4.8", "input_modalities": [TEXT], "context_length": 200000},
    {"id": "google/gemini-3.5-flash", "input_modalities": [TEXT], "reasoning": {"efforts": ["low", "high"]}},
    {"id": "deepseek/deepseek-v4-pro", "input_modalities": [TEXT], "context_length": 262144},
    {"id": "orcarouter/auto", "input_modalities": [TEXT], "context_length": 200000},
    {"id": "orcarouter/fusion", "input_modalities": [TEXT], "context_length": 1000000},
)


@dataclass(frozen=True)
class Provider:
    """A named, directly selectable provider definition."""
    id: str
    label: str
    base_url: str
    default_model: str
    key_envs: tuple
    catalog_url: str = ""
    docs_url: str = ""
    description: str = ""


PROVIDERS = {
    "orcarouter": Provider(
        id="orcarouter",
        label="OrcaRouter Cyber Inference",
        base_url=ORCAROUTER_API_BASE,
        default_model="orcarouter/auto",
        key_envs=(ORCAROUTER_KEY_ENV,) + ORCAROUTER_KEY_FALLBACK_ENVS,
        catalog_url=ORCAROUTER_API_BASE + "/models",
        docs_url="https://www.orcarouter.ai/cyber",
        description=("Cyber inference for authorized security teams: routes guardrail "
                     "classification over one OpenAI-compatible endpoint."),
    ),
}


class ProviderError(ValueError):
    """Raised with an actionable message; never carries a credential."""


@dataclass
class ModelCatalog:
    models: list
    source: str  # "live" or "seed"
    degraded: bool = False
    detail: str = ""
    extra: dict = field(default_factory=dict)

    def ids(self):
        return [m["id"] for m in self.models]


def resolve_provider(provider_id):
    try:
        return PROVIDERS[provider_id]
    except KeyError:
        raise ProviderError(f"Unknown provider {provider_id!r}; choose from {sorted(PROVIDERS)}")


def api_base(provider, env=None):
    """Explicit OrcaRouter API override wins, then the provider default."""
    env = os.environ if env is None else env
    if provider.id == "orcarouter":
        override = env.get("ORCA_API_BASE_URL") or None
        if override:
            return _check_url(override, "ORCA_API_BASE_URL")
    return provider.base_url


def resolve_api_key(provider, env=None):
    """Read the key through the project's existing environment secret habit."""
    env = os.environ if env is None else env
    for name in provider.key_envs:
        value = env.get(name)
        if value:
            return value
    raise ProviderError("No OrcaRouter credential found: set "
                        + " or ".join(provider.key_envs)
                        + " (create a key at https://www.orcarouter.ai/console)")


def _check_url(url, name):
    from urllib.parse import urlparse
    parsed = urlparse(url)
    if (parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.fragment
            or parsed.params or any(c.isspace() for c in url)):
        raise ProviderError(f"{name} must be an http(s) URL")
    if parsed.scheme != "https" and parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise ProviderError(f"{name} must use HTTPS unless it points at loopback")
    return url


def capability_filter(capability):
    """Return a predicate for chat-compatible models matching an entry's needs.

    ``text`` is the benchmark's actual modality (policy/context/target are
    rendered to text). ``multimodal`` requires every non-text input declared by
    the caller via :func:`make_input_filter`; unknown metadata fails closed.
    """
    if capability not in CAPABILITIES:
        raise ProviderError(f"Unknown capability {capability!r}; choose from {list(CAPABILITIES)}")

    def keep(model):
        endpoint_types = model.get("supported_endpoint_types")
        if endpoint_types is not None and not (set(endpoint_types) & TEXT_ENDPOINT_TYPES):
            return False
        arch = model.get("architecture")
        if isinstance(arch, dict):
            outputs = arch.get("output_modalities")
            if outputs is not None and "text" not in outputs:
                return False
        # Declared non-chat endpoint families are excluded even when a model
        # also advertises a chat endpoint type.
        declared = model.get("supported_endpoint_types")
        if isinstance(declared, list) and set(declared) & NON_TEXT_ENDPOINT_TYPES:
            return False
        return True
    return keep


def make_input_filter(capability, input_modalities=ACTIVE_INPUT_MODALITIES):
    """Chat filter plus an explicit input-modality requirement (fail closed)."""
    base = capability_filter(capability)
    required = frozenset(input_modalities)
    non_text = required - {TEXT}

    def keep(model):
        if not base(model):
            return False
        if not non_text:
            return True
        arch = model.get("architecture")
        declared = arch.get("input_modalities") if isinstance(arch, dict) else None
        if not isinstance(declared, list):
            return False
        return non_text <= set(declared)
    return keep


def _normalize(item):
    if not isinstance(item, dict) or not isinstance(item.get("id"), str) or not item["id"].strip():
        return None
    model = {"id": item["id"]}
    for key in ("context_length", "name"):
        if isinstance(item.get(key), (str, int)) and not isinstance(item.get(key), bool):
            model[key] = item[key]
    if isinstance(item.get("supported_endpoint_types"), list):
        model["supported_endpoint_types"] = [t for t in item["supported_endpoint_types"] if isinstance(t, str)]
    arch = item.get("architecture")
    if isinstance(arch, dict) and isinstance(arch.get("input_modalities"), list):
        model["architecture"] = {"input_modalities": [m for m in arch["input_modalities"] if isinstance(m, str)]}
        if isinstance(arch.get("output_modalities"), list):
            model["architecture"]["output_modalities"] = [
                m for m in arch["output_modalities"] if isinstance(m, str)]
    return model


def parse_catalog(payload):
    """Parse a ``/models`` body into normalized records; rejects unusable shapes."""
    data = payload.get("data") if isinstance(payload, dict) else payload
    if not isinstance(data, list):
        raise ProviderError("Model catalog response has no 'data' list")
    seen, models = set(), []
    for item in data[:CATALOG_MAX_ITEMS]:
        model = _normalize(item)
        if model is None or model["id"] in seen:
            continue
        seen.add(model["id"])
        models.append(model)
    return models


def fetch_catalog(url, api_key="", timeout=CATALOG_TIMEOUT):
    headers = {"Accept": "application/json"}
    if api_key:
        headers["Authorization"] = "Bearer " + api_key
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw = response.read(CATALOG_MAX_BYTES + 1)
    except urllib.error.HTTPError as e:
        raise ProviderError(f"Model catalog returned HTTP {e.code}")
    except (urllib.error.URLError, OSError) as e:
        raise ProviderError(f"Model catalog unreachable: {type(e).__name__}")
    if len(raw) > CATALOG_MAX_BYTES:
        raise ProviderError("Model catalog response too large")
    try:
        return parse_catalog(json.loads(raw.decode("utf-8")))
    except (ValueError, UnicodeDecodeError):
        raise ProviderError("Model catalog is not valid JSON")


def seed_catalog():
    return ModelCatalog(models=[dict(m) for m in SEED_MODELS], source="seed", degraded=True,
                        detail="live discovery unavailable; using verified cold-start seed")


def discover_models(provider, api_key="", capability=TEXT, fetch=fetch_catalog, url=None):
    """Discover chat-compatible models for one entry, filtered by capability."""
    url = url or (api_base(provider) + "/models")
    keep = make_input_filter(capability)
    try:
        models = fetch(url, api_key)
    except ProviderError as e:
        catalog = seed_catalog()
        catalog.detail = str(e) + "; using verified cold-start seed"
        catalog.models = [m for m in catalog.models if keep(m)]
        return catalog
    filtered = [m for m in models if keep(m)]
    return ModelCatalog(models=filtered, source="live", extra={"total": len(models)})


def filter_models(models, capability=TEXT):
    keep = make_input_filter(capability)
    return [m["id"] for m in models if keep(m)]


def model_selector_options(provider, models, capability=TEXT):
    """The exact option list a model selector must bind for this entry."""
    options = filter_models(models, capability)
    options = _with_id(options, provider.default_model)
    return options


def _with_id(options, model_id):
    return [model_id] + [o for o in options if o != model_id]


def check_model(provider, model_id, models, capability=TEXT):
    """Reject a stale/incompatible selection; default model is always accepted."""
    options = model_selector_options(provider, models, capability)
    # The provider default is a routing alias that live catalogs may omit.
    if model_id != provider.default_model and model_id not in options:
        raise ProviderError(f"Model {model_id!r} is not available for capability {capability!r} on "
                            f"{provider.label}; choose one of {len(options)} compatible models")
    return model_id


def describe_catalog(catalog):
    status = "degraded" if catalog.degraded else "ok"
    return {"source": catalog.source, "status": status, "count": len(catalog.models),
            "detail": catalog.detail}
