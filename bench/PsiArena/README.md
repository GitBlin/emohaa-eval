# Ψ-Arena: Interactive Assessment and Optimization of LLM-based Psychological Counselors

Reference implementation for the paper **"Ψ-ARENA: Interactive Assessment and
Optimization of LLM-based Psychological Counselors with Tripartite Feedback."**

PsiArena evaluates how well a large language model can act as a **psychological
counselor**. Instead of scoring isolated replies, it runs a full **25-turn counseling
session** between role-playing agents, then scores the session from **three
perspectives** (client, supervisor, counselor — 33 dimensions total) and — in a
**closed loop** — feeds that critique back to **self-reflect and rewrite** the
counselor's behavior. Every model call goes through one **OpenAI-compatible** endpoint,
so any provider works.

The three agents:

| Agent | Role | Paper model | Configurable as |
|---|---|---|---|
| **Counselor** | the model under test | (your model) | `PSIARENA_COUNSELOR_*` |
| **Client** | a help-seeker simulated from a role card | `gpt-4o-mini` | `PSIARENA_CLIENT_*` |
| **Judge** | three-party evaluator + feedback summarizer | `gpt-4o` | `PSIARENA_JUDGE_*` |

Each role can point at its **own** endpoint, key and model
(`PSIARENA_<ROLE>_BASE_URL` / `_API_KEY` / `_MODEL`), falling back to the shared
`PSIARENA_BASE_URL` / `PSIARENA_API_KEY` — so the model under test and the GPT-4o judge
can live on different providers.

## Pipeline

```
                 ┌──────────────────────── role card (1 of 100) ───────────────────────┐
                 ▼                                                                      ▼
   generate_dialogues.py  ──►  dialogue{i}.txt  ──►  evaluate_dialogues.py  ──►  scores{i}.txt
   (counselor ⇄ client, 25 turns)                   (client + supervisor +          │
        ▲                                             counselor scoring)            │
        │                                                                           ▼
        └──────────────── feedback (rewrite mode) ◄──── summarize ◄──── aggregate_scores.py
```

Three generation **modes** correspond to the paper's prompting / optimization settings:

| Mode | Paper term | What the counselor gets |
|---|---|---|
| **`vanilla`** | *Vanilla Prompt* | only a generic *"helpful assistant"* system prompt |
| **`psycho`** | *Psycho Prompt* | a psychology-grounded, stage-aware system prompt |
| **`rewrite`** | *Closed-Loop Optimization* | on top of `psycho`, every counselor turn is **self-reflected** and **rewritten** |

The closed-loop `rewrite` follows the paper's three steps per turn: the counselor (1)
reviews its draft reply and reflects on its strengths/weaknesses using the distilled
three-party feedback **plus the knowledge base**, (2) rewrites the reply, and (3) the
revised session is re-evaluated. This yields the paper's large gains (up to +141%).

Each session is staged: **early** (turns 1–7, build rapport), **middle** (8–15, deepen
insight), **late** (16–25, turn insight into action and summarize).

## Structure

```
psiarena-github/
├── psiarena/
│   ├── config.py            # env-based config + one OpenAI-compatible client (3 roles)
│   ├── data.py              # loaders for role cards / knowledge / prompt templates
│   ├── pipeline.py          # 25-turn session loop; vanilla/psycho/rewrite; text cleaning
│   ├── evaluate.py          # three-party evaluation of a finished dialogue
│   └── scoring.py           # parse + aggregate scores (means, pass-rates, format check)
├── scripts/
│   ├── generate_dialogues.py   # counselor ⇄ client → dialogue{i}.txt
│   ├── evaluate_dialogues.py   # dialogue{i}.txt → scores{i}.txt
│   └── aggregate_scores.py     # scores → means / pass-rates  (--check for format)
├── data/
│   ├── role_cards.json      # 100 client personas + presenting problems
│   ├── knowledge.txt        # psychotherapy theory/technique knowledge base (rewrite)
│   └── prompts/             # all system / evaluation / feedback prompt templates (.txt)
├── requirements.txt
├── .env.example
└── README.md
```

Prompts live in `data/prompts/` as plain text (templates use `str.format`
placeholders such as `{round}`, `{knowledge}`, `{dialogue}`). Generated dialogues and
scores are written under `runs/` (git-ignored).

## Data

* **`role_cards.json`** — 100 client personas, each with demographics, cultural
  background, personality, emotional state, and a detailed presenting problem. One card
  drives one session.
