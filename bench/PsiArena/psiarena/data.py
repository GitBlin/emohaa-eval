"""Loaders for the bundled data assets (role cards, knowledge base, prompts)."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
PROMPTS_DIR = DATA_DIR / "prompts"


@lru_cache(maxsize=1)
def load_role_cards() -> list[str]:
    """Return the 100 client role cards (persona + presenting problem)."""
    with open(DATA_DIR / "role_cards.json", encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def load_knowledge() -> str:
    """Return the psychotherapy theory/technique knowledge base (rewrite mode)."""
    return (DATA_DIR / "knowledge.txt").read_text(encoding="utf-8")


@lru_cache(maxsize=None)
def load_prompt(name: str) -> str:
    """Read ``data/prompts/<name>.txt``. Templates use ``str.format`` placeholders."""
    return (PROMPTS_DIR / f"{name}.txt").read_text(encoding="utf-8")
