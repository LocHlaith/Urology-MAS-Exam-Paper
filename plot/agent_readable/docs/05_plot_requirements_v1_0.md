# 转换来源：`plot/raw/作图-1.0.docx`

## 转换元数据

- 来源路径：`plot/raw/作图-1.0.docx`
- 来源 SHA256：`bbaeeebc4019bc79e264471b5a5045b2c08cfb0801b2e0941c4033ee3001306b`
- 生成时间：`2026-05-19T21:04:44`
- 转换方法：pandoc docx -> GitHub-Flavored Markdown (`--wrap=none`)
- Agent 规则：将“原始摘录”部分视为来源材料。不要从本文件推断缺失的统计量、panel 标签、样本量或图形样式。

## Agent 特别警示

本文是第一作者的主绘图要求来源。文中“数据字典最小修改”里的 `*.csv` 名称是建议的数据结构和变量命名，不是图片交付格式，也不代表仓库当前已有这些文件。后续绘图只能使用已经定位到的真实数据；缺失项写 `UNKNOWN_OR_CONFLICTING`。

## 原始摘录

**MAS辅助泌尿外科住院医闭卷考试命题研究  
最小增量数据分析、作图与补充材料完善方案**

*目标期刊优先适配：npj Digital Medicine；备选：JAMA Network Open、NEJM AI*

版本定位：单机构双院区（主院区与非主院区，约25+25）、同场考试、A/B双顺序题块随机分配、入卷前专家-AI平行安全筛查、最终专家盲法质量评价、来源辨识与总量效率/成本评估。

# 一、总判断：以机会最大的顶刊为主线

在 NEJM AI、JAMA Network Open、npj Digital Medicine 三个冲刺目标中，当前研究机会最大的仍是 npj Digital Medicine。理由不是样本量或临床外延强，而是本研究可以被重构为“可审计的多智能体AI工作流在专科医学评估生成中的前瞻性验证”。NEJM AI 更强调改变医学实践或患者结局；JAMA Network Open 需要更广泛的临床、政策或卫生经济学意义；npj Digital Medicine 的范围更能容纳数字医学、AI与真实工作流实施的交叉研究。

|                      |            |                                      |                                                                                                                                     |
|----------------------|------------|--------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------|
| **目标期刊**         | **适配度** | **当前机会**                         | **最小增量策略**                                                                                                                    |
| npj Digital Medicine | 最高       | 冲刺可行；若结果强，约20%–35%量级    | 把主线写成human-in-the-loop MAS workflow validation；主图突出安全闸门、critical defects、认知层级边界、来源辨识与总量质量校正效率。 |
| JAMA Network Open    | 中低       | 不建议首投；泌尿单机构小样本机会有限 | 只有在总时间节省非常显著且能转化为healthcare workforce/education efficiency时才可尝试；否则作为不现实冲刺。                         |
| NEJM AI              | 低         | 极高概率desk reject                  | 除非重构成通用医学AI评估基准或跨专科benchmark，否则不作为实际目标。                                                                 |

# 二、必须冻结的最终设计表述

-   设计名称：single-institution, two-setting, randomized two-sequence block-order validation study。

-   研究场景：主院区与非主院区，各约25名考生；非主院区可为合并场景，不进行单个分院区推断。

-   A/B顺序：按当前表格固定为 Form A = Human → MAS；Form B = MAS → Human。全文不得出现相反版本。

-   随机方式：建议仅按 training setting（主院区/非主院区）分层区组随机；PGY不再分层分析，只作为描述变量或协变量。

-   入卷前：采用AI自动评分/安全筛查，达到阈值后由另一批专家平行审核；此阶段为安全与组卷质量控制，不作为最终研究终点。

-   最终评分：采用另一组盲法专家进行题目质量评分、缺陷判断和来源辨识；主终点只使用人类专家盲法复合质量评分。

-   效率/成本：由于人工流程只能获得整卷总时间，主文只做总量比较与质量校正效率；不做人工与MAS逐阶段比较。

**建议Methods核心表述：**

> This was a single-institution, two-setting, randomized two-sequence block-order validation study conducted across main-campus and non-main-campus training settings. The examination consisted of two 50-item blocks: one MAS-assisted block and one human-written block. Form A presented the human-written block followed by the MAS-assisted block, whereas Form B presented the MAS-assisted block followed by the human-written block. Within each training setting, examinees were randomly assigned to Form A or Form B. The design enabled within-examinee comparison between item sources while partially controlling for block-order and fatigue effects. Training-setting analyses were exploratory because the study was not powered for setting-specific inference.

