"""Three-party evaluation of a finished counseling dialogue.

Each dialogue is scored from three perspectives, all by the judge model:

    * **client**     — how the help-seeker experienced the session (16 dimensions)
    * **supervisor** — a clinical supervisor's assessment (8 dimensions)
    * **counselor**  — the counselor's structured self-assessment (9 dimensions)

The combined result is written as a ``scores`` block; each scored dimension ends with
a ``[得分]N分`` (or ``[得分]N/A``) line consumed by :mod:`psiarena.scoring`.
"""
from __future__ import annotations

from . import data
from .config import chat

DIALOGUE_HEADER = "\n<Dialogue History>\n"


def _with_dialogue(prompt: str, dialogue_text: str) -> str:
    return f"{prompt}{DIALOGUE_HEADER}{dialogue_text}"


def evaluate_dialogue(card_index: int, dialogue_text: str) -> str:
    """Run all three evaluators on one dialogue and return the combined scores block."""
    card = data.load_role_cards()[card_index]

    # client perspective
    client_system = data.load_prompt("client_eval_prefix") + card
    client_score = chat(
        "judge",
        [{"role": "system", "content": client_system},
         {"role": "user", "content": _with_dialogue(data.load_prompt("eval_client"), dialogue_text)}],
    )

    # supervisor perspective
    supervisor_score = chat(
        "judge",
        [{"role": "system", "content": data.load_prompt("supervisor_system")},
         {"role": "user", "content": _with_dialogue(data.load_prompt("eval_supervisor"), dialogue_text)}],
    )

    # counselor self-assessment
    counselor_score = chat(
        "judge",
        [{"role": "system", "content": data.load_prompt("eval_counselor_system")},
         {"role": "user", "content": _with_dialogue(data.load_prompt("eval_counselor"), dialogue_text)}],
    )

    return (
        f"来访者评分: {client_score}\n"
        f"督导评分: {supervisor_score}\n"
        f"心理咨询师评分: {counselor_score}\n"
    )
