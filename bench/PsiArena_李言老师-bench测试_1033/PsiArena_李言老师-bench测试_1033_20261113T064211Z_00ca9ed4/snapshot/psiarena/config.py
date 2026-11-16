"""Explicit role configuration; no model fallback between roles."""
from __future__ import annotations
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / '.env')
except ImportError:
    pass

ROLES = ('counselor', 'client', 'judge')

@dataclass(frozen=True)
class RoleConfig:
    model: str
    base_url: str
    api_key: str
    thinking: str | None = None
    reasoning_effort: str | None = None

@dataclass(frozen=True)
class Settings:
    roles: dict[str, RoleConfig]
    temperature: float
    max_tokens: int
    timeout: float
    counselor_provider: str

    @property
    def counselor_model(self): return self.roles['counselor'].model
    @property
    def client_model(self): return self.roles['client'].model
    @property
    def judge_model(self): return self.roles['judge'].model

@lru_cache(maxsize=1)
def get_settings() -> Settings:
    provider = os.getenv('PSIARENA_COUNSELOR_PROVIDER', 'ai_role')
    if provider not in ('ai_role', 'openai'):
        raise ValueError('PSIARENA_COUNSELOR_PROVIDER must be ai_role or openai')
    roles = {}
    for role in ROLES:
        prefix = f'PSIARENA_{role.upper()}_'
        if role == 'counselor' and provider == 'ai_role':
            roles[role] = RoleConfig('ai-role-bot-' + os.getenv('PSIARENA_AI_ROLE_BOT_ID', '1030'), '', '')
            continue
        model = os.getenv(prefix+'MODEL', '').strip()
        url = (os.getenv(prefix+'BASE_URL') or os.getenv('PSIARENA_BASE_URL', '')).strip()
        key = (os.getenv(prefix+'API_KEY') or os.getenv('PSIARENA_API_KEY', '')).strip()
        if not all((model, url, key)):
            raise ValueError(f'Missing {prefix}MODEL/BASE_URL/API_KEY (shared endpoint/key allowed)')
        thinking = os.getenv(prefix+'THINKING', '').strip() or None
        if thinking not in (None, 'enabled', 'disabled'):
            raise ValueError(f'{prefix}THINKING must be enabled or disabled (or empty)')
        effort = os.getenv(prefix+'REASONING_EFFORT', '').strip() or None
        if effort not in (None, 'low', 'medium', 'high', 'max'):
            raise ValueError(f'{prefix}REASONING_EFFORT must be low/medium/high/max')
        if effort and thinking == 'disabled':
            raise ValueError(f'{prefix}REASONING_EFFORT conflicts with disabled thinking')
        roles[role] = RoleConfig(model, url, key, thinking, effort)
    temperature = float(os.getenv('PSIARENA_TEMPERATURE', '0.7'))
    max_tokens = int(os.getenv('PSIARENA_MAX_TOKENS', '2048'))
    timeout = float(os.getenv('PSIARENA_TIMEOUT', '120'))
    if not 0 <= temperature <= 2 or max_tokens <= 0 or timeout <= 0:
        raise ValueError('Invalid sampling/timeout settings')
    return Settings(roles, temperature, max_tokens, timeout, provider)

@lru_cache(maxsize=None)
def _client_for(base_url: str, api_key: str, timeout: float):
    from openai import OpenAI
    # Stateful counselor requests must never be replayed automatically.
    return OpenAI(api_key=api_key, base_url=base_url, timeout=timeout, max_retries=0)


def chat(role: str, messages: list[dict], **overrides) -> str:
    if role not in ROLES:
        raise ValueError(f'Unknown role: {role}')
    s = get_settings()
    from .runtime import current_run
    run = current_run.get()
    if role == 'counselor' and s.counselor_provider == 'ai_role':
        from .ai_role import active_session
        session = active_session.get()
        if session is None:
            raise RuntimeError('ai_role chat requires counselor_session; refusing shared user context')
        return session.chat(messages)
    rc = s.roles[role]
    limit = int(os.getenv(f'PSIARENA_{role.upper()}_MAX_TOKENS', str(s.max_tokens)))
    payload = dict(model=rc.model, messages=messages,
                   temperature=overrides.get('temperature', s.temperature),
                   max_tokens=overrides.get('max_tokens', limit), stream=False)
    if rc.thinking is not None:
        # SDK forwards thinking to the top-level JSON body.
        payload['extra_body'] = {'thinking': {'type': rc.thinking}}
    if rc.reasoning_effort is not None:
        payload['reasoning_effort'] = rc.reasoning_effort
    target = run.next_call(role) if run else None
    from .ai_role_transport import write_json, now
    if target:
        write_json(target / 'request.json', {'at': now(), **payload})
    try:
        resp = _client_for(rc.base_url, rc.api_key, s.timeout).chat.completions.create(**payload)
        if target:
            write_json(target / 'response.json', resp.model_dump(mode='json'))
            run.record_usage(role, resp.usage.model_dump(mode='json') if resp.usage else None)
        if not resp.choices:
            raise RuntimeError(f'{role}: completion returned no choices')
        choice = resp.choices[0]
        if rc.thinking == 'disabled':
            reasoning = getattr(choice.message, 'reasoning_content', None)
            details = getattr(resp.usage, 'completion_tokens_details', None)
            reasoning_tokens = getattr(details, 'reasoning_tokens', 0) or 0
            if reasoning or reasoning_tokens > 0:
                raise RuntimeError(f'{role}: provider returned reasoning despite disabled thinking')
        if choice.finish_reason != 'stop' or not choice.message.content:
            raise RuntimeError(f'{role}: incomplete/empty completion (finish_reason={choice.finish_reason})')
        return choice.message.content
    except Exception as exc:
        if target:
            # Do not persist exception text, which some providers include credentials in.
            write_json(target / 'error.json', {'type': type(exc).__name__, 'at': now()})
        raise
