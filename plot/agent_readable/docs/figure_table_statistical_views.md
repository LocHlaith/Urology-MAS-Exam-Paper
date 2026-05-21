保密说明：本文档采用虚构题目编号和示例，不包含真实来源揭盲信息。真实来源标签应仅在数据库锁定和盲法评分完成后合并。

# **0. 先理解“统计粒度”：每一行数据代表什么**

统计粒度是本研究最容易混淆、也最决定统计方法的概念。所谓统计粒度，就是数据库中“一行”代表的观察单位。AI/MAS 与人工题目的比较不能简单地把所有评分或所有作答堆在一起做 t 检验，因为同一专家会评很多题，同一道题会被很多专家评，同一考生也会回答很多题。

|                         |                               |                                                                |                                                        |
|-------------------------|-------------------------------|----------------------------------------------------------------|--------------------------------------------------------|
| **粒度**                | **一行代表什么**              | **典型数据表**                                                 | **主要用途**                                           |
| 题目级 item-level       | 一行=一道题                   | item\_master.csv、text\_features.csv、defect\_adjudication.csv | 题目来源、主题、认知层级、题型、文本特征、最终缺陷状态 |
| 专家×题目 rater-item    | 一行=某专家对某题的一次评分   | expert\_ratings.csv                                            | 质量评分、分维度评分、缺陷判断、来源猜测               |
| 考生×题目 student-item  | 一行=某考生对某题的一次作答   | responses.csv                                                  | 正确率、题目难度、混合模型、CTT 指标                   |
| 考生×题块 student-block | 一行=某考生在一个题块的成绩   | derived\_block\_scores.csv                                     | 同一考生 MAS block 与 Human block 配对比较             |
| 候选题级 candidate-item | 一行=MAS 流程生成的一道候选题 | mas\_candidate\_log.csv                                        | AI 自动筛查、候选题流失、专家入卷审核                  |
| 工作流级 workflow-level | 一行=人工或 MAS 整套流程      | workflow\_total\_time\_cost.csv                                | 总耗时、专家耗时、API 成本、每道合格题时间             |

虚构例子：题目 Q\_STONE\_014 是一道“输尿管结石合并感染的下一步处理”题。题目级表中它只有一行；若 5 位专家评分，它在 expert\_ratings.csv 中有 5 行；若 52 名住院医作答，它在 responses.csv 中有 52 行。统计模型必须承认这些重复测量结构，否则会夸大样本量。

# **Figure 1. Auditable MAS workflow and two-sequence validation design**

统计视角：工作流验证与研究设计说明。Figure 1 不承担疗效或质量差异检验任务，而是向读者交代 MAS 题目如何生成、如何被安全筛查、如何入卷、考生如何被随机到 A/B 双顺序，以及最终研究终点如何组织。

|                         |                           |                                                         |                                                                               |                                                                                             |
|-------------------------|---------------------------|---------------------------------------------------------|-------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------|
| **Panel**               | **分析粒度**              | **数据来源**                                            | **设计目的**                                                                  | **具体例子**                                                                                |
| A 题库输入与 MAS 生成   | 工作流级/资料源级         | prompt\_log、source\_material\_catalog、exam\_blueprint | 说明 MAS 不是自由生成，而是在授权材料、考试蓝图、题型和认知层级约束下生成。   | 例：输入“结石、肿瘤、感染、尿控”等蓝图域，并要求每域含 knowledge/application/reasoning 题。 |
| B AI 自动评分与安全筛查 | 候选题级                  | mas\_candidate\_log                                     | 展示 AI safety gate：答案键校验、指南一致性、多个合理答案、潜在不安全建议等。 | 例：候选题 C027 被 AI 标记为“multiple plausible answers”，未进入专家入卷审核。              |
| C 专家平行入卷审核      | 候选题×专家或候选题裁决级 | safety\_screening\_log、mas\_candidate\_log             | 说明入卷前专家审核仅是安全控制，不是最终盲法主评分。                          | 例：两名专家均认为 C031 题干歧义，最终排除；C044 经轻微修改后入卷。                         |
| D A/B 双顺序考试设计    | 考生级                    | exam\_form\_assignment.csv                              | 说明 Form A=Human→MAS，Form B=MAS→Human，并在 training setting 内随机。       | 例：S001 被分到 A 先做人类题块；S002 被分到 B 先做 MAS 题块。                               |
| E 终点域框架            | 概念级/终点级             | 所有终点汇总表                                          | 把质量、安全、认知边界、来源辨识、学生表现和效率放在同一验证框架。            | 例：即使平均质量非劣，若 critical defect 不可接受，仍不能主张无条件部署。                   |

