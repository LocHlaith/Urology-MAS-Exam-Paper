# UroEMAS 补充数据材料整理、命名与交付指南
**面向 npj Digital Medicine / Nature Portfolio 投稿的内部 Supplement Protocol**
**适用项目：UroEMAS 多智能体辅助泌尿外科住院医闭卷考试命题研究**
**版本：v1.0 | 日期：2026-07-11 | 用途：师弟执行数据整理、补充材料制作与投稿前核对**

> **重要说明**
>
> 本文件用于把补充数据材料的整理任务拆解为可执行清单，不可直接作为投稿正文。
> 所有结果、样本量、P 值、置信区间、非劣效判断和效率结论，必须以锁库后的真实数据和预先冻结的统计分析计划为准。
> 涉及完整题干、答案、解析、教材/指南来源、住院医师个人信息和完整 API 日志的材料，应优先按“公开脱敏版 + 受控访问审计包”处理。

# 0. 如何使用本指南
本指南把“需要整理什么、从哪里取数、整理成什么文件、如何命名、谁来复核、哪些内容不能公开”统一为一套执行流程。师弟执行时应遵守“先建文件夹与字段字典，再回填数据；先保留原始记录，再生成分析表；先完成公开脱敏版，再单独封存受控访问包”的顺序。

> **一句话定位**
>
> 本次补充材料的任务不是证明“AI 会出题”，而是为 UroEMAS 这一受约束、角色分离、可审计、专家监督的最终可用题开发流程，建立可复核的数据底座、审计轨迹和投稿级透明报告。

# 目录
- 1. 固定证据边界与数据整理原则
- 2. 文件夹结构、版本控制和交付规范
- 3. Supplementary Information PDF 整理任务
- 4. Supplementary Tables 与 Figures 整理任务
- 5. Supplementary Data 文件清单与字段模板
- 6. 受控访问审计包、脱敏和考试安全
- 7. 统计分析代码与可复现交付
- 8. 质量控制、交叉核对和常见错误
- 9. 执行时间轴、交付物和完成标准
- 10. 投稿前一页式核对单
- 附录 A. 可复制的文件命名规则
- 附录 B. 数据表字段与整理任务核对单
- 附录 C. 师弟每日汇报模板

# 1. 固定证据边界与数据整理原则
本节是整理数据时必须保持一致的口径。任何表格、图、代码注释、文件名和投稿说明都不得把 UroEMAS 题目误写为未经治理的大语言模型原始输出。

## 1.1 必须固定的整理对象

| 整理对象 | 定义 | 整理时必须避免的误读 |
| --- | --- | --- |
| Human items | 人工专家命题流程产出的最终可用题；不是“所有专家曾经草拟过的题”。 | 与 UroEMAS 题的比较终点必须建立在进入预设评价或最终试卷的题目上。 |
| UroEMAS items | 经 UroEMAS 工作流生成、筛查、必要时修订，并进入预设评价流程或最终试卷的题。 | 不得解释为 deepseek-reasoner 单次 prompt 原始输出。 |
| Expert ratings | 三名高级临床教学专家在不知道来源条件下完成的逐题评分、缺陷判断和来源判断。 | 机器派生评分只作探索性辅助，不能替代专家评分。 |
| Student responses | 最终纳入分析的 50 名住院医师逐题作答、题块顺序、院区、培训年级和考后题块来源判断。 | 学生来源判断是题块层面，不是单题层面。 |
| Workflow efficiency | 每道合格题开发所需 API 成本、自动筛查、专家审核、修订和组卷时间。 | 效率比较应指“最终可用题开发流程”，不是初稿生成速度。 |

## 1.2 证据层级与数据优先级

