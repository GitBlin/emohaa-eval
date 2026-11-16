"""Offline checks: official EU joint scoring, isolation, retries and recovery."""
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
import evaluate_emobench as ev


class EmoBenchTests(unittest.TestCase):
    def case(self, task='EU'):
        keys = ['answer'] if task == 'EA' else ['answer_q1', 'answer_q2']
        return {'trial_id': 'trial_000000', 'sample_id': task+':1', 'task': task,
                'language': 'en', 'repeat': 0, 'category': 'test', 'fine_category': None,
                'question_type': None, 'labels': {k: 'B' for k in keys},
                'maps': {k: {'A': 'B', 'B': 'A', 'F': 'F'} for k in keys}, 'cot': False,
                'request': {'botId': 1030, 'content': 'test'}}

    def test_eu_requires_both_answers(self):
        case = self.case()
        both = ev.score('{"answer_q1":"A","answer_q2":"A"}', case)
        self.assertTrue(both['correct'])
        partial = ev.score('{"answer_q1":"A","answer_q2":"B"}', case)
        self.assertEqual(partial['status'], 'ok')
        self.assertFalse(partial['correct'])
        self.assertEqual(partial['component_correct'], {'answer_q1': True, 'answer_q2': False})
        missing = ev.score('{"answer_q1":"A"}', case)
        self.assertEqual(missing['status'], 'invalid_answer')
        self.assertFalse(missing['correct'])
        self.assertTrue(ev.score('{"answer_q1":"F","answer_q2":"A"}', case)['prediction_shown']['answer_q1'] == 'F')

    def test_ea_mapping_and_invalid_json(self):
        c = self.case('EA')
        self.assertTrue(ev.score('```json\n{"answer":"A"}\n```', c)['correct'])
        for reply in ['A', '{"answer":"a"}', '{"answer":"Z"}', '{"answer":"A","answer":"B"}', '[]']:
            self.assertEqual(ev.score(reply, c)['status'], 'invalid_answer')

    def test_context_failure_blocks_question(self):
        class Fake:
            token = 'not-a-real-token'
            def call(self, method, endpoint, target, name, **kwargs):
                if name == 'clear': return {'role': 'flush_context'}
                if name == 'context_before': return {'content': [{'role': 'user'}]}
                raise AssertionError('chat must not be reached')
        with tempfile.TemporaryDirectory() as tmp:
            r = ev.evaluate_one(Fake(), self.case(), Path(tmp), {'max_attempts': 1, 'bot_id': 1030}, 'unique')
            self.assertEqual(r['status'], 'request_error')
            self.assertEqual(r['attempts'][0]['stage'], 'verify_context')

    def test_invalid_answer_not_retried(self):
        class Fake:
            token = 'not-a-real-token'
            chats = 0
            def call(self, method, endpoint, target, name, **kwargs):
                if name == 'clear': return {'role': 'flush_context'}
                if name == 'context_before': return {'content': []}
                if name == 'context_after': return {'content': [{'role': 'user'}, {'role': 'role'}]}
                self.chats += 1
                return 'not JSON', {}
        fake = Fake()
        with tempfile.TemporaryDirectory() as tmp:
            r = ev.evaluate_one(fake, self.case(), Path(tmp), {'max_attempts': 3, 'bot_id': 1030}, 'unique')
            self.assertEqual(r['status'], 'invalid_answer')
            self.assertEqual(fake.chats, 1)

    def test_authentication_failure_recorded_then_retry(self):
        class Fake:
            token = None
            attempts = 0
            def authenticate(self):
                self.attempts += 1
                if self.attempts == 1: raise ev.APIError('temporary')
                self.token = 'fake'
            def call(self, method, endpoint, target, name, **kwargs):
                if name == 'clear': return {'role': 'flush_context'}
                if name == 'context_before': return {'content': []}
                if name == 'context_after': return {'content': [{'role': 'user'}, {'role': 'role'}]}
                return '{"answer_q1":"A","answer_q2":"A"}', {}
        with tempfile.TemporaryDirectory() as tmp, patch.object(ev.time, 'sleep'):
            r = ev.evaluate_one(Fake(), self.case(), Path(tmp), {'max_attempts': 2, 'bot_id': 1030}, 'unique')
            self.assertTrue(r['correct'])
            self.assertEqual([a['status'] for a in r['attempts']], ['error', 'received'])

    def test_full_input_counts_and_official_format(self):
        with tempfile.TemporaryDirectory() as tmp:
            ev.main(['--dry-run', '--output-dir', tmp])
            run = next(Path(tmp).iterdir())
            cases = ev.read(run/'plan.json')
            self.assertEqual(len(cases), 2400)
            self.assertEqual(len({(c['task'], c['language'], c['sample_id']) for c in cases}), 800)
            for case in cases:
                self.assertTrue(all(shown == original for m in case['maps'].values() for shown, original in m.items()))
                self.assertNotIn('[[', case['request']['content'])
            eu = next(c for c in cases if c['task']=='EU')
            self.assertIn('answer_q1', eu['request']['content'])
            self.assertEqual(len(eu['maps']['answer_q1']), 6)
            (run/'snapshot/emobench_api.py').write_text('tampered')
            with self.assertRaises(ValueError): ev.main(['--report-only', str(run)])

    def test_eu_pair_vote_does_not_synthesize_answer(self):
        cases = [{**self.case(), 'trial_id': f'trial_{i:06d}', 'repeat': i} for i in range(3)]
        replies = ['{"answer_q1":"A","answer_q2":"B"}',
                   '{"answer_q1":"B","answer_q2":"A"}',
                   '{"answer_q1":"A","answer_q2":"A"}']
        rows = [{**c, **ev.score(reply, c), 'reply': reply, 'attempts': []} for c, reply in zip(cases, replies)]
        manifest = {'tasks': ['EU'], 'languages': ['en'], 'repeats': 3, 'bot_id': 1030,
                    'script_version': 'test', 'model_version': 'unknown', 'harness_version': 'unknown',
                    'seed': 42, 'cot': False, 'shuffle_options': False, 'context_policy': 'test', 'protocol_differences': []}
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp)
            result = ev.summarize(run, manifest, cases, rows, 'complete')
            vote = ev.read(run/'question_votes.json')[0]
            self.assertIsNone(vote['prediction'])
            self.assertFalse(vote['correct'])
            self.assertEqual(result['task_language']['EU']['en']['auxiliary_vote']['ties_or_no_answer'], 1)
            export = json.loads((run/'official_format/EU/round_1.jsonl').read_text())
            self.assertEqual(export['emo_answer'], 'B')
            self.assertEqual(export['cause_answer'], 'A')

    def test_parallel_users_and_resume_no_resend(self):
        barrier = threading.Barrier(4)
        lock = threading.Lock()
        users = []
        class Fake:
            def __init__(self, base, key, secret, uid, *args):
                self.uid = uid; self.token = None; self.session = self; self.history=[]
            def close(self): pass
            def authenticate(self): self.token = 'fake'
            def call(self, method, endpoint, target, name, **kwargs):
                if name == 'bots': return [{'id': 1030}]
                payload = kwargs.get('payload') or kwargs.get('params')
                assert payload['botId'] == 1030
                if name == 'clear': self.history=[]; return {'role': 'flush_context'}
                if name.startswith('context'): return {'content': self.history.copy()}
                with lock: users.append(self.uid)
                barrier.wait(timeout=5)
                self.history = [{'role': 'user'}, {'role': 'role'}]
                return '{"answer_q1":"A","answer_q2":"A","answer":"A"}', {}
        with tempfile.TemporaryDirectory() as tmp, patch.object(ev, 'Client', Fake):
            self.assertEqual(ev.main(['--limit', '1', '--repeats', '1', '--workers', '4', '--output-dir', tmp]), 0)
            run = next(Path(tmp).iterdir())
            self.assertEqual(len(users), 4)
            self.assertEqual(len(set(users)), 4)
            summary = ev.read(run/'summary.json')
            self.assertEqual(summary['completed_trials'], 4)
            self.assertEqual(len(summary['task_language']), 2)
            self.assertEqual(ev.main(['--resume', str(run)]), 0)
            self.assertEqual(len(users), 4)


if __name__ == '__main__':
    unittest.main()
