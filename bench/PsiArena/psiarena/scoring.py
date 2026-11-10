"""Parse and aggregate three-party scores.

Each scored dimension produces a ``[得分]N分`` line (or ``[得分]N/A`` when the
dimension was not addressed). A complete scores file has 33 such lines, ordered:

    * dimensions  1–16  → client perspective
    * dimensions 17–24  → supervisor perspective
    * dimensions 25–33  → counselor self-assessment

The client/counselor averages divide by the fixed dimension counts (16 and 9), so an
unscored ``N/A`` lowers the mean; the supervisor average divides by its scored count.
"""
from __future__ import annotations

import re
from pathlib import Path

# number of dimensions per perspective (sum = 33)
N_CLIENT = 16
N_SUPERVISOR = 8
N_COUNSELOR = 9
N_TOTAL = N_CLIENT + N_SUPERVISOR + N_COUNSELOR

# "pass" thresholds used in the paper for the per-perspective pass-rate counts
THRESHOLDS = {"client": 2.6, "supervisor": 3.0, "counselor": 3.8, "overall": 3.0}

_SCORE_RE = re.compile(r"\d+")


def parse_score_file(path: str | Path) -> dict | None:
    """Parse one ``scores*.txt`` file into per-perspective averages.

    Returns ``None`` if the file does not contain exactly ``N_TOTAL`` ``[得分]`` lines.
    """
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    client, supervisor, counselor = [], [], []
    total_marks = 0
    for line in lines:
        if "[得分]" not in line:
            continue
        total_marks += 1
        m = _SCORE_RE.search(line)
        if not m:  # "[得分]N/A" — counted as a dimension but contributes no number
            continue
        value = int(m.group())
        if total_marks <= N_CLIENT:
            client.append(value)
        elif total_marks <= N_CLIENT + N_SUPERVISOR:
            supervisor.append(value)
        else:
            counselor.append(value)

    if total_marks != N_TOTAL:
        return None

    client_avg = sum(client) / N_CLIENT
    supervisor_avg = sum(supervisor) / len(supervisor) if supervisor else 0.0
    counselor_avg = sum(counselor) / N_COUNSELOR
    total = sum(client) + sum(supervisor) + sum(counselor)
    overall = total / (N_CLIENT + N_COUNSELOR + len(supervisor))
    return {
        "client": client_avg,
        "supervisor": supervisor_avg,
        "counselor": counselor_avg,
        "overall": overall,
        "marks": total_marks,
    }


def check_dir(score_dir: str | Path, n: int = 100) -> list[tuple[int, int]]:
    """Return ``(card_index, mark_count)`` for files whose mark count != ``N_TOTAL``.

    Missing files are reported as ``(index, -1)``.
    """
    score_dir = Path(score_dir)
    bad = []
    for i in range(n):
        path = score_dir / f"scores{i}.txt"
        if not path.exists():
            bad.append((i, -1))
            continue
        marks = sum("[得分]" in ln for ln in path.read_text(encoding="utf-8").splitlines())
        if marks != N_TOTAL:
            bad.append((i, marks))
    return bad


def aggregate(score_dir: str | Path, n: int = 100) -> dict:
    """Aggregate per-perspective means and pass-rates across ``n`` dialogues."""
    score_dir = Path(score_dir)
    rows, skipped = [], []
    for i in range(n):
        path = score_dir / f"scores{i}.txt"
        parsed = parse_score_file(path) if path.exists() else None
        if parsed is None:
            skipped.append(i)
        else:
            rows.append(parsed)

    means = {k: round(sum(r[k] for r in rows) / len(rows), 2) for k in
             ("client", "supervisor", "counselor")} if rows else {}
    if means:
        means["overall"] = round(
            (means["client"] + means["supervisor"] + means["counselor"]) / 3, 2
        )
    passes = {
        k: sum(1 for r in rows if r[k] >= THRESHOLDS[k])
        for k in ("client", "supervisor", "counselor", "overall")
    }
    return {"n_scored": len(rows), "skipped": skipped, "means": means, "passes": passes}
