# 数据处理与绘图逻辑复核报告

日期：2026-05-21

## 结论

当前仓库尚未包含最终盲法专家质量复合评分。根据第一作者要求，主终点必须等专家评分表进入仓库后再计算；现有 QGEval 与 LLM 只能作为入卷前 QC / 机器代理 / Supplementary exploratory concordance，不能作为 Figure 2 主终点结论。

本次已将现有 QGEval 与 LLM 细则分数从“直接使用两个总分或直接使用 LLM 原始维度”改为“先归一化，再映射到论文用机器代理维度”。这些字段命名为 `machine_proxy_*`，以避免与后续专家 `quality_score` 混淆。

## 已修正

1. QGEval 与 LLM 不再直接作为 Figure 2A 的两条总分曲线。
   - 旧逻辑：`llm_score_5_mean` 和 `qgeval_score_5_mean` 并列画 MAS-Human 差值。
   - 新逻辑：输出并使用 `machine_proxy_quality_score_mean`，仅标注为 QC-only machine proxy。

2. LLM 原始细则不再直接作为 Figure 2B 的分维度评分。
   - 旧逻辑：直接画 `llm_流畅性_mean`、`llm_明确性_mean`、`llm_综合性_mean` 等。
   - 新逻辑：使用以下归一化后的论文代理维度：
     - `machine_proxy_presentation_clarity`
     - `machine_proxy_blueprint_relevance`
     - `machine_proxy_answer_validity`
     - `machine_proxy_item_design`
     - `machine_proxy_cognitive_feedback`

3. 已新增细则映射表。
   - 文件：`plot/agent_readable/derived_data/machine_rating_domain_crosswalk.csv`
   - 作用：记录每个机器代理维度由哪些 QGEval/LLM 原始细则组成，以及不同满分量表如何归一到 1-5 分。
   - 归一公式：`1 + 4 * (raw - 1) / (max_score - 1)`。

4. 缺陷 proxy 不再只依赖少数 LLM 原始字段。
   - 旧逻辑：主要依据 LLM 的正确性、可解性、排他性、明确性、答案解析评分。
   - 新逻辑：同时使用 QGEval 的可回答性、答案一致性、一致性，以及 LLM 的正确性、可解性、绝对性等，并结合 `machine_proxy_answer_validity`、`machine_proxy_presentation_clarity`、`machine_proxy_item_design`。
   - 注意：这仍然是 machine screen proxy，不是专家裁决缺陷。

5. Figure 3 的质量边界 proxy 改为机器代理复合分。
   - 旧逻辑：按认知层级比较 `llm_score_5_mean`。
   - 新逻辑：按认知层级比较 `machine_proxy_quality_score_mean`。

6. 来源辨识混淆矩阵已补出数据处理与绘图逻辑。
   - 新增：`source_detection_item_level.csv`
   - 新增：`source_detection_confusion_matrix.csv`
   - 新增：`source_detection_metrics.csv`
   - Figure 4B 代码已从 Correct/Incorrect 柱状图改为混淆矩阵。
   - Figure 4C 代码已改为 balanced accuracy、sensitivity、specificity。

7. 考生空作答处理已修正。
   - 旧逻辑：空分数直接跳过，导致 4997 条作答。
   - 新逻辑：空作答按预设记为 incorrect，并用 `response_missing=1` 标记；现在为 5000 条作答，其中 3 条为空作答。

## 现有数据仍不能完全满足者

1. 最终盲法专家质量复合评分缺失。
   - 缺少文件：`expert_ratings.csv`
   - 需要字段：`rater_id, item_id, rater_phase, quality_score, dimension_scores, major_defect, critical_defect_type, source_guess`
   - 影响：Figure 2A、Figure 2B、Figure 2E、Figure 3A、Figure 3D 的正式专家结果均不能完成。
   - 当前处理：只保留 machine proxy，明确标注为 QC-only。

2. 专家缺陷裁决表缺失。
   - 缺少文件：`defect_adjudication.csv`
   - 需要字段：`item_id, final_major_defect, final_critical_defect, adjudication_reason`
   - 影响：Figure 2C、Figure 2D、Figure 3B 的正式安全缺陷图不能完成。
   - 当前处理：`defect_adjudication_proxy.csv` 仍然只是机器代理。

3. MAS 候选题与安全筛查漏斗缺失。
   - 缺少文件：`mas_candidate_log.csv`
   - 需要字段：`candidate_id, AI_score, AI_flags, pass_AI_threshold, expert_screen_decision, exclusion_reason, final_item_id`
   - 影响：Figure 1 的候选题筛选漏斗、Supplementary Fig. 1、Supplementary Table 2 只能做结构示意，不能给真实数量和筛除原因。

4. 工作流总时间与成本缺失。
   - 缺少文件：`workflow_total_time_cost.csv`
   - 影响：Figure 4D-F 仍只能占位。
   - 注意：考生考试用时不能冒充命题工作流人力时间。

5. 来源辨识原始逐题 `source_guess` 缺失。
   - 当前原始表只有“是否成功判断”。
   - 已能做：基于 forced-pair 成功/失败反推出一个 2x2 混淆矩阵。
   - 不能做：真正独立估计判断偏倚、无法判断类别、专家/学生分层、置信度/AUC。
   - 若明天能补表，建议字段为：`rater_id, item_id, source_true, source_guess, confidence_optional`。

6. 当前环境未能重生成 PDF panels。
   - `build_plot_datasets.py` 已成功运行。
   - `make_manuscript_panels.py` 的语法检查通过。
   - 但当前 Python 环境缺少 `matplotlib`，且仓库文件列表中未见 `scripts/plotting/make_manuscript_figures.py`，因此本次未重导出 PDF。

## 明天收到专家评分后的接入建议

1. 新建或导入 `plot/agent_readable/derived_data/expert_ratings.csv`，不要覆盖机器评分表。

2. `rater_phase` 至少区分：
   - `pre_administration_safety_screening`
   - `blinded_outcome_rating`

3. 主终点只筛选：
   - `rater_phase == blinded_outcome_rating`
   - `quality_score`

4. 机器代理字段保留为：
   - 入卷前 QC 证据
   - AI/LLM 与专家评分一致性分析
   - Supplementary exploratory analysis

5. Figure 2 与 Figure 3 的正式质量图应优先切换到专家评分；机器代理图若保留，应放 Supplement 或明确标注 QC-only。
