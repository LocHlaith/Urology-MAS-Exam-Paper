# Scripts

Use commands from the repository root.

## Generation

```powershell
python scripts/generation/txt_to_bank.py
python scripts/generation/bank_to_new_bank.py --banks A1,A2
```

## Evaluation

```powershell
python scripts/evaluation/verify_by_fuzzywuzzy.py
python scripts/evaluation/verify_by_ngram.py --n 3
python scripts/evaluation/verify_by_sentencebert.py
python scripts/evaluation/verify_by_textstat.py
python scripts/evaluation/qgeval.py --bank_set new --banks A1
python scripts/evaluation/llm.py --bank_set new --banks A1
python scripts/evaluation/analysis.py --banks A1
python scripts/evaluation/test_point.py --banks A1
```

## Plotting

```powershell
python scripts/plotting/statistics_for_test_point.py
python scripts/plotting/chart.py
python scripts/plotting/chart_for_q_and_l.py
python scripts/plotting/time.py
```

## Reporting

```powershell
python scripts/reporting/json_to_docx.py
python scripts/reporting/temp_verify_by_textstat.py
python scripts/reporting/temp_qgeval.py
python scripts/reporting/temp_llm.py
```

All scripts should use `scripts/project_paths.py` for repository paths.