| 优先级 | 数据内容 | 用途 | 对应交付物 |
| --- | --- | --- | --- |
| 第一优先级 | 盲法专家复合质量评分、重大命题缺陷、critical defect | 决定主结论能否成立 | expert_ratings.xlsx；defect_adjudication.xlsx |
| 第二优先级 | 蓝图匹配、题型、考点、认知层级、题块顺序 | 决定比较是否公平 | item_master.xlsx；exam_form_assignment.xlsx |
| 第三优先级 | 学生逐题作答、按院区/认知层级正确率、CTT 指标 | 支持测量功能与疲劳效应分析 | student_item_responses.xlsx；ctt_outputs.xlsx |
| 第四优先级 | 专家与学生来源辨识、MAS-like 判断特征 | 支持治理讨论 | source_identification.xlsx；mas_like_features.xlsx |
| 第五优先级 | 开发时间、成本、相似性、修订强度、prompt 和日志 | 支持可审计性与部署价值 | workflow_time_cost.xlsx；similarity_metrics.xlsx；prompt_archive.zip |

## 1.3 数据整理底线
- [ ] 每一个 item_id 必须在 item_master、expert_ratings、responses、ctt_outputs、time_cost、similarity_metrics 中可追踪。
- [ ] 公开数据表优先使用匿名 item_id、student_id、rater_id；完整题干和答案进入受控访问包。
- [ ] 任何“预设”“锁库前冻结”“探索性”字样必须与实际记录一致，不得事后包装。
- [ ] 所有结论性表格必须同时保留 point estimate、CI、样本量/题目数、分析单位和模型说明。

# 2. 文件夹结构、版本控制和交付规范
请先建立统一目录，再开始整理数据。任何临时文件、截图、微信传输文件或手工改名文件，都必须最后归入以下目录并补充 README。

```text
UroEMAS_Supplement_Package_v1.0/
├─ 00_README_and_Data_Dictionary/
├─ 01_Raw_Protected_Do_Not_Edit/
├─ 02_Deidentified_Public_Data/
├─ 03_Supplementary_Information_PDF_Source/
├─ 04_Supplementary_Tables/
├─ 05_Supplementary_Figures/
├─ 06_Analysis_Code/
├─ 07_Outputs_Locked/
├─ 08_Controlled_Access_Audit_Package/
└─ 09_Submission_Checklists_and_Logs/
```

| 目录 | 放什么 | 最低交付物 |
| --- | --- | --- |
| 00_README_and_Data_Dictionary | 所有字段定义、取值范围、缺失值编码、版本日志、联系人 | README.md；data_dictionary.xlsx；version_log.xlsx |
| 01_Raw_Protected_Do_Not_Edit | 原始作答、原始专家评分、原始日志、完整题目、答案键 | 只读保存；不得在此目录直接改数 |
| 02_Deidentified_Public_Data | 公开补充数据表，删除姓名、工号、完整题干、敏感答案解析 | Supplementary_Data_*.xlsx/csv |
| 03_Supplementary_Information_PDF_Source | 补充 PDF 的 Word 源文件、图表引用、rubric、SAP | Supplementary_Information.docx |
| 04_Supplementary_Tables | 所有 Supplementary Table 的可编辑源表 | STable_S1_*.xlsx |
| 05_Supplementary_Figures | 所有 Supplementary Figure 的源数据、脚本和输出图 | SFigure_S1_*.png/pdf |
| 06_Analysis_Code | 清洗、建模、bootstrap、作图代码 | R 或 Python 脚本；session_info.txt |
| 07_Outputs_Locked | 锁库后最终结果表、模型对象、图、日志 | 不得覆盖，只能追加新版本 |
| 08_Controlled_Access_Audit_Package | 完整题目、完整 prompt、API 日志、来源映射和审计轨迹 | 加密保存；需访问说明 |
| 09_Submission_Checklists_and_Logs | 投稿前核对单、伦理/预注册/报告规范清单 | checklist_*.docx/xlsx |

## 2.1 版本命名规则