常见误区：不要把 Figure 1 做成“AI 流程宣传图”。它应是可审计 validation workflow：生成、筛查、盲法评分、考试随机化和结果分析之间的边界必须清楚。

# **Figure 2. Primary expert-rated quality and safety-critical defects**

统计视角：盲法专家质量评价与安全关键缺陷。Figure 2 是质量主证据所在，核心是“MAS 辅助题目在盲法专家复合质量评分上是否非劣于人工题目，同时不增加 major/critical defects”。

|                          |                                       |                                        |                                                                         |                                                                                                                                                                                            |
|--------------------------|---------------------------------------|----------------------------------------|-------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Panel**                | **分析粒度**                          | **数据来源**                           | **设计目的**                                                            | **具体例子/模型**                                                                                                                                                                          |
| A 主终点森林图           | 专家×题目                             | expert\_ratings + item\_master         | 估计 MAS-Human 复合质量评分差，并与非劣效界值比较。                     | 模型：quality\_score \~ source + topic + cognitive\_level + item\_type + has\_vignette + (1\|rater\_id)+(1\|item\_id)。例：MAS-Human=-0.08，95%CI -0.21\~0.06，若下限&gt;-0.30，可判非劣。 |
| B 分维度评分             | 专家×题目×维度                        | expert\_ratings 长表                   | 识别 MAS 在哪些维度可能短板，例如排他性、防猜性、思维性，而不仅看总分。 | 例：MAS 流畅性接近人工，但“干扰项迷惑性”低 0.25 分，提示干扰项设计需加强。                                                                                                                 |
| C major/critical defects | 主图用题目级裁决；敏感性可用专家×题目 | defect\_adjudication + expert\_ratings | 评价安全底线，避免平均分掩盖答案键错误、多个合理答案或指南不一致。      | 例：Q\_INFECT\_009 被最终裁定存在“多个合理答案”，记为 major defect；若涉及不安全处置，则记为 critical。                                                                                    |
| D 缺陷裁决流程           | 题目级流程                            | defect\_adjudication\_log              | 说明独立评审、分歧处理、第三方裁决，提升主观判断可信度。1               | 例：100 题中 7 题被至少一名专家标记，最终 3 题经裁决为 major defect。                                                                                                                      |
| E 专家一致性             | 专家×题目                             | expert\_ratings                        | 检验评分体系可靠性：连续分数用 ICC，二分类缺陷用 kappa/Gwet AC1。       | 例：质量总分 ICC=0.72 表示专家评分可靠性尚可；缺陷事件稀少时报告一致率和 Gwet AC1 更稳。                                                                                                   |

解释边界：Figure 2 的非劣效结论不能脱离安全门槛。平均质量评分非劣并不意味着可以取消人工终审；critical defects 必须单独报告，并作为 safety veto。

# **Figure 3. Performance boundaries by cognitive level**

统计视角：认知层级能力边界。Figure 3 回答的不是“MAS 总体是否能出题”，而是“MAS 在 knowledge、application、reasoning 三个认知复杂度层级上的表现是否不同”。这是数字医学叙事中最重要的能力边界分析。

|                                |                      |                                                   |                                                                    |                                                                                                                                          |
|--------------------------------|----------------------|---------------------------------------------------|--------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------|
| **Panel**                      | **分析粒度**         | **数据来源**                                      | **设计目的**                                                       | **具体例子/解释**                                                                                                                        |
| A 专家质量评分差               | 专家×题目            | expert\_ratings + item\_master                    | 比较每个认知层级内 MAS-Human 质量评分差。                          | 例：knowledge +0.02；application -0.05；reasoning -0.28。若 reasoning 明显更低，提示高阶临床推理题是 MAS 边界。                          |
| B 缺陷风险差                   | 题目级裁决           | defect\_adjudication + item\_master               | 比较不同认知层级内 major/critical defect 风险差。                  | 例：reasoning 层级中 MAS 2/12 有 major defect，Human 0/10，有必要加强高阶题 safety gate。                                                |
| C 学生正确率差                 | 考生×题目            | responses + item\_master + exam\_form\_assignment | 评估实际考试中 MAS 与人工题的难度校准是否随认知层级变化。          | 模型：correct \~ source\*cognitive\_level + block\_position + order\_group + setting + training\_year + topic + (1\|student)+(1\|item)。 |
| D source×cognitive\_level 交互 | 专家×题目或考生×题目 | expert\_ratings 或 responses                      | 正式检验 MAS-Human 差距是否随认知层级升高而扩大。                  | 交互解释：\[(MAS-Human)\_reasoning - (MAS-Human)\_knowledge\]。例：-0.30 表示从知识到推理，MAS 相对差距扩大 0.30 分。                    |
| E 探索性 CTT 指标              | 题目级               | responses 派生 + item\_master                     | 展示难度、区分度、干扰项效率；主文可只放一个指标，完整 CTT 放 SI。 | 例：Q\_STONE\_014 正确率 0.42、item-rest r=0.31、干扰项效率 0.75，说明偏难但有区分度。                                                   |

