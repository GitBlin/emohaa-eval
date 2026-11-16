"""Offline regression cases. No API calls; not automatically run by the smoke script."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from psiarena.scoring import HEADERS, COUNTS, parse_score_text, ScoreFormatError, aggregate


def score_text(scores=None):
    scores = scores or {key: [3]*count for key, count in COUNTS.items()}
    return ''.join(HEADERS[key]+'\n'+''.join(
        f'[维度]{key}_{i:02d}\n[分析]对话证据\n[得分]{value}\n'
        for i, value in enumerate(scores[key], 1)) for key in COUNTS)


class ScoringTests(unittest.TestCase):
    def test_range_and_duplicate_and_missing(self):
        text = score_text()
        for bad in (text.replace('[得分]3', '[得分]9', 1),
                    text.replace('client_02', 'client_01'),
                    text.replace('[得分]3\n', '', 1)):
            with self.assertRaises(ScoreFormatError):
                parse_score_text(bad)

    def test_mark_value_not_first_number_and_na(self):
        text = score_text().replace('[分析]对话证据', '[分析]第99轮的证据', 1)
        text = text.replace('[得分]3', '[得分]N/A', 1)
        row = parse_score_text(text)
        self.assertEqual(row['totals']['client'], 45)
        self.assertEqual(row['client'], 45/16)

    def test_paper_strict_boundary_and_and(self):
        values = {'client': [3]*14+[0]*2, 'supervisor': [3]*8, 'counselor': [4]*8+[3]}
        row = parse_score_text(score_text(values), 'paper_v1')
        self.assertEqual(row['totals'], {'client': 42, 'supervisor': 24, 'counselor': 35})
        self.assertFalse(any(row['passes'].values()))
        values['client'] = [4]*16
        values['supervisor'] = [4]*8
        values['counselor'] = [2]*9
        self.assertFalse(parse_score_text(score_text(values), 'paper_v1')['passes']['overall'])

    def test_aggregate_same_overall_and_explicit_coverage(self):
        with tempfile.TemporaryDirectory() as directory:
            text = score_text({'client': [4]*16, 'supervisor': [4]*8, 'counselor': [2]*9})
            Path(directory, 'scores0.txt').write_text(text)
            row = parse_score_text(text)
            report = aggregate(directory, n=2)
            self.assertEqual(report['means']['overall'], row['overall'])
            self.assertEqual(report['coverage'], 0.5)
            self.assertEqual(report['pass_rates']['overall'], 0.5)
            self.assertFalse(report['complete'])


class FakeClient:
    def __init__(self, *args, **kwargs):
        self.history = []
        self.calls = []
    def authenticate(self): pass
    def call(self, method, endpoint, directory, name, **kwargs):
        self.calls.append((endpoint, kwargs))
        if endpoint.endswith('/clearContext'):
            self.history = []
            return {'role': 'flush_context'}
        if endpoint.endswith('/context'):
            return {'content': self.history.copy()}
        self.history.extend([{'role': 'user'}, {'role': 'role'}])
        return '回复', {'finish_seen': True}


class MemoryTests(unittest.TestCase):
    def test_clear_once_append_only_and_independent_user(self):
        from psiarena.ai_role import AiRoleSession
        with tempfile.TemporaryDirectory() as directory, \
             patch('psiarena.ai_role.Client', FakeClient), \
             patch('psiarena.ai_role.credentials', return_value=('https://example.invalid', 'key', 'secret')), \
             patch('psiarena.config.get_settings', return_value=SimpleNamespace(timeout=60)):
            first = AiRoleSession(Path(directory)/'a', 'a')
            second = AiRoleSession(Path(directory)/'b', 'b')
            self.assertNotEqual(first.user_id, second.user_id)
            first.start()
            first.chat([{'role': 'system', 'content': '规则'}, {'role': 'user', 'content': '第一问'}])
            first.chat([{'role': 'system', 'content': '规则'}, {'role': 'user', 'content': '第二问'}])
            self.assertEqual(sum(p.endswith('/clearContext') for p, _ in first.client.calls), 1)
            chats = [k['payload']['content'] for p, k in first.client.calls if p.endswith('/completions')]
            self.assertIn('规则', chats[0])
            self.assertEqual(chats[1], '第二问')
            # Loss of session history blocks the next chat rather than resetting memory.
            first.client.history = []
            with self.assertRaises(Exception):
                first.chat([{'role': 'user', 'content': '第三问'}])
            self.assertEqual(first.turn, 2)
            self.assertTrue(first.failed)



class ThinkingConfigTests(unittest.TestCase):
    def test_disabled_is_forwarded_without_reasoning_effort(self):
        from psiarena.config import RoleConfig, chat
        rc = RoleConfig('deepseek-v4.1-flash-1017', 'https://example.invalid/v1', 'not-a-real-key', 'disabled')
        settings = SimpleNamespace(roles={'client': rc}, counselor_provider='ai_role', max_tokens=2048,
                                   temperature=0.7, timeout=60)
        response = SimpleNamespace(usage=None, choices=[SimpleNamespace(
            finish_reason='stop', message=SimpleNamespace(content='回复', reasoning_content=None))])
        from unittest.mock import MagicMock
        client = MagicMock()
        client.chat.completions.create.return_value = response
        with patch('psiarena.config.get_settings', return_value=settings), \
             patch('psiarena.config._client_for', return_value=client):
            self.assertEqual(chat('client', [{'role': 'user', 'content': '你好'}]), '回复')
            payload = client.chat.completions.create.call_args.kwargs
            self.assertEqual(payload['extra_body'], {'thinking': {'type': 'disabled'}})
            self.assertNotIn('reasoning_effort', payload)
            settings.roles['client'] = RoleConfig('deepseek-v4.1-flash-1017', 'https://example.invalid/v1', 'not-a-real-key', 'enabled', 'medium')
            self.assertEqual(chat('client', [{'role': 'user', 'content': '你好'}]), '回复')
            medium_payload = client.chat.completions.create.call_args.kwargs
            self.assertEqual(medium_payload['reasoning_effort'], 'medium')
            self.assertEqual(medium_payload['extra_body'], {'thinking': {'type': 'enabled'}})
            settings.roles['client'] = rc
            response.choices[0].message.reasoning_content = 'unexpected reasoning'
            with self.assertRaises(RuntimeError):
                chat('client', [{'role': 'user', 'content': '你好'}])


if __name__ == '__main__':
    unittest.main()
