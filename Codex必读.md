# Codex必读

本仓库服务于比较“Human出题质量”和“UroEmas（泌尿外科试卷多智能体系统）出题质量”的论文。我是第二作者，负责编程、统计、绘图。

## 实验流程

1. 获得Human题库
邀请Human专家命制了Human题库。因为医学专家习惯使用Word，而Word不便于机器处理，所以先将Word转换为TXT，再结构化为JSON，位于datasets。

2. 获得UroEmas题库
调用Deepseek API，学习Human题库和命题规范，生成JSON格式的UroEmas题库。第一轮生成题干、选项，第二轮生成答案解析，第三轮生成考点还原。

3. 机器评价题库
对于Human题库的每道题目，计算并标注了可读性，然后调用Deepseek API，标注了QGEval评分和LLM评分，评分细则位于prompts\evaluation。
对于UroEmas题库的每道题目，计算并标注了可读性、和Human题库的文本相似性，然后调用Deepseek API，标注了QGEval评分和LLM评分，评分细则位于prompts\evaluation。

4. 第一轮抽题
从Human题库和UroEmas题库中分别抽取70题，邀请三位Human专家，标注了QGEval评分和LLM评分等，位于plot\data\raw\expert_rating_workbooks\专家*-专家评分——统计版.xlsx，* = 1, 3, 4。这三份XLSX结构相同，均包含P、P被筛、P汇总、M、M被筛、M-合并、图灵测试、P-分题型、M合并-分题型、P布鲁姆分类、M布鲁姆分类。

其中：

- P汇总由P、P被筛拼接而成。

- M-合并由M、M被筛拼接而成。

- 图灵测试是指由专家猜测各个题目来自Human还是UroEmas。

- 布鲁姆分类是指按照认知层级分类统计。

实际上：

- P、M，即“第二轮筛选组成试卷”中选出的50题。

- P被筛、M被筛，“被筛”是指“被删”，即“第二轮筛选组成试卷”中落选的20题。

5. 机器与专家评价Major Defect
调用Deepseek API，并邀请Human专家，评价Major Defect，评分细则位于prompts\evaluation\major_defects.md，发现这70题没有Major Defect。为了验证Major Defect评分细则的合理性，我们从Human题库和UroEmas题库中按比例抽取低分段50题与中分段50题（outputs\major_defects\samples），调用Deepseek API，并邀请Human专家，评价Major Defect。Deepseek API结果位于outputs\major_defects\manual_txt，Human专家结果还未发来。

6. 第二轮筛选组成试卷
从第一轮Human70题和UroEmas70题中分别抽取50题，组成Human试卷（P卷）和UroEmas试卷（M卷）。为了便于第一作者查看试卷，我将试卷转换为TXT文件，即outputs\report_drafts中的P卷解析标注版和M卷解析标注版。因为QGEval评分和LLM评分具有随机性，所以对于每道题，调用四次Deepseek API，获得了四组QGEval评分和LLM评分，所以P卷解析标注版和M卷解析标注版各有四份。

7. 模拟考试
为了消除考生疲劳的影响，将“P卷在前、M卷在后”的考试称为A卷，将“M卷在前、P卷在后”的考试称为B卷，得到了考生的作答数据，即plot\raw_data\试卷作答情况.xlsx、plot\raw_data\试卷作答情况 - 2.xlsx，其中：

- 试卷作答情况.xlsx根据年级、院区、疲劳（即AB卷）分类统计。

- 试卷作答情况 - 2.xlsx根据题型分类统计。

8. 处理数据并绘图。
在绘图时，LLM统一改称为ULM。

## 你的工作

你将整理本仓库文件，得到可以交给审稿人审阅的文件夹。

为此，第一作者撰写了UroEMAS_补充数据材料整理与交付指南_v1.0.md。然而，第一作者对本仓库的代码逻辑、绘图逻辑没有任何了解，该指南几乎是一派胡言。

请充分掌握本仓库的代码逻辑、绘图逻辑，重写指南、完成整理。基于以下原则：

0. Human专家评价的Major Defect结果还未发来，这是本仓库唯一缺失的代码与数据，不是今天能够解决的，请无视与Human专家评价的Major Defect结果相关的代码逻辑、绘图逻辑，包括Figure1C、1D、1E。

1. 本仓库代码已经正确、完整，不含错误、缺失。第一作者凭空想象、无端讨要的代码，例如甚至要求 R 语言代码，不必强行满足其要求，而应充分利用本仓库代码，整理出第一作者所意图的被审阅内容。

2. 本仓库数据已经正确、完整，不含错误、缺失。部分数据也许没有raw表格（例如Deepseek费用与耗时），但已在代码中体现，可以整理出来供审稿人审阅。

3. 绘图逻辑.md、绘图参数.md是为了让你快速了解绘图逻辑，不一定完全准确。本仓库代码的权威性高于绘图逻辑.md、绘图参数.md。

4. 因为医学刊物审稿人习惯使用Word（.docx）与Excel（.xlsx），所以最终文件夹内以.docx、.xlsx、.py。如果你不便阅读或处理.docx、.xlsx，建议暂时使用.md、.csv。
