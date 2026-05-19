# 脚本目录

本目录按项目流程说明脚本位置与职责。这里不列“常用命令”，因为不同阶段的运行参数和输入文件差异很大，后续应查看具体脚本和项目路径配置。

## 路径与环境

- `scripts/project_paths.py`：仓库路径的单一事实来源，集中定义 `data/`、`prompts/`、`outputs/` 等目录。
- `scripts/deepseek_env.py`：读取 `.env` 中的 DeepSeek API 配置。

## 人类题库转换

这一阶段的目标是把已经拿到的人类题库转换为程序可读取的 JSON，不属于 DeepSeek 生成题库。

- `scripts/generation/word_to_txt.py`：将原始 Word 题库材料转换为 TXT，作为后续结构化解析的输入。
- `scripts/generation/txt_to_bank.py`：从 TXT 中解析题干、选项、答案、解析和病例题结构，生成 `data/banks/bank_*.json`。这些 `bank_*.json` 统一称为人类题库。

## DeepSeek/MAS 出题

这一阶段才是 DeepSeek/MAS 根据人类题库和提示词生成新题库。

- `scripts/generation/bank_to_new_bank.py`：读取 `data/banks/bank_*.json` 和 `prompts/generation/` 中的提示词，调用 DeepSeek 生成 `data/banks/new_bank_*.json`。

## 新题库评价与标注

这些脚本用于评价或补充 `new_bank_*.json`，部分脚本也可通过参数评价人类题库。

- `scripts/evaluation/verify_by_fuzzywuzzy.py`：用 FuzzyWuzzy/Levenshtein 检查新题库与人类题库的文本相似度。
- `scripts/evaluation/verify_by_ngram.py`：用 n-gram Jaccard 检查文本重叠。
- `scripts/evaluation/verify_by_sentencebert.py`：用 Sentence-BERT 计算语义相似度。
- `scripts/evaluation/verify_by_textstat.py`：计算可读性指标。
- `scripts/evaluation/qgeval.py`：调用 DeepSeek 按 QGEval 维度评分。
- `scripts/evaluation/llm.py`：调用 DeepSeek 按医学教育/题目质量 rubric 评分。
- `scripts/evaluation/analysis.py`：生成或补充题目解析类字段。
- `scripts/evaluation/analysis_make_up.py`：补齐缺失解析字段。
- `scripts/evaluation/test_point.py`：标注题目考点。

## 试卷质量评价

第一作者曾从我提供的 `new_bank_*.json` 中抽题组成试卷（A卷、B卷），再让我用与评价题库相同的方法评价试卷质量。以下脚本服务于这类“组卷后试卷”的评价。

- `scripts/evaluation/exam_paper_verify_by_textstat.py`：为 `outputs/report_drafts/B.json` 中的试卷题目计算可读性。
- `scripts/evaluation/exam_paper_qgeval.py`：为 `outputs/report_drafts/B.json` 中的试卷题目写入 QGEval 评分。
- `scripts/evaluation/exam_paper_llm.py`：为 `outputs/report_drafts/B.json` 中的试卷题目写入 LLM rubric 评分。

## 报告导出

- `scripts/reporting/json_to_docx.py`：将 `new_bank_*.json` 导出为给合作者查看的 Word 文档。
