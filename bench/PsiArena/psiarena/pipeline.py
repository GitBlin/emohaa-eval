"""Multi-turn counseling dialogue generation.

A session is a 25-turn loop between two role-playing agents:

    * the **counselor** (the model under test), and
    * the **client** (a help-seeker simulated from one of the 100 role cards).

Three generation modes (paper terms in parentheses):

    * ``vanilla`` (Vanilla Prompt) — counselor gets only a generic assistant prompt.
    * ``psycho``  (Psycho Prompt)  — counselor gets a psychology-grounded prompt.
    * ``rewrite`` (Closed-Loop Optimization) — each counselor turn is self-reflected
                  and rewritten using three-party feedback + a knowledge base.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from . import data
from .config import chat

# ---- turn orchestration constants ----

NUM_TURNS = 25

# The client's first incoming line, fed to the counselor as the opening user message.
COUNSELOR_OPENER = {"vanilla": "你好！", "psycho": "咨询师你好！", "rewrite": "咨询师你好！"}

# In psycho/rewrite the client's first message is a fixed greeting (not the counselor text).
CLIENT_KICKOFF = "你好，我是你今天的心理咨询师！"

# Suffix appended to each client reply when it is handed back to the counselor.
COUNSELOR_TURN_SUFFIX = (
    "<第{n}轮:让你的回答保持简短，限制每次回复中的信息量，字数限制在100字左右。"
    "一次提出一个问题，不要分点描述{extra}。>"
)

# Suffix appended to each counselor line when it is handed to the client.
CLIENT_TURN_SUFFIX = (
    "<第{n}轮:当前是{stage}阶段，请遵循对应的对话规则进行回复，"
    "每轮只针对对话规则中的一个方面进行回复。>"
)

# Characters kept when normalizing model output (CJK text + common punctuation);
# everything else (emoji, markdown, stray symbols, ...) is stripped.
_ALLOWED_RANGES = [
    (0x0030, 0x2A6D),   # basic latin / digits / symbols
    (0x3400, 0x4DBF),   # CJK Extension A
    (0x4E00, 0x9FA5),   # CJK Unified Ideographs
]
_ALLOWED_PUNCT = "，。！？：；（）【】〔〕《》、@#&$%-"
_CLEAN_RE = re.compile(
    "[^" + "".join(f"{chr(a)}-{chr(b)}" for a, b in _ALLOWED_RANGES) + _ALLOWED_PUNCT + "]"
)
_ROUND_TAG_RE = re.compile(r"<第\d+轮>")


def clean_text(text: str) -> str:
    """Strip leaked round tags and any non-CJK/punctuation characters."""
    text = _ROUND_TAG_RE.sub("", text)
    return _CLEAN_RE.sub("", text)


def stage_for_turn(turn: int) -> str:
    """Early / middle / late stage label for a 0-indexed turn."""
    if turn < 7:
        return "初期"
    if turn < 15:
        return "中期"
    return "后期"


def build_client_system_prompt(card: str) -> str:
    """The client's system prompt for dialogue generation: persona + interaction rules."""
    prefix = data.load_prompt("client_dialogue_prefix")
    suffix = data.load_prompt("client_dialogue_suffix")
    return f"{prefix}{card}{suffix}"


def counselor_system_prompt(mode: str) -> str:
    """The counselor's system prompt for the given mode."""
    if mode == "vanilla":
        return "You are a helpful assistant."
    if mode == "psycho":
        return data.load_prompt("counselor_psycho")
    if mode == "rewrite":
        return data.load_prompt("counselor_rewrite")
    raise ValueError(f"unknown mode: {mode}")


# ---- feedback (rewrite mode only) --------------------------------------------------

def split_scores_sections(scores_text: str) -> tuple[str, str, str]:
    """Split a scores file into (client, supervisor, counselor) sections by header.

    The evaluation step writes three blocks led by ``来访者评分:`` / ``督导评分:`` /
    ``心理咨询师评分:``; this recovers them for the feedback summarizers.
    """
    client, supervisor, counselor, current = [], [], [], None
    for line in scores_text.splitlines(keepends=True):
        if line.startswith("来访者评分:"):
            current = client
        elif line.startswith("督导评分:"):
            current = supervisor
        elif line.startswith("心理咨询师评分:"):
            current = counselor
        if current is not None:
            current.append(line)
    return "".join(client), "".join(supervisor), "".join(counselor)


def summarize_feedback(scores_text: str) -> tuple[str, str, str]:
    """Summarize prior three-party scores into actionable feedback (rewrite mode)."""
    client_block, supervisor_block, counselor_block = split_scores_sections(scores_text)
    feed_client = chat(
        "judge",
        [{"role": "system", "content": data.load_prompt("feedback_client")},
         {"role": "user", "content": client_block}],
    )
    feed_supervisor = chat(
        "judge",
        [{"role": "system", "content": data.load_prompt("feedback_supervisor")},
         {"role": "user", "content": supervisor_block}],
    )
    feed_counselor = chat(
        "judge",
        [{"role": "system", "content": data.load_prompt("feedback_counselor")},
         {"role": "user", "content": counselor_block}],
    )
    return feed_client, feed_supervisor, feed_counselor


