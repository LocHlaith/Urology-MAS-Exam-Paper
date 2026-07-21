# AGENTS.md

本仓库服务于比较“Human出题质量”和“UroEMAS（泌尿外科试卷多智能体系统）出题质量”的论文。我是第二作者，负责编程、统计、绘图。

## 实验流程

1. 获得Human题库
邀请Human专家命制了Human题库。因为医学专家习惯使用Word，而Word不便于机器处理，所以先将Word转换为TXT，再结构化为JSON，位于datasets。

2. 获得UroEMAS题库
调用Deepseek API，学习Human题库和命题规范，生成JSON格式的UroEMAS题库。第一轮生成题干、选项，第二轮生成答案解析，第三轮生成考点还原。

3. 机器评价题库
对于Human题库的每道题目，计算并标注了可读性，然后调用Deepseek API，标注了QGEval评分和ULM评分，评分细则位于prompts\evaluation。
对于UroEMAS题库的每道题目，计算并标注了可读性、和Human题库的文本相似性，然后调用Deepseek API，标注了QGEval评分和ULM评分，评分细则位于prompts\evaluation。

4. 第一轮抽题
从Human题库和UroEMAS题库中分别抽取70题，邀请三位Human专家，标注了QGEval评分和ULM评分等，位于plot\data\raw\expert_rating_workbooks\专家*-专家评分——统计版.xlsx，* = 1, 3, 4。这三份XLSX结构相同，均包含P、P被筛、P汇总、M、M被筛、M-合并、图灵测试、P-分题型、M合并-分题型、P布鲁姆分类、M布鲁姆分类。

其中：

- P汇总由P、P被筛拼接而成。

- M-合并由M、M被筛拼接而成。

- 图灵测试是指由专家猜测各个题目来自Human还是UroEMAS。

- 布鲁姆分类是指按照认知层级分类统计。

实际上：

- P、M，即“第二轮筛选组成试卷”中选出的50题。

- P被筛、M被筛，“被筛”是指“被删”，即“第二轮筛选组成试卷”中落选的20题。

5. 机器与专家评价Major Defect
调用Deepseek API，并邀请Human专家，评价Major Defect，评分细则位于prompts\evaluation\major_defects.md，发现这70题没有Major Defect。为了验证Major Defect评分细则的合理性，我们从Human题库和UroEMAS题库中按比例抽取低分段50题与中分段50题（outputs\major_defects\samples），调用Deepseek API，并邀请Human专家，评价Major Defect。Deepseek API结果位于outputs\major_defects\manual_txt，Human专家结果还未发来。

6. 第二轮筛选组成试卷
从第一轮Human70题和UroEMAS70题中分别抽取50题，组成Human试卷（P卷）和UroEMAS试卷（M卷）。为了便于第一作者查看试卷，我将试卷转换为TXT文件，即outputs\report_drafts中的P卷解析标注版和M卷解析标注版。因为QGEval评分和ULM评分具有随机性，所以对于每道题，调用四次Deepseek API，获得了四组QGEval评分和ULM评分，所以P卷解析标注版和M卷解析标注版各有四份。

7. 模拟考试
为了消除考生疲劳的影响，将“P卷在前、M卷在后”的考试称为A卷，将“M卷在前、P卷在后”的考试称为B卷，得到了考生的作答数据，即plot\raw_data\试卷作答情况.xlsx、plot\raw_data\试卷作答情况 - 2.xlsx，其中：

- 试卷作答情况.xlsx根据年级、院区、疲劳（即AB卷）分类统计。

- 试卷作答情况 - 2.xlsx根据题型分类统计。

8. 处理数据并绘图。
机器评分方法在仓库与绘图中统一称为ULM。

## 你的临时工作

对于critical defects安全门槛.xlsx的每一道题，请全网搜索相关医学依据，并根据prompts\evaluation\major_defects.md，标注Major Defect及其理由。

注意：

1. 是由你搜索、判断、标注，而不是调用Deepseek API。但这一点无需在critical defects安全门槛.xlsx中注明。

2. 格式可参考critical defects安全门槛_已弃用版（有错误）.xlsx，但严禁盲目照抄critical defects安全门槛_已弃用版（有错误）.xlsx的任何内容。

3. 对于含有多个小问的题目（如A3/A4、B、X型题），不能对于所有小问给出一组笼统的Major Defect，而应对于每个小问，逐一给出一组Major Defect。对于每个含有多个小问的题目，不妨将其对应的Major Defect划成多行。这是critical defects安全门槛_已弃用版（有错误）.xlsx的错误之一。

4. 调用Deepseek API评价Major Defect的代码逻辑中相应修改，但无需真实运行。