# 三、最小增加工作量的主文图表重构

目标是最大限度利用已计划数据，减少新增实验，把Figure从“医学教育考试流程”升级为“数字医学AI工作流验证”。正文建议控制为5张主图、3张主表；其余放Supplement。

|              |                                                                |                                                                                                                               |                                  |
|--------------|----------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------|----------------------------------|
| **正文元素** | **推荐标题**                                                   | **核心内容**                                                                                                                  | **工作量**                       |
| Figure 1     | Auditable MAS workflow and two-sequence validation design      | A：AI自动评分与安全筛查；B：专家平行审核入卷；C：A/B双顺序；D：主/非主院区随机；E：终点框架。                                 | 低：主要是重画流程图。           |
| Figure 2     | Primary expert-rated quality and safety-critical defects       | A：复合质量评分非劣效森林图；B：分维度评分；C：major/critical defects；D：adjudication；E：专家一致性。                       | 中：已有评分和缺陷数据即可。     |
| Figure 3     | Performance boundaries by cognitive level                      | 按knowledge/application/reasoning展示质量差、缺陷率、学生正确率、source×cognitive\_level模型结果。                            | 中：需要按cognitive\_level重算。 |
| Figure 4     | Source detectability and aggregate quality-adjusted efficiency | 来源辨识accuracy/balanced accuracy/混淆矩阵；整卷总人力时间、每道合格题时间、每道无重大缺陷合格题时间；人工总时间敏感性分析。 | 中低：效率部分改为总量。         |
| Figure 5     | Examinee-level performance and block-order effects             | 配对得分、MAS-human差值、A/B顺序效应、setting探索性展示。                                                                     | 低：已有responses即可。          |
| Table 1      | Item blueprint and textual characteristics                     | 主题、认知层级、病例题、题型、字数、指南年份、文本重叠/可读性。                                                               | 低到中：文本指标可自动计算。     |
| Table 2      | Examinee baseline and randomization balance                    | Form A vs Form B；主院区/非主院区；training year；既往成绩如有。                                                              | 低。                             |
| Table 3      | Primary and key secondary endpoints                            | 估计值、CI、预设界值、判定、解释级别。                                                                                        | 低。                             |

# 四、主图逐Panel修改方案

## Figure 1. Auditable MAS workflow and two-sequence validation design

参与者及研究流程

总共 56 名符合条件的候选人从邵逸夫医院的主院区（n=34）和非主院区（n=22）中依次被招募。为尽量减少选择偏差和伦理问题，实施了一套严格的排除标准。如果候选人符合以下任何一项标准，则会被排除在外：（1）在过去三个月内参与过类似的与人工智能相关的提案研究；（2）在评估内容方面存在显著的知识缺口（例如，由于长期病假或培训不足）；（3）属于弱势群体——排除研究机构的员工或研究者的下属——具体包括患有精神疾病、认知障碍、重症患者、未成年人、孕妇或文盲的人。

剩余的符合条件的参与者被随机分配接受测试试卷A 或试卷 B。初步测试表明，该评估的最短完成时间约为 15 分钟。根据项目反应理论的假设，仅通过随机猜测来正确回答单项选择题（SCQ）的概率估计为 0.20（1/5）。通过随机选择来正确回答不定项选择题（MRQ）的概率极低，接近于零。因此，那些在主观认知量表（SCQ）上的准确率在 0.15 至 0.25 之间，以及在记忆再现量表（MRQ）上的准确率在 0.00 至 0.05 之间的人，被归类为对该模块“没有掌握知识”。符合这些标准的个体（SCQ ≤ 0.25 且 MRQ ≤ 0.05）随后被排除在最终分析之外，以确保数据的准确性。最终我们筛选出邵逸夫医院的主院区（n=32）和非主院区（n=18）符合要求的样本进行下一步的分析。

我们整理了我院泌尿外科历年出科考试题原题作为人工泌尿外科出科考题库。同时摘取了人民卫生出版社第10版的外科学课本中有关泌尿外科的章节内容以及最新版的中国泌尿外科指南以及EAU指南，《中国执业医师规范化培训结业考核大纲（泌尿外科）》《吴阶平泌尿外科学》等作为MAS系统的出题大纲。使用大语言模型如Qwen、GPT-4等输入结构化Prompt进行出题。

