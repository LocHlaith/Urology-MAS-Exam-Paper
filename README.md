# Urology-MAS-Exam-Paper

本仓库用于比较人类专家与 MAS（多智能体系统）命题质量。当前正式绘图入口是 `scripts/plotting/make_final_figures.py`，逐 panel 的现行逻辑与学术规范风险见 `绘图逻辑.md`。

## 目录与数据血缘

| 路径 | 角色 | 说明 |
|---|---|---|
| `data/raw/human_question_documents/` | 原始输入 | 人类题库及试卷 Word 文档；raw 中只保留原始文档。 |
| `data/intermediate/human_question_text/` | 中间数据 | Word 转出的 TXT。 |
| `data/intermediate/structured_question_bank/` | 中间数据 | 从 TXT 结构化得到、尚未按题型拆分的 JSON。 |
| `data/banks/` | 分析数据 | `bank_*.json` 为人类题库，`new_bank_*.json` 为 MAS 题库。 |
| `plot/data/raw/exam_response_workbooks/` | 原始输入 | 两份考生作答 Excel。 |
| `plot/data/raw/expert_rating_workbooks/` | 原始输入 | 仓库现有的三份专家评分 Excel。 |
| `plot/data/derived/source_workbooks/` | 派生数据 | 原始或历史工作簿逐工作表导出的 CSV；由 manifest 记录来源。 |
| `plot/data/derived/` | 派生数据 | 统一作答表、题目表、统计模型输入、统计结果及各 panel 数据。 |
| `outputs/figures/panels/` | 输出 | 当前 30 个可编辑 PDF panel。 |
| `outputs/figure_source_data/` | 输出 | 与 30 个 panel 一一对应的审稿人源数据工作簿。 |
| `outputs/report_drafts/` | 输出 | P 卷、M 卷四轮机器评分的解析标注文本。 |

`exam_responses/` 与 `exam_responses_2/` 曾被放在 raw 下，但它们是 Excel 工作表导出的 CSV，并与 `derived/source_workbooks/` 中的对应文件逐行重复；现已去重，数据构建脚本直接读取后者。

## 正式重建顺序

```powershell
python scripts/plotting/build_plot_datasets.py
python scripts/plotting/make_final_figures.py
python scripts/plotting/export_panel_source_data.py
```

路径常量统一定义在 `scripts/project_paths.py`。旧版 `make_manuscript_panels.py`、`make_manuscript_figures.py` 和带 `legacy_` 前缀的脚本仅用于历史复核，不是当前投稿图入口。

## 已知来源缺口

以下缺口不影响当前脚本从已保存 CSV 重建图，但影响从最原始材料端到端复现，交付审稿人前必须披露或补齐：

- `root_xlsx_csv_manifest.csv` 所列三份“专家评分——统计版.xlsx”不在仓库。现有 raw 专家工作簿没有 `P汇总`、`M汇总/M-合并` 等全部统计工作表，因此 Figure 2B–2D、4B–4D 依赖历史导出的工作表 CSV。
- `expert_ratings_updated.csv` 记录的三个 `*_cleaned.xlsx` 来源文件不在仓库；Figure 2E–2F 依赖该结构化派生表。
- `效率分析.xlsx` 原始工作簿不在仓库；Figure 5 使用其已导出的 `efficiency_analysis__01__Sheet1.csv`。
- Figure 2B–2D/4B–4D 每位专家每个来源使用 70 题，而 Figure 2E–2F 使用每个来源 50 题；两套专家数据口径并不相同，不能不加说明地视为同一分析集。
