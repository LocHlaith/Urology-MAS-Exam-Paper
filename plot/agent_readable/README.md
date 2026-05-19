# Agent-readable plot source package

Generated at: `2026-05-19T21:04:46`

This folder is a mechanical conversion of `plot/` for downstream plotting/statistics agents. It separates source text, worksheet data, visual assets, and provenance metadata.

## Contents

- `AGENT_BRIEF.md`: strict usage rules for plotting agents.
- `docs/*.md`: converted Word/PPT source text and worksheet summaries. Word/PPT files have an `Original Extract` section; workbook files are export metadata plus previews.
- `data/**/*.csv`: worksheet cell values exported from `.xlsx` files.
- `assets/ppt_media/**`: media extracted from the PPTX package.
- `assets/visual_reference_previews/**`: downscaled previews of `.tif` style references.
- `manifest.json`: source paths, SHA256 hashes, conversion methods, and output paths.
- `tools/convert_plot_sources.py`: reproducible converter.

## Source map

| Source | Type | Main outputs |
| --- | --- | --- |
| `plot/Figure 统一参数.docx` | `docx` | `plot/agent_readable/docs/01_figure_unified_parameters.md` |
| `plot/MAS_Statistical_Protocol_Package/Analysis_Statistical_Protocol.docx` | `docx` | `plot/agent_readable/docs/02_analysis_statistical_protocol.md` |
| `plot/MAS_Statistical_Protocol_Package/Figure_Table_Statistical_Views.docx` | `docx` | `plot/agent_readable/docs/03_figure_table_statistical_views.md` |
| `plot/PPT作图——3张.pptx` | `pptx` | `plot/agent_readable/docs/04_ppt_three_figures.md`, `plot/agent_readable/assets/ppt_media/ppt_three_figures/image1.png`, `plot/agent_readable/assets/ppt_media/ppt_three_figures/image10.png` ... |
| `plot/作图-1.0.docx` | `docx` | `plot/agent_readable/docs/05_plot_requirements_v1_0.md` |
| `plot/作图格式参考/Figure1.tif` | `tif` | `plot/agent_readable/assets/visual_reference_previews/Figure1_preview.png`, `plot/agent_readable/docs/visual_references.md` |
| `plot/作图格式参考/Figure2.tif` | `tif` | `plot/agent_readable/assets/visual_reference_previews/Figure2_preview.png`, `plot/agent_readable/docs/visual_references.md` |
| `plot/浙江大学邵逸夫医院泌尿外科出科考考试蓝图.docx` | `docx` | `plot/agent_readable/docs/06_exam_blueprint.md` |
| `plot/试卷作答情况 - 2.xlsx` | `xlsx` | `plot/agent_readable/docs/07_exam_responses_2_workbook.md`, `plot/agent_readable/data/exam_responses_2/01_m_a1.csv`, `plot/agent_readable/data/exam_responses_2/02_m_a2.csv` ... |
| `plot/试卷作答情况.xlsx` | `xlsx` | `plot/agent_readable/docs/08_exam_responses_workbook.md`, `plot/agent_readable/data/exam_responses/01_m.csv`, `plot/agent_readable/data/exam_responses/02_m.csv` ... |

## Regenerate

From the repository root:

```powershell
python plot\agent_readable\tools\convert_plot_sources.py
```
