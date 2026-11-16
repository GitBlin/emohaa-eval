"""Three independent judge calls with fixed dimension IDs and raw score retention."""
from __future__ import annotations
from pathlib import Path
from . import data
from .config import chat
from .scoring import COUNTS, HEADERS, parse_section

DIALOGUE_HEADER = '\n<Dialogue History>\n'

def _with_dialogue(prompt: str, dialogue_text: str) -> str:
    return f'{prompt}{DIALOGUE_HEADER}{dialogue_text}'


def evaluate_dialogue(card_index: int, dialogue_text: str, *, output_dir=None) -> str:
    card = data.load_role_cards()[card_index]
    systems = {'client': data.load_prompt('client_eval_prefix') + card,
               'supervisor': data.load_prompt('supervisor_system'),
               'counselor': data.load_prompt('eval_counselor_system')}
    scores = []
    for perspective, count in COUNTS.items():
        ids = ', '.join(f'{perspective}_{i:02d}' for i in range(1, count+1))
        instruction = ('\n<输出格式补充>严格按原量表顺序逐项评分。每项单独输出三行：'
                       '\n[维度]固定ID 维度名称\n[分析]评分依据\n[得分]整数分数或N/A'
                       f'\n本视角恰好{count}项，固定ID依次为：{ids}。不要输出其他[得分]标记。'
                       '\n</输出格式补充>')
        raw = chat('judge', [
            {'role': 'system', 'content': systems[perspective]},
            {'role': 'user', 'content': _with_dialogue(data.load_prompt('eval_'+perspective) + instruction, dialogue_text)},
        ])
        scores.append(f'{HEADERS[perspective]} {raw}\n')
        if output_dir is not None:
            directory = Path(output_dir)
            directory.mkdir(parents=True, exist_ok=True)
            (directory / f'judge_{perspective}.txt').write_text(raw, encoding='utf-8')
            (directory / 'scores.partial.txt').write_text(''.join(scores), encoding='utf-8')
        parse_section(raw, perspective, require_ids=True)
    return ''.join(scores)
