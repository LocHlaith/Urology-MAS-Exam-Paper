# 实际代码链

- `scripts/generation/word_to_txt.py` 和 `scripts/generation/txt_to_bank.py` 用于把已经取得的人类题库转换为程序可读的 `data/banks/bank_*.json`。人类题库来源是 Word，TXT 只是程序解析中间文件；这一步是资料结构化，不是 MAS 出题。
- `scripts/generation/bank_to_new_bank.py` 是 MAS 出题脚本：它读取人类题库和 `prompts/generation/`，生成 `data/banks/new_bank_*.json`。
- `scripts/generation/add_answer_explanation.py` 和 `scripts/generation/add_test_point.py` 用于在 MAS 题库生成后补充“答案解析”和“考点还原”，属于生成后的内容补全，不属于质量评价。
- `scripts/evaluation/qgeval.py` 和 `llm.py` 可通过 `--bank_set old/new` 评价人类题库或 MAS 题库；其中 `old` 是历史兼容写法，含义为人类题库，`new` 含义为 MAS 题库。
- `scripts/evaluation/verify_by_*` 用于比较 `new_bank_*.json` 与人类题库 `bank_*.json`。
- `scripts/evaluation/exam_paper_*` 处理用户明确提供的组卷后试卷 JSON；这类脚本与题库评价脚本同属评价与标注，不属于报告导出。
- `scripts/reporting/json_to_docx.py` 只用于人工审阅导出，不是绘图数据来源。