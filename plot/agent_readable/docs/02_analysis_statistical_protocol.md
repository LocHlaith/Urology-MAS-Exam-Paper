# 转换来源：`plot/raw/MAS_Statistical_Protocol_Package/Analysis_Statistical_Protocol.docx`

## 转换元数据

- 来源路径：`plot/raw/MAS_Statistical_Protocol_Package/Analysis_Statistical_Protocol.docx`
- 来源 SHA256：`c2123c878cd32d373d3241d7c8a56fd8ccc6c85852ee076d414ef0f9604e4901`
- 生成时间：`2026-05-19T21:04:44`
- 转换方法：pandoc docx -> GitHub-Flavored Markdown (`--wrap=none`)
- Agent 规则：将“原始摘录”部分视为来源材料。不要从本文件推断缺失的统计量、panel 标签、样本量或图形样式。

## Agent 特别警示

原文中的 `source_key.csv`、`item_master.csv`、`expert_ratings.csv`、`responses.csv` 等名称是统计 protocol 设想的数据表名，不代表当前仓库已经存在这些锁定分析表，也不是图片交付格式。正式图片交付仍为可编辑 PDF。

## 原始摘录

**分析与统计 Protocol**

MAS 辅助泌尿外科住院医闭卷考试命题研究 · Statistical Analysis Protocol

用途：供研究生、统计师与临床专家在同一套术语下理解每张图表的统计单位、数据来源、模型层级与结果解释边界。

保密说明：本文档采用虚构题目编号和示例，不包含真实来源揭盲信息。真实来源标签应仅在数据库锁定和盲法评分完成后合并。

# **1. 研究目标与总体设计**

本研究目标是验证一个可审计、专家在环的多智能体 AI/MAS 命题工作流，在泌尿外科住院医闭卷考试题目生成中的质量、安全性、认知层级边界、来源辨识、考生表现和总量效率。研究设计为 single-institution, two-setting, randomized two-sequence block-order validation study。

-   考试由两个 50 题题块组成：一个 MAS-assisted block，一个 human-written block。

-   Form A = Human → MAS；Form B = MAS → Human。

-   在 training setting 内进行随机分配；training setting 分为 main 与 non\_main。

-   主终点仅使用最终盲法专家复合质量评分；入卷前 AI 和专家筛查属于工作流安全控制。

-   training year 作为描述变量或协变量，不作为主要分层推断依据。

# **2. 盲法、锁库与来源标签管理**

所有题目在专家评分和来源辨识阶段均应使用 blinded item\_id。真实来源 source\_true 不得出现在专家评分表中。专家或学生的“该题是否为 AI”判断应记录为 source\_guess，而非 source\_true。

| **文件**                    | **可见范围**       | **关键内容**                                      | **控制原则**               |
|-----------------------------|--------------------|---------------------------------------------------|----------------------------|
| blinded\_rating\_sheet.xlsx | 专家可见           | 题干、选项、答案解析、评分维度、source\_guess     | 不得包含真实来源标签。     |
| source\_key.csv             | 仅数据管理员可见   | item\_id, source\_true                            | 评分锁定后再合并。         |
| item\_master.csv            | 统计团队解盲后可见 | source\_true, topic, cognitive\_level, item\_type | 用于所有模型的核心桥接表。 |

# **3. 数据表与变量字典**

| **数据表**                      | **粒度**              | **关键变量**                                                                                                                              | **用途**                                 |
|---------------------------------|-----------------------|-------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------|
| item\_master.csv                | 题目级                | item\_id, source\_true, topic, cognitive\_level, item\_type, has\_vignette, case\_id                                                      | 蓝图平衡、模型协变量、所有题目级合并。   |
| expert\_ratings.csv             | 专家×题目             | rater\_id, item\_id, rater\_phase, quality\_score, dimension\_scores, major\_defect, critical\_defect\_type, source\_guess                | 主终点、分维度评分、缺陷判断、来源辨识。 |
| defect\_adjudication.csv        | 题目级                | item\_id, final\_major\_defect, final\_critical\_defect, adjudication\_reason                                                             | 最终缺陷状态；安全分析主图。             |
| responses.csv                   | 考生×题目             | student\_id, item\_id, selected\_option, correct, response\_time\_optional                                                                | 正确率模型、CTT、题块得分派生。          |
| exam\_form\_assignment.csv      | 考生级                | student\_id, form, order\_group, training\_setting, training\_year, prior\_score\_optional                                                | 随机化平衡、顺序效应、考生协变量。       |
| mas\_candidate\_log.csv         | 候选题级              | candidate\_id, AI\_score, AI\_flags, pass\_AI\_threshold, expert\_screen\_decision, exclusion\_reason, final\_item\_id                    | MAS 漏斗、AI threshold 效能、安全筛查。  |
| workflow\_total\_time\_cost.csv | 工作流级              | workflow, total\_minutes, total\_expert\_minutes, total\_nonexpert\_minutes, api\_cost, number\_final\_items, number\_nondefective\_items | 总量效率与质量校正效率。                 |
| text\_features.csv              | 题目级或题目×资料源级 | item\_id, word\_count, readability, ngram\_overlap, cosine\_similarity                                                                    | 文本重叠、文本新颖性、模板化程度。       |

