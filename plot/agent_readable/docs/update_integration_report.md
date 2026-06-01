# 2026-05-26 第一作者更新接入与绘图代码修改报告

## 接入原则

- `data/first_author_update/` 保存第一作者 5 月 26 日补充文件的原始副本，包括修订建议 Word、critical defect 分类要求和 3 份专家评分工作簿。
- `scripts/ingest_first_author_update.py` 将专家评分工作簿解析为可追溯长表，不手工改数；通过题干文本与 `derived_data/item_master.csv` 进行模糊匹配。
- `scripts/make_revised_figures.py` 使用 update 派生表和既有考试作答表生成修订后的 Figure 3、Figure 4、Figure 5 面板，导出 PNG 与 PDF。

## 新增派生数据

- `expert_ratings_updated.csv`：3 位专家 × 100 道题 = 300 行专家评分；其中专家 1、专家 3 提供来源判断，专家 4 的来源判断为空但评分保留。
- `expert_rating_item_summary_updated.csv`：逐题专家评分汇总。
- `source_detection_updated.csv`：专家来源辨识逐判断表；共 200 条有来源判断记录。
- `source_detection_metrics_updated.csv`：accuracy、balanced accuracy、MAS sensitivity、Human specificity。
- `source_task_ratings_updated.csv`：来源辨识任务中的评分数据，用于 Figure 4C。
- `critical_defect_taxonomy_updated.csv`：从 `critical_defect.docx` 提取的 critical/major defect 排除项分类。
- `expert_rating_match_qc_updated.csv`：题干模糊匹配 QC，列出匹配分数偏低的条目供人工复核。

## 绘图代码修改重点

### Figure 3

- Figure 3A 改为专家评分长表中的 `quality_score_5`，差值方向统一为 `MAS - Human`，并加入 `-0.30` 非劣性界值线。
- Figure 3B 纠正为缺陷风险差，不再复用正确率图；当前使用既有 `defect_adjudication_proxy.csv`，因为 update 补充文件提供的是 defect 分类要求而非逐题裁决结果。
- Figure 3C 使用学生作答正确率，横轴明确为 percentage points。

### Figure 4

- Figure 4A 采用 update 专家来源判断计算 balanced accuracy，并显示 50% chance line 与 45%–55% near-chance 区间。
- Figure 4B 从 Correct/Incorrect 改为 true source × guessed source 的混淆结构堆叠比例图。
- Figure 4C 将模糊的 “Rating in source task” 改为 “Source-task item rating (1-5)”，用箱线图叠加原始点。

### Figure 5

- Figure 5B 按 Form A/B 对配对题块得分连线着色，直接呈现 Human→MAS 与 MAS→Human 顺序。
- Figure 5C 展示同一考生 `MAS - Human` 题块得分差，并按 Form A/B 分层。
- Figure 5D 删除 proxy 表述，脚本输出考生层面的配对 `MAS - Human` 正确率差和 95% bootstrap CI；由于单一 Form 内 source 与 block position 完全共线，分 Form 行不强行标注为 adjusted。
- Figure 5E 标记为 exploratory setting-stratified difference，避免被误读为确证性中心间推断。

## 仍需人工确认的点

- `expert_rating_match_qc_updated.csv` 中部分人工题匹配分数偏低，原因多为题干表达与 `item_master.csv` 不完全一致；交稿前建议由项目负责人按题号复核。
- update 的 `critical_defect.docx` 只给出缺陷类别和“每个排除项记录数量/比例”的要求，未给出逐题 critical defect 裁决；因此 Figure 3B 仍标注为基于既有 proxy/adjudication 数据生成。
- Figure 5D 当前为可复现的考生层面配对差值版本；如后续确定混合效应模型或可识别的 cluster bootstrap 作为正式统计方案，可在同一脚本中替换 `model_diff()` 函数。
