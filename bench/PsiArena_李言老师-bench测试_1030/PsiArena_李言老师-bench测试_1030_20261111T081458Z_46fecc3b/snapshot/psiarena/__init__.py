"""PsiArena — a multi-agent benchmark for LLM psychological counseling.

Three role-playing agents (counselor / client / supervisor) drive a closed loop of
multi-turn counseling dialogue, three-party evaluation, and feedback-guided rewriting.
All model calls go through a single OpenAI-compatible API (see ``psiarena.config``).
"""

__version__ = "1.0.0"
