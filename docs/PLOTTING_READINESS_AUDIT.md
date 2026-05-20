# 绘图就绪性审计

检查日期：2026-05-20

本文档只服务于后续绘图、统计和补充分析 agent：说明第一作者真正要求什么、仓库当前有什么、哪些图能画到什么程度、哪些内容必须继续澄清。若本文件与原始绘图要求冲突，以 `plot/agent_readable/docs/05_plot_requirements_v1_0.md` 的“原始摘录”为优先；若本文件与仓库实际文件不一致，以实际文件为准并先更新审计。

## 总结论

当前仓库尚不具备直接绘制全部正式主图所需的锁定分析数据。可以立即做的事情主要是：

1. 搭建可编辑 PDF 的 Matplotlib 样式模板。
2. 绘制 Figure 1 的低数字/无数字概念流程版，并把缺失漏斗数字标成 `UNKNOWN_OR_CONFLICTING`。
3. 从作答工作簿开始整理考生级、题块级和题目级中间表。M卷 = MAS，P卷 = 人类已确认；仍需补齐最终入卷题清单、专家评分、缺陷裁决和效率数据后，才能画完整正式主图。

不能做的事情：

- 不能把原文中出现的 `*.csv` 数据表名写成仓库已经存在的文件。
- 不能把 `*.csv` 写成第一作者要求的图片交付格式。第一作者要求所有图片画成可编辑 PDF。
- 不能把 QGEval/LLM 机器评分替代最终盲法专家复合质量评分。
- 不能把人工核对 TXT 或脚本默认路径当成正式统计结果。

## 项目目的与作者分工

本项目服务于论文：比较人类出题质量与 MAS 出题质量，并评估真实考试中的考生表现、来源辨识、效率和安全性。

我是论文第二作者，负责本项目中的编程、统计和绘图。代码流程大致为：

1. 人类题库来源是 Word，先转换为 TXT 中间文件，再结构化为 `data/banks/bank_*.json`。
2. 模型阅读人类题库和提示词，生成 MAS 题库 `data/banks/new_bank_*.json`。
3. 对 MAS 题库补充答案解析和考点还原，并对 MAS 题库、人类题库或用户明确提供的组卷后试卷 JSON 进行文本相似度、可读性、QGEval、LLM 评分。
4. 根据 `plot/` 中第一作者给出的绘图要求，整理数据并输出可编辑 PDF 图。

## 已复核的绘图来源

- `plot/agent_readable/docs/05_plot_requirements_v1_0.md`：主绘图要求，含 5 张主图、3 张主表、补充材料、A/B 顺序、主终点、效率边界等。
- `plot/agent_readable/docs/01_figure_unified_parameters.md`：统一绘图参数，含 Python、Matplotlib、字体、字号、600 dpi、矢量输出文字可编辑等。
- `plot/agent_readable/docs/02_analysis_statistical_protocol.md`：统计分析 protocol，定义终点、模型、统计粒度和解释边界。
- `plot/agent_readable/docs/03_figure_table_statistical_views.md`：逐图逐表的数据粒度、数据来源和常见误区。
- `plot/agent_readable/docs/06_exam_blueprint.md`：考试蓝图，含题型、分值、知识领域、认知层级。
- `plot/agent_readable/docs/07_exam_responses_2_workbook.md` 与 `08_exam_responses_workbook.md`：作答工作簿的机械转换摘要和原始/缓存单元格导出。
- `plot/agent_readable/docs/visual_references.md`：TIF 风格参考图预览和尺寸。

## 第一作者硬要求

- 图片交付：所有图片画成可编辑 PDF。PNG 只能作为预览或检查图。
- 全局样式：Python 3.11 + Matplotlib、DejaVu Sans、正文字号 8 pt、panel 字母 10 pt bold、白色不透明背景、600 dpi、矢量输出保留可编辑文字。
- 研究设计表述：single-institution, two-setting, randomized two-sequence block-order validation study。
- A/B 顺序：Form A = Human -> MAS；Form B = MAS -> Human。全文不得出现相反版本。
- 作答工作簿映射：M卷 = MAS，P卷 = 人类。因此 Form A = P卷 -> M卷；Form B = M卷 -> P卷。
- 主文建议：5 张主图、3 张主表。
- 主终点：最终盲法专家复合质量评分。AI 自动评分和入卷前专家筛查只是工作流安全控制或补充探索。
- 效率/成本：主文只做整卷总量比较与质量校正效率，不做人类流程与 MAS 的逐阶段比较。
- 解释边界：来源不可辨识不等于质量等同；CTT 是探索性；Form A/B 不是配对，同一考生的 MAS block vs Human block 才是配对。