> **固定命名格式**
>
> 项目_材料类型_编号_简短说明_日期_版本号.扩展名
> 例：UroEMAS_SupplementaryData_03_StudentItemResponses_20260711_v1.0.xlsx
> 例：UroEMAS_SFigure_S3_ItemFlow_20260711_v1.0.pdf

## 2.2 文件命名与版本控制检查
- [ ] 所有最终文件使用英文文件名，避免空格、中文标点和“最终最终版”。
- [ ] 每次修改后在 version_log.xlsx 中写明修改人、时间、修改内容和是否影响结论。
- [ ] 锁库后不得覆盖原文件；如必须更新，使用 v1.1、v1.2，并在 README 解释原因。
- [ ] 公开版与受控访问版必须文件名区分：Public / ControlledAccess。

# 3. Supplementary Information PDF 整理任务
Supplementary Information PDF 负责承载方法细节、rubric、流程图、SAP 摘要和透明报告，不应混入大型逐题数据表。师弟应先整理 Word 源文件，再由主笔统一润色。

| 章节 | 建议标题 | 需要整理的内容 | 原始来源 | 复核人 |
| --- | --- | --- | --- | --- |
| Note 1 | Study protocol and deviations | 研究设计、注册、伦理、招募、排除、终点层级、偏离记录 | protocol_summary.docx；ethics_approval.pdf；registration_record.pdf | 主笔复核 |
| Note 2 | Reporting checklist mapping | CONSORT-AI / SPIRIT-AI / STROBE / Nature reporting summary 对照表 | reporting_checklist_mapping.xlsx | 统计+主笔 |
| Note 3 | UroEMAS workflow architecture | 角色分离、输入输出、JSON schema、模型标识、temperature、日志字段 | prompt_archive；api_log_summary；workflow_diagram | AI 流程负责人 |
| Note 4 | Human expert item-development workflow | 人工命题依据、蓝图、时间记录、报酬、审核和格式统一流程 | human_item_development_log.xlsx | 命题组 |
| Note 5 | Blueprint and item taxonomy | 题型、topic、40 项考点、Bloom 认知层级、Human/MAS 平衡 | item_master.xlsx；blueprint_mapping.xlsx | 师弟初整 |
| Note 6 | Randomization and blinding | AB/BA 随机顺序、院区/年级平衡、解盲时间线、masking 表 | randomization_log.xlsx；masking_timeline.docx | 统计复核 |
| Note 7 | Expert scoring rubrics | QGEval 七维度、UML 16 维度、评分锚点、缺陷定义 | rubric_full.docx | 专家组复核 |
| Note 8 | Safety screening and adjudication | 严重缺陷、critical defect、分歧处理、匿名案例 | defect_adjudication_log.xlsx | 安全审核负责人 |
| Note 9 | Statistical analysis plan | 模型公式、非劣效界值、bootstrap、降阶规则、敏感性分析 | SAP_locked.pdf；analysis_code | 统计负责人 |
| Note 10 | AI-use disclosure and reproducibility limitations | 模型更新限制、prompt/脚本/日志保留、LLM judge 探索性边界 | model_call_audit_summary.xlsx | AI 流程负责人 |

## 3.1 Supplementary Information 写作检查
- [ ] 每个 Note 开头用 2–3 句说明目的，不要把方法细节散落到多个文件。
- [ ] 任何 “exploratory” 分析必须明确标注，不能与主要终点混在同一结论层级。
- [ ] 完整题干、答案和解析如涉及考试安全，Supplementary Information 中只放去标识化示例或结构化说明。
- [ ] 所有模型公式与主文 Methods 保持一致；若 Supplement 更详细，主文必须能对应。

# 4. Supplementary Tables 与 Figures 整理任务

## 4.1 Supplementary Tables 最小清单

