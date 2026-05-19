# Agent 可读绘图资料包

生成时间：`2026-05-19T21:04:46`

本目录是 `plot/` 的机械转换版本，供后续绘图、统计和补充实验 agent 阅读。它把原始文本、工作簿数据、视觉素材和来源元数据分开放置。

## 内容

- `AGENT_BRIEF.md`：绘图 agent 必须遵守的使用规则。
- `docs/*.md`：由 Word/PPT 转换出的原文内容和工作簿摘要。Word/PPT 文件包含“原始摘录”部分；工作簿文件包含导出元数据和预览。
- `data/**/*.csv`：从 `.xlsx` 工作簿导出的单元格值。它们是原始/缓存导出，不是图片交付格式。
- `assets/ppt_media/**`：从 PPTX 包中提取的媒体。
- `assets/visual_reference_previews/**`：`.tif` 风格参考图的降采样预览。
- `manifest.json`：来源路径、SHA256 哈希、转换方法和输出路径。
- `tools/convert_plot_sources.py`：可复现转换脚本。

特别注意：原始 Word 资料中的 `*.csv` 表名属于统计设计或数据字典措辞，不等于当前仓库已经存在这些文件，也不等于第一作者要求图片交付为 CSV。第一作者要求的图片交付格式是可编辑 PDF。

作答工作簿中 M/P 的来源映射已确认：M卷 = MAS，P卷 = 人类。结合 A/B 顺序，Form A = P卷 -> M卷，Form B = M卷 -> P卷。

## 来源映射

| 原始文件 | 类型 | 主要输出 |
| --- | --- | --- |
| `plot/Figure 统一参数.docx` | `docx` | `plot/agent_readable/docs/01_figure_unified_parameters.md` |
| `plot/MAS_Statistical_Protocol_Package/Analysis_Statistical_Protocol.docx` | `docx` | `plot/agent_readable/docs/02_analysis_statistical_protocol.md` |
| `plot/MAS_Statistical_Protocol_Package/Figure_Table_Statistical_Views.docx` | `docx` | `plot/agent_readable/docs/03_figure_table_statistical_views.md` |
| `plot/PPT作图——3张.pptx` | `pptx` | `plot/agent_readable/docs/04_ppt_three_figures.md`、`plot/agent_readable/assets/ppt_media/ppt_three_figures/image1.png`、`plot/agent_readable/assets/ppt_media/ppt_three_figures/image10.png` 等 |
| `plot/作图-1.0.docx` | `docx` | `plot/agent_readable/docs/05_plot_requirements_v1_0.md` |
| `plot/作图格式参考/Figure1.tif` | `tif` | `plot/agent_readable/assets/visual_reference_previews/Figure1_preview.png`、`plot/agent_readable/docs/visual_references.md` |
| `plot/作图格式参考/Figure2.tif` | `tif` | `plot/agent_readable/assets/visual_reference_previews/Figure2_preview.png`、`plot/agent_readable/docs/visual_references.md` |
| `plot/浙江大学邵逸夫医院泌尿外科出科考考试蓝图.docx` | `docx` | `plot/agent_readable/docs/06_exam_blueprint.md` |
| `plot/试卷作答情况 - 2.xlsx` | `xlsx` | `plot/agent_readable/docs/07_exam_responses_2_workbook.md`、`plot/agent_readable/data/exam_responses_2/01_m_a1.csv`、`plot/agent_readable/data/exam_responses_2/02_m_a2.csv` 等 |
| `plot/试卷作答情况.xlsx` | `xlsx` | `plot/agent_readable/docs/08_exam_responses_workbook.md`、`plot/agent_readable/data/exam_responses/01_m.csv`、`plot/agent_readable/data/exam_responses/02_m.csv` 等 |

## 重新生成

从仓库根目录运行：

```powershell
python plot\agent_readable\tools\convert_plot_sources.py
```

注意：重新运行转换脚本可能覆盖本目录下的转换说明文件。若需要长期保持中文包装语，应同步更新转换脚本模板。
