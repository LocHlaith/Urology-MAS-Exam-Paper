# Panel 数据缺口说明

本说明基于 `plot/agent_readable` 下的绘图脚本、`derived_data` 派生数据表、`source_data_fig_*.xlsx`、以及当前仓库中实际可读取的文件整理。检查时间为 2026-06-04。

特别约束：当前没有人工卷效率的任何可靠信息，因此所有涉及人工卷用时、人工成本、人工流程效率的 panel 均不得擅自补值、推算或用假设值替代。

## 总体结论

多数质量、学生答题表现、考试顺序与区组比较相关 panel 已具备可绘制数据。仍存在三类关键缺口：

1. **正式人工缺陷 adjudication 缺失**：当前 `defect_adjudication_proxy.csv` 是机器筛查代理结果，不是正式逐题人工专家裁决。该缺口影响 Figure 2C、2D、3B，并会进一步影响 Figure 4E 中“非缺陷题”分母。
2. **人工卷效率数据缺失**：`workflow_total_time_cost_TEMPLATE.csv` 仍为空模板。Figure 4D-F 只能绘制 MAS/AI 已观测出题时间，不能绘制完整的人类 vs AI 用时/成本/效率比较。
3. **部分更新数据需 QC 或方法确认**：专家评分/来源识别数据存在 item 覆盖与量表异常信号；Figure 2E、3D、5D、5E 若要做推断性结论，还需锁定统计模型。

## Panel 逐项缺口

| Panel | 绘图要求/主题 | 当前可用数据 | 缺少或需确认的数据 | 当前状态 |
|---|---|---|---|---|
| Figure 1A | MAS/AI 出题工作流与题目生成输入 | `item_master.csv`、`mas_question_generation_time.csv`、AI 出题时间派生表可支持题量与 MAS 生成时间描述 | 脚本引用的 `docs/gpt_image2_figure1_prompt.md` 当前未见；若需期刊级整合图，还缺 Figure 1 整体版式/图像资产最终稿 | 可绘制流程概念图；集成图资产未齐 |
| Figure 1B | 机器安全筛查/安全门控 | `machine_safety_screening_source_summary.csv`、`machine_safety_screening_by_run.csv` 可用 | 若 panel 要表达“专家确认的安全门控”，还缺人工专家安全复核记录；当前只能表达机器筛查流程 | 可绘制机器筛查；专家确认不足 |
| Figure 1C | 专家审阅边界/缺陷分类流程 | `critical_defect_taxonomy_updated.csv` 有缺陷分类 | 脚本引用的 `data/first_author_update/critical_defect.docx` 当前未见；缺逐题正式人工 adjudication 表 | 可绘制分类/流程；逐题裁决缺失 |
| Figure 1D | 考卷设计、form 分配、交叉/平衡设计 | `exam_form_assignment.csv`、`table2_student_randomization_baseline.csv` 可用 | 未见实质数据缺口 | 可绘制 |
| Figure 1E | 研究终点/分析域 | `table3_objective_performance_endpoints.csv` 可用 | 需作者最终确认 endpoint 命名是否与正文一致 | 可绘制 |
| Figure 2A | 专家综合质量评分 | `expert_ratings_updated.csv`、`expert_rating_item_summary_updated.csv` 可用 | `expert_rating_item_summary_updated.csv` 中 MAS 唯一 item summary 仅 44 个，少于 50；需确认是否为题号映射/合并导致。另有评分超过 5 分量表的异常信号，需清洗或说明 | 可绘制，但需 QC 后定稿 |
| Figure 2B | 专家分维度/组件评分 | `expert_ratings_updated.csv` 可用 | 同 Figure 2A：需确认量表范围、item 映射与异常值处理 | 可绘制，但需 QC 后定稿 |
| Figure 2C | major/critical defect 比例 | `defect_adjudication_proxy.csv`、`critical_defect_taxonomy_updated.csv` 可产生代理统计 | 缺正式逐题人工专家 adjudication：item_id、major_defect、critical_defect、缺陷类别、裁决者、最终裁决等 | 只能绘制 proxy，不能作为正式缺陷裁决图 |
| Figure 2D | 缺陷判定/专家 adjudication 工作流 | taxonomy 和 proxy 数据可支持概念流程 | 缺实际人工 adjudication 记录与最终裁决表 | 可画流程示意；实证节点数据不足 |
| Figure 2E | 专家评分一致性/可靠性 | `expert_ratings_updated.csv` 可用于 rater consistency 摘要 | 需锁定统计方法：ICC、weighted kappa、mixed model 或其他；同时需处理量表和 item 映射 QC | 可绘制描述性一致性；推断模型待确认 |
| Figure 3A | 不同认知层级下的质量评分 | `fig3A_quality_by_cognitive_level_updated.csv`、专家评分长表可用 | 依赖 Figure 2A/B 的评分 QC；需确认 MAS item summary 少 6 题是否影响分层均值 | 可绘制，但需 QC 后定稿 |
| Figure 3B | 不同认知层级下的缺陷风险 | `defect_adjudication_proxy.csv`、`item_master.csv` 可产生代理结果 | 缺正式逐题人工 defect adjudication | 只能绘制 proxy |
| Figure 3C | 不同认知层级下学生正确率 | `responses.csv`、`item_master.csv` 可用，响应层数据完整 | 未见实质数据缺口 | 可绘制 |
| Figure 3D | 来源 × 认知层级交互 | 派生数据可支持现有 panel 概念 | 脚本提示未见第一作者更新后的 Figure 3D panel 文件；若要做交互推断，需锁定模型与协变量 | 可绘制探索/描述图；最终模型待确认 |
| Figure 3E | 不同认知层级下 CTT 指标 | `ctt_item_analysis.csv`、`item_master.csv` 覆盖 100 题 | 脚本提示未见第一作者更新后的 Figure 3E panel 文件；若只按现有要求绘制，未见数据缺口 | 可绘制 |
| Figure 4A | 来源识别 balanced accuracy | `source_detection_updated.csv`、`source_detection_metrics_updated.csv` 可用 | 当前来源识别数据为 200 次判断、2 名评分者、94 个 item；需确认缺少的 6 个 item 是否应补齐，或确认 n=94 是设计内样本 | 可绘制，但需 item 覆盖确认 |
| Figure 4B | 真实来源 × 猜测来源混淆矩阵 | `source_detection_updated.csv`、`fig4B_source_detection_confusion_updated.csv` 可用 | 同 Figure 4A：需确认 94/100 item 覆盖问题 | 可绘制，但需 item 覆盖确认 |
| Figure 4C | 来源识别任务评分/置信或相关评分 | `source_task_ratings_updated.csv` 可用 | 发现至少一处评分超出 1-5 量表范围的异常值，例如 H047 的 `source_task_rating_5` 为 7.3913；需清洗或作者确认 | 可绘制前需 QC |
| Figure 4D | 工作流总用时/出题时间比较 | AI/MAS 观测出题时间可用：`mas_question_generation_time.csv`、`fig4D_mas_observed_generation_time.csv`、`ai_efficiency_filled_from_update.csv` | 缺人工卷总用时、人工专家/非专家用时、人工成本；`workflow_total_time_cost_TEMPLATE.csv` 为空 | 不能绘制完整人类 vs AI 比较；只能画 MAS-only |
| Figure 4E | 质量校正后单位题目用时/效率 | MAS-only 派生数据存在：`fig4E_quality_adjusted_time_available_mas_only.csv` | 缺人工卷总用时；缺正式 defect adjudication 支持的非缺陷题分母；不能用 proxy 替代正式人工作为定稿依据 | 不能绘制完整比较；只能画 MAS-only 或标注缺数据 |
| Figure 4F | 效率敏感性分析 | `fig4F_efficiency_sensitivity_available_mas_only.csv` 有 MAS ±20% 情景 | 缺人工卷基础用时/成本、敏感性范围与假设；用户明确禁止增补人工效率信息 | 不能绘制完整敏感性比较 |
| Figure 5A | 两序列/两 form 考试设计 schema | `exam_form_assignment.csv`、`block_scores.csv` 可用 | 未见实质数据缺口 | 可绘制 |
| Figure 5B | paired block scores | `block_scores.csv`、`fig5_block_score_differences_updated.csv` 可用 | 未见实质数据缺口 | 可绘制 |
| Figure 5C | MAS-Human 差值按随机序列展示 | `block_scores.csv`、`fig5_block_score_differences_updated.csv` 可用 | 未见实质数据缺口 | 可绘制 |
| Figure 5D | 按序列调整后的正确率 | `responses.csv`、`item_master.csv`、`exam_form_assignment.csv`、`fig5D_adjusted_correct_rate_by_sequence_updated.csv` 可用 | 若正文要报告调整模型结果，需锁定具体模型和协变量；绘图本身未见数据缺口 | 可绘制 |
| Figure 5E | training setting 分层探索性差异 | `responses.csv`、`table2_student_randomization_baseline.csv` 与相关派生表可用 | 分层样本量有限；若要宣称异质性效应，需要预先指定交互/异质性检验模型。当前更适合标注 exploratory | 可绘制探索图 |

