# 泌尿外科 MAS 出科考试论文项目

本仓库服务于一项比较“人类出题质量”与“MAS 出题质量”的泌尿外科规培出科考试论文。研究目标不是单纯生成题目，而是围绕人类题库、MAS 题库、组卷、评价、统计和绘图形成一条可追溯的论文工作流。

我是论文第二作者，负责本项目中的编程、统计和绘图工作。本仓库中的代码、结构化数据、转换文档和审计说明，主要用于支持后续分析与生成可编辑 PDF 论文图。

## 项目流程

1. 第一阶段：整理人类题库。人类题库来源是 Word，代码先将 Word 转成 TXT 中间文件，再结构化为 `data/banks/bank_*.json`。
2. 第二阶段：MAS 出题。模型读取人类题库和提示词，生成 JSON 格式的 MAS 题库，即 `data/banks/new_bank_*.json`。
3. 第三阶段：内容补全与评价。对 MAS 题库补充答案解析、考点还原，并对人类题库、MAS 题库或第一作者组卷后的试卷进行文本相似度、可读性、QGEval 和 LLM 评分。
4. 第四阶段：统计与绘图。根据第一作者在 `plot/` 中给出的绘图要求，整理分析数据并输出可编辑 PDF 图。

## 目录说明

- `scripts/`：可运行脚本，按实际用途分为人类题库结构化、MAS 出题与内容补全、题库/试卷评价和人工审阅导出。
- `scripts/project_paths.py`：项目路径的单一事实来源。新增脚本应优先复用这里的路径常量。
- `prompts/`：模型调用所需 prompt，按生成与评价分组。
- `data/banks/`：题库 JSON。`bank_*.json` 是人类题库，`new_bank_*.json` 是 MAS 题库。
- `data/raw/datasets/`：人类题库 Word 文件及其程序解析中间文件等原始/中间资料。
- `plot/`：第一作者提供的绘图要求、格式参考和作答工作簿；`plot/raw/` 保存不建议后续 agent 直接读取的原始文件。
- `plot/agent_readable/`：已转换成 agent 友好形式的绘图要求、工作簿单元格导出和 TIF 预览。
- `outputs/`：当前保留的输出材料，主要用于人工核对和后续正式绘图输出。
- `docs/`：给人和 agent 看的工程说明、防幻觉规则和绘图就绪性审计。

## Agent 使用规则

绘图或统计 agent 必须先读 [docs/AGENT_GROUNDING.md](docs/AGENT_GROUNDING.md)，再读 `plot/agent_readable/AGENT_BRIEF.md`。遇到缺失、冲突或只有示例值的内容，应标记为 `UNKNOWN_OR_CONFLICTING`，不要补写成事实。

第一作者对图片交付的要求是可编辑 PDF。CSV、JSON 或 Excel 只属于数据来源或统计整理材料，不是图片交付格式。
