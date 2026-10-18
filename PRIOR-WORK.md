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
