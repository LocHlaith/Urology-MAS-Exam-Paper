# Urology MAS Exam Paper

泌尿外科规培考试出卷与评估项目。代码通过 DeepSeek API 生成题库、补充解析/考点/评分字段，并输出统计、图表和给合作者查看的报告材料。

## Directory Map

- `scripts/`: 可运行脚本。按用途分为 `generation/`, `evaluation/`, `plotting/`, `reporting/`。
- `scripts/project_paths.py`: 项目路径的单一事实来源。新增脚本应优先复用这里的路径常量。
- `prompts/`: DeepSeek 调用所需 prompt，按生成、分析、评价分组。
- `data/banks/`: 题库 JSON。`bank_*.json` 是原始/人工题库，`new_bank_*.json` 是 MAS 生成题库。
- `data/raw/datasets/`: 原始 Word/TXT/PPT 数据材料。
- `plot/`: 第一作者提供的绘图要求与格式参考。
- `plot/agent_readable/`: 已转换成 agent 友好形式的绘图要求、Excel CSV、PPT 媒体和 TIF 预览。
- `outputs/`: 派生产物，包括 `bank_docx/`, `statistics/`, `report_drafts/`, `figures/`。
- `docs/`: 给人和 agent 看的工程说明与防幻觉规则。

## Common Commands

```powershell
python scripts/generation/bank_to_new_bank.py --banks A1,A2
python scripts/evaluation/verify_by_textstat.py
python scripts/evaluation/qgeval.py --bank_set new --banks A1
python scripts/evaluation/llm.py --bank_set new --banks A1
python scripts/plotting/chart.py
python scripts/reporting/json_to_docx.py
```

API 密钥放在 `.env`，字段参考 `.env.example`。

## Agent Rule

绘图或统计 agent 必须先读 [docs/AGENT_GROUNDING.md](docs/AGENT_GROUNDING.md)，再读 `plot/agent_readable/AGENT_BRIEF.md`。遇到缺失、冲突或只有示例值的内容，应标记为 `UNKNOWN_OR_CONFLICTING`，不要补写成事实。