研究生要点：Panel C 的正确率差不等于质量差。正确率低可能是题目更难、认知层级更高、主题更偏或位置更靠后导致疲劳。因此必须调整 block\_position、topic 和 cognitive\_level。

# **Figure 4. Source detectability and aggregate quality-adjusted efficiency**

统计视角：来源辨识与总量质量校正效率。Figure 4 将“能否看出 AI 来源”和“是否节省人力”分开处理。不可辨识不等于质量等同；效率也必须按照整卷总量和质量校正指标计算。

|                           |                 |                                                        |                                                                                      |                                                                                |
|---------------------------|-----------------|--------------------------------------------------------|--------------------------------------------------------------------------------------|--------------------------------------------------------------------------------|
| **Panel**                 | **分析粒度**    | **数据来源**                                           | **设计目的**                                                                         | **具体例子/解释**                                                              |
| A 来源辨识准确率          | 评价者×题目     | source\_detection.csv 或 expert\_ratings/source\_guess | 评价专家或学生是否能稳定区分 MAS 与人工题；建议报告 accuracy 和 balanced accuracy。  | 例：balanced accuracy=0.52，90%CI 0.47\~0.56，接近随机，但不能推出质量相同。   |
| B 混淆矩阵                | 评价者×题目汇总 | source\_guess + source\_true                           | 观察真 MAS/真人工分别被猜成 MAS 或 Human 的比例。                                    | 例：许多人工题也被猜为 AI，可能说明人工题格式模板化，而不是 MAS 完全像人类。   |
| C sensitivity/specificity | 评价者×题目     | source\_guess + source\_true                           | 拆分真 MAS 被识别为 MAS 的能力和真人工被识别为人工的能力。                           | 例：sensitivity 0.60、specificity 0.44，说明评价者偏向猜 AI。                  |
| D 整卷总人力时间          | 工作流级        | workflow\_total\_time\_cost.csv                        | 比较 Human 与 MAS 工作流的 total human time、expert time、nonexpert time、API cost。 | 例：Human 总人力 1200 分钟，MAS 总人力 360 分钟；不得做人工与 MAS 逐阶段比较。 |
| E 每道合格题/无缺陷题时间 | 工作流级派生    | workflow\_total\_time\_cost + defect counts            | 用质量校正效率避免“快但缺陷多”的误导。                                               | 例：MAS 360/45=8.0 分钟/无重大缺陷题；Human 1200/48=25.0 分钟/无重大缺陷题。   |
| F 时间敏感性分析          | 情景级          | scenario\_time\_cost.csv                               | 评估人工时间±20%、MAS 时间±20%、不同专家时薪假设下结论是否稳健。                     | 例：即使 MAS 时间+20%、人工时间-20%，MAS 每道无缺陷题仍更省人力。              |

关键表述：Source detectability near chance means evaluators could not reliably identify source; it does not prove educational equivalence. Efficiency claims should be expressed as aggregate quality-adjusted workflow efficiency, not step-by-step process superiority. 草案要求人工流程只有整卷总时间时，主文避免逐阶段比较。

# **Figure 5. Examinee-level performance and block-order effects**

统计视角：考生表现与题块顺序效应。Figure 5 关注真实考试中同一考生在 MAS 与人工题块上的表现，以及 A/B 顺序是否造成疲劳或练习效应。