| 编号 | 建议标题 | 核心内容 | 交付形式 |
| --- | --- | --- | --- |
| Table S1 | Study protocol summary | 设计、场景、对象、比较流程、终点、样本、注册和伦理 | 补充 PDF 或单独 xlsx |
| Table S2 | Participant flow and exclusions | 56 招募、34/22 院区、排除 6 人、最终 50 人及原因 | 补充 PDF |
| Table S3 | Baseline characteristics | 院区、培训年级、性别/年龄如允许、order group 平衡 | xlsx + PDF |
| Table S4 | Expert characteristics | 专家资历、角色、是否参与命题/筛查/评分/组卷 | 补充 PDF |
| Table S5 | Examination blueprint | 题型、topic、cognitive level、Human/MAS 数量和最终试卷数量 | xlsx + PDF |
| Table S6 | Model and prompt parameters | model identifier、temperature、调用时间、JSON schema、重复调用次数 | 补充 PDF |
| Table S7 | Candidate item generation and attrition | 3600+ → 候选库 → 70 评价题 → 50 最终题；剔除原因 | 核心表 |
| Table S8–S9 | Human and UroEMAS time/cost | 逐题开发时间、API 成本、审核和修订时间、总成本 | xlsx |
| Table S10–S11 | QGEval and UML item-level scores | rater × item 层面的逐维度评分和总分 | 大型 Supplementary Data |
| Table S12 | Inter-rater reliability | ICC/kappa、95% CI、按总分和维度展示 | 补充 PDF |
| Table S13–S14 | Primary NI and defect results | 调整均值差异、CI、δ、OR、critical defect | 主结果补充表 |
| Table S15–S16 | Source identification | 专家逐题、学生题块层面的混淆矩阵、accuracy、balanced accuracy | 补充 PDF + xlsx |
| Table S17–S21 | Student performance, CTT, reliability, AB/BA | 正确率、Bloom 分层、难度、区分度、KR-20/alpha、疲劳效应 | xlsx + 图源数据 |
| Table S22–S25 | Sensitivity, MAS-like, similarity, machine-derived | 修订强度、感知模型、相似性监测、机器派生评分 | 探索性补充 |

## 4.2 Supplementary Figures 最小清单

| 编号 | 建议标题 | 面板内容 | 主要任务 |
| --- | --- | --- | --- |
| Figure S1 | Study design schematic | 双院区、56 招募、50 分析、AB/BA、来源判断、专家盲评 | 主流程图 |
| Figure S2 | UroEMAS workflow diagram | 输入材料、角色分离、生成、解析、分类、筛查、修订、候选库 | 可审计性 |
| Figure S3 | Human and UroEMAS item flow | Human 70；UroEMAS 3600+；评价 70；最终 50+50 | denominator 透明 |
| Figure S4 | Blinding and source-concealment timeline | 匿名化、统一排版、专家评分、来源判断、学生考试、解盲 | masking 透明 |
| Figure S5 | Non-inferiority forest plot | QGEval、UML、各维度差异、95% CI、非劣效界值 | 主终点支持 |
| Figure S6–S7 | Expert scores and defect rates | 评分分布、缺陷分类、CI | 质量—安全 |
| Figure S8–S11 | Student performance and CTT | 正确率热图、难度-区分度、干扰项效率、AB/BA 疲劳效应 | 测量功能 |
| Figure S12 | Source identification performance | 专家/学生混淆矩阵、balanced accuracy、response bias | 治理亮点 |
| Figure S13 | Time and cost comparison | 每道合格题专家工时、API 成本、审核时间、总成本 | 效率附加价值 |

## 4.3 图表制作检查
- [ ] 每张图只承担一个主任务：质量、安全、测量功能、治理或效率。
- [ ] 图中所有估计值必须带 CI；非劣效或等效边界必须标注是否预设。
- [ ] Figure S3 必须清楚展示 denominator，避免把 3600+ 候选题与 70/50 最终题混淆。
- [ ] Figure S13 只解释“最终可用题开发效率”，不得写成“模型写题速度”。

