# Agent 防幻觉规则

本仓库同时包含原始资料、生成题库、评价输出、报告草稿和第一作者绘图要求，后续 agent 很容易把不同层级的材料混在一起。生成论文图、统计结论或面向正文的表述前，必须遵守本文件。

## 来源优先级

1. `plot/agent_readable/AGENT_BRIEF.md`
2. `docs/PLOTTING_READINESS_AUDIT.md`
3. `plot/agent_readable/manifest.json`
4. `plot/agent_readable/docs/*.md`
5. `data/banks/*.json`
6. `outputs/statistics/*.txt`
7. `outputs/report_drafts/*`

`outputs/report_drafts/` 是协作者审阅草稿和手工报告材料，不是研究设计或绘图要求的权威来源。

`docs/PLOTTING_READINESS_AUDIT.md` 记录当前本地数据能支持哪些图表、哪些信息缺失，以及哪些内容不能推断。遇到 `UNKNOWN_OR_CONFLICTING` 必须停止并请求澄清。

## 图片输出硬要求

- 第一作者要求：所有图片最终交付为可编辑的 PDF 文件。
- `plot/agent_readable/docs/01_figure_unified_parameters.md` 允许 PNG/PDF/SVG，但本项目最终交付优先级以“可编辑 PDF”为准。
- Matplotlib 导出 PDF 时应保留可编辑文字，例如设置 `pdf.fonttype: 42`，不要把文字转成路径或栅格图。
- CSV 或其他表格名称只属于数据整理/统计建模层面，不能写成“第一作者要求以 CSV 交付图片”。

## 作答工作簿映射

- 本项目已确认：M卷 = MAS，P卷 = 人类。
- 结合第一作者要求的 A/B 顺序：Form A = Human -> MAS，即 P卷 -> M卷；Form B = MAS -> Human，即 M卷 -> P卷。
- 不要把 M/P 映射反写。若其他字段、题号连接或公式含义不清，仍应回到 workbook、sheet 和单元格来源核对。

## 实际代码链

- `scripts/generation/word_to_txt.py` 和 `scripts/generation/txt_to_bank.py` 用于把已经取得的人类题库转换为程序可读的 `data/banks/bank_*.json`。这一步是资料结构化，不是 DeepSeek 出题。
- `scripts/generation/bank_to_new_bank.py` 才是 DeepSeek/MAS 出题脚本：它读取人类题库和 `prompts/generation/`，生成 `data/banks/new_bank_*.json`。
- `scripts/evaluation/analysis.py`、`analysis_make_up.py`、`test_point.py` 只标注 `new_bank_*.json`。
- `scripts/evaluation/qgeval.py` 和 `llm.py` 可通过 `--bank_set old/new` 评价人类题库或新题库。
- `scripts/evaluation/verify_by_*` 用于比较 `new_bank_*.json` 与人类题库 `bank_*.json`。
- `scripts/evaluation/exam_paper_*` 处理第一作者从 `new_bank_*.json` 抽题组卷后的试卷 JSON，例如 `outputs/report_drafts/B.json`；这类脚本与题库评价脚本同属评价与标注，不属于报告导出。

## 禁止推断

- 不要从文件名推断样本量、panel 标签、统计模型、非劣效界值、颜色或字体。
- 不要把 `XXX` 等占位符当成真实数据。
- 不要把示例命令、docstring、旧绝对路径当作分析要求。
- 原始数据元信息中可能有旧电脑上的 `source_file` 绝对路径；仓库内路径应以 `scripts/project_paths.py` 为准。
- 不要混用 `bank_*.json` 和 `new_bank_*.json`，除非明确说明比较的是人类题库与 DeepSeek/MAS 生成题库。
- 不要把 `outputs/statistics/*.txt` 直接当作正式图的锁定结果；正式图需要从原始 JSON/表格重算并记录脚本。
- 不要把原始绘图要求中出现的 `*.csv` 数据表名理解为仓库已经存在的文件，也不要理解为图片交付格式；它们是统计设计或数据字典层面的表名。

## 作图前追溯表

每张图制作前，必须在工作记录或代码注释里建立一个小表：

| 图/面板 | 要求来源 | 数据来源 | 派生统计量 | 未解决假设 |
| --- | --- | --- | --- | --- |

任何一项缺失或互相矛盾时，写 `UNKNOWN_OR_CONFLICTING` 并停止澄清。

## 路径规则

- 使用 `scripts/project_paths.py`，不要硬编码项目路径。
- JSON 题库输入优先来自 `data/banks/`。
- `prompts/` 只作为 DeepSeek prompt 来源，不作为绘图要求来源。
- 第一作者绘图要求以 `plot/agent_readable/` 为入口。
- 新运行日志写入 `outputs/logs/`；该目录已被 git 忽略。
