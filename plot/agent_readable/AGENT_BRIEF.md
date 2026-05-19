# Agent plotting brief

## Non-negotiable rules

1. Use source wording from Word/PPT files in `docs/*` as quoted requirements, not as paraphrased interpretation.
2. Use `manifest.json` to verify which converted file came from which original file.
3. Treat worksheet CSV files as raw/cached cell exports; formulas are not evaluated and display formatting is not applied. Do not invent variable meanings beyond the workbook summaries and source documents.
4. Treat TIF previews and PPT media as visual references only unless a source text explicitly assigns them a figure requirement.
5. If a panel label, sample size, statistical model, noninferiority margin, color, font, or data source is missing or contradictory, mark it as `UNKNOWN_OR_CONFLICTING` and ask for clarification.
6. Keep `Figure 统一参数.docx`/`docs/*figure_unified_parameters.md` as the global formatting source unless a figure-specific requirement explicitly overrides it.
7. Do not treat examples, placeholder `XXX`, or fictional protocol values as real locked data.

## Recommended plotting workflow

1. Read `manifest.json` and this brief first.
2. Read `docs/*figure_unified_parameters.md` for global visual settings.
3. Read `docs/*plot_requirements_v1_0.md`, then the statistical protocol documents, before designing panels.
4. Load CSV files from `data/` with explicit filenames and sheet names. Keep a record of source workbook and sheet for every derived statistic.
5. Before producing a figure, create a small panel-to-source table: panel, source file, quoted requirement, data file/sheet, unresolved assumptions.
6. In code comments or figure metadata, cite source paths rather than relying on memory.