# **4. 终点层级**

| **终点层级**                  | **指标**                                              | **分析粒度**                | **判定与解释**                                                                          |
|-------------------------------|-------------------------------------------------------|-----------------------------|-----------------------------------------------------------------------------------------|
| Primary endpoint              | 盲法专家复合质量评分                                  | 专家×题目                   | 非劣效：MAS-Human 95%CI 下限 &gt; -δ。推荐 δ=-0.30/5 分，同时报告 -0.20 SD 敏感性解释。 |
| Key safety endpoint           | major defect 与 critical defect                       | 题目级裁决；专家×题目敏感性 | critical defect 单独报告，可作为 safety veto。                                          |
| Cognitive boundary endpoint   | source×cognitive\_level 交互                          | 专家×题目或考生×题目        | 检验 MAS-Human 差距是否随认知层级增加而扩大。                                           |
| Examinee performance endpoint | 正确率、题块得分                                      | 考生×题目；考生×题块        | 估计难度校准、题块顺序与疲劳效应。                                                      |
| Source detectability endpoint | accuracy、balanced accuracy、sensitivity、specificity | 评价者×题目                 | 45%–55% 严格等效区间可用于“接近随机辨识”的判断。                                        |
| Efficiency endpoint           | 总人力时间、每道合格题时间、每道无重大缺陷合格题时间  | 工作流级                    | 只做整卷总量比较；不做人工与 MAS 逐阶段比较。                                           |

# **5. 主终点模型：专家盲法质量评分非劣效**

主模型：

quality\_score \~ source + topic + cognitive\_level + item\_type + has\_vignette + (1 \| rater\_id) + (1 \| item\_id)

核心估计量为调整后的 MAS-Human 均值差。判定规则：95%CI 下限高于预设非劣效界值 -δ，则认为 MAS-assisted items 在盲法专家质量评分上非劣。

虚构例子：共有 100 道最终入卷题，5 位专家评分，共 500 行 expert\_ratings。模型估计 MAS-Human=-0.08，95%CI -0.21 到 0.06。若预设 δ=-0.30，则结论为非劣；但如果同批数据出现不可接受 critical defect，结论必须限制为“专家在环条件下可接受”，不能说完全替代人工。

# **6. 分维度评分与评分一致性**

分维度评分可采用与主模型类似的混合模型，按维度分别估计 MAS-Human 差值。若维度较多，建议控制解释重点，不把每个维度都作为主要终点。

-   连续总分或维度分：ICC 或混合模型方差成分。

-   有序等级：weighted kappa。

-   二分类缺陷：kappa、Gwet AC1 或一致率；事件稀少时 Gwet AC1 更稳。

# **7. major/critical defects 分析**

优先使用 adjudicated item-level defect status 作为主图和主要安全表述。专家独立缺陷判断用于一致性和敏感性分析。

若事件数足够，可用混合 logistic：major\_defect \~ source + topic + cognitive\_level + item\_type + (1\|rater\_id)+(1\|item\_id)。若不收敛或事件过少，预设降级为题目级风险差、Fisher exact test 或 bootstrap CI。

虚构例子：MAS 50 题中 3 题 final\_major\_defect，Human 50 题中 1 题。风险差=+4 个百分点。若 CI 很宽，应解释为“不确定性较大”，而不是简单说 MAS 缺陷更多。

# **8. 认知层级边界分析**

认知层级必须在 source unblinding 前冻结，推荐三层：knowledge、application、reasoning。

| **层级**    | **定义**                                       | **虚构例子**                                                       |
|-------------|------------------------------------------------|--------------------------------------------------------------------|
| knowledge   | 事实、定义、指南推荐、诊断标准、并发症识别     | 例：无痛性肉眼血尿最常见提示膀胱肿瘤。                             |
| application | 单病情境下选择检查、诊断或治疗                 | 例：2 cm 肾盂结石、肾功能正常、无感染，选择合适处理策略。          |
| reasoning   | 复杂病例、多因素权衡、下一步处理、风险收益判断 | 例：感染性梗阻结石、休克、肾功能恶化，判断先解除梗阻而非单纯碎石。 |

关键模型：quality\_score \~ source\*cognitive\_level + covariates + (1\|rater\_id)+(1\|item\_id)。交互项解释为 MAS-Human 差距是否随认知层级变化。例如：\[(MAS-Human)\_reasoning - (MAS-Human)\_knowledge\] = -0.30，表示相对于知识题，推理题中 MAS 相对人工质量差距扩大 0.30 分。

# **9. 考生作答、题块得分与顺序效应**

考生×题目模型：

correct\_ij \~ source + block\_position + order\_group + training\_setting + training\_year + topic + cognitive\_level + (1 \| student\_id) + (1 \| item\_id)

认知边界扩展模型：