# 5. Supplementary Data 文件清单与字段模板
Supplementary Data 是审稿人复核结果的核心。每个文件必须有 data dictionary、唯一主键、缺失值编码和版本号。大型表格建议 xlsx + csv 双格式保存；投稿时按期刊要求提交。

| 文件编号 | 文件名 | 最低字段 | 分析单位 |
| --- | --- | --- | --- |
| Supplementary Data 1 | Item_Level_Master_Dataset | item_id；source；item_type；topic；cognitive_level；has_vignette；stem_length；final_exam_inclusion；revision_intensity；similarity；defect_status；time_cost | 一行一题 |
| Supplementary Data 2 | Expert_Ratings | rater_id；item_id；source；QGEval 7 维度；QGEval total；UML 16 维度；UML total；major_defect；defect_type；source_guess | rater × item |
| Supplementary Data 3 | Student_Item_Response_Data | student_id；campus；training_year；order_group；block_position；item_id；source；topic；cognitive_level；selected_answer；correct | student × item |
| Supplementary Data 4 | Student_Block_Perception_Data | student_id；block_id；true_source；guessed_source；difficulty；clinical relevance；urology relevance；overall quality；confidence | student × block |
| Supplementary Data 5 | CTT_and_Reliability_Outputs | difficulty；discrimination；point_biserial；distractor_efficiency；KR20/alpha；bootstrap CI；flagged_item | item 或 block 层面 |
| Supplementary Data 6 | Randomization_and_Blinding_Metadata | student_id；order_group；campus；training_year；block_sequence；randomization_seed/method；unblinding_date | student 层面 |
| Supplementary Data 7 | Workflow_Time_and_Cost | item_id；workflow；phase；person_role；minutes；api_cost；review_cost；revision_round；accepted | item × phase |
| Supplementary Data 8 | Prompts_and_JSON_Schemas | system prompts；role prompts；item-type prompts；explanation prompt；classification prompt；JSON schema；validation rules | zip |
| Supplementary Data 9 | Similarity_and_Originality_Metrics | item_id；reference_item_id；cosine similarity；Levenshtein；n-gram overlap；threshold；action_taken | item × reference |
| Supplementary Data 10 | Model_Call_Audit_Log_Summary | call_id；module；timestamp；model；temperature；input/output tokens；status；validation pass/fail；cost | call 层面 |

## 5.1 主键与合并规则

| 主键 | 建议编码 | 用途 |
| --- | --- | --- |
| item_id | ITEM001–ITEM140 或 H001/M001 的匿名编码 | 贯穿所有 item-level 数据表；公开版不含完整题干。 |
| student_id | STU001–STU050 | 贯穿作答、题块感知、随机化表；不保留姓名、工号、手机号。 |
| rater_id | R01–R03 或 Expert01–Expert03 | 贯穿专家评分与来源判断；专家身份信息单独受控保存。 |
| block_id | B1/B2 或 FormA_Block1 等 | 用于连接 order_group、block_position、true_source。 |
| call_id | API 调用唯一编号 | 用于连接 prompt、输出、验证结果和成本。 |

## 5.2 数据表统一规范
- [ ] source 变量统一使用 Human / UroEMAS，不混用 MAS、AI、LLM、expert 等。
- [ ] 缺失值统一编码为 NA，不用空白、0 或 “无”。
- [ ] 所有百分比同时保留分子和分母。
- [ ] 所有时间字段保留单位 minutes，成本字段保留币种和换算规则。
- [ ] 每个 Supplementary Data 文件第一张 sheet 命名为 README，说明字段和生成日期。

# 6. 受控访问审计包、脱敏和考试安全
完整题目、答案、解析、来源映射和 API 原始日志具有考试安全、版权和参与者隐私风险。公开数据应足以复核主要分析；完整材料应进入受控访问包，并在 Data Availability 中说明限制理由和申请方式。