鉴于我们生成的是泌尿外科出科考题目，因此我们的考试蓝图与我们现有的由人工专家命题并审核组卷的人工出科考试卷完全相同。详见文档1。

指南一致性即生成题目符合EAU指南或最新版的中国泌尿外科指南，答案键即ABCDE。其余项目都在LLM评分之内，critical defect flag包括与指南不一致，基础格式错误（答案键错误或缺少或过多，选项错误/歧义，题干错误/歧义，答案有歧义，以及其他严重的不合规缺陷）。

我们题库一共有XXX道题，在经过AI自动评分与安全筛查后，我们通过随机抽样的方法抽出其中的70道题，然后我们交给专家进行安全筛查与入卷控制，最终在优先满足试卷考点结构比例，题型比例要求后选取其中分值较高的50题组成MAS测试卷。

由浙江大学医学院附属邵逸夫医院的泌尿外科临床带教专家王老师出题并组卷，而后由其他几位泌尿外科临床带教专家定期更新题库与替换试题后，我们得到了一份人工专家测试卷。将两者进行组合成A卷与B卷，其中A卷是 Human→MAS，B卷是MAS→Human以尽可能排除考试过程中疲劳效应的干扰。然后将试卷随机分发给不同年级以及不同院区的考生。

-   Panel A：题库输入与MAS生成：授权历史材料、考试蓝图(暂缓）、指南/共识、题型与认知层级约束。

-   Panel B：AI自动评分与安全筛查：指南一致性、单一最佳答案、答案键校验、干扰项有效性、题干歧义、critical defect flag。

-   Panel C：专家平行入卷审核：仅用于安全筛查与入卷控制；不参与最终盲法主评分。

-   Panel D：考试设计：Form A = Human→MAS；Form B = MAS→Human；主院区/非主院区内随机。

-   Panel E：终点域：专家质量非劣效、major/critical defects、认知层级边界、来源辨识、学生表现、总量质量校正效率。

## Figure 2. Primary expert-rated quality and safety-critical defects

-   Panel A：主终点森林图。横轴为MAS-Human专家复合质量评分差；虚线为−0.30分或−0.20 SD非劣效界值。

-   Panel B：专家分维度评分。建议只保留人类专家rubric，不把AI大法官放入主图。

-   Panel C：major defects与critical defects。critical defects至少包括答案键错误、指南不一致、多个合理答案、潜在不安全建议。

-   Panel D：缺陷adjudication流程。展示独立判断、分歧、第三方裁决和最终缺陷状态。

-   Panel E：专家评分一致性：ICC、weighted kappa或一致率。

## Figure 3. Performance boundaries by cognitive level

-   Panel A：不同认知层级的专家质量评分差。

-   Panel B：不同认知层级的major/critical defect风险差。

-   Panel C：不同认知层级的学生正确率差。

-   Panel D：source × cognitive\_level交互模型估计。

-   Panel E：探索性CTT指标按认知层级或整体展示；若图面拥挤，CTT移至Supplement。

## Figure 4. Source detectability and aggregate quality-adjusted efficiency

-   Panel A：专家与学生来源辨识准确率及90% CI，叠加45%–55%严格等效区间。

-   Panel B：来源辨识混淆矩阵。

-   Panel C：balanced accuracy、sensitivity、specificity；若有confidence，可加AUC到Supplement。

-   Panel D：整卷总人力时间比较，区分专家人力、非专家人力、AI/API成本。

-   Panel E：每道最终合格题总人力时间，以及每道无重大缺陷合格题总人力时间。

-   Panel F：人工总时间敏感性分析：base case、人工时间−20%、人工时间+20%；避免逐阶段比较。

## Figure 5. Examinee-level performance and block-order effects

-   Panel A：A/B顺序示意。

-   Panel B：每名考生MAS题块与人工题块配对得分。

-   Panel C：MAS-Human个体内差值分布，按Form A/B着色。

-   Panel D：混合模型估计的总体MAS-human正确率差，调整block\_position、order\_group、training\_setting、training\_year、topic、cognitive\_level。

-   Panel E：主院区/非主院区探索性展示，用于说明队列同质性或异质性，不作确证性推断。

# 五、补充材料与SI图表最小包

|                       |                                                                                                   |              |            |
|-----------------------|---------------------------------------------------------------------------------------------------|--------------|------------|
| **SI项目**            | **内容**                                                                                          | **是否建议** | **工作量** |
| Supplementary Fig. 1  | MAS agent architecture与audit trail：生成、自动评分、阈值、专家平行审核、入卷。                   | 必须         | 低         |
| Supplementary Fig. 2  | AI大法官/LLM评分与盲法专家评分一致性：ICC、Bland-Altman或相关图。                                 | 建议         | 中         |
| Supplementary Fig. 3  | 探索性CTT全图：难度、区分度、干扰项效率、KR-20/alpha bootstrap CI。                               | 必须         | 中         |
| Supplementary Fig. 4  | 来源辨识misclassification analysis：被误判为AI/人类的题目特征。                                   | 建议         | 中         |
| Supplementary Fig. 5  | 效率敏感性分析：人工总时间±20%、MAS时间±20%、不同专家时薪假设。                                   | 必须         | 低         |
| Supplementary Table 1 | Prompt模板、模型版本、温度、检索材料、禁止项、输出格式。                                          | 必须         | 低         |
| Supplementary Table 2 | 入卷前AI评分阈值、专家安全筛查规则和排除原因。                                                    | 必须         | 中低       |
| Supplementary Table 3 | 逐题item analysis：source、topic、cognitive\_level、difficulty、discrimination、defect、quality。 | 必须         | 中         |
| Supplementary Table 4 | 文本重叠与可读性：Levenshtein、cosine similarity、n-gram overlap、字数。                          | 建议         | 低到中     |
| Supplementary Methods | 非劣效界值依据、盲态SD换算、SAP、代码版本。                                                       | 必须         | 低         |

# 六、统计分析计划：按npj Digital Medicine优先重写

## 6.1 主终点：专家盲法复合质量评分非劣效

主终点只设一个：盲法专家复合质量评分。AI自动评分和入卷前专家安全筛查只属于工作流质量控制，不进入主终点。

推荐模型：**  
quality\_score \~ source + topic + cognitive\_level + item\_type + has\_vignette + (1 \| rater\_id) + (1 \| item\_id)**

-   核心估计：MAS − Human 调整后均值差。

-   判定：95% CI下限 &gt; −δ。

-   δ建议：主尺度为−0.30/5分；同时报告标准化界值−0.20 SD。

-   如果缺少历史SD，可在解盲前用盲态pooled SD将−0.20 SD换算为原始分数，并同时报告−0.30分敏感性结果。

## 6.2 重大缺陷与critical defects

推荐模型：**  
major\_defect \~ source + topic + cognitive\_level + item\_type + (1 \| rater\_id) + (1 \| item\_id)**

-   若缺陷事件稀疏导致混合logistic不收敛，则预设降级为adjudicated item-level风险差、Fisher exact test或bootstrap CI。

-   critical defects单独报告，并设为安全否决项。即使平均质量评分非劣效，如果出现不可接受critical defect，也不能宣称工作流可无条件部署。

## 6.3 学生作答与顺序效应

主模型：**  
correct\_ij \~ source + block\_position + order\_group + training\_setting + training\_year + topic + cognitive\_level + (1 \| student\_id) + (1 \| item\_id)**

关键探索模型：**  
correct\_ij \~ source \* cognitive\_level + block\_position + order\_group + training\_setting + training\_year + topic + (1 \| student\_id) + (1 \| item\_id)**

-   source×cognitive\_level 是npjDM版本最重要的能力边界分析。

-   source×training\_setting仅作探索性展示，不作为结论依据。

-   Form A/B之间不是配对关系，不能用配对t检验；同一考生MAS vs Human题块得分才是配对分析。

## 6.4 来源辨识

-   主指标：accuracy、balanced accuracy、sensitivity、specificity。

-   严格等效区间：45%–55%；宽松敏感性区间可预设40%–60%，但不能事后改。

-   CI必须考虑rater与item聚类；如果混合模型复杂，可报告cluster bootstrap CI。

-   解释要谨慎：不可辨识不等于质量等同，只说明评价者无法稳定判断来源。

## 6.5 总量效率/成本

-   主分析：整卷总人力时间、每道最终合格题总人力时间、每道无重大缺陷合格题总人力时间。

-   区分：total human time、expert time、non-expert time、API cost。

-   人工流程只有总时间，因此不做逐阶段比较。MAS若有逐阶段记录，仅作为描述性SI。

-   必须报告time\_source和time\_granularity，避免审稿人质疑回忆偏倚。

# 七、还可以补充、但工作量不大的分析/实验

|                         |                                            |                                                          |                            |            |
|-------------------------|--------------------------------------------|----------------------------------------------------------|----------------------------|------------|
| **新增项目**            | **目的**                                   | **数据需求**                                             | **主文/SI**                | **优先级** |
| AI自动评分阈值效能分析  | 证明入卷前AI评分不是装饰，而能筛掉低质量题 | 每道MAS候选题AI评分、是否进入专家审核、专家审核结论      | SI为主，Figure 1可简化展示 | 高         |
| AI-专家安全筛查一致性   | 支持human-in-the-loop safety gate          | AI flag与专家critical defect判断                         | SI                         | 高         |
| MAS候选题流失图         | 展示生成→自动评分→专家审核→最终入卷的漏斗  | 候选题数量、筛除原因                                     | Figure 1或SI               | 高         |
| 文本重叠/可读性分析     | 回应“是否只是改写旧题”                     | 原始材料、MAS题、人工题文本                              | Table 1或SI                | 中         |
| 来源误判题特征分析      | 回应“不可辨识可能因专家题模板化”           | source guess、题干长度、cognitive level、quality score等 | SI                         | 中         |
| 总时间敏感性分析        | 弥补人工只有总时间的缺陷                   | 人工总时间、MAS总时间                                    | Figure 4或SI               | 高         |
| 高阶推理题案例审查      | 展示MAS能力边界，适合npjDM叙事             | reasoning题的质量、缺陷、正确率                          | 主文小段+SI表              | 中         |
| 盲态pooled SD换算margin | 增强非劣效界值来历                         | 专家评分盲态数据                                         | Methods/SI                 | 高         |

# 八、数据字典最小修改

-   exam\_form\_assignment.csv：campus改为training\_setting，取值main/non\_main；保留training\_year但不分层分析。

-   responses.csv：campus同样改为training\_setting；form定义统一为A=Human→MAS，B=MAS→Human。

-   expert\_ratings.csv：增加rater\_phase，区分pre-administration safety screening与blinded\_outcome\_rating。主终点只取blinded\_outcome\_rating。

-   新增mas\_candidate\_log.csv：candidate\_id、AI\_score、AI\_flags、pass\_AI\_threshold、expert\_screen\_decision、exclusion\_reason、final\_item\_id。

-   development\_time\_cost.csv改为workflow\_total\_time\_cost.csv：workflow、total\_minutes、total\_expert\_minutes、total\_nonexpert\_minutes、api\_cost、number\_final\_items、number\_nondefective\_items、time\_source、time\_granularity。

-   若MAS有逐阶段时间，另设mas\_phase\_time\_cost.csv；不得与人工流程做逐阶段对比。

|                                 |                                                                                                                                                                            |                                    |
|---------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------|
| **文件**                        | **关键变量**                                                                                                                                                               | **用途**                           |
| mas\_candidate\_log.csv         | candidate\_id, AI\_score, AI\_flags, pass\_AI\_threshold, expert\_screen\_decision, exclusion\_reason, final\_item\_id                                                     | 支持AI自动筛查和专家安全审核漏斗。 |
| workflow\_total\_time\_cost.csv | workflow, total\_minutes, total\_expert\_minutes, total\_nonexpert\_minutes, api\_cost, number\_final\_items, number\_nondefective\_items, time\_source, time\_granularity | 支持总量效率与质量校正效率。       |
| expert\_ratings.csv             | rater\_phase, rater\_id, item\_id, quality\_score, major\_defect, critical\_defect\_type                                                                                   | 区分入卷前安全筛查与最终盲法评分。 |
| item\_master.csv                | training\_blueprint\_domain, cognitive\_level, item\_type, has\_vignette, source\_material\_id, readability metrics                                                        | 支持蓝图平衡、认知层级和文本特征。 |

# 九、非劣效界值的可辩护写法

目前没有权威文献直接规定“医学考试题目5分专家质量评分的非劣效界值应为−0.30分”。最稳妥做法是采用三角支撑：CONSORT非劣效报告规范 + 医学教育非劣效方法学 + MID/half-SD分布法 + 本地专家共识/盲态SD换算。

-   主界值：−0.30/5分。

-   标准化解释：约等于−0.20 SD，小于常用half-SD MID经验阈值，因此属于保守的小效应劣势。

-   程序保障：数据锁定前预设；若使用盲态pooled SD换算，应在source unblinding前完成。

-   安全保障：非劣效通过仍需major/critical defect双门槛，不让平均分掩盖安全问题。

**建议Methods表述：**

> The noninferiority margin was prespecified before source unblinding as −0.30 points on the 5-point composite expert quality scale, corresponding approximately to a small standardized difference of −0.20 SD based on historical or blinded pooled expert-rating variability. Because no universally accepted minimally important difference exists for expert-rated examination-item quality, the margin was triangulated using noninferiority reporting guidance, methodological recommendations for equivalence and noninferiority designs in medical education, distribution-based interpretability benchmarks, and assessment-committee consensus. Noninferiority was interpreted together with safety requirements: no excess in major defects and no unacceptable critical defects.

# 十、删改清单：为提高npjDM机会必须做的清洁工作

|                                                   |                                                                       |
|---------------------------------------------------|-----------------------------------------------------------------------|
| **必须删/改**                                     | **替换为**                                                            |
| 三院区、three campuses、院区1/2/3、多中心教学成果 | 主院区/非主院区；two-setting internal validation；setting探索性展示。 |
| PGY1/2/3分层分析                                  | training\_year作为描述变量或协变量；不作分层推断。                    |
| A/B顺序互相矛盾                                   | 全文统一：A=Human→MAS，B=MAS→Human。                                  |
| 配对t检验比较A/B                                  | 独立样本比较或回归；配对分析仅用于同一考生MAS vs Human得分。          |
| 人工与MAS逐阶段时间分解比较                       | 整卷总时间、每道合格题时间、每道无重大缺陷合格题时间、敏感性分析。    |
| AI大法官作为主图或主结论                          | 降级为Supplementary exploratory concordance。                         |
| 证明题目原创性                                    | 改为评估文本重叠和文本新颖性。                                        |
| CTT证明题目考起来不差                             | 改为探索性CTT特征。                                                   |
| 不可辨识=AI像专家                                 | 改为来源辨识接近随机/达到预设等效，但不等同于质量等同。               |

# 十一、推荐投稿包装

-   主标题建议：Prospective validation of an auditable multi-agent AI workflow for urology residency examination-item generation。

-   备选标题：Validation of multi-agent-system-assisted item generation for urology residency written examinations: a two-setting randomized block-order study。

-   摘要Question：Can an auditable, human-in-the-loop multi-agent AI workflow generate urology residency examination items that are noninferior to human-written items in blinded expert-rated quality without increasing safety-critical defects?

-   摘要Meaning：MAS可作为专家在环的题库建设辅助工作流，但不能替代人工终审，也不能证明其全面评价临床能力。

# 十二、参考依据与可查询文献

1.  npj Digital Medicine. Aims and scope. https://www.nature.com/npjdigitalmed/aims

2.  NEJM AI. About / Aims and Scope. https://ai.nejm.org/about

3.  JAMA Network Open. Instructions for Authors. https://jamanetwork.com/journals/jamanetworkopen/pages/instructions-for-authors

4.  Piaggio G, Elbourne DR, Pocock SJ, Evans SJW, Altman DG; CONSORT Group. Reporting of Noninferiority and Equivalence Randomized Trials: Extension of the CONSORT 2010 Statement. JAMA. 2012;308(24):2594-2604. doi:10.1001/jama.2012.87802

5.  Klasen M, Sopka S. Demonstrating equivalence and non-inferiority of medical education concepts. Medical Education. 2021;55(4):455-461. doi:10.1111/medu.14420

6.  Althunian TA, de Boer A, Groenwold RHH, Klungel OH. Defining the non-inferiority margin and analysing non-inferiority: an overview. British Journal of Clinical Pharmacology. 2017;83(8):1636-1642. doi:10.1111/bcp.13280

7.  Norman GR, Sloan JA, Wyrwich KW. Interpretation of changes in health-related quality of life: the remarkable universality of half a standard deviation. Medical Care. 2003;41(5):582-592. doi:10.1097/00005650-200305000-00004

**最终建议：**以npj Digital Medicine作为冲刺包装，但不要把小样本双院区当作卖点。真正卖点是可审计MAS工作流、入卷前AI-专家安全筛查、盲法专家非劣效、critical defects、认知层级边界和总量质量校正效率。若数据结果不够强，JMIR Medical Education或BMC Medical Education是更现实落点。
