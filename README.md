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
| `plot/data/raw/expert_rating_workbooks/` | 原始输入 | 三份完整专家评分 Excel，含汇总、图灵测试、分题型与布鲁姆分类工作表。 |
| `plot/data/raw/效率分析.xlsx` | 原始输入 | Human 命题用时及成本、共同人工环节。 |
| `plot/data/raw/人工卷用时及成本.docx` | 原始输入 | 效率分析的文字版原始记录，用于交叉核对 Excel。 |
| `plot/data/derived/source_workbooks/` | 派生数据 | 原始或历史工作簿逐工作表导出的 CSV；由 manifest 记录来源。 |
| `plot/data/derived/` | 派生数据 | 统一作答表、题目表、统计模型输入、统计结果及各 panel 数据。 |
| `outputs/figures/panels/` | 输出 | 当前 25 个代码生成的可编辑 PDF panel；Figure 1A、1B、2A、3A、4A 改由 GPT 构图后在 PPT 手工临摹。 |
| `outputs/figure_source_data/` | 输出 | 与 25 个代码生成 panel 一一对应的审稿人源数据工作簿。 |
| `outputs/report_drafts/` | 输出 | P 卷、M 卷四轮机器评分的解析标注文本。 |

`exam_responses/` 与 `exam_responses_2/` 曾被放在 raw 下，但它们是 Excel 工作表导出的 CSV，并与 `derived/source_workbooks/` 中的对应文件逐行重复；现已去重，数据构建脚本直接读取后者。

## 正式重建顺序

```powershell
python scripts/plotting/export_raw_workbooks_to_csv.py
python scripts/plotting/build_plot_datasets.py
python scripts/plotting/make_final_figures.py
python scripts/plotting/export_panel_source_data.py
```

路径常量统一定义在 `scripts/project_paths.py`。旧版 `make_manuscript_panels.py`、`make_manuscript_figures.py` 和带 `legacy_` 前缀的脚本仅用于历史复核，不是当前投稿图入口。

## 当前来源口径

- Figure 2B–2F、4B–4D 均直接读取 `plot/data/raw/expert_rating_workbooks/` 的三份完整原始工作簿；每位专家评价 Human 70 题和 MAS 70 题。
- Figure 2E 使用 raw 工作簿中的 23 个维度构造标准化综合分，并以评分顺序为可用过程协变量；Figure 2F 直接对 raw 的 QGEval 与 ULM 总分计算三专家 ICC。
- Figure 5 的 Human 时间和成本直接读取 `plot/data/raw/效率分析.xlsx`，并与 `plot/data/raw/人工卷用时及成本.docx` 交叉核对；考生考试时长只用于 Figure 6。
- `plot/data/derived/expert_ratings_updated.csv` 与旧版绘图脚本只保留作历史复核，不进入当前 Figure 2E/2F。
- Figure 1A、1B、2A、3A、4A 的 GPT 官网构图提示词位于 `prompts/figures/GPT官网流程图提示词.md`。