|                             |                      |                                       |                                                                     |                                                                                                                                           |
|-----------------------------|----------------------|---------------------------------------|---------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------|
| **Panel**                   | **分析粒度**         | **数据来源**                          | **设计目的**                                                        | **具体例子/模型**                                                                                                                         |
| A A/B 顺序示意              | 设计级               | exam\_form\_assignment                | 说明 Form A=Human→MAS，Form B=MAS→Human。                           | 例：S001 属于 A，先做人类题块；S026 属于 B，先做 MAS 题块。                                                                               |
| B 每名考生配对题块得分      | 考生×题块            | responses 派生 block\_scores          | 同一考生内部比较 MAS block 与 Human block，这是配对比较的正确位置。 | 例：S001 Human 40/50、MAS 38/50；S002 Human 34/50、MAS 35/50。                                                                            |
| C 个体内差值分布            | 考生级               | block\_scores                         | 展示 MAS-Human 分数差是否围绕 0，按 Form A/B 着色观察顺序效应。     | 例：差值=MAS\_score-Human\_score；若 B 组普遍更低，可能存在第二题块疲劳或顺序影响。                                                       |
| D 调整后正确率差模型        | 考生×题目            | responses + item\_master + assignment | 估计控制题目、考生、顺序、setting 后的总体 MAS-Human 正确率差。     | 模型：correct \~ source + block\_position + order\_group + setting + training\_year + topic + cognitive\_level + (1\|student)+(1\|item)。 |
| E training setting 探索展示 | 考生级或模型分层估计 | responses + assignment                | 展示主院区/非主院区异质性，但不作确证性推断。                       | 例：main setting 差值 +1.5pp，non-main -2.0pp；只能说探索性差异，不能说中心效应成立。                                                     |

常见误区：Form A 与 Form B 是不同考生组，不是配对。配对分析只适用于同一考生的 MAS block 与 Human block。

# **Main Tables. 主表的统计视角**

|                                                      |              |                                                    |                                                                                               |                                                                                                         |
|------------------------------------------------------|--------------|----------------------------------------------------|-----------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------|
| **Table**                                            | **分析粒度** | **数据来源**                                       | **设计目的**                                                                                  | **具体例子/解释**                                                                                       |
| Table 1. Item blueprint and textual characteristics  | 题目级       | item\_master.csv、text\_features.csv               | 证明 MAS 与人工题在主题、认知层级、题型、病例题比例和文本长度上可比；为后续模型调整提供依据。 | 例：Human 组 reasoning 10 题、MAS 组 reasoning 12 题；若不调整 cognitive\_level，质量差比较可能偏倚。   |
| Table 2. Examinee baseline and randomization balance | 考生级       | exam\_form\_assignment.csv、baseline.csv           | 描述 Form A 与 Form B 在 training setting、training year、既往成绩等方面是否平衡。            | 例：A 组 26 人，B 组 25 人；main/non-main 比例接近。该表主要描述，不需要堆砌显著性检验。                |
| Table 3. Primary and key secondary endpoints         | 结果汇总级   | 模型输出汇总、defect、source detection、efficiency | 将主终点和关键次要终点压缩成审稿人一眼可读的结果矩阵。                                        | 例：质量评分 MAS-Human=-0.08；major defect RD=+2.0pp；balanced accuracy=0.52；每道无缺陷题时间比=0.32。 |

# **Supplementary Figures and Tables. 补充材料的统计视角**

|                                                              |                     |                                                          |                                                                                        |                                                                               |
|--------------------------------------------------------------|---------------------|----------------------------------------------------------|----------------------------------------------------------------------------------------|-------------------------------------------------------------------------------|
| **SI Figure**                                                | **分析粒度**        | **数据来源**                                             | **设计目的**                                                                           | **具体例子/解释**                                                             |
| Supplementary Fig. 1 MAS architecture and audit trail        | 工作流级/候选题级   | prompt\_log、mas\_candidate\_log、safety\_screening\_log | 展示 MAS 代理架构、提示词链、自动评分、阈值、专家筛查和审计轨迹。                      | 例：生成 180 道候选题，AI gate 排除 70 道，专家筛查排除 20 道，最终选 50 道。 |
| Supplementary Fig. 2 AI/LLM scoring vs blinded expert rating | 题目级或专家×题目   | LLM\_judge\_scores、expert\_ratings                      | 说明 AI 大法官评分与专家评分的一致性，只作为探索性验证，不进入主终点。                 | 例：Bland-Altman 显示 LLM 对低质量题有轻微高估倾向。                          |
| Supplementary Fig. 3 Full CTT analysis                       | 题目级              | responses 派生                                           | 完整展示 difficulty、discrimination、distractor efficiency、KR-20/alpha bootstrap CI。 | 例：某题 p=0.88 但 discrimination=0.05，说明太容易且区分度弱。                |
| Supplementary Fig. 4 Source misclassification analysis       | 题目级或评价者×题目 | source\_guess、item\_master、text\_features              | 解释哪些题容易被误判为 AI 或人工，避免把不可辨识过度解释为质量等同。                   | 例：解析过于模板化的人工题也可能被猜为 AI。                                   |
| Supplementary Fig. 5 Efficiency sensitivity analysis         | 工作流×情景级       | workflow\_total\_time\_cost、scenario\_time\_cost        | 检验效率结论在时间和成本假设改变时是否稳健。                                           | 例：专家时薪从 300 到 800 元/小时，MAS 仍降低质量校正成本。                   |

