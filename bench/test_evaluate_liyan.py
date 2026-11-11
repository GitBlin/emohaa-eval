"""Offline regression checks; never contacts the remote API."""
import json
from pathlib import Path
import random
import tempfile
import threading
import time
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

    def test_bilingual_rounds_and_flagged_subset(self):
        cases = [{**self.case(), "trial_id": f"{lang}_{i}", "language": lang, "repeat": i}
                 for lang in ("zh", "en") for i in range(3)]
        rows = [{**c, **ev.score("[[A]]" if c["language"] == "zh" else "[[B]]", c),
                 "reply": "", "attempts": [], "elapsed_seconds": 1} for c in cases]
        manifest = {"repeats": 3, "interval": 0, "dataset_questions": 1,
                    "model_version": "unknown", "harness_version": "unknown"}
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp)
            ev.write_json(run/'data_audit.json', {"language_option_mismatches": [{"sample_id": "test:1"}]})
            result = ev.summarize(run, manifest, cases, rows, "complete")
            self.assertEqual(result['rounds_by_language']['zh']['mean_accuracy'], 1)
            self.assertEqual(result['rounds_by_language']['en']['mean_accuracy'], 0)
            self.assertEqual(result['rounds_by_language']['en']['complete_rounds'], 3)
            self.assertEqual(result['excluding_option_count_mismatches']['by_language']['zh']['count'], 0)
            self.assertEqual(result['trials']['count'], 6)

    def test_parallel_users_and_round_accounting(self):
        barrier = threading.Barrier(3)
        lock = threading.Lock()
        users = []
        class MockClient:
            def __init__(self, base, key, secret, uid, *args):
                self.uid = uid
                self.session = self
            def close(self):
                pass
            def authenticate(self):
                pass
            def call(self, method, endpoint, directory, name, **kwargs):
                if name == 'bots':
                    return [{'id': 1030}]
                if name == 'bot_detail':
                    return {'id': 1030}
                request = kwargs.get('payload') or kwargs.get('params')
                if request is not None and request.get('botId') != 1030:
                    raise AssertionError('all chat and context requests must target bot 1030')
                if name == 'clear':
                    return {'role': 'flush_context'}
                if name.startswith('context'):
                    return {'content': []}
                with lock:
                    users.append(self.uid)
                barrier.wait(timeout=5)
                return '[[A]]', {}
        with tempfile.TemporaryDirectory() as tmp, patch.object(ev, 'Client', MockClient):
            self.assertEqual(ev.main(['--bot-id', '1030', '--languages', 'zh', '--limit', '2', '--repeats', '3', '--workers', '3',
                                      '--interval', '0', '--output-dir', tmp]), 0)
            run = next(Path(tmp).iterdir())
            self.assertEqual(len(users), 6)
            self.assertEqual(len(set(users)), 6)
            summary = ev.read_json(run/'summary.json')
            self.assertEqual(summary['completed_trials'], 6)
            self.assertEqual(summary['repeat_statistics']['complete_rounds'], 3)
            self.assertTrue(all(m['count'] == 2 for m in summary['by_repeat'].values()))
            users.clear()
            self.assertEqual(ev.main(['--resume', str(run)]), 0)
            self.assertEqual(users, [])

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
            ev.main(['--languages', 'zh', '--dry-run', '--limit', '2', '--repeats', '1', '--output-dir', tmp])
            run = next(Path(tmp).iterdir())
            manifest, cases = ev.read_json(run/'manifest.json'), ev.read_json(run/'plan.json')
            ev.trial(MockClient(), cases[0], run, manifest)
            MockClient.chat_calls = 0
            self.assertEqual(ev.main(['--resume', str(run)]), 0)
            self.assertEqual(MockClient.chat_calls, 1)
            self.assertEqual(ev.read_json(run/'summary.json')['completed_trials'], 2)


if __name__ == '__main__':
    unittest.main()
