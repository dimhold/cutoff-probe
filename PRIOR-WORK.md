# Who has already done this: cutoff-probe (A9)

Taken on 2026-10-19 before the first model call. Translated from the Russian
original, content unchanged.

Sources: Semantic Scholar through a rate limited client (raw responses in
`prior/s2.json`), the arXiv API over https (after 5 requests it returned
nothing for everything, including a paper known to exist, so this was
throttling rather than absence), DuckDuckGo, the GitHub API. Brave returned a
captcha.

## The niche "effective cutoff differs from the stated one" is taken

- **Dated Data: Tracing Knowledge Cutoffs in Large Language Models**
  (Cheng et al., 2024, [arXiv:2403.12958](https://arxiv.org/abs/2403.12958),
  81 citations). Introduces the *effective cutoff*, distinct from the stated
  one and shows that the two diverge. The method is perplexity over versions
  of Wikipedia and CommonCrawl documents, so it **needs logits and open
  weights**. It traces the gap to the data: old content in new CommonCrawl
  dumps and deduplication.
- **Beyond the Reported Cutoff: Where LLMs Fall Short on Financial Knowledge**
  ([arXiv:2504.00042](https://arxiv.org/abs/2504.00042)). 197 thousand
  questions about the finances of US companies by year, compared with fact.
  Black box like ours, but the subject is financial and the resolution is a
  year.
- **mattm/llm-knowledge-cutoff** (2023, Matt Mazur's blog): a knowledge curve
  of GPT-4 Turbo by celebrity deaths per month. Exactly our method, "share
  correct by month", on 1 model and a different subject.

## Neighbouring niches

- **Correct Code, Vulnerable Dependencies** (PinTrace,
  [arXiv:2605.06279](https://arxiv.org/abs/2605.06279)): which library versions
  models write into code; 10 models converge on the same small set of versions.
  This is a consequence of the cutoff in code, but they do not measure the
  cutoff.
- **Simulated Ignorance Fails** ([arXiv:2601.13717](https://arxiv.org/abs/2601.13717)),
  **Can LLMs Be Constrained to the Past?** ([arXiv:2606.05804](https://arxiv.org/abs/2606.05804)),
  **Can Prompts Rewind Time** ([arXiv:2510.02340](https://arxiv.org/abs/2510.02340)):
  about making a model forget what comes after a date. A different question.
- **Deprecated API usage** ([arXiv:2406.09834](https://arxiv.org/abs/2406.09834)),
  **RustEvo2** ([arXiv:2503.16922](https://arxiv.org/abs/2503.16922)),
  **ReCode** ([arXiv:2506.20495](https://arxiv.org/abs/2506.20495)):
  outdated APIs in model code. Not about the date.
- **Soju06/knowpatch** (GitHub, March 2026): a tool that feeds an agent
  corrections for outdated versions. A tool, not a measurement.
- **Tables of stated cutoffs** (HaoooWang/llm-knowledge-cutoff-dates, 502
  stars; stackprism.ai/cutoff; knowledge-cutoff.date): restatements of vendor
  dates, without checking.

## Vendor stated cutoffs (page snapshots of 2026-10-19, `prior/`)

| model | reliable knowledge cutoff | training data cutoff |
|---|---|---|
| claude-opus-5-5, claude-sonnet-5-5, claude-haiku-5-5, claude-fable-5-1 | Jun 2026 | Jun 2026 |
| claude-opus-5 | May 2026 | May 2026 |
| claude-sonnet-5 | Jan 2026 | Jan 2026 |
| claude-haiku-4-5 | Feb 2025 | Jul 2025 |

## What remains ours

Searched: Semantic Scholar (9 queries in `prior/s2.json`), DuckDuckGo for
"knowledge cutoff npm package versions" and "measure claude knowledge cutoff
software release", GitHub. **Not found:** a measurement of the effective cutoff
of Anthropic's closed models through package registries, at monthly resolution,
comparing 3 numbers at once: what the vendor says, what the model says about
itself and where the curve actually falls. Not found either: a comparison of 2
generations from 1 lab on 1 battery.

The framing is therefore **not "we discovered that the cutoff is wrong"**
(that is Dated Data, 2024), but a check of their conclusion on closed models
without logits, on a subject a programmer depends on every day: which package
versions the model knows.

## Added at review on 2026-10-21, after the counting

Everything above was written before the first call and is left as it was.
This section was added after the results were counted, when a reviewer
pointed to studies the search above had missed. Each was checked on
arxiv.org/abs over https (the export API answered HTTP 429 that day, including
for arXiv:2403.12958, which exists). A search over arxiv.org/search on the same
day ("knowledge cutoff", "effective cutoff", "training cutoff" benchmark,
"cutoff date" language models, knowledge cutoff package versions) found
nothing closer. The arXiv API had been throttled on 2026-10-19 after 5
requests, so arXiv was in effect not searched before the run.

**The black box niche is taken too.**

- **LLMLagBench: Identifying Temporal Training Boundaries in Large Language
  Models** (Pęzik et al., 2025,
  [arXiv:2511.12116](https://arxiv.org/abs/2511.12116)). A freshness
  benchmark from questions about news events, with changepoint detection, on
  35 models. Its Table 3 gives for each model the cutoff according to the
  developer, according to the model itself and according to the benchmark:
  the same 3 numbers as here. The Claude rows are Claude 3 Haiku, Claude 3
  Opus, Claude 3.5 Sonnet and Claude Sonnet 4. For Claude Sonnet 4 it finds 2
  changepoints (2023-02 and 2024-12) against a provider date of 2025-01 and a
  self reported 2024-04. For all 4 Claude models the self reported date is
  earlier than the provider's.
- **HindsightBench: A Black-Box Behavioral Audit Protocol for Parametric
  Hindsight in Time-Indexed LLM Decision Tasks** (Jia, 2026,
  [arXiv:2607.18867](https://arxiv.org/abs/2607.18867)). Preregistered, no
  logprobs, a macroeconomic panel, 15 models from 7 vendors. Its behaviorally
  effective cutoff is the last month with an outcome recall propensity (LAP)
  above 0.1, defined for 12 recall capable models. Effective cutoffs span 22
  months; where a vendor date is published (7 of the 12) 5 are early, by up to
  8 months, 1 is exact and 1 is 1 month late. 2 models overlap with this
  panel: Claude Sonnet 5 measured 2025-10 (here: 2025-01 by the registered
  rule; last month with more than 10% `known=true`, the closest analog of
  LAP, 2025-06; the same month by share correct) and Claude Haiku 4.5 measured
  2024-10 (here: rule not applicable; last month with more than 10%
  `known=true` 2024-08; estimate arm hits up to 2025-02). The 10% comparison
  was chosen after the data.
- **Large Language Models Lack Temporal Awareness of Medical Knowledge**
  (TempoMed-Bench, Guan et al., 2026,
  [arXiv:2605.13045](https://arxiv.org/abs/2605.13045)). On medical guidelines
  the accuracy falls as a gradual linear decline rather than a sharp edge at
  the cutoff. That comes before the slope finding here.
- **Set the Clock: Temporal Alignment of Pretrained Language Models** (Zhao
  et al., 2024, [arXiv:2402.16797](https://arxiv.org/abs/2402.16797)).
  Pretrained models mostly answer from knowledge older than their pretraining
  cutoff. It was among the Semantic Scholar responses in `prior/s2.json` and
  was not read at the time.
- **LibEvoBench: Probing Temporal Knowledge Stratification in Code Generation
  Models** (Cipollone et al., 2026,
  [arXiv:2606.25402](https://arxiv.org/abs/2606.25402)). Whether models keep
  the APIs of several versions of Python libraries apart. A neighbouring niche,
  not the date.
- **CutoffBench** (Spohn, 2025), cited by HindsightBench as a deployed cutoff
  estimator at cutoffbench.com. On 2026-10-21 that domain was for sale and no
  repository was found, so it could not be checked.

**What is left after them.** Not "3 numbers side by side" (LLMLagBench has
them) and not "black box effective cutoff before the vendor date" (LLMLagBench
and HindsightBench). Left: the Claude 5.5 generation, which none of them
covers, with the previous generation of the same lab on the same battery;
package releases dated by the registries at monthly resolution; a control of
200 nonexistent versions in the same batches; and the self report as the
Claude Code CLI delivers it, with a cutoff line in its system prompt. There
the 5.5 generation gives the vendor date in 63 of 70 answers, where
LLMLagBench saw earlier Claude models name dates earlier than the vendor's.