| 公开级别 | 材料类型 | 处理方式 |
| --- | --- | --- |
| 可公开 | 匿名 item_id、题型、topic、认知层级、评分、正确/错误、CTT、时间成本汇总、相似性指标 | Supplementary Data 1–10 |
| 谨慎公开 | 题干长度、选项长度、简化缺陷案例、prompt 模板 | 去除完整题干、答案、教材原文和敏感病例细节 |
| 受控访问 | 完整 Human 70 题、完整 UroEMAS 70 题、最终 50+50 试卷、答案键、解析、修订前后版本、来源映射 | Controlled_Access_Audit_Package |
| 不公开或仅伦理允许时查看 | 住院医师身份信息、专家真实姓名、完整原始 API payload、可能含版权材料的输入文本 | 加密封存，访问需 PI 批准 |

## 6.1 受控访问包内容
- [ ] 完整 Human 70 题、完整 UroEMAS 70 题、最终 50+50 试卷。
- [ ] 答案键、答案解析、考点归类和蓝图映射。
- [ ] UroEMAS 原始输出、自动筛查记录、专家安全筛查记录、修订前后版本。
- [ ] prompt 全文、JSON schema、模型调用摘要、完整 API 日志索引。
- [ ] 来源映射文件、随机化密钥、解盲记录、数据锁定记录。
- [ ] 访问说明：申请条件、联系人、预计回复时间、数据使用协议和禁止再分发条款。

> **脱敏原则**
>
> 公开表中只保留复核统计分析必需的信息。若某字段不能改变主要分析，但可能暴露考试题、个人身份或版权材料，应从公开版移除并写入受控访问包索引。

# 7. 统计分析代码与可复现交付
代码包应让统计分析者或审稿人能够从脱敏数据表重新生成主要结果表和图。所有脚本应按“数据清洗 → 主分析 → 次要分析 → 探索性分析 → 作图”的顺序组织。

| 代码目录 | 任务 | 最低文件 |
| --- | --- | --- |
| 00_environment | R/Python 版本、包版本、session_info、随机种子 | session_info.txt；requirements.txt |
| 01_data_cleaning | 读取原始脱敏表、类型转换、缺失值处理、主键检查 | clean_data.R 或 clean_data.py |
| 02_primary_quality_safety | 非劣效模型、major defect 模型、ICC/kappa | primary_models.R |
| 03_student_performance_ctt | 正确率、campus/Bloom 分层、CTT、KR-20/alpha、bootstrap | ctt_analysis.R |
| 04_order_fatigue | AB/BA 顺序、block_position、source × block_position | order_effects.R |
| 05_source_identification | accuracy、balanced accuracy、混淆矩阵、专家 vs 学生模型、MAS-like 模型 | source_identification.R |
| 06_efficiency_similarity | 时间成本、API 成本、相似性、修订强度敏感性分析 | workflow_efficiency.R |
| 07_figures_tables | 所有主图、补充图、补充表输出脚本 | make_figures_tables.R |

## 7.1 代码复现检查
- [ ] 代码运行后生成的表格数值必须与 manuscript、Supplementary Information 和 Supplementary Data 一致。
- [ ] 所有模型输出保存原始对象或文本摘要，不能只保留截图。
- [ ] bootstrap 次数、随机种子、CI 类型和模型降阶规则必须写在代码注释和 SAP 中。
- [ ] 若模型不收敛，保留不收敛日志，并记录最终采用的简化模型。

# 8. 质量控制、交叉核对和常见错误

## 8.1 强制交叉核对表

