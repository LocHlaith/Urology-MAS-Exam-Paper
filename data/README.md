# 数据目录

- `banks/bank_*.json`：人类题库。
- `banks/new_bank_*.json`：MAS 题库，包含逐步累计的评价字段。
- `raw/datasets/`：人类题库 Word 文件及程序解析所需的中间文本/结构化文件。人类题库来源是 Word，TXT 和 JSON 是后续处理产物。

不要根据数据文件名推断研究设计、图片要求或最终统计结论。绘图要求以 `plot/agent_readable/` 为入口，来源优先级见 `docs/AGENT_GROUNDING.md`。
