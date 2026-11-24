"""Evaluate three local counselors with the same visible input as the bot harness."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
import sys
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from psiarena import data
from psiarena.ai_role_transport import append_json, now, write_json
from psiarena.config import _client_for, get_settings
from psiarena.evaluate import evaluate_dialogue
from psiarena.pipeline import _Session, clean_text
from psiarena.runtime import current_run, run_log
from psiarena.scoring import aggregate, parse_score_text

MODELS = {
    'educhat-r1-001-32b-qwen3.0': 8000,
    'PsychAgent-Qwen3-32B': 30001,
    'cpsycounx': 8931,
}


class LocalSession(_Session):
    def _counselor_reply(self, turn, last_client_text):
        messages = self._counselor_msgs
        # Match the bot transport: move the benchmark instruction into the first user turn.
        opening = dict(messages[1])
        opening['content'] = (
            '<咨询行为要求>\n' + messages[0]['content']
            + '\n</咨询行为要求>\n' + opening['content']
        )
        payload = {
            'model': self.model,
            'messages': [{'role': 'system', 'content': ''}, opening, *messages[2:]],
            'temperature': self.temperature,
            'max_tokens': self.max_tokens,
        }
        log = current_run.get().next_call('counselor')
        write_json(log / 'request.json', payload)
        response = self.api.chat.completions.create(**payload)
        write_json(log / 'response.json', response.model_dump(mode='json'))
        choice = response.choices[0]
        if choice.finish_reason != 'stop' or not choice.message.content:
            raise RuntimeError(f'Counselor incomplete or empty: {choice.finish_reason}')
        return clean_text(choice.message.content)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cards', type=int, default=50)
    parser.add_argument('--workers-per-model', type=int, default=4)
    parser.add_argument('--max-tokens', type=int, default=2048)
    parser.add_argument('--output-dir', type=Path)
    args = parser.parse_args()
    cards = data.load_role_cards()
    if not 1 <= args.cards <= len(cards) or min(args.workers_per_model, args.max_tokens) < 1:
        parser.error('Invalid card count, concurrency, or token limit')
    settings = get_settings()
    indices = list(range(args.cards))
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '_' + uuid4().hex[:8]
    root = args.output_dir or ROOT.parent / ('PsiArena_local_models_' + stamp)
    root.mkdir(parents=True, exist_ok=False)
    print('Archive:', root, flush=True)

    def run_model(model, port):
        run = root / model
        run.mkdir()
        url = f'http://127.0.0.1:{port}/v1'
        api = _client_for(url, 'EMPTY', max(240, settings.timeout))
        write_json(run / 'manifest.json', {
            'model': model, 'base_url': url, 'cards': indices, 'turns': 25,
            'history': 'full', 'mode': 'psycho', 'protocol': 'code',
            'workers': args.workers_per_model, 'temperature': settings.temperature,
            'max_tokens': args.max_tokens, 'system_prompt': '', 'user_prompt_template': '',
            'roles': {role: {'model': settings.roles[role].model,
                             'reasoning_effort': settings.roles[role].reasoning_effort}
                      for role in ('client', 'judge')},
        })

        def run_card(index):
            directory = run / 'cards' / f'{index:03d}'
            directory.mkdir(parents=True)
            session = LocalSession(mode='psycho', card=cards[index], feedback=None)
            session.model, session.api = model, api
            session.temperature, session.max_tokens = settings.temperature, args.max_tokens
            try:
                with run_log(directory):
                    dialogue = session.run(
                        turns=25, history='full',
                        checkpoint=lambda turn, lines: write_json(
                            directory / 'dialogue_progress.json',
                            {'completed_turns': turn, 'dialogue': lines},
                        ),
                    )
                    transcript = '\n'.join(dialogue) + '\n'
                    (run / f'dialogue{index}.txt').write_text(transcript, encoding='utf-8')
                    scores = evaluate_dialogue(index, transcript, output_dir=directory)
                    (run / f'scores{index}.txt').write_text(scores, encoding='utf-8')
                    write_json(directory / 'parsed_scores.json', parse_score_text(scores, 'code'))
                return {'card': index, 'status': 'complete', 'at': now()}
            except Exception as exc:
                return {'card': index, 'status': 'error', 'at': now(),
                        'error_type': type(exc).__name__, 'http_status': getattr(exc, 'status_code', None)}

        with ThreadPoolExecutor(max_workers=args.workers_per_model) as pool:
            for future in as_completed([pool.submit(run_card, index) for index in indices]):
                event = future.result()
                append_json(run / 'execution_log.jsonl', event)
                print(model, event, flush=True)
        summary = aggregate(run, protocol='code', indices=indices)
        write_json(run / 'summary.json', summary)
        return summary['complete']

    with ThreadPoolExecutor(max_workers=len(MODELS)) as pool:
        jobs = [pool.submit(run_model, model, port) for model, port in MODELS.items()]
        results = [job.result() for job in jobs]
    return 0 if all(results) else 2


if __name__ == '__main__':
    sys.exit(main())