# ---- the session loop --------------------------------------------------------------

@dataclass
class Feedback:
    client: str
    supervisor: str
    counselor: str


@dataclass
class _Session:
    mode: str
    card: str
    feedback: Feedback | None = None
    dialogue: list[str] = field(default_factory=list)
    _counselor_msgs: list[dict] = field(default_factory=list)
    _client_msgs: list[dict] = field(default_factory=list)

    def __post_init__(self):
        sys_prompt = counselor_system_prompt(self.mode)
        opener = COUNSELOR_OPENER[self.mode]
        self._counselor_msgs.append({"role": "system", "content": sys_prompt})
        self._counselor_msgs.append({"role": "user", "content": opener + "<第1轮>"})
        self._client_msgs.append(
            {"role": "system", "content": build_client_system_prompt(self.card)}
        )

    # -- counselor side --
    def _counselor_reply(self, turn: int, last_client_text: str) -> str:
        raw = clean_text(chat("counselor", self._counselor_msgs))
        if self.mode != "rewrite":
            return raw
        return self._reflect_and_rewrite(turn, raw, last_client_text)

    def _reflect_and_rewrite(self, turn: int, raw: str, last_client_text: str) -> str:
        # 1) reflect: list the shortcomings of the raw reply
        reflect_sys = data.load_prompt("rewrite_reflect").format(
            round=turn + 1,
            feedback_client=self.feedback.client,
            feedback_supervisor=self.feedback.supervisor,
            feedback_counselor=self.feedback.counselor,
            knowledge=data.load_knowledge(),
            dialogue="".join(self.dialogue),
        )
        defect = chat(
            "counselor",
            [{"role": "system", "content": reflect_sys},
             {"role": "user", "content": f"你当前轮次的回复：{raw}"}],
        )
        # 2) improve: rewrite the reply addressing the defects
        improve_sys = data.load_prompt("rewrite_improve_system").format(
            round=turn + 1, defect=defect
        )
        improve_user = data.load_prompt("rewrite_improve_user").format(
            client_reply=last_client_text, counselor_reply=raw
        )
        improved = chat(
            "counselor",
            [{"role": "system", "content": improve_sys},
             {"role": "user", "content": improve_user}],
        )
        improved = improved.replace("心理咨询师: ", "")
        # 3) on the final turn, make sure the session is wrapped up
        if turn == NUM_TURNS - 1:
            finalize_sys = data.load_prompt("rewrite_finalize").format(
                dialogue="".join(self.dialogue)
            )
            improved = chat(
                "counselor",
                [{"role": "system", "content": finalize_sys},
                 {"role": "user", "content": f"当前轮次你的回复：{improved}\n"}],
            ).replace("心理咨询师: ", "")
        return improved

    # -- client side --
    def _client_reply(self, turn: int, counselor_text: str) -> str:
        if turn == 0 and self.mode in ("psycho", "rewrite"):
            content = CLIENT_KICKOFF
        else:
            content = counselor_text
        tag = CLIENT_TURN_SUFFIX.format(n=turn + 1, stage=stage_for_turn(turn))
        self._client_msgs.append({"role": "user", "content": content + tag})
        reply = clean_text(chat("client", self._client_msgs))
        self._client_msgs.append({"role": "assistant", "content": reply})
        return reply

    def run(self) -> list[str]:
        extra = "或格式化输出" if self.mode == "rewrite" else ""
        last_client_text = COUNSELOR_OPENER[self.mode]
        for turn in range(NUM_TURNS):
            if turn > 5:  # sliding window: drop the oldest user+assistant exchange
                for _ in range(2):
                    self._counselor_msgs.pop(1)
                    self._client_msgs.pop(1)

            counselor_text = self._counselor_reply(turn, last_client_text)
            self.dialogue.append(f"心理咨询师: {counselor_text}")
            self._counselor_msgs.append({"role": "assistant", "content": counselor_text})

            client_text = self._client_reply(turn, counselor_text)
            self.dialogue.append(f"来访者: {client_text}")
            suffix = COUNSELOR_TURN_SUFFIX.format(n=turn + 2, extra=extra)
            self._counselor_msgs.append({"role": "user", "content": client_text + suffix})
            last_client_text = client_text
        return self.dialogue


def generate_dialogue(card_index: int, mode: str, feedback: Feedback | None = None) -> list[str]:
    """Generate one full counseling dialogue for the given role card and mode.

    Returns the dialogue as a list of ``"心理咨询师: ..."`` / ``"来访者: ..."`` lines.
    ``feedback`` is required for ``rewrite`` mode (summarized prior three-party scores).
    """
    if mode == "rewrite" and feedback is None:
        raise ValueError("rewrite mode requires feedback (see summarize_feedback).")
    card = data.load_role_cards()[card_index]
    return _Session(mode=mode, card=card, feedback=feedback).run()
