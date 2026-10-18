# CRITERIA: cutoff-probe (A9)

Written on 2026-10-19 before the first model call. The battery had been taken
(`battery.json`), no model answers existed yet.

This is an English translation of the original registration, which was written
in Russian. Content is unchanged; the local run directory path is replaced by
the name of the environment variable that now sets it.

## Question

Does a model's knowledge cutoff, measured by facts, match what the vendor says
and what the model says about itself?

## Battery

`battery.py` takes from the npm and PyPI registries the time of first
publication of every stable release of 100 popular packages (50 and 50) and
keeps the first stable release of each minor line X.Y (usually X.Y.0; for
typescript it is 5.3.2, for django 5.0). `nestjs` and `airflow` have no
releases under those names on npm and PyPI and drop out. For each month from
2023-01 to 2026-10 up to 12 releases are taken, 1 per package, while packages
last. In total 552 real releases. Plus 200 versions that do not exist (the
next major and the next minor after the latest published), absence checked
against the registry's full version list on the day of the snapshot.

## Models

`claude-opus-5-5`, `claude-sonnet-5-5`, `claude-haiku-5-5`, `claude-fable-5-1`,
`claude-opus-5`, `claude-sonnet-5`, `claude-haiku-4-5`. CLI 2.1.302, an empty
directory (`CUTOFF_CLEANROOM`), `--tools ""`, empty MCP config, system prompt
replaced with "You are a helpful assistant.".

**Known confounder, not removable on a subscription:** the CLI puts the line
"Today's date is 2026-10-19" and the working directory into the context under
any flags (checked: `--system-prompt`, `--exclude-dynamic-system-prompt-sections`;
`--bare` does not log in on a subscription). It is the same for all models and
all questions, so comparisons between models and months are fair, but the self
report on the cutoff is taken with "today" known to the model. That is exactly
the condition the model works in inside Claude Code.

## Measures

1. **Knowledge curve (primary).** For each real release: "when was version V
   of package P first published?", answer as JSON `{known, month}`. Correct if
   `known=true` and the month is at most 1 away from the reference. By month of
   publication: share correct, share confidently wrong, share abstaining.
   2 repeats.
   **Measured cutoff:** the last month after which the rolling share correct
   (3 month window) falls below half of the model's mean share for 2024 and
   never rises above it again.
2. **False recognition.** The same question on versions that do not exist. The
   share of `known=true` is the baseline rate of invention and curve 1 cannot
   be read without it: a correct month can be guessed by interpolating between
   neighbouring versions.
3. **Frontier per package.** "What is the most recent stable version of P that
   you know?" The named version is matched against the registry and its
   publication date is the model's frontier for that package. Median over
   packages. 2 repeats.
4. **Self report.** 6 wordings of "what is your cutoff", 5 repeats per model.

## Expectation

- The measured cutoff of the 5.5 generation is earlier than the stated Jun 2026
  by at least 2 months: the last months before the cutoff are thin in training
  data (as in Dated Data).
- The self report is earlier than both the stated and the measured cutoff
  (models tend to name the date of the previous generation).
- haiku-4-5 knows beyond its reliable cutoff (Feb 2025), but not beyond its
  training cutoff (Jul 2025).

## What would refute the expectation

- The measured cutoff matches the stated one to the month for every model of
  the current generation: then the vendor date is honest and that gets written
  just as plainly.
- False recognition above 20%: then curve 1 measures a tendency to guess rather
  than knowledge and the primary measure is replaced by "confidently wrong"
  against "correct".
- The curve has no break and declines smoothly from 2023: then a "cutoff" as a
  point does not exist and that is the main result.

## Who has already done this

`PRIOR-WORK.md`. In short: a gap between effective and stated cutoff was shown
in Dated Data (arXiv:2403.12958) on open models via perplexity. Ours: closed
models, black box, package registries, 3 numbers side by side, 2 generations.
