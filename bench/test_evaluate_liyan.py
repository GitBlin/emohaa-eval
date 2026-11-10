"""Offline regression checks; never contacts the remote API."""
import json
from pathlib import Path
import random
import tempfile
import unittest
from unittest.mock import patch

import evaluate_liyan as ev


class EvaluationTests(unittest.TestCase):
    def case(self):
        return {"trial_id": "trial_000000", "sample_id": "test:1", "task_file": "test",
                "ability": "test", "language": "zh", "repeat": 0, "answer": "B",
                "map": {"A": "B", "B": "A"}, "request": {"botId": 242, "content": "test"}}

    def frame(self, content):
        return {"model": "242", "choices": [{"delta": {"content": content}}]}

    def test_sse_double_encoding_and_end(self):
        events = []
        lines = ["data:" + json.dumps(json.dumps(self.frame("[[A]]"))), "",
                 'data:{"choices":[{"finishReason":"stop"}]}', ""]
        answer, meta = ev.parse_sse(lines, events.append)
        self.assertEqual(answer, "[[A]]")
        self.assertTrue(meta["finish_seen"])
        self.assertEqual(len(events), 2)

    def test_sse_boundaries_multiline(self):
        lines = [': keepalive', 'event: message', 'data:{"choices":',
                 'data:[{"delta":{"content":"中文"}}]}', '', 'data:[DONE]']
        self.assertEqual(ev.parse_sse(lines, lambda _: None)[0], "中文")

    def test_sse_business_error_and_truncation(self):
        with self.assertRaises(ev.APIError):
            ev.parse_sse(['data:{"model":"error","choices":[{"delta":{"content":"失败"}}]}', ''], lambda _: None)
        with self.assertRaises(ev.ProtocolError):
            ev.parse_sse(['data:' + json.dumps(self.frame('[[A]]')), ''], lambda _: None)
        with self.assertRaises(ev.APIError):
            ev.unpack({"success": False, "code": "901", "message": "失败"})

    def test_answer_scoring(self):
        case = self.case()
        self.assertTrue(ev.score("[[A]]", case)["correct"])
        self.assertFalse(ev.score("[[B]]", case)["correct"])
        for text in ("", "A", "拒答", "[[C]]", "[[A]] [[B]]"):
            self.assertEqual(ev.score(text, case)["status"], "invalid_answer")
        self.assertTrue(ev.score("解释 [[A]]", case)["correct"])
        self.assertFalse(ev.score("解释 [[A]]", case)["strict_format"])

    def test_context_failure_blocks_chat(self):
        class MockClient:
            calls = []

            def call(self, method, endpoint, directory, name, **kwargs):
                self.calls.append(name)
                if name == 'clear':
                    return {"role": "flush_context"}
                if name == 'context_before':
                    return {"content": [{"role": "user", "content": "old"}]}
                raise AssertionError('chat must not be sent')
        client = MockClient()
        with tempfile.TemporaryDirectory() as tmp, patch.object(ev.time, "sleep"):
            row = ev.trial(client, self.case(), Path(tmp), {"max_attempts": 2})
            self.assertEqual(row['status'], 'request_error')
            self.assertEqual(client.calls, ['clear', 'context_before'] * 2)
            self.assertTrue((Path(tmp)/'trials/trial_000000/result.json').exists())

    def test_retry_keeps_failed_attempt_and_resets(self):
        class MockClient:
            n = 0

            def call(self, method, endpoint, directory, name, **kwargs):
                if name == 'clear':
                    return {"role": "flush_context"}
                if name.startswith('context'):
                    return {"content": []}
                self.n += 1
                if self.n == 1:
                    raise ev.APIError('temporary')
                return '[[A]]', {}
        with tempfile.TemporaryDirectory() as tmp, patch.object(ev.time, "sleep"):
            row = ev.trial(MockClient(), self.case(), Path(tmp), {"max_attempts": 2})
            self.assertTrue(row['correct'])
            self.assertEqual([a['status'] for a in row['attempts']], ['error', 'received'])
            self.assertNotIn('error', row)

    def test_vote_ties_not_guessed(self):
        cases = [{**self.case(), 'trial_id': f'trial_{i:06d}', 'repeat': i} for i in range(2)]
        rows = []
        for i, case in enumerate(cases):
            rows.append({**case, **ev.score('[[A]]' if i == 0 else '[[B]]', case),
                         'reply': '', 'attempts': [], 'elapsed_seconds': 1})
        manifest = {'repeats': 2, 'interval': 0, 'dataset_questions': 2860,
                    'model_version': 'unknown', 'harness_version': 'unknown'}
        with tempfile.TemporaryDirectory() as tmp:
            s = ev.summarize(Path(tmp), manifest, cases, rows, 'complete')
            self.assertEqual(s['question_vote_ties_or_no_answer'], 1)
            self.assertEqual(s['question_vote_accuracy'], 0)
            self.assertEqual(s['trials']['accuracy'], .5)

    def test_resume_sends_only_unfinished_trials(self):
        class MockClient:
            chat_calls = 0

            def __init__(self, *args):
                self.session = self

            def close(self):
                pass

            def authenticate(self):
                pass

            def call(self, method, endpoint, directory, name, **kwargs):
                if name == 'bots':
                    return [{'id': 242}]
                if name == 'bot_detail':
                    return {'id': 242}
                if name == 'clear':
                    return {'role': 'flush_context'}
                if name.startswith('context'):
                    return {'content': []}
                type(self).chat_calls += 1
                return '[[A]]', {}
        with tempfile.TemporaryDirectory() as tmp, patch.object(ev, 'Client', MockClient), patch.object(ev.time, 'sleep'):
            ev.main(['--dry-run', '--limit', '2', '--repeats', '1', '--output-dir', tmp])
            run = next(Path(tmp).iterdir())
            manifest, cases = ev.read_json(run/'manifest.json'), ev.read_json(run/'plan.json')
            ev.trial(MockClient(), cases[0], run, manifest)
            MockClient.chat_calls = 0
            self.assertEqual(ev.main(['--resume', str(run)]), 0)
            self.assertEqual(MockClient.chat_calls, 1)
            self.assertEqual(ev.read_json(run/'summary.json')['completed_trials'], 2)


if __name__ == '__main__':
    unittest.main()