| 核对项 | 必须确认的问题 | 对应文件 |
| --- | --- | --- |
| 样本量 | 56 招募、50 分析、主院区 32、副院区 18 是否全文件一致 | Table S2、Results、Data 3、Data 6 |
| 题目数量 | Human 70、UroEMAS 70、最终 50+50、3600+ 候选题是否口径一致 | Figure S3、Table S7、item_master |
| 来源标签 | Human/UroEMAS 是否统一；A/B 是否在解盲前被隐藏 | 所有数据表 |
| 分析单位 | 专家逐题 vs 学生题块层面是否清楚区分 | source_identification |
| 非劣效边界 | δ=0.30/0.25/0.20/2.00/4.00 是否与量表一致 | SAP、Table S13 |
| 时间成本 | 是否包含人工审核、修订和组卷，而不仅是 API 生成时间 | Data 7、Figure S13 |
| 相似性 | 相似性监测是否写成 surveillance，而不是绝对原创性证明 | Data 9、Supplement Note |
| 机器派生评分 | 是否明确为探索性，不进入主要结论 | Data 10 或 Table S25 |

## 8.2 常见错误与修正方式

| 错误 | 风险 | 修正方式 |
| --- | --- | --- |
| 把 UroEMAS 题写成 AI 原始输出 | 高 | 统一改为 UroEMAS workflow items / MAS-assisted items，并说明经筛查和修订。 |
| 用 P>0.05 证明等效 | 高 | 改为报告 CI、预设边界和 non-inferiority/equivalence 判定。 |
| 把学生和专家来源识别直接比较 | 中高 | 说明判断单位不同；使用谨慎解释或模型化比较。 |
| 公开完整题干和答案 | 高 | 改为公开结构化变量；完整题目进入受控访问包。 |
| 效率只算 API 时间 | 高 | 补齐专家审核、自动筛查、修订、格式规范化和组卷时间。 |
| 文件名混乱或版本覆盖 | 中 | 恢复 version_log；使用日期和 v 编号。 |
| 缺失数据未说明 | 中 | 在 README 和 data dictionary 中定义缺失原因和编码。 |

# 9. 执行时间轴、交付物和完成标准

| 时间 | 任务 | 交付物 | 完成标准 |
| --- | --- | --- | --- |
| Day 1 | 建立文件夹、命名规则、README、data dictionary 初稿 | 目录结构截图；README.md；data_dictionary.xlsx | PI 确认 |
| Day 2–3 | 整理 item_master、expert_ratings、student_responses、source_identification | Supplementary Data 1–4 初版 | 主键完整率 100% |
| Day 4 | 整理 CTT、randomization、time_cost、similarity、model_call audit | Supplementary Data 5–10 初版 | 字段完整、单位统一 |
| Day 5 | 整理 Supplementary Tables S1–S25 源表 | STable 源文件夹 | 数值与数据表一致 |
| Day 6 | 整理 Supplementary Figures 源数据和草图 | SFigure 源数据和初稿图 | 每图任务明确 |
| Day 7 | 整理 Supplementary Information PDF 源文档 | Supplementary_Information_Source.docx | Note 1–10 完整 |
| Day 8 | 建立受控访问审计包索引和脱敏说明 | Controlled_Access_Index.xlsx；Data_Availability_Draft.docx | PI 审核通过 |
| Day 9–10 | 统一复核、修正版本、生成锁定输出 | Locked outputs v1.0 | 所有 cross-check 通过 |

## 9.1 师弟每日汇报格式

> **日期：YYYY-MM-DD**
>
> 今日完成：
> 1.
> 2.
> 发现的问题：
> 1. 缺失字段/口径冲突/无法判断的来源：
> 2. 需要师兄/PI 决策的问题：
> 明日计划：
> 当前文件版本：
> 需要锁定或备份的文件：