## 数据表名的解释边界

第一作者原文和统计 protocol 中出现了 `item_master.csv`、`responses.csv`、`expert_ratings.csv`、`workflow_total_time_cost.csv` 等表名。这些是建议的数据结构、统计粒度或数据字典名称，不代表当前仓库已有这些文件，也不代表图片交付格式。

后续 agent 若需要这些表，必须先检查仓库是否存在锁定分析表。若不存在，只能写“需要整理/需要补齐”，不能按表名发明字段或数据。

## 当前仓库已有信息

### 题库 JSON

- 人类题库：`data/banks/bank_*.json`，共 775 条。A1 267，A2 422，A3 48，A4 20，B 12，X 6。
- MAS 题库：`data/banks/new_bank_*.json`，共 3676 条。A1 480，A2 323，A3 647，A4 679，B 788，X 759。
- MAS 题库包含部分机器评价字段：文本相似度、可读性、QGEval、LLM、`test_point` 等。
- 人类题库也包含 QGEval/LLM 字段，但缺少 MAS 题库中的相似度、可读性和考点字段。

### 作答工作簿

- 原始工作簿：`plot/raw/试卷作答情况.xlsx`、`plot/raw/试卷作答情况 - 2.xlsx`。
- 已转换摘要：`plot/agent_readable/docs/08_exam_responses_workbook.md`、`plot/agent_readable/docs/07_exam_responses_2_workbook.md`。
- 可见信息包括：M卷/P卷、A/B卷、院区、年级、姓名/编号、题号、标准答案、作答、分值、前 27%/30% 与后 27%/30% 名单、疲劳性探索与总时长、评价系统与图灵测试等。
- 已确认映射：M卷 = MAS，P卷 = 人类。该映射可用于整理题块级 MAS-Human 配对得分和题目来源。
- 这些导出是 Excel 单元格的原始/缓存文本，不会重新计算公式，也不会保留显示格式；正式统计前必须回到 workbook 和单元格位置核对。

### 蓝图与设计文字

- 考试蓝图给出 50 题、100 分、90 分钟，题型结构为 A1 7 题、A2 18 题、A3/A4 14 小题、B 3 小题、X 8 题。
- 蓝图认知层级为 Recall、Comprehension、Application、Analysis。
- 统计 protocol 推荐认知层级为 knowledge、application、reasoning。二者不是同一体系，正式绘图前必须冻结映射规则。
- `05_plot_requirements_v1_0.md` 给出参与者叙述：候选 56 人，主院区 34、非主院区 22；排除后主院区 32、非主院区 18。绘制流程图前应与工作簿和排除记录交叉核对。

### 人工核对材料

- `outputs/report_drafts/` 当前保留 A/B 卷解析标注版 TXT，可用于核对试卷答案解析、评分字段和考点还原文字。
- 该目录不是绘图要求来源，也不是锁定统计结果来源。

## 关键缺口

正式绘图前至少需要澄清或整理：

1. 最终入卷 100 题清单：题号、题型、所属 M/P 题块、Form A/B 呈现位置、答案键、蓝图领域、认知层级。来源可由 M卷 = MAS、P卷 = 人类派生，但仍需逐题连接表。
2. 第一作者抽取题目组成的试卷统计量：题型、来源、蓝图领域、认知层级、文本特征、机器评分等应按最终试卷清单重算，而不是按整个题库统计。
3. 真实来源标签 `source_true` 与盲法评分表的合并方式：评分锁定前不能泄漏，评分锁定后才能合并。
4. 最终盲法专家评分数据：评分者、评分阶段、复合质量评分、分维度评分、来源猜测。
5. major/critical defect 的最终裁决数据：独立判断、分歧处理、第三方裁决、最终状态。
6. MAS 候选题漏斗：候选题总数、AI 自动筛查阈值、随机抽样 70 题、专家筛查结论、排除原因、最终 50 题。
7. 效率数据：人类整卷总时间、MAS 整卷总时间、专家/非专家时间、API 成本、时间来源、时间粒度和敏感性情景。
8. 学生逐题作答的可靠长表：考生 ID、题目 ID、选择、正确性、题块位置、题目来源。
9. 认知层级映射：蓝图四级是否合并为 protocol 三级，合并规则必须预先写明。
10. 模型版本、temperature、运行配置、prompt log 是否完整，尤其用于补充表 prompt/model settings。

## 主图就绪性

