"""Independent PsiArena runner with bounded recovery for incomplete replies."""
import re
import time

import evaluate_local_models as runner
from psiarena import evaluate, pipeline
from psiarena.config import chat
from psiarena.scoring import ScoreFormatError, parse_section


def retry(operation, *, invalid=(), attempts=3):
    for attempt in range(attempts):
        try:
            return operation(attempt)
        except Exception as exc:
            status = getattr(exc, 'status_code', None)
            transient = status in (408, 429, 500, 502, 503, 504)
            transient |= type(exc).__name__ in ('APITimeoutError', 'APIConnectionError')
            if attempt + 1 == attempts or not (transient or isinstance(exc, invalid)):
                raise
            time.sleep(2 ** attempt)


def resilient_client(role, messages, **kwargs):
    return retry(lambda _: chat(role, messages, **kwargs), invalid=(RuntimeError,))


def resilient_judge(role, messages):
    match = re.search(r'固定ID依次为：(client|supervisor|counselor)_01', messages[-1]['content'])
    if match is None:
        raise ValueError('Missing judge perspective')

    def score(_):
        raw = chat(role, messages)
        parse_section(raw, match[1], require_ids=True)
        return raw

    return retry(score, invalid=(RuntimeError, ScoreFormatError))


class IncompleteCounselorReply(RuntimeError):
    pass


class ReliableLocalSession(runner.LocalSession):
    def _counselor_reply(self, turn, last_client_text):
        initial_limit = self.max_tokens

        context_budget = None

        def generate(attempt):
            nonlocal context_budget
            # Larger budget for CPsyCounX, while leaving context room where possible.
            self.max_tokens = min(4096, initial_limit * (2 if attempt and self.model == 'cpsycounx' else 1))
            if context_budget is not None:
                self.max_tokens = min(self.max_tokens, context_budget)
            try:
                reply = super(ReliableLocalSession, self)._counselor_reply(turn, last_client_text)
            except RuntimeError as exc:
                if str(exc).startswith('Counselor incomplete or empty:'):
                    raise IncompleteCounselorReply(str(exc)) from exc
                raise
            except Exception as exc:
                # vLLM reports the exact prompt size when the requested budget will not fit.
                message = str(getattr(exc, 'body', ''))
                limit = re.search(r'maximum context length is (\d+) tokens and your request has (\d+) input tokens', message)
                if getattr(exc, 'status_code', None) == 400 and limit:
                    remaining = int(limit[1]) - int(limit[2])
                    if 0 < remaining < self.max_tokens:
                        context_budget = remaining
                        raise IncompleteCounselorReply('Adjusted generation budget to fit context') from exc
                raise
            if not reply.strip():
                raise IncompleteCounselorReply('Counselor returned blank text')
            return reply

        try:
            return retry(generate, invalid=(IncompleteCounselorReply,))
        finally:
            self.max_tokens = initial_limit


if __name__ == '__main__':
    pipeline.chat = resilient_client
    evaluate.chat = resilient_judge
    runner.LocalSession = ReliableLocalSession
    raise SystemExit(runner.main())
