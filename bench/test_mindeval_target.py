"""Run upstream MindEval 2 with either an audited Lingx session or a model API."""
import os
from pathlib import Path
import sys
import threading

from bench_gateway import AiRoleSession, BENCH, configure, parser, write_json


def main():
    p = parser(__doc__)
    p.add_argument("--members", type=int, default=1)
    p.add_argument("--sessions", type=int, default=1)
    p.add_argument("--workers", type=int, default=1)
    p.add_argument("--counselor-base-url", help="Separate OpenAI-compatible URL for the API counselor")
    args = p.parse_args()
    if args.counselor_base_url and args.target != "api":
        p.error("--counselor-base-url requires --target api")
    if min(args.members, args.sessions, args.workers) < 1:
        p.error("members, sessions and workers must be positive")
    base, key = configure(args)
    repo = BENCH / "MindEval"
    out = args.output.resolve()
    sys.path.insert(0, str(repo))
    os.chdir(repo)
    from mindeval import arc
    from mindeval.scripts import generate_interactions as interactions, generate_judgments as judgments
    from mindeval.session import Counselor

    target = args.target_model if args.target == "api" else f"lingx-bot-{args.bot_id}"
    for role, model in (("PATIENT", args.patient_model), ("COUNSELOR", target), ("JUDGE", args.judge_model)):
        separate = role == "COUNSELOR" and args.counselor_base_url
        os.environ.update({
            f"MINDEVAL_{role}_MODEL": f"openai/{model}",
            f"MINDEVAL_{role}_API_BASE": args.counselor_base_url if separate else base,
            f"MINDEVAL_{role}_API_KEY": os.getenv("MINDEVAL_LOCAL_API_KEY", "EMPTY") if separate else key,
        })
    if args.target == "agent":
        local = threading.local()
        original_session, original_preflight = arc.run_session, interactions.preflight

        def close():
            session = getattr(local, "session", None)
            if session is not None:
                session.client.session.close()
                del local.session

        def wrap(fn):
            def run(*a, **kw):
                try:
                    return fn(*a, **kw)
                finally:
                    close()
            return run

        def respond(self, system_prompt, transcript):
            if not hasattr(local, "session"):
                import uuid
                local.session = AiRoleSession(out / "agent_requests" / uuid.uuid4().hex, "MindEval")
                local.session.start()
            if transcript[-1]["role"] != "assistant":
                raise ValueError("Expected a simulated member message")
            reply = local.session.chat([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": transcript[-1]["content"]},
            ])
            return reply, {"requested_model": target}

        Counselor.respond = respond
        arc.run_session = wrap(original_session)
        interactions.preflight = wrap(original_preflight)

    status = interactions.main(out, members=args.members, sessions=args.sessions,
                               max_turns=args.turns, max_workers=args.workers,
                               patient_timeout=90, counselor_timeout=90, counselor_retries=1)
    if status == 2:
        return status
    grade = judgments.main(out, max_workers=args.workers, judge_timeout=120,
                           judge_retries=1, judge_params={})
    print(f"Artifacts: {out}", flush=True)
    return grade or status


if __name__ == "__main__":
    raise SystemExit(main())
