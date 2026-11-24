"""Copy a finished archive and retry only missing EduChat/PsychAgent scores."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from pathlib import Path
import shutil
import time
from uuid import uuid4

import evaluate_local_models_reliable as fix

r = fix.runner


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--until-complete', action='store_true')
    args = parser.parse_args()
    fix.pipeline.chat = fix.resilient_client
    fix.evaluate.chat = fix.resilient_judge
    args.output.mkdir()
    jobs = []
    for model in ('educhat-r1-001-32b-qwen3.0', 'PsychAgent-Qwen3-32B'):
        source = args.source / model
        target = args.output / model
        summary = json.loads((source / 'summary.json').read_text())
        shutil.copytree(source, target)
        jobs.extend((model, target, index) for index in summary['skipped'])
        print(model, 'missing:', summary['skipped'], flush=True)
    r.write_json(args.output / 'retry_plan.json', {
        'source': str(args.source.resolve()), 'workers': 2,
        'cases': {model: [i for m, _, i in jobs if m == model]
                  for model in ('educhat-r1-001-32b-qwen3.0', 'PsychAgent-Qwen3-32B')},
    })
    settings = r.get_settings()
    cards = r.data.load_role_cards()

    def retry_case(model, target, index):
        card = target / 'cards' / f'{index:03d}'
        attempt = card / ("repair_attempt_" + uuid4().hex[:8])
        transcript = target / f'dialogue{index}.txt'
        with r.run_log(attempt):
            if not transcript.exists():
                checkpoints = [card / 'dialogue_progress.json', *card.glob('repair_attempt*/dialogue_progress.json')]
                progress = max((json.loads(path.read_text()) for path in checkpoints if path.exists()),
                               key=lambda item: item['completed_turns'],
                               default={'completed_turns': 0, 'dialogue': []})
                lines = progress['dialogue']
                completed = progress['completed_turns']
                assert len(lines) == 2 * completed

                class ReplaySession(fix.ReliableLocalSession):
                    def _counselor_reply(self, turn, last_client_text):
                        if turn < completed:
                            return lines[2 * turn].removeprefix('心理咨询师: ')
                        return super()._counselor_reply(turn, last_client_text)

                    def _client_reply(self, turn, counselor_text):
                        if turn >= completed:
                            return super()._client_reply(turn, counselor_text)
                        from psiarena.pipeline import CLIENT_KICKOFF, CLIENT_TURN_SUFFIX, stage_for_turn
                        content = CLIENT_KICKOFF if turn == 0 else counselor_text
                        tag = CLIENT_TURN_SUFFIX.format(n=turn + 1, stage=stage_for_turn(turn))
                        reply = lines[2 * turn + 1].removeprefix('来访者: ')
                        self._client_msgs.extend([
                            {'role': 'user', 'content': content + tag},
                            {'role': 'assistant', 'content': reply},
                        ])
                        return reply

                session = ReplaySession(mode='psycho', card=cards[index], feedback=None)
                session.model = model
                session.api = r._client_for(f'http://127.0.0.1:{r.MODELS[model]}/v1',
                                            'EMPTY', max(240, settings.timeout))
                session.temperature, session.max_tokens = settings.temperature, 2048
                dialogue = session.run(turns=25, history='full', checkpoint=lambda turn, text:
                    r.write_json(attempt / 'dialogue_progress.json', {'completed_turns': turn, 'dialogue': text}))
                transcript.write_text('\n'.join(dialogue) + '\n', encoding='utf-8')
            scores = fix.retry(lambda _: r.evaluate_dialogue(index, transcript.read_text(), output_dir=attempt))
            parsed = r.parse_score_text(scores, 'code')
            (target / f'scores{index}.txt').write_text(scores, encoding='utf-8')
            r.write_json(card / 'parsed_scores.json', parsed)

    while True:
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = {pool.submit(retry_case, *job): job for job in jobs}
            for future in as_completed(futures):
                model, target, index = futures[future]
                error = future.exception()
                event = {'model': model, 'card': index, 'status': 'error' if error else 'complete',
                         'error_type': type(error).__name__ if error else None, 'at': r.now()}
                r.append_json(target / 'repair_log.jsonl', event)
                print(event, flush=True)

        jobs = []
        complete = True
        for model in ('educhat-r1-001-32b-qwen3.0', 'PsychAgent-Qwen3-32B'):
            target = args.output / model
            summary = r.aggregate(target, protocol='code', indices=list(range(50)))
            r.write_json(target / 'summary.json', summary)
            complete = complete and summary['complete']
            jobs.extend((model, target, index) for index in summary['skipped'])
            print(model, 'scored', summary['n_scored'], flush=True)
        if complete or not args.until_complete:
            return 0 if complete else 2
        time.sleep(20)


if __name__ == '__main__':
    raise SystemExit(main())