| 图 | 第一作者要求 | 当前状态 | 不能推断的点 |
| --- | --- | --- | --- |
| Figure 1 | MAS workflow + A/B 双顺序验证设计：AI 自动评分、安全筛查、专家审核、A/B 设计、主/非主院区随机、终点框架 | 可画概念流程；参与者数和 A/B 顺序有原文来源；MAS 候选题漏斗数字不完整 | `XXX` 题库总数、AI gate 通过数、专家筛查排除原因、最终 50 题选择过程不能编 |
| Figure 2 | 盲法专家复合质量评分非劣效、分维度评分、major/critical defects、缺陷裁决、专家一致性 | 不能直接画正式主图 | 仓库未见最终盲法专家评分、缺陷裁决和一致性数据；QGEval/LLM 不能替代 |
| Figure 3 | 按认知层级展示质量差、缺陷风险、学生正确率、source × cognitive_level 交互、CTT | 只能做准备或探索 | M/P 来源映射已确认；仍缺认知层级冻结规则、逐题连接表、作答长表和专家评分连接 |
| Figure 4 | 来源辨识 accuracy/balanced accuracy/混淆矩阵；整卷总人力时间、每道合格题/无重大缺陷题时间；敏感性分析 | 来源辨识可从工作簿探索；效率部分不能正式绘图 | 需要真实来源、评价者类型、缺失处理、整卷总时间/API 成本/敏感性假设 |
| Figure 5 | 考生 MAS block 与 Human block 配对得分、个体内差值、A/B 顺序效应、setting 探索性展示 | 题块级配对得分具备整理基础：M卷 = MAS，P卷 = 人类 | Form A/B 不能做配对；调整后正确率模型、CTT 和题目级分析仍需题目级长表与最终入卷题连接 |

## 主表与补充材料就绪性

| 项目 | 当前状态 |
| --- | --- |
| Table 1 Item blueprint and textual characteristics | 部分具备。蓝图和题库 JSON 存在；最终入卷 100 题清单、来源标签、文本特征锁定表仍缺。 |
| Table 2 Examinee baseline and randomization balance | 部分具备。工作簿可见 A/B、院区、年级；既往成绩和排除记录是否完整仍需确认。 |
| Table 3 Primary and key secondary endpoints | 暂不具备。依赖专家评分、缺陷裁决、来源辨识和效率结果。 |
| Supplementary Fig. MAS architecture/audit trail | 可画概念图；真实 audit trail 需要候选题筛查记录和排除原因。 |
| Supplementary Fig. AI/LLM vs expert rating | 有 AI/LLM 字段；缺最终盲法专家评分，不能画一致性结论。 |
| Supplementary Fig. Full CTT | 可从作答工作簿整理；M卷 = MAS、P卷 = 人类已确认。仍需先锁定题号、答案键、逐题来源和题目连接。 |
| Supplementary Fig. source misclassification | 可从评价系统与图灵测试/来源判断相关 sheet 开始；需真实来源和评价者定义。 |
| Supplementary Fig. efficiency sensitivity | 缺基础效率数据和情景假设，暂不能画。 |
| Supplementary Table prompt/model settings | prompt 文件存在；模型版本、temperature、运行配置、完整 prompt log 需核对。 |
| Supplementary Table text overlap/readability | MAS 题库层面可探索；若代表最终入卷题，需先锁定最终题目清单。 |

## 禁止推断清单

- 不要把第一作者的图片要求写成 CSV 要求；最终图片是可编辑 PDF。
- 不要把原文建议的数据表名当成当前仓库已有文件。
- 不要把机器评分 QGEval/LLM 写成最终盲法专家评分。
- 不要把人工核对 TXT 写成锁定统计结果；正式图需要从 JSON、workbook 或锁定分析数据重算。
- 不要把 `bank_*.json` 和 `new_bank_*.json` 混写；前者统一称为人类题库，后者称为 MAS 题库。
- 不要把来源辨识接近随机解释为质量等同。
- 不要对 Form A 和 Form B 做配对分析；配对只适用于同一考生的 MAS block 与 Human block。
- 不要把 M/P 映射反过来；本项目已确认 M卷 = MAS，P卷 = 人类。
- 不要在未冻结认知层级映射前画 source × cognitive_level 的正式结论。

## 后续 agent 操作建议

1. 先生成可编辑 PDF 样式模板，验证 `pdf.fonttype: 42`、DejaVu Sans、8 pt、白底和 panel 字母。
2. 先建立“图/面板-原文要求-数据来源-派生统计量-未解决假设”表；任一项缺失即写 `UNKNOWN_OR_CONFLICTING`。
3. Figure 1 可以先画概念版，但缺失数字必须明示，不能用占位符推断。
4. 作答工作簿整理时保留 workbook、sheet、行列位置和公式单元格信息。
5. 在专家评分、缺陷裁决、来源标签、效率数据未锁定前，不要输出正式主结论图。
