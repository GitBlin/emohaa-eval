"""Offline checks for full history and context isolation under overlapping workers."""
import sys
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from psiarena.runtime import current_run, run_log
from psiarena.pipeline import _Session

class ParallelTests(unittest.TestCase):
    def test_overlapping_run_contexts_are_separate(self):
        barrier = Barrier(2)
        def task(label):
            with run_log(Path('/tmp') / label):
                barrier.wait(timeout=5)
                self.assertEqual(current_run.get().directory.name, label)
                first = current_run.get().next_call('client')
                barrier.wait(timeout=5)
                self.assertTrue(str(first).endswith('00001_client'))
            self.assertIsNone(current_run.get())
        with ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(task, ['psi_context_a', 'psi_context_b']))

    def test_full_history_keeps_earliest_messages_after_window_boundary(self):
        seen = []
        def fake_chat(role, messages):
            if role == 'client':
                seen.append([dict(m) for m in messages])
            return 'test reply'
        with patch('psiarena.pipeline.chat', side_effect=fake_chat), \
             patch('psiarena.pipeline.counselor_system_prompt', return_value='counselor'), \
             patch('psiarena.pipeline.build_client_system_prompt', return_value='client'):
            _Session(mode='psycho', card='card').run(25, history='full')
        self.assertEqual(len(seen[-1]), 50)  # system + 24 pairs + current user
        self.assertEqual(seen[-1][1], seen[0][1])
        self.assertIn('第25轮', seen[-1][-1]['content'])

if __name__ == '__main__':
    unittest.main()
