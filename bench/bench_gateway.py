"""Shared AxonHub configuration and the existing audited Lingx adapter."""
import argparse
import os
from pathlib import Path
import sys

BENCH = Path(__file__).resolve().parent
sys.path.insert(0, str(BENCH / "PsiArena"))

from psiarena.ai_role import AiRoleSession
from psiarena.ai_role_transport import write_json


def parser(description):
    p = argparse.ArgumentParser(description=description)
    p.add_argument("--target", choices=("agent", "api"), default="agent")
    p.add_argument("--bot-id", type=int, default=1030)
    p.add_argument("--target-model", default=os.getenv("AXONHUB_TARGET_MODEL", "deepseek-v4.1-flash-1017"))
    p.add_argument("--patient-model", default=os.getenv("AXONHUB_PATIENT_MODEL", "deepseek-v4.1-flash-1017"))
    p.add_argument("--judge-model", default=os.getenv("AXONHUB_JUDGE_MODEL", "deepseek-v4.1-flash-1017"))
    p.add_argument("--turns", type=int, default=2)
    p.add_argument("--output", type=Path, required=True)
    return p


def configure(args):
    if args.turns < 1:
        raise SystemExit("--turns must be positive")
    key = os.getenv("AXONHUB_API_KEY")
    if not key:
        raise SystemExit("Set AXONHUB_API_KEY before running")
    os.environ["PSIARENA_AI_ROLE_BOT_ID"] = str(args.bot_id)
    return os.getenv("AXONHUB_BASE_URL", "https://axonhub.ai-role.cn/v1").rstrip("/"), key
