"""Strict 16+8+9 parsing and explicit code/paper_v1 aggregation protocols.

code keeps upstream thresholds, N/A denominators and item-weighted overall.
paper_v1 uses zero for N/A, strict total thresholds and AND overall pass.
"""
from __future__ import annotations
import re
from pathlib import Path

N_CLIENT, N_SUPERVISOR, N_COUNSELOR = 16, 8, 9
N_TOTAL = 33
COUNTS = {"client": 16, "supervisor": 8, "counselor": 9}
LIMITS = {"client": 4, "supervisor": 4, "counselor": 5}
HEADERS = {"client": "来访者评分:", "supervisor": "督导评分:", "counselor": "心理咨询师评分:"}
THRESHOLDS = {"client": 2.6, "supervisor": 3.0, "counselor": 3.8, "overall": 3.0}
PROTOCOLS = ("code", "paper_v1")

class ScoreFormatError(ValueError):
    pass


def parse_section(text: str, perspective: str, *, require_ids: bool = False) -> list[int | None]:
    """New outputs use fixed IDs; historical named blocks are accepted in order."""
    blocks = re.findall(r"\[维度\](.*?)\[分析\](.*?)\[得分\]([^\n]*)", text, re.S)
    expected = COUNTS[perspective]
    if len(blocks) != expected or any(text.count(tag) != expected for tag in ("[维度]", "[分析]", "[得分]")):
        raise ScoreFormatError(f"{perspective}: expected {expected} complete dimension blocks")
    names, values = set(), []
    for i, (name, analysis, score) in enumerate(blocks, 1):
        name = name.strip()
        if not name or name in names or not analysis.strip():
            raise ScoreFormatError(f"{perspective}: empty/duplicate dimension or empty analysis")
        names.add(name)
        ids = re.findall(r"\b(client|supervisor|counselor)_(\d{2})\b", name)
        if (ids or require_ids) and ids != [(perspective, f"{i:02d}")]:
            raise ScoreFormatError(f"{perspective}: unexpected dimension ID at {i}")
        match = re.fullmatch(r"\s*(N/A|\d+)(?:\s*分)?\s*[。.]?\s*", score, re.I)
        if not match:
            raise ScoreFormatError(f"{perspective}: invalid score at {i}")
        value = None if match[1].upper() == "N/A" else int(match[1])
        if value is not None and not 0 <= value <= LIMITS[perspective]:
            raise ScoreFormatError(f"{perspective}: score outside range at {i}")
        values.append(value)
    return values


def parse_score_text(text: str, protocol: str = "code") -> dict:
    if protocol not in PROTOCOLS:
        raise ValueError(f"unknown protocol: {protocol}")
    parts = re.split(r"(?m)^(来访者评分:|督导评分:|心理咨询师评分:)", text)
    if len(parts) != 7 or parts[0].strip() or parts[1::2] != list(HEADERS.values()):
        raise ScoreFormatError("expected three ordered, unique perspective headers")
    values = {key: parse_section(parts[2*i+2], key) for i, key in enumerate(COUNTS)}
    totals = {key: sum(v for v in row if v is not None) for key, row in values.items()}
    denominators = dict(COUNTS)
    if protocol == "code":
        denominators["supervisor"] = sum(v is not None for v in values["supervisor"])
    row = {key: totals[key] / denominators[key] if denominators[key] else 0.0 for key in COUNTS}
    if protocol == "code":
        row["overall"] = sum(totals.values()) / sum(denominators.values())
        passes = {key: row[key] >= limit for key, limit in THRESHOLDS.items()}
    else:
        row["overall"] = sum(row.values()) / 3
        passes = {key: totals[key] > limit for key, limit in {"client": 42, "supervisor": 24, "counselor": 35}.items()}
        passes["overall"] = all(passes.values())
    row.update(protocol=protocol, marks=N_TOTAL, values=values, totals=totals,
               denominators=denominators, passes=passes,
               na_counts={key: sum(v is None for v in vals) for key, vals in values.items()})
    return row


def parse_score_file(path: str | Path, protocol: str = "code") -> dict | None:
    try:
        return parse_score_text(Path(path).read_text(encoding="utf-8"), protocol)
    except ScoreFormatError:
        return None


def check_dir(score_dir: str | Path, n: int = 100) -> list[tuple[int, int]]:
    bad = []
    for i in range(n):
        path = Path(score_dir) / f"scores{i}.txt"
        if not path.exists():
            bad.append((i, -1))
        elif parse_score_file(path) is None:
            bad.append((i, path.read_text(encoding="utf-8").count("[得分]")))
    return bad


def aggregate(score_dir: str | Path, n: int = 100, protocol: str = "code", *, indices=None) -> dict:
    if protocol not in PROTOCOLS:
        raise ValueError(f"unknown protocol: {protocol}")
    indices = list(range(n) if indices is None else indices)
    if not indices or len(set(indices)) != len(indices):
        raise ValueError("expected a nonempty list of unique card indices")
    rows, errors = [], {}
    for i in indices:
        try:
            rows.append(parse_score_text((Path(score_dir) / f"scores{i}.txt").read_text(encoding="utf-8"), protocol))
        except (FileNotFoundError, ScoreFormatError) as exc:
            errors[i] = str(exc)
    keys = (*COUNTS, "overall")
    means = {key: sum(r[key] for r in rows) / len(rows) for key in keys} if rows else {}
    passes = {key: sum(r["passes"][key] for r in rows) for key in keys}
    return {"protocol": protocol, "n_expected": len(indices), "n_scored": len(rows),
            "complete": not errors, "coverage": len(rows)/len(indices),
            "skipped": list(errors), "errors": errors, "means": means, "passes": passes,
            "pass_rates": {key: count/len(indices) for key, count in passes.items()},
            "pass_rates_valid_only": {key: count/len(rows) if rows else None for key, count in passes.items()},
            "pass_rate_denominator": "all planned dialogues; invalid/missing are not passes"}
