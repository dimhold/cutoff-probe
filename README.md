# Where does a model's knowledge of package releases actually stop?

Every Claude model ships with a stated knowledge cutoff. This repository checks
that date against fact: 552 releases from the npm and PyPI registries, 12 per
month from 2023-01 to 2026-10, each with a publication time taken from the
registry itself. 7 models were asked which of those versions they know and in
which month each came out, with "do not know" allowed. 200 versions that do not
exist were mixed into the same batches to measure how often a model claims to
know something that is not there.

## Others first

The gap between an effective and a stated cutoff is not new. **Dated Data**
(Cheng et al., 2024, [arXiv:2403.12958](https://arxiv.org/abs/2403.12958))
named the effective cutoff and showed it diverges from the stated one, on open
models, through perplexity over dated document versions. **Beyond the Reported
Cutoff** ([arXiv:2504.00042](https://arxiv.org/abs/2504.00042)) did it as a
black box on company financials at yearly resolution. Matt Mazur's
**llm-knowledge-cutoff** (2023) drew a monthly curve for 1 model from celebrity
deaths. What this study adds is the same question asked of closed models
without logits, on a subject programmers depend on daily, at monthly
resolution, with 4 numbers side by side (vendor date, measured curve, frontier
per package, self report) and 2 generations of 1 lab on 1 battery. Full search
record: [PRIOR-WORK.md](PRIOR-WORK.md).

## What came out

| model | stated | measured | 95% bootstrap | frontier median | self report in the CLI |
|---|---|---|---|---|---|
| claude-opus-5-5 | 2026-06 | 2025-09 | 2025-08..2025-10 | 2025-08 | 2026-06 in 18 of 18 |
| claude-sonnet-5-5 | 2026-06 | 2025-12 | 2025-12..2026-01 | 2025-10 | 2026-06 in 18 of 19 |
| claude-haiku-5-5 | 2026-06 | 2025-09 | 2025-08..2025-10 | 2025-09 | 2026-06 in 12 of 13 |
| claude-fable-5-1 | 2026-06 | 2025-11 | 2025-10..2025-11 | 2025-09 | 2026-06 in 15 of 20 |
| claude-opus-5 | 2026-05 | 2025-10 | 2025-09..2025-10 | 2025-10 | 2026-05 in 21 of 22 |
| claude-sonnet-5 | 2026-01 | 2025-01 | 2024-12..2025-02 | 2025-02 | 2026-01 in 18 of 22 |
| claude-haiku-4-5 | 2025-02 | rule not applicable | | 2024-02 | 2025-02 in 16 of 16 |

- The 5.5 generation stops knowing releases 6 to 9 months before its stated
  Jun 2026. From 2026-03 to 2026-09 no model has a single correct answer.
- The cutoff is a slope rather than a point: 4 to 9 months from the last month
  at 90% of the 2024 level to the first at 10%, for the 6 models where the rule
  applies.
- False recognition of versions that do not exist: 0 of 400 for opus-5-5 and
  sonnet-5-5, at most 20 of 392 (5.1%) for haiku-4-5. The curve measures
  knowledge, not willingness to guess.
- Asked about their own cutoff, the models repeat the vendor date in 118 of 130
  answers. The CLI puts "Assistant knowledge cutoff is June 2026" into the
  system prompt (captured for haiku-5-5 in `context-check.json`). Asked to set
  that line aside, opus-5-5 and opus-5 both answer 2025-01 in 5 of 5, 8 and 9
  months earlier than their own curves.
- The newer opus-5-5 (stated Jun 2026) does not know further than opus-5
  (stated May 2026): 2025-09 against 2025-10, intervals overlapping.

Verdicts on each preregistered expectation and every limitation:
[RESULTS.md](RESULTS.md). All tables: [stats.md](stats.md).

## Method

- **Registration first.** [CRITERIA.md](CRITERIA.md) and
  [PRIOR-WORK.md](PRIOR-WORK.md) were written on 2026-10-19 before the first
  model call, including the cutoff rule and what would refute each expectation.
- **Battery from the registries.** [`battery.py`](battery.py) takes the first
  stable release of every minor line of 100 popular packages (50 npm, 50 PyPI;
  `nestjs` and `airflow` have no releases under those names, which leaves 98)
  and keeps up to 12 per month, at most 1 per package before any package gets a
  second. Nonexistent controls are the next major and the next minor after the
  latest published version, checked against the full version list on the
  snapshot day.
- **Measured cutoff.** Correct means `known=true` and a month at most 1 away
  from the registry. The cutoff is the last month after which the 3 month
  rolling share correct falls below half of the model's 2024 mean and never
  recovers. Bootstrap: 2000 resamples within each month.
- **Isolation.** Claude Code CLI 2.1.302 on a subscription, `--tools ""`,
  `--strict-mcp-config` with an empty MCP config, system prompt replaced with
  "You are a helpful assistant.", run from an empty directory whose parents are
  checked for `CLAUDE.md`, `.claude`, `AGENTS.md` and `.cursorrules`. The CLI
  still adds today's date and a cutoff line; that is recorded, not removed.
- **Batches of 20.** Real and nonexistent versions are shuffled together and a
  batch is identical for every model. The model in each response envelope was
  checked against the requested one: 1075 of 1075 matched.
- **Arms beyond the registration.** `guess0` (a month estimate is required,
  "remember" is a separate flag) and `self2` (asked to set the cutoff line
  aside) were added during the run and are reported as such.

## Reproduce

Python 3.8 or later, standard library only.

The numbers, offline, from the committed journal:

    python analyze.py     # part 1 of stats.md, writes out/stats.json
    python intervals.py   # part 2 of stats.md, seeded bootstrap

Both outputs are byte for byte identical to the tables in `stats.md` apart
from the 2 file headers. Failed journal rows (`"ok": false`) are skipped by
both scripts.

The battery, from the live registries (gives today's snapshot, not the one of
2026-10-19, which is the committed `battery.json` and `data/releases.json`):

    python battery.py

The model calls (needs the `claude` CLI logged in; resumes from the journal and
skips cells already taken):

    CUTOFF_CLEANROOM=/tmp/cleanroom-cutoff-probe python run.py self,batch0,front0,self2,guess0,front1,batch1

The phase order above is the order of the actual run. Every prompt that
`run.py` builds today is identical to the prompt stored in the journal for the
same key (checked for all 1075 successful rows).

## Files

| path | what it is |
|---|---|
| `CRITERIA.md` | the registration, written before the run |
| `PRIOR-WORK.md` | who has done this already and what is left |
| `battery.py` | builds the battery from the registries |
| `battery.json` | the battery: 552 real releases, 200 nonexistent versions, per package metadata |
| `data/releases.json` | every version of every package with its first publication time, the reference for the frontier |
| `run.py` | the harness |
| `analyze.py` | the CRITERIA measures |
| `intervals.py` | bootstrap, Wilson intervals, monthly slices |
| `context-check.json` | what the CLI put in front of the prompt, quoted by 2 models |
| `out/calls.jsonl` | the journal: every call with prompt, reply, usage and cost, including the 168 failed rows |
| `out/stats.json` | machine readable output of `analyze.py` |
| `out/*.log` | harness console logs |
| `prior/` | vendor pages with the stated cutoffs, raw Semantic Scholar responses |
| `RESULTS.md` | verdicts and limitations |
| `stats.md` | all tables |

Not included: `data/registry/`, the raw registry responses (437 MB, the
largest single file 68 MB). `battery.py` refetches them. The derived
`data/releases.json` holds everything the analysis reads from them.

## Redaction

The files were produced on a personal machine and were scrubbed before
publication. Every change is listed here; nothing else was edited.

- `context-check.json`: the account email quoted back by opus-5-5 is replaced
  with `[REDACTED]` (haiku-5-5 had redacted it in its own reply) and the run
  directory path with `<CUTOFF_CLEANROOM>`.
- `out/*.log`: the local time zone in 9 rate limit messages is replaced with
  `<local tz>` and 2 restart markers written with a local month name are
  rewritten as ISO dates.
- Code: hard coded local paths became environment variables
  (`CUTOFF_CLEANROOM`, `CUTOFF_PROMPTS`, `CUTOFF_QUOTA_GLOB`) with temp
  directory defaults; comments, docstrings and table headings were translated
  from Russian; `run.py` gained the `self` phase branch, rebuilt from the
  journal (it had been removed from the harness after that phase ran; its keys
  and prompts match the 130 stored rows exactly).
- `prior/`: the full HTML snapshot of the models overview page is replaced by
  a transcribed excerpt of the rows used.
- `out/calls.jsonl` is unchanged. It holds no session ids, paths or account
  data: the harness stored only the reply, usage, model usage and cost from
  each CLI envelope.

Timestamps in the journal and the logs are local machine time, GMT+3.

## Licence and citation

Code under MIT, data and text under CC BY 4.0, with third party registry
metadata and vendor pages excepted: [LICENSE](LICENSE). How to cite:
[CITATION.cff](CITATION.cff).