# 10. 投稿前一页式核对单
- [ ] Supplementary Information PDF 包含流程、rubric、SAP、masking、缺陷定义、AI 使用披露。
- [ ] Supplementary Data 1–10 均有 README sheet、字段字典、版本号和生成日期。
- [ ] item_id、student_id、rater_id 在所有表中一致，无重复主键或无法合并记录。
- [ ] 公开版删除完整题干、答案、解析、个人身份信息和不可公开版权内容。
- [ ] 受控访问包包含完整题目、答案、prompt、日志、修订记录、来源映射和申请说明。
- [ ] 所有主要结果可由代码从脱敏数据重新生成。
- [ ] 所有图表中样本量、题目数、CI、边界和探索性标签一致。
- [ ] Data Availability、Code Availability、Ethics、AI-use disclosure 与补充材料一致。
- [ ] 主文、图注、Supplement 和 Cover letter 中没有“AI 替代专家”“证明原创性”“P>0.05 等效”等过度表述。

> **最终交付标准**
>
> 师弟最终交付的不应是散乱文件，而是一套可被主笔直接用于投稿的 Supplement Package：公开脱敏数据、补充 PDF 源文件、图表源文件、可复现代码、受控访问审计包索引和一页式核对单。

# 附录 A. 可复制的文件命名规则

| 材料类型 | 命名示例 |
| --- | --- |
| Supplementary Information | UroEMAS_SupplementaryInformation_Source_20260711_v1.0.docx |
| Supplementary Data | UroEMAS_SupplementaryData_01_ItemLevelMaster_20260711_v1.0.xlsx |
| Supplementary Table | UroEMAS_STable_S13_PrimaryNonInferiority_20260711_v1.0.xlsx |
| Supplementary Figure | UroEMAS_SFigure_S5_NonInferiorityForest_20260711_v1.0.pdf |
| Analysis Code | UroEMAS_Code_03_PrimaryQualitySafety_20260711_v1.0.R |
| Controlled Access | UroEMAS_ControlledAccess_Index_20260711_v1.0.xlsx |
| Version Log | UroEMAS_VersionLog_20260711_v1.0.xlsx |

# 附录 B. 数据表字段与整理任务核对单

| 数据表 | 最少字段 | 主要用途 |
| --- | --- | --- |
| item_master.xlsx | item_id、source、block_id、topic、cognitive_level、item_type、has_vignette、key_option、n_options、within_block_position、stem_length、final_inclusion | 蓝图平衡、CTT、来源辨识解释模型 |
| expert_ratings.xlsx | rater_id、rater_type、item_id、QGEval 维度、UML 维度、quality_score、major_defect、defect_type、source_guess | Figure 2、Table S10–S14 |
| student_responses.xlsx | student_id、form、campus、training_year、item_id、source、block_position、item_position、selected_option、correct、missing | Figure 3、Figure 5、CTT |
| source_identification.xlsx | rater_id/student_id、rater_type、item_or_block_id、true_source、guessed_source、confidence、correct_guess | Figure 4、来源辨识模型 |
| development_time_cost.xlsx | item_id、workflow、phase、person_role、minutes、api_cost、review_cost、accepted、revision_round | Figure S13、效率成本 |
| revision_log.xlsx | item_id、original_version_available、final_version_available、revision_intensity、revision_round、reviewer_role、reason | 修订强度敏感性分析 |
| similarity_metrics.xlsx | item_id、reference_item_id、cosine_similarity、Levenshtein、n_gram_overlap、threshold、action_taken | 近重复监测与审计 |
| model_call_audit.xlsx | call_id、module、timestamp、model、temperature、tokens、status、validation_result、cost | AI 使用披露与流程复现 |

# 附录 C. 师弟每日汇报模板

| 汇报项 | 填写内容 |
| --- | --- |
| 今日完成文件 | 列出文件名、版本号、保存路径 |
| 今日发现问题 | 缺失字段、口径冲突、样本量不一致、无法判断是否公开 |
| 需要师兄决定 | 是否删除字段、是否进入受控访问、是否采用某个统计口径 |
| 明日计划 | 明确到文件和表格编号 |
| 风险提示 | 任何可能影响主结论、伦理、考试安全或版权的问题 |

---

*本 Markdown 文件由同名 Word 执行指南转换生成，用于团队内部协作、数据整理和投稿前核对。*
