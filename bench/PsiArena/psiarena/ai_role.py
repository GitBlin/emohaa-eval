"""Stateful ai-role counselor: fresh user per session, clear ONCE, audit each turn.

The platform controls its own context window and hidden system prompt. The first
request embeds harness instructions in user content; this is a product adaptation.
No retry after ambiguous chat errors, no clearing between successful turns.
"""
from __future__ import annotations
import ast
import os
import uuid
from contextvars import ContextVar
from contextlib import contextmanager
from pathlib import Path
from .ai_role_transport import Client, ProtocolError, write_json, now

active_session = ContextVar('psiarena_ai_role_session', default=None)


def credentials():
    # Read constants only; never import/execute or log the credential-bearing file.
    path = Path(os.getenv('PSIARENA_AI_ROLE_CREDENTIAL_FILE', str(Path(__file__).resolve().parents[3] / 'bot_chat_client.py')))
    defaults = {}
    if path.exists():
        for node in ast.parse(path.read_text(encoding='utf-8')).body:
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant):
                for name in node.targets:
                    if isinstance(name, ast.Name) and name.id in ('DEFAULT_BASE_URL', 'DEFAULT_API_KEY', 'DEFAULT_API_SECRET'):
                        defaults[name.id] = node.value.value
    url = os.getenv('PSIARENA_AI_ROLE_BASE_URL') or defaults.get('DEFAULT_BASE_URL', 'https://www.ai-role.cn')
    key = os.getenv('PSIARENA_AI_ROLE_API_KEY') or defaults.get('DEFAULT_API_KEY')
    secret = os.getenv('PSIARENA_AI_ROLE_API_SECRET') or defaults.get('DEFAULT_API_SECRET')
    if not key or not secret:
        raise ValueError('Set PSIARENA_AI_ROLE_API_KEY/API_SECRET or local credential file')
    return url, key, secret


class AiRoleSession:
    def __init__(self, directory, label, *, embed_system_prompt=True):
        self.embed_system_prompt = embed_system_prompt
        from .config import get_settings
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.bot_id = int(os.getenv('PSIARENA_AI_ROLE_BOT_ID', '1030'))
        self.user_id = 'psi_' + uuid.uuid4().hex
        self.client = Client(*credentials(), self.user_id, timeout=get_settings().timeout)
        self.turn = 0
        self.failed = False
        self.params = {'botId': self.bot_id, 'courseProgressId': 0, 'onlyLastSession': 'true', 'pageNum': 0, 'pageSize': 100}
        write_json(self.directory / 'session.json', {
            'at': now(), 'label': label, 'user_id': self.user_id, 'bot_id': self.bot_id,
            'memory': 'new user; clear+verify once at start; retain server context within session',
            'context_policy': 'platform-managed full session; not upstream sliding counselor window',
            'system_prompt_delivery': ('user content on first turn' if embed_system_prompt else 'no harness instructions'),
            'retry': 'none; ambiguous failures require fresh session',
        })

    def start(self):
        self.client.authenticate()
        clear = self.client.call('POST', '/open/chat/clearContext', self.directory, 'clear_start',
                                 payload={'botId': self.bot_id, 'courseProgressId': 0})
        if not isinstance(clear, dict) or clear.get('role') != 'flush_context':
            raise ProtocolError('clearContext did not confirm flush_context')
        self.audit('context_start', 0)

    def audit(self, name, expected):
        history = self.client.call('GET', '/open/chat/context', self.directory, name, params=self.params)
        if not isinstance(history, dict) or not isinstance(history.get('content'), list):
            raise ProtocolError('Invalid context response')
        messages = history['content']
        if any(not isinstance(m, dict) for m in messages):
            raise ProtocolError('Invalid context message')
        counts = {role: sum(m.get('role') == role for m in messages) for role in ('user', 'role')}
        if counts != {'user': expected, 'role': expected}:
            raise ProtocolError(f'Context audit failed at turn {self.turn}: expected {expected} pairs, got {counts}')

    def chat(self, messages):
        if self.failed:
            raise ProtocolError('Session blocked after prior failure; create a fresh session')
        try:
            if not messages or messages[-1]['role'] != 'user':
                raise ProtocolError('ai_role expects the next user turn')
            self.audit(f'turn_{self.turn+1:02d}_before', self.turn)
            content = messages[-1]['content']
            if self.turn == 0 and self.embed_system_prompt:
                system = '\n'.join(m['content'] for m in messages if m['role'] == 'system')
                content = f'<咨询行为要求>\n{system}\n</咨询行为要求>\n{content}'
            reply, metadata = self.client.call('POST', '/open/chat/completions', self.directory,
                f'turn_{self.turn+1:02d}_chat', payload={'botId': self.bot_id, 'content': content,
                'isStream': True, 'returnTts': False, 'courseProgressId': 0}, chat=True)
            if not reply or reply == '内容生成状态失败，请稍后重试':
                raise ProtocolError('Empty/failed counselor reply')
            self.turn += 1
            self.audit(f'turn_{self.turn:02d}_after', self.turn)
            write_json(self.directory / f'turn_{self.turn:02d}.json', {'reply': reply, 'metadata': metadata})
            return reply
        except Exception:
            self.failed = True
            raise

@contextmanager
def counselor_session(directory=None, label='session', mode='psycho'):
    from .config import get_settings
    if get_settings().counselor_provider != 'ai_role':
        yield None
        return
    if mode == 'rewrite':
        raise ValueError('ai_role rewrite is unsupported: reflection calls would pollute live session memory')
    if directory is None:
        raise ValueError('ai_role requires an explicit audit output directory')
    if active_session.get() is not None:
        raise RuntimeError('Nested ai_role sessions are not allowed')
    session = AiRoleSession(directory, label)
    token = active_session.set(session)
    try:
        session.start()
        yield session
    finally:
        session.client.session.close()
        active_session.reset(token)
