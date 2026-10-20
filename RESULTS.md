# RESULTS: cutoff-probe (A9)

The niche is taken, see `PRIOR-WORK.md` and the section "What is ours" below:
any text about this result names Dated Data first.

Counted on 2026-10-20 with `analyze.py` plus intervals and monthly slices
(`intervals.py`). All tables are in `stats.md`; this file holds only what the
verdicts need. Translated from the Russian original, numbers unchanged.

## What was measured

The question from `CRITERIA.md`: does the knowledge cutoff measured by facts
match the vendor date and what the model says about itself?

- **Battery** (`battery.json`, registry snapshot of 2026-10-19): 552 real
  releases from npm and PyPI, 12 for each month from 2023-01 to 2026-10, the
  first stable release of a minor line; plus 200 versions that do not exist.
- **Panel:** `claude-opus-5-5`, `claude-sonnet-5-5`, `claude-haiku-5-5`,
  `claude-fable-5-1` (vendor: Jun 2026), `claude-opus-5` (May 2026),
  `claude-sonnet-5` (Jan 2026), `claude-haiku-4-5` (reliable Feb 2025,
  training Jul 2025). CLI 2.1.302, empty directory, no tools and no MCP. The
  answering model matched the requested one in all 1075 successful calls.
- **Measures:** knowledge curve (batches of 20 questions "do you know this
  version and its month", "do not know" is allowed), false recognition on
  versions that do not exist, frontier per package, self report. Correct means
  `known=true` and the month at most 1 away from the reference.

## What was taken

| phase | what | successful calls |
|---|---|---|
| batch0, batch1 | knowledge curve and false recognition, 2 repeats | 266 + 266 |
| front0, front1 | frontier, 2 repeats | 56 + 56 |
| self | self report, 6 wordings | 130 of 210 |
| self2 | self report asked to set the cutoff line aside | 35 of 35 |
| guess0 | arm with a required month estimate, 1 repeat | 266 |

Per model that is 752 questions per repeat, so 1104 answers on real releases
and 400 on nonexistent ones over 2 repeats. 3 batches of 532 were not fully
parsed (1 for sonnet-5, 2 for haiku-4-5).

The CRITERIA plan (2 repeats) is complete: by `run.jobs_for` and
`run.done_keys`, batch0, batch1, front0, front1, self2 and guess0 have no jobs
left. Phases batch2 and front2 were in the default list of the original
`run.py`, but are not in the CRITERIA plan and were not run.

**168 failed journal rows are excluded:** 163 with
`OAuth session expired and could not be refreshed` (night of 2026-10-19,
06:18 to 13:42; 153 in guess0 and 10 in self2) and 5 with
`no stdin data received in 3s` in guess0. All these cells were later retaken
successfully; there are no duplicates among successful keys.

The self phase stopped at 130 of 210 calls when the run moved to batches (13
to 22 answers per model). It is not a random subsample in the strict sense.
The number of answers differs by model.

After batch1 the harness hung on 2026-10-20: process alive, no calls after
00:50. This does not affect the data; everything planned was already in the
journal.

## Main finding

**Current generation models know package releases 6 to 9 months earlier than
the stated date and state the stated date about themselves because the CLI
hands it to them.** The vendor gives Jun 2026 for all 4 models of 5.5; the
curve falls below half of the 2024 level in 2025-09 (opus-5-5, haiku-5-5),
2025-11 (fable-5-1) and 2025-12 (sonnet-5-5). From 2026-03 to 2026-09 none of
the 7 models has a single correct answer; the only exception after that is 4%
for sonnet-5 in 2026Q4.

| model | vendor | measured | 95% bootstrap | earlier than vendor | frontier median / p90 | self report in CLI | self report without the line |
|---|---|---|---|---|---|---|---|
| opus-5-5 | 2026-06 | 2025-09 | 2025-08..2025-10 | 9 mo | 2025-08 / 2025-10 | 2026-06 x18 | 2025-01 x5 |
| sonnet-5-5 | 2026-06 | 2025-12 | 2025-12..2026-01 | 6 mo | 2025-10 / 2025-12 | 2026-06 x18 of 19 | 2025-05..2025-09 |
| haiku-5-5 | 2026-06 | 2025-09 | 2025-08..2025-10 | 9 mo | 2025-09 / 2025-10 | 2026-06 x12 of 13 | 2025-01..2025-05 |
| fable-5-1 | 2026-06 | 2025-11 | 2025-10..2025-11 | 7 mo | 2025-09 / 2025-11 | 2026-06 x15 of 20 | 2025-01..2025-05 |
| opus-5 | 2026-05 | 2025-10 | 2025-09..2025-10 | 7 mo | 2025-10 / 2026-02 | 2026-05 x21 of 22 | 2025-01 x5 |
| sonnet-5 | 2026-01 | 2025-01 | 2024-12..2025-02 | 12 mo | 2025-02 / 2025-09 | 2026-01 x18 of 22 | 2025-02, 2025-04 |
| haiku-4-5 | 2025-02 | (rule not applicable) | 2024-04..2025-01 | | 2024-02 / 2024-07 | 2025-02 x16 | 2024-04 x3, 2025-02 x2 |

The measured cutoff is stable between repeats: repeat 0 and repeat 1 differ by
at most 2 months (opus-5-5: 2025-10 and 2025-08) and coincide for 4 models.
The frontier per package independently gives the same picture: the median for
the 5.5 generation lies in 2025-08..2025-10.

The new generation does not know further than the old one: opus-5-5 (vendor
Jun 2026) measures at 2025-09, opus-5 (vendor May 2026) at 2025-10 and the
intervals overlap.

## Verdicts on the expectations

**1. The measured cutoff of 5.5 is earlier than Jun 2026 by at least 2 months.
Confirmed, with margin.** The gap is 6 to 9 months; the upper bootstrap bound
for all 4 is no later than 2026-01, so the gap is at least 5 months. Monthly
for opus-5-5 the share correct is 22/24 in 2025-01 and 17/24 in 2025-06, then
11/24 in 2025-08, 3/24 in 2025-12, 0/24 from 2026-02. Refutation 1 (match with
the vendor to the month for every current generation model) did not fire for
any model.

**2. The self report is earlier than both the stated and the measured cutoff.
Depends on the condition; refuted in the working condition.** On the 6 ordinary
wordings the models name exactly the vendor date in 118 answers of 130, that
is later than measured, not earlier. The reason is visible in
`context-check.json`: the CLI puts the line "Assistant knowledge cutoff is June
2026" into the system prompt (captured for haiku-5-5). The model repeats it.
The line was not captured for the other models, but each names exactly its own
vendor date (opus-5 2026-05, sonnet-5 2026-01, haiku-4-5 2025-02), which is
consistent with such a line. CRITERIA knew only about the line with today's
date; the cutoff line was found afterwards.
When the model is asked to set this line aside (self2, 5 answers per model),
the expectation holds for 5 models of the 6 where the measurement applies: all
25 answers of opus-5-5, sonnet-5-5, haiku-5-5, fable-5-1 and opus-5 are earlier
than both the vendor date and the measured cutoff. opus-5-5 and opus-5 both
answer 2025-01 5 times of 5, 8 to 9 months earlier than their own curve.
sonnet-5 names 2025-02 and 2025-04, earlier than the vendor but later than its
measured 2025-01. The second half of the expectation ("models name the date of
the previous generation") cannot be checked by this measurement: 2025-01 does
not match any vendor date in the table in `PRIOR-WORK.md`.

**3. haiku-4-5 knows beyond its reliable cutoff (Feb 2025), but not beyond its
training cutoff (Jul 2025). The first half was not confirmed.** In the primary
arm haiku-4-5 almost always answers "do not know": its 2024 baseline is 4.3%
(12/275 correct), so the CRITERIA break rule means nothing for it (point
2024-12, bootstrap 2024-04..2025-01). It has to be read from the arm with a
required estimate (1 repeat, not in CRITERIA):

| window | with estimate: month hit | 95% CI |
|---|---|---|
| 2024-01..2024-12 | 50/144 = 34.7% | 27.4..42.8% |
| 2025-01..2025-02 | 9/24 = 37.5% | 21.2..57.3% |
| 2025-03..2025-07 | 2/60 = 3.3% | 0.9..11.4% |
| 2025-08..2026-10 | 5/180 = 2.8% | 1.2..6.3% |

Knowledge holds to 2025-02 and then falls to the level of months the model
certainly never saw. The window between the reliable and the training cutoff
is indistinguishable from the period after the training cutoff. The frontier
says the same: maximum 2025-02, p90 2024-07. The second half of the
expectation (not beyond Jul 2025) holds, but trivially. Sensitivity for
haiku-4-5 is low, so the conclusion reads "no knowledge is visible beyond Feb
2025", not "there is none".

**Refutation 2: false recognition above 20%. Did not fire.** Share of
`known=true` on versions that do not exist: 0/400 for opus-5-5 and sonnet-5-5,
3/400 for haiku-5-5 (0.8%, CI 0.3..2.2%), 1/400 for fable-5-1, 4/400 for
opus-5, 2/394 for sonnet-5, at most 20/392 for haiku-4-5 (5.1%, CI 3.3..7.7%).
The curve measures knowledge; the primary measure is not replaced. Confidently
wrong answers on real releases for opus-5-5, sonnet-5-5, fable-5-1 and opus-5
run from 0 to 1% by quarter; for haiku-5-5 10 to 32% by quarter up to 2025Q4,
so haiku-5-5 is the only model of the new generation that confidently confuses
months.

**Refutation 3: a smooth decline from 2023 without a break. Did not fire, but
the break is a slope, not a point.** For opus-5-5, sonnet-5-5, fable-5-1 and
opus-5 the share correct sits on a plateau of 81 to 100% by quarter from 2023Q1
to 2025Q2 and then falls; haiku-5-5 has a lower plateau (65 to 89%), sonnet-5
starts declining earlier, from 2025Q1. From the last month where the rolling
window is at least 90% of the baseline to the first where it is at most 10%
there are 4 months for sonnet-5-5, 6 for opus-5, 7 for fable-5-1, 8 for
haiku-5-5 and 9 for opus-5-5 and sonnet-5. The cutoff exists as a band of half
a year. The point from the CRITERIA rule is the middle of the slope.

## What else is visible

- **The arm with a required estimate does not measure knowledge.** Among "do
  not remember" answers on releases from 2026-04..2026-10, which the models
  never saw, the month hits in 43 to 63% for the 4 models of 5.5 and opus-5
  (17% for sonnet-5, 4% for haiku-4-5; the Russian original said "the 5 and
  5.5 models", which overstated it). Estimates
  cluster around the date in the context: for opus-5-5 on 48 releases from
  2026-07..2026-10 the most frequent estimate is 2026-08 (15 times). That is
  the anchor "Today's date is 2026-10-19", not memory. So the primary arm
  remains the one where "do not know" is allowed, as CRITERIA said. The same
  arm, by share "remember and hit", gives cutoffs 1 to 2 months earlier than
  the primary arm (2025-07..2025-10 for the 5.5 generation); no contradiction.
- **sonnet-5 diverges from the vendor most of all:** stated Jan 2026, measured
  2025-01, frontier median 2025-02. Its curve starts to sag already in 2024
  (2024 baseline 0.719 against 0.941 to 1.000 for opus-5-5, sonnet-5-5,
  fable-5-1 and opus-5, and 0.812 for haiku-5-5).
- The frontier maximum is unreliable: for opus-5 it is 2026-08 with 13
  nonexistent versions of 200, so the table shows p90 rather than the maximum.

## Limitations

- **The cutoff line in the system prompt.** The CLI on a subscription adds both
  today's date and the line "Assistant knowledge cutoff is ...". The self report
  in the working condition therefore measures repetition of the line and self2
  is 1 wording with 5 repeats. In the primary arm the line is the same for all
  questions and, judging by false recognition of 0 to 1%, does not push toward
  invention, but its effect on the share of "known" is not measured.
- **Narrow subject:** months of minor releases of 98 popular packages (50 and
  50 minus `nestjs` and `airflow`). This is the cutoff for package versions, not
  for knowledge in general. Popular packages are probably better represented in
  training data than average.
- **Batches of 20.** Neighbouring versions of 1 package in a batch can suggest
  the month by interpolation. The 1 month tolerance makes this easier. False
  recognition was taken in the same condition and is low, but it does not rule
  out interpolating a month from neighbours.
- 2 repeats for the primary arm and the frontier, 1 for the estimate arm; 12
  releases per month per model per repeat, 24 answers per cell.
- The self phase was taken at 130 of 210, 13 to 22 answers per model.
- For haiku-4-5 the break rule does not apply because of the 4.3% baseline;
  the verdict on it rests on an arm that was not in CRITERIA.
- Subscription through the CLI, not the API: temperature and other parameters
  are not under control. Cost by the CLI journal is $36.96 for 1075 calls
  (nominal, on a subscription).

## What is ours

Others first (`PRIOR-WORK.md`). The gap between effective and stated cutoff
was shown in **Dated Data** (Cheng et al., 2024,
[arXiv:2403.12958](https://arxiv.org/abs/2403.12958)) on open models via
perplexity; in **Beyond the Reported Cutoff**
([arXiv:2504.00042](https://arxiv.org/abs/2504.00042)) as a black box on
financial facts at yearly resolution; a monthly curve on celebrity deaths for 1
model is in **mattm/llm-knowledge-cutoff** (2023).

Ours on top of that: Anthropic's closed models without logits, a subject a
programmer needs every day (npm and PyPI package versions), monthly resolution,
4 numbers side by side (vendor, curve, frontier, self report) and 2 generations
from 1 lab on 1 battery. Searched Semantic Scholar, DuckDuckGo and GitHub (the
queries are in `PRIOR-WORK.md`) and did not find this combination. Separately
ours: inside Claude Code the model states its cutoff on the client's word. When
that hint is removed, the 5 and 5.5 models other than sonnet-5 name a month 3
to 10 months earlier than their own knowledge curve (25 answers of 25 earlier;
the Russian original said "half a year or more", which holds for 22 of those 25
answers, so the range is given here instead).