## 需要向第一作者补充或确认的数据

1. **正式逐题 defect adjudication 表**  
   建议字段：`item_id`、`source`、`major_defect`、`critical_defect`、`defect_category`、`adjudicator_id`、`final_decision`、`adjudication_note`。该表将决定 Figure 2C、2D、3B 以及 Figure 4E 的正式分母。

2. **人工卷效率数据**  
   至少需要：人工卷总用时、专家用时、非专家用时、人工成本、最终纳入题目数、非缺陷题数、时间记录来源与时间粒度。当前不得填补或推算这些值。

3. **来源识别与 source-task rating 完整性说明**  
   当前来源识别统计显示 94 个 item，而最终题库为 100 题。需补齐缺失 item，或明确说明来源识别任务只纳入 94 个 item 的原因。

4. **专家评分量表与异常值清洗规则**  
   当前存在超过 5 分量表范围的评分/均值信号，需确认是数据录入错误、量表转换错误，还是脚本聚合问题。

5. **Figure 1 的最终整合图资产**  
   若 Figure 1 要提交为单张多 panel journal-ready 图，需要最终版式、prompt 或图像资产。目前仓库内主要是分 panel 文件与脚本生成结果。

6. **统计模型锁定**  
   Figure 2E、3D、5D、5E 如需推断性结论，应由作者确认模型形式、协变量、置信区间/检验方法和多重比较处理。

## 当前绘制建议

可以继续绘制或定稿的数据充分 panel：Figure 1D、1E、3C、3E、5A、5B、5C、5D，以及标注为探索性的 5E。

可以绘制但需在图注或方法中明确限制的 panel：Figure 1A-C、2A、2B、2E、3A、3D、4A、4B、4C。

不建议作为正式比较图绘制的 panel：Figure 2C、2D、3B 若未补正式人工 adjudication，只能标注为 proxy；Figure 4D-F 在缺少人工卷效率数据前，不能绘制完整人类 vs AI 效率比较，只能保留 MAS-only 观测结果或标注缺数据。
