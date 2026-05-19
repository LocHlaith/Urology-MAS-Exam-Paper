# 泌尿外科 MAS 出科考试论文项目

本仓库服务于一项比较“人类出题质量”与“DeepSeek/MAS 辅助出题质量”的泌尿外科规培出科考试论文。研究目标不是单纯生成题目，而是围绕人类题库、DeepSeek 生成题库、组卷、评价、统计和绘图形成一条可追溯的论文工作流。

我是论文第二作者，负责本项目中的编程、统计和绘图工作。本仓库中的代码、结构化数据、转换文档和审计说明，主要用于支持后续分析与生成可编辑 PDF 论文图。

## 项目流程

1. 第一阶段：整理人类题库。人类题库来自 Word/TXT 等材料，代码先将其转换为便于程序读取的 JSON，即 `data/banks/bank_*.json`。
2. 第二阶段：DeepSeek/MAS 出题。DeepSeek 阅读人类题库和提示词，生成 JSON 格式的新题库，即 `data/banks/new_bank_*.json`。
3. 第三阶段：评价与标注。对人类题库、新题库或第一作者组卷后的试卷进行文本相似度、可读性、QGEval、LLM 评分、解析和考点标注。
4. 第四阶段：统计与绘图。根据第一作者在 `plot/` 中给出的绘图要求，整理分析数据并输出可编辑 PDF 图。

## 目录说明

- `scripts/`：可运行脚本，按实际用途分为人类题库转换、DeepSeek 出题、评价标注、试卷评价和报告导出。
- `scripts/project_paths.py`：项目路径的单一事实来源。新增脚本应优先复用这里的路径常量。
- `prompts/`：DeepSeek 调用所需 prompt，按生成、分析、评价分组。
- `data/banks/`：题库 JSON。`bank_*.json` 是人类题库，`new_bank_*.json` 是 DeepSeek/MAS 生成题库。
- `data/raw/datasets/`：原始 Word、TXT、PPT 数据材料。
- `plot/`：第一作者提供的绘图要求、格式参考和作答工作簿。
- `plot/agent_readable/`：已转换成 agent 友好形式的绘图要求、工作簿单元格导出、PPT 媒体和 TIF 预览。
- `outputs/`：派生产物，包括 `bank_docx/`、`statistics/`、`report_drafts/`、`figures/`。
- `docs/`：给人和 agent 看的工程说明、防幻觉规则和绘图就绪性审计。

## Agent 使用规则

绘图或统计 agent 必须先读 [docs/AGENT_GROUNDING.md](docs/AGENT_GROUNDING.md)，再读 `plot/agent_readable/AGENT_BRIEF.md`。遇到缺失、冲突或只有示例值的内容，应标记为 `UNKNOWN_OR_CONFLICTING`，不要补写成事实。

第一作者对图片交付的要求是可编辑 PDF。CSV、JSON 或 Excel 只属于数据来源或统计整理材料，不是图片交付格式。
