"""Runtime configuration and OpenAI-compatible client factory.

PsiArena has three *roles*, and each can point at its **own** OpenAI-compatible endpoint
(useful when, e.g., the model under test is on one provider while the judge is GPT-4o on
another):

    * counselor  — the model under test (plays the psychological counselor)
    * client     — the simulated help-seeker (paper used ``gpt-4o-mini``)
    * judge      — the evaluators and the feedback summarizer (paper used ``gpt-4o``)

Configure with environment variables (a local ``.env`` is auto-loaded if
``python-dotenv`` is installed). Set the **shared** defaults once, then override per role
only where it differs:

    # shared defaults (used by any role that doesn't override them)
    PSIARENA_BASE_URL          https://your-endpoint/v1
    PSIARENA_API_KEY           your-key

    # per role: <ROLE> is COUNSELOR / CLIENT / JUDGE
    PSIARENA_<ROLE>_MODEL      model name for this role
    PSIARENA_<ROLE>_BASE_URL   endpoint for this role     (default: PSIARENA_BASE_URL)
    PSIARENA_<ROLE>_API_KEY    key for this role          (default: PSIARENA_API_KEY)

    # sampling / limits (shared)
    PSIARENA_TEMPERATURE       sampling temperature        (default: 0.7)
    PSIARENA_MAX_TOKENS        max completion tokens       (default: 2048)
    PSIARENA_TIMEOUT           per-request timeout (s)     (default: 60)

If a role sets no model, the counselor model is used as a fallback so a single shared
endpoint "just works" out of the box.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

try:  # optional convenience — load a local .env if present
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover - dotenv is optional
    pass

from openai import OpenAI

ROLES = ("counselor", "client", "judge")


@dataclass(frozen=True)
class RoleConfig:
    model: str
    base_url: str
    api_key: str


@dataclass(frozen=True)
class Settings:
    roles: dict[str, RoleConfig]
    temperature: float
    max_tokens: int
    timeout: float

    # convenience accessors (read-only)
    @property
    def counselor_model(self) -> str:
        return self.roles["counselor"].model

    @property
    def client_model(self) -> str:
        return self.roles["client"].model

    @property
    def judge_model(self) -> str:
        return self.roles["judge"].model


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Read per-role configuration from the environment (cached for the process)."""
    shared_url = os.environ.get("PSIARENA_BASE_URL", "").strip()
    shared_key = os.environ.get("PSIARENA_API_KEY", "").strip()

    # resolve the counselor model first; client/judge fall back to it when unset
    counselor_model = os.environ.get("PSIARENA_COUNSELOR_MODEL", "glm-5.1").strip()

    roles: dict[str, RoleConfig] = {}
    for role in ROLES:
        prefix = f"PSIARENA_{role.upper()}_"
        model = os.environ.get(prefix + "MODEL", "").strip() or counselor_model
        base_url = os.environ.get(prefix + "BASE_URL", "").strip() or shared_url
        api_key = os.environ.get(prefix + "API_KEY", "").strip() or shared_key
        if not base_url or not api_key:
            raise SystemExit(
                f"Missing endpoint for the '{role}' role: set {prefix}BASE_URL/"
                f"{prefix}API_KEY, or the shared PSIARENA_BASE_URL/PSIARENA_API_KEY "
                "(see .env.example or the README)."
            )
        roles[role] = RoleConfig(model=model, base_url=base_url, api_key=api_key)

    return Settings(
        roles=roles,
        temperature=float(os.environ.get("PSIARENA_TEMPERATURE", "0.7")),
        max_tokens=int(os.environ.get("PSIARENA_MAX_TOKENS", "2048")),
        timeout=float(os.environ.get("PSIARENA_TIMEOUT", "60")),
    )


@lru_cache(maxsize=None)
def _client_for(base_url: str, api_key: str, timeout: float) -> OpenAI:
    """One OpenAI-compatible client per (endpoint, key); reused across roles that share it."""
    return OpenAI(api_key=api_key, base_url=base_url, timeout=timeout)


def chat(role: str, messages: list[dict], **overrides) -> str:
    """Send one chat-completion request **as the given role** and return the text.

    ``role`` is one of ``"counselor"`` / ``"client"`` / ``"judge"`` — each uses its own
    model and endpoint. Temperature and max_tokens fall back to the global settings.
    """
    if role not in ROLES:
        raise ValueError(f"unknown role {role!r}; expected one of {ROLES}")
    s = get_settings()
    rc = s.roles[role]
    client = _client_for(rc.base_url, rc.api_key, s.timeout)
    resp = client.chat.completions.create(
        model=rc.model,
        messages=messages,
        temperature=overrides.get("temperature", s.temperature),
        max_tokens=overrides.get("max_tokens", s.max_tokens),
        stream=False,
    )
    return resp.choices[0].message.content or ""
