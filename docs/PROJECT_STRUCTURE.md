# Project Structure

## Code

- `scripts/generation/`: convert raw question materials and call DeepSeek to generate `new_bank_*.json`.
- `scripts/evaluation/`: score and annotate generated banks with similarity, readability, QGEval, LLM, analysis, and test points.
- `scripts/plotting/`: generate statistics and paper-style exploratory figures from `data/banks/`.
- `scripts/reporting/`: export banks or report-draft JSON to collaborator-facing Word/TXT materials.
- `scripts/project_paths.py`: central paths. Update this file when the repository layout changes.

## Inputs

- `data/raw/datasets/`: raw source documents and text exports.
- `data/banks/bank_*.json`: original/manual bank files.
- `data/banks/new_bank_*.json`: generated MAS bank files and their accumulated evaluation fields.
- `prompts/generation/`: prompts for converting old/manual banks to generated banks.
- `prompts/analysis/`: prompts for generating item analysis fields.
- `prompts/evaluation/`: prompts for QGEval, LLM scoring, and test-point annotation.

## Outputs

- `outputs/bank_docx/`: Word exports of generated banks.
- `outputs/statistics/`: text/JSON statistics files.
- `outputs/report_drafts/`: temporary report materials for first-author review.
- `outputs/figures/`: generated figures.
- `outputs/logs/`: runtime logs, ignored by git.

## Plotting Requirements

`plot/` contains the first author's original plotting package. `plot/agent_readable/` is a mechanical conversion for agents; it does not replace the original files.
