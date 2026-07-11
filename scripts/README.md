# 脚本目录

本目录按项目流程说明脚本位置与职责。脚本入口、默认路径和输出目录应优先查看 `scripts/project_paths.py`。

## 注释风格

各脚本的注释应服务于防止误读，而不是记录修改历史。脚本开头统一使用“脚本用途 / 流程阶段 / 主要输入 / 主要输出 / 重要边界”五项说明；正文分区统一使用 `# ===== 中文短标题 =====`；行内注释只解释流程边界、字段顺序、不可显然的解析策略和不可推断点。不要在注释中保留临时称呼、历史修复语境或口语化说明。

## 路径与环境

- `scripts/project_paths.py`：仓库路径的单一事实来源，集中定义 `data/`、`prompts/`、`outputs/` 等目录。
- `scripts/deepseek_env.py`：读取 `.env` 中的 DeepSeek API 配置。DeepSeek 是当前模型 API 服务提供方；研究流程统一表述为 MAS 出题。

## 人类题库结构化

人类题库来源是 Word。TXT 只是为了便于程序解析而生成的中间文件，不是独立来源，也不是 MAS 出题结果。

- `scripts/generation/word_to_txt.py`：将人类题库 Word 文件转换为 TXT 中间文件。
- `scripts/generation/txt_to_bank.py`：从 TXT 中解析题干、选项、参考答案、答案解析和病例题结构，生成 `data/banks/bank_*.json`。这些文件统一称为人类题库。

## MAS 出题与内容补全

这一阶段读取人类题库和 generation prompt，生成或补全 MAS 题库 `data/banks/new_bank_*.json`。

- `scripts/generation/bank_to_new_bank.py`：读取 `data/banks/bank_*.json` 和 `prompts/generation/prompts_for_bank_to_new_bank_*.txt`，调用模型生成 MAS 题库。
- `scripts/generation/add_answer_explanation.py`：为 MAS 题库补充或补齐“答案解析”字段。既有 JSON 字段名为 `analysis` / `analysis1` 等。
- `scripts/generation/add_test_point.py`：为 MAS 题库补充“考点还原”字段。既有 JSON 字段名为 `test_point`。
- `scripts/generation/measure_question_generation_time.py`：按题型统计 MAS 出题耗时。该脚本将临时题库写入 `timing_runs/`，并输出绘图用 `plot/agent_readable/derived_data/mas_question_generation_time.csv`。

## 题库评价

这些脚本写入机器派生评价字段，不能替代最终盲法专家评分。

- `scripts/evaluation/verify_by_fuzzywuzzy.py`：用 FuzzyWuzzy/Levenshtein 比较 MAS 题库与人类题库的文本相似度。
- `scripts/evaluation/verify_by_ngram.py`：用 n-gram Jaccard 比较 MAS 题库与人类题库的文本重叠。
- `scripts/evaluation/verify_by_sentencebert.py`：用 Sentence-BERT 比较 MAS 题库与人类题库的语义相似度。
- `scripts/evaluation/verify_by_textstat.py`：为 MAS 题库计算可读性指标。
- `scripts/evaluation/qgeval.py`：为人类题库或 MAS 题库写入 QGEval 机器评分。命令行中的 `old` 是历史兼容写法，含义为人类题库；`new` 含义为 MAS 题库。
- `scripts/evaluation/llm.py`：为人类题库或 MAS 题库写入 LLM rubric 机器评分。命令行中的 `old/new` 含义同上。
- `scripts/evaluation/major_defects.py`：按题型比例抽样，使用 `prompts/evaluation/prompt_for_major_defects.txt` 和 `prompts/evaluation/major_defects.md` 调用 DeepSeek 标注 critical defects，并写入 `outputs/critical_defects/critical_defects_AI标记.xlsx`。D:J 写入 1-7 类 0/1 标记，K:Q 写入对应理由；默认 dry-run，只有 `annotate --run-api` 会调用 API。

## 试卷质量评价

第一作者从题库中抽题组成试卷后，可使用以下脚本按与题库评价相近的方式处理试卷 JSON。试卷 JSON 必须由用户通过参数明确提供，不得从文件名或历史路径推断。

- `scripts/evaluation/exam_paper_verify_by_textstat.py`：为指定试卷 JSON 计算可读性。
- `scripts/evaluation/exam_paper_qgeval.py`：为指定试卷 JSON 写入 QGEval 机器评分。
- `scripts/evaluation/exam_paper_llm.py`：为指定试卷 JSON 写入 LLM rubric 机器评分。

## 人工审阅导出

- `scripts/reporting/json_to_docx.py`：将题库 JSON 导出为给合作者人工审阅的 Word 文档。