|                                                               |                       |                                                   |                                                                                         |                                                                                    |
|---------------------------------------------------------------|-----------------------|---------------------------------------------------|-----------------------------------------------------------------------------------------|------------------------------------------------------------------------------------|
| **SI Table/Methods**                                          | **分析粒度**          | **数据来源**                                      | **设计目的**                                                                            | **具体例子/解释**                                                                  |
| Supplementary Table 1 Prompt templates and model settings     | 工作流步骤级          | prompt\_log、model\_config                        | 提高 MAS 工作流可复现性：模型版本、温度、检索材料、禁止项、输出格式。                   | 例：generation temperature=0.3，safety-check temperature=0.0。                     |
| Supplementary Table 2 AI threshold and expert screening rules | 候选题级/规则级       | mas\_candidate\_log、screening\_rules             | 说明入卷前安全筛查标准与排除原因。                                                      | 例：AI\_score&lt;3.5 或 answer\_key\_conflict flag 直接进入人工复核或排除。        |
| Supplementary Table 3 Item-level analysis                     | 题目级                | item\_master、expert\_summary、responses\_summary | 逐题列出 source、topic、cognitive\_level、quality、defect、difficulty、discrimination。 | 例：Q\_URO\_022：application，质量均分 4.2，difficulty 0.63，discrimination 0.28。 |
| Supplementary Table 4 Text overlap and readability            | 题目级或题目×资料源级 | text\_features、source\_material\_catalog         | 评估文本重叠和文本新颖性，避免声称“证明原创性”。                                        | 例：与教材片段 cosine similarity=0.42，5-gram overlap=0.08。                       |
| Supplementary Methods Statistical analysis plan               | 方法级                | SAP 文档、代码版本、锁库记录                      | 记录非劣效界值、模型、聚类处理、缺失值、敏感性分析、source unblinding 程序。            | 例：解盲前锁定 -0.30/5 分界值，并预设盲态 pooled SD 敏感性分析。                   |

# **结果解释模板：从统计结果到论文语言**

|              |                                                     |                                                                                                                    |
|--------------|-----------------------------------------------------|--------------------------------------------------------------------------------------------------------------------|
| **结果类型** | **虚构结果**                                        | **推荐解释边界**                                                                                                   |
| 专家质量非劣 | MAS-Human=-0.08, 95%CI -0.21 to 0.06, margin=-0.30  | 可写：MAS-assisted items were noninferior in blinded expert-rated quality. 不可写：MAS 质量优于人工。              |
| 认知层级边界 | reasoning 交互项=-0.30, 95%CI -0.55 to -0.05        | 可写：quality margins narrowed for high-complexity reasoning items. 不可写：AI 不能做临床推理题。                  |
| 缺陷风险     | major defect RD=+4pp, 95%CI -3 to +12pp             | 可写：no statistically clear excess was observed, but uncertainty remains. 若 critical defect 出现，必须单独讨论。 |
| 来源辨识     | balanced accuracy=0.52, 90%CI 0.47 to 0.56          | 可写：evaluators could not reliably distinguish source. 不可写：AI 与人工质量完全相同。                            |
| 效率         | time per nondefective item: MAS 8min vs Human 25min | 可写：MAS workflow reduced aggregate quality-adjusted human time. 不可写：每个阶段 MAS 都优于人工。                |

# **附录：推荐数据库主键与连接关系**

|               |                            |                                                                                    |
|---------------|----------------------------|------------------------------------------------------------------------------------|
| **字段**      | **作用**                   | **连接关系**                                                                       |
| item\_id      | 所有题目相关表的核心连接键 | item\_master ↔ expert\_ratings ↔ responses ↔ defect\_adjudication ↔ text\_features |
| rater\_id     | 专家评分者标识             | expert\_ratings 中用于随机效应和一致性分析                                         |
| student\_id   | 考生标识                   | responses ↔ exam\_form\_assignment ↔ baseline                                      |
| candidate\_id | MAS 候选题标识             | mas\_candidate\_log ↔ safety\_screening\_log；final\_item\_id 连接到 item\_master  |
| case\_id      | 共享病例题干标识           | 同一病例下多个小题可用 case\_id 标记；敏感性分析可考虑 (1\|case\_id)               |

最终建议：每次做模型前先问“一行代表什么”。只要粒度判断正确，模型公式、聚类处理、图表解释和审稿回复都会清晰很多。
