# 项目结构

## 代码

- `scripts/generation/`：包含两类性质不同的脚本：一类把人类题库材料结构化为 `bank_*.json`，另一类调用 DeepSeek/MAS 生成 `new_bank_*.json`。
- `scripts/evaluation/`：为新题库或组卷后试卷补充相似度、可读性、QGEval、LLM 评分、题目解析和考点标注。
- `scripts/reporting/`：将题库或报告草稿 JSON 导出为给合作者查看的 Word/TXT 材料。
- `scripts/project_paths.py`：集中管理仓库路径。仓库结构变化时优先更新这个文件。

## 输入

- `data/raw/datasets/`：原始资料文档和文本导出。
- `data/banks/bank_*.json`：人类题库文件。
- `data/banks/new_bank_*.json`：MAS 生成题库及其累计评价字段。
- `prompts/generation/`：DeepSeek/MAS 阅读人类题库并生成新题库时使用的 prompt。
- `prompts/analysis/`：生成题目解析字段时使用的 prompt。
- `prompts/evaluation/`：QGEval、LLM 评分和考点标注相关 prompt。

## 输出

- `outputs/bank_docx/`：生成题库的 Word 导出。
- `outputs/statistics/`：文本或 JSON 形式的统计摘要。
- `outputs/report_drafts/`：给第一作者或合作者审阅的报告草稿、组卷后试卷 JSON 和手工整理材料。
- `outputs/figures/`：后续正式绘图脚本的输出位置；论文图片应输出为可编辑 PDF。
- `outputs/logs/`：运行日志，已被 git 忽略。

## 绘图要求

`plot/` 保存第一作者提供的原始绘图包。`plot/agent_readable/` 是为了便于 agent 阅读而做的机械转换，不替代原始文件。

第一作者要求最终图片为可编辑 PDF；统计整理中可能出现 CSV 或其他表格，但这些不是图片交付格式。
