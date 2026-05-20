# 项目结构

## 代码

- `scripts/generation/`：包含三类脚本：把人类题库 Word 结构化为 `bank_*.json`，根据人类题库生成 MAS 题库 `new_bank_*.json`，以及为 MAS 题库补充答案解析和考点还原。
- `scripts/evaluation/`：为题库或用户明确提供的试卷 JSON 写入文本相似度、可读性、QGEval 和 LLM 等机器派生评价字段。
- `scripts/reporting/`：将题库 JSON 导出为给合作者人工审阅的 Word 材料；不作为绘图数据来源。
- `scripts/project_paths.py`：集中管理仓库路径。仓库结构变化时优先更新这个文件。

## 输入

- `data/raw/datasets/`：资料文档和文本导出。
- `data/banks/bank_*.json`：人类题库文件。
- `data/banks/new_bank_*.json`：MAS 题库及其累计评价字段。
- `prompts/generation/`：MAS 出题、答案解析补充和考点还原使用的 prompt。
- `prompts/evaluation/`：QGEval 与 LLM 评分相关 prompt。

## 输出

- `outputs/report_drafts/`：当前保留 A/B 卷解析标注版 TXT，用于人工核对试卷解析与标注内容；不是绘图要求来源。
- `outputs/figures/`：后续正式绘图脚本的输出位置；论文图片应输出为可编辑 PDF。
- `outputs/report_exports/`：人工审阅导出脚本需要时生成的 Word 材料。

## 绘图要求

`plot/raw/` 保存第一作者提供但不建议后续 agent 直接读取的原始绘图文件。`plot/agent_readable/` 是为了便于 agent 阅读而做的结构化整理，不替代原始文件。

第一作者要求最终图片为可编辑 PDF；统计整理中可能出现 CSV、JSON、Excel 或其他表格，但这些不是图片交付格式。