* **`knowledge.txt`** — a compact knowledge base distilled from 11 major counseling
  approaches (CBT, person-centered, psychodynamic, …; cf. Corey, *Practice of Counseling
  and Psychotherapy*), injected into the reflection step of `rewrite` mode only.
* **Scoring rubric** — three perspectives, **33 dimensions** total: client subjective
  experience (16 dims, 0–4), supervisor professional competency/ethics (8 dims, 0–4,
  APA-based), counselor reflective self-assessment (9 dims, 0–5). Each scored dimension
  emits a `[得分]N` line.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env        # then fill in your endpoint + key
```

Python 3.10+. Configure one OpenAI-compatible endpoint via environment variables (a
local `.env` is auto-loaded if `python-dotenv` is installed):

```bash
# shared defaults
export PSIARENA_BASE_URL="https://your-endpoint/v1"
export PSIARENA_API_KEY="your-key"
# per role: model (and optionally its own *_BASE_URL / *_API_KEY)
export PSIARENA_COUNSELOR_MODEL="glm-5.1"      # model under test
export PSIARENA_CLIENT_MODEL="gpt-4o-mini"     # paper's simulated client
export PSIARENA_JUDGE_MODEL="gpt-4o"           # paper's evaluator
# e.g. put the judge on a different provider:
# export PSIARENA_JUDGE_BASE_URL="https://api.openai.com/v1"
# export PSIARENA_JUDGE_API_KEY="sk-..."
```

Any role without its own `*_MODEL` falls back to the counselor model, and without its
own `*_BASE_URL`/`*_API_KEY` falls back to the shared ones — so a single endpoint still
works for a quick smoke test.

## Run

```bash
# 1) generate sessions for the model under test (pick a mode)
python scripts/generate_dialogues.py --mode vanilla --output-dir runs/glm_vanilla
python scripts/generate_dialogues.py --mode psycho  --output-dir runs/glm_psycho

# 2) score them (writes scores{i}.txt next to the dialogues)
python scripts/evaluate_dialogues.py --input-dir runs/glm_psycho

# 3) feedback-guided rewrite — learns from an already-evaluated run
python scripts/generate_dialogues.py --mode rewrite \
    --output-dir runs/glm_rewrite --feedback-dir runs/glm_psycho
python scripts/evaluate_dialogues.py --input-dir runs/glm_rewrite

# 4) aggregate
python scripts/aggregate_scores.py --score-dir runs/glm_rewrite --check   # verify format
python scripts/aggregate_scores.py --score-dir runs/glm_rewrite           # means + pass-rates
```

Every script takes `--start` / `--end` to process a subset of cards and `--resume` to
skip already-produced files, so long runs are easy to checkpoint. A single full run is
100 cards × 25 turns; start with `--end 1` to smoke-test your endpoint.

## Output format

`dialogue{i}.txt` alternates speaker-tagged lines:

```
心理咨询师: 你好！很高兴见到你。有什么我可以帮你的吗？
来访者: 我也不知道该从哪说起……就是心里挺闷的。
...
```

`scores{i}.txt` holds three blocks (`来访者评分:` / `督导评分:` / `心理咨询师评分:`),
each dimension formatted as:

```
[维度]...    [分析]...    [得分]3
```

`aggregate_scores.py` reports per-perspective means (1–5) and the pass-rate counts used
in the paper (client ≥ 2.6, supervisor ≥ 3.0, counselor ≥ 3.8, overall ≥ 3.0).

## Reproducing the paper

`aggregate_scores.py` reproduces the paper's **Table 2** numbers. For example,
the GPT-3.5 Turbo rows (mean score and pass-rate):

| Setting | Mode | Client | Supervisor | Counselor | Overall |
|---|---|---|---|---|---|
| Vanilla Prompt | `vanilla` | 2.68 (57%) | 2.60 (13%) | 3.43 (10%) | 2.90 (33%) |
| Psycho Prompt  | `psycho`  | 2.61 (50%) | 2.66 (20%) | 3.60 (22%) | 2.96 (39%) |

## Citation

```bibtex
@inproceedings{zhu2026psi,
  title     = {$\Psi$-Arena: Interactive assessment and optimization of LLM-based
               psychological counselors with tripartite feedback},
  author    = {Zhu, Shijing and Chen, Zhuang and Bi, Guanqun and Li, Binghang and
               Deng, Yaxi and Wan, Dazhen and Peng, Libiao and Xiao, Xiyao and
               Zhang, Rongsheng and Lv, Tangjie and others},
  booktitle = {Proceedings of the AAAI Conference on Artificial Intelligence},
  volume    = {40},
  number    = {3},
  pages     = {2272--2280},
  year      = {2026}
}
```
