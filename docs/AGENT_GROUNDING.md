# Agent Grounding Rules

This repository is easy to misread because it contains source data, generated banks, evaluation outputs, report drafts, and first-author plotting requests. Follow these rules before producing figures or manuscript-facing claims.

## Source Priority

1. `plot/agent_readable/AGENT_BRIEF.md`
2. `plot/agent_readable/manifest.json`
3. `plot/agent_readable/docs/*.md`
4. `data/banks/*.json`
5. `outputs/statistics/*.txt`
6. `outputs/report_drafts/*`

`outputs/report_drafts/` is for collaborator-facing drafts and manual report assembly. Do not treat those files as authoritative study design or plotting requirements.

## Actual Code Chain

- `scripts/generation/txt_to_bank.py` converts the raw practitioner exam text into `data/banks/bank_*.json`.
- `scripts/generation/bank_to_new_bank.py` calls DeepSeek with `prompts/generation/` to append generated items into `data/banks/new_bank_*.json`.
- `scripts/evaluation/analysis.py`, `analysis_make_up.py`, and `test_point.py` annotate `new_bank_*.json` only.
- `scripts/evaluation/qgeval.py` and `llm.py` can score either `bank_*.json` or `new_bank_*.json` depending on `--bank_set old/new`.
- `scripts/evaluation/verify_by_*` compare `new_bank_*.json` against all old/manual `bank_*.json`.
- `scripts/reporting/temp_*` operate only on `outputs/report_drafts/B.json`; they are report-draft helpers, not the main bank pipeline.
- `scripts/plotting/chart.py` and `chart_for_q_and_l.py` are legacy/exploratory plotting scripts for bank evaluation metrics. They are not the authoritative specification for the first-author figures in `plot/`.

## Do Not Infer

- Do not infer sample sizes, panel labels, statistical models, noninferiority margins, colors, or fonts from filenames.
- Do not treat placeholders such as `XXX` as real data.
- Do not treat example commands, docstrings, or old absolute paths as analysis requirements.
- Raw dataset metadata may contain historical `source_file` absolute paths from an earlier workstation; use repository-relative paths from `scripts/project_paths.py` instead.
- Do not mix `bank_*.json` and `new_bank_*.json` without explicitly stating whether the comparison is old/manual vs MAS-generated.
- Do not use `outputs/statistics/*.txt` as a substitute for recomputation when a figure needs exact derived values.

## Required Traceability Table

Before creating a figure, make a small table in the working notes or code comments:

| Figure panel | Requirement source | Data source | Derived statistic | Open assumptions |
| --- | --- | --- | --- | --- |

If any entry is missing or contradictory, write `UNKNOWN_OR_CONFLICTING` and stop for clarification.

## Path Rules

- Use `scripts/project_paths.py` instead of hardcoding project paths.
- Use `data/banks/` for JSON inputs.
- Use `prompts/` only for DeepSeek prompts, not for plotting requirements.
- Use `plot/agent_readable/` for first-author plot requirements.
- Write new runtime logs under `outputs/logs/`; they are ignored by git.