correct\_ij \~ source\*cognitive\_level + block\_position + order\_group + training\_setting + training\_year + topic + (1 \| student\_id) + (1 \| item\_id)

题块得分为考生×题块级派生数据，同一考生的 MAS block 与 Human block 可以配对展示。Form A 与 Form B 之间不是配对，只能做独立组比较或回归调整。

# **10. CTT 探索性测量学分析**

| **指标**              | **计算**                      | **解释边界**                                         |
|-----------------------|-------------------------------|------------------------------------------------------|
| difficulty / p-value  | 答对人数 / 作答人数           | 数值越高题越容易；不要把 p-value 当统计显著性 p 值。 |
| discrimination        | item-rest correlation         | 该题是否区分总分高低的考生；总分应排除该题本身。     |
| distractor efficiency | 有效干扰项数量 / 错误选项总数 | 有效干扰项可定义为至少 5% 考生或至少 2 名考生选择。  |
| KR-20/alpha           | 整卷或题块内部一致性          | 样本量小需 bootstrap CI，解释为探索性。              |

# **11. 来源辨识分析**

评价者×题目数据中 source\_guess 与 source\_true 合并后计算 accuracy、balanced accuracy、sensitivity、specificity。若允许“无法判断”，需预设主分析处理方式：作为第三类、作为错误，或排除后敏感性分析。

建议主解释使用 balanced accuracy 和 90%CI，并与 45%–55% 等效区间比较。来源不可辨识只说明评价者无法可靠判断来源，不证明质量相同。

# **12. 效率与成本分析**

由于人工流程通常只有整卷总时间，主文仅比较 workflow-level aggregate metrics。MAS 如果有逐阶段记录，可放 Supplement 描述，但不得与人工流程逐阶段直接比较。

| **指标**                   | **公式**                                            | **解释**                             |
|----------------------------|-----------------------------------------------------|--------------------------------------|
| Total human time           | total\_expert\_minutes + total\_nonexpert\_minutes  | 总人力投入。                         |
| Time per final item        | total\_human\_minutes / number\_final\_items        | 每道最终入卷题的人力时间。           |
| Time per nondefective item | total\_human\_minutes / number\_nondefective\_items | 质量校正效率，推荐作为核心效率指标。 |
| Total cost                 | expert\_cost + nonexpert\_cost + api\_cost          | 需预设时薪和 API 成本来源。          |

# **13. 缺失数据和异常值处理**

-   专家评分缺失：记录缺失原因；主模型可使用可用评分，敏感性分析可限制于完整评分题目。

-   考生作答缺失：未作答默认记为 incorrect；若技术性缺失，单独标记并做敏感性分析。

-   题目被考试后裁定 critical defect：主分析保留并标记；敏感性分析可排除该题，报告对正确率和 CTT 的影响。

-   极端作答时间如使用：预设截尾规则，例如低于 1 秒或高于 99th percentile 作为异常。

# **14. 多重性与推断层级**

本研究只设置一个 primary endpoint：盲法专家复合质量评分非劣效。其他分析，包括分维度评分、认知层级边界、CTT、来源辨识和效率，均为 key secondary 或 exploratory。解释时应避免把探索性显著性当作确证性结论。

# **15. 代码、复现与质量控制**

1\. 锁定 item\_master、expert\_ratings、responses 和 source\_key 的版本号。

2\. 在 source unblinding 前冻结 cognitive\_level、非劣效界值、主模型和缺失值规则。

3\. 所有图表均由分析数据集自动生成，不手工改数。

4\. 导出 fig3\_item\_level.csv、fig3\_rater\_item\_level.csv、fig3\_response\_level.csv 作为 Figure 3 的可追溯中间表。

5\. 每个主要模型保存公式、软件版本、包版本、随机种子和输出日志。

# **16. 建议的结果报告顺序**

1\. 先报告题目蓝图和随机化平衡，证明比较基础合理。

2\. 报告主终点专家质量非劣效，并立即报告 major/critical defects。

3\. 报告认知层级边界，强调 high-complexity reasoning items 的能力边界。

4\. 报告来源辨识，避免将不可辨识解释为质量等同。

5\. 报告考生表现与顺序效应，说明实际考试中的难度校准。

6\. 最后报告总量质量校正效率和敏感性分析。

# **17. 推荐论文句式**

-   Noninferiority was assessed using the adjusted mean difference in blinded expert-rated composite quality scores between MAS-assisted and human-written items.

-   Cognitive-level analyses were prespecified to identify potential performance boundaries across knowledge recall, clinical application, and higher-order reasoning items.

-   Critical defects were interpreted as a safety endpoint and were not averaged into the quality score.

-   Source detectability was interpreted as the ability to identify item origin, not as evidence of quality equivalence.

-   Efficiency was evaluated using aggregate workflow-level human time and quality-adjusted time per nondefective final item.

# **18. 交付给研究生的数据理解口诀**

先问粒度，再选模型；先锁来源，再做盲评；先看安全，再谈非劣；先调顺序，再比正确率；先做总量，再谈效率。
