# 泌尿外科出科考试命卷论文项目

本仓库服务于一项比较“人类出题质量”和“MAS（多智能体系统）出题质量”的论文。我是论文第二作者，负责本项目中的编程、统计和绘图工作。

## 项目流程

- 一、获得人类题库
我们邀请人类专家命制了人类题库。因为医学专家习惯使用Word，而Word不便于机器处理，所以我们先将Word文档转换为TXT文件，再结构化为JSON格式。

- 二、获得MAS题库
我们调用deepseek-reasoner模型，学习人类题库和命题规范，生成JSON格式的MAS题库。第一轮生成题干和选项，第二轮生成答案解析和考点还原。

- 三、机器评价题库
对于人类题库的每道题目，我们标注了可读性，然后调用deepseek-reasoner模型，标注了QGEval评分和LLM评分。
对于MAS题库的每道题目，我们标注了可读性、和人类题库的文本相似性，然后调用deepseek-reasoner模型，标注了QGEval评分和LLM评分。

- 四、组成试卷
我们从人类题库和MAS题库中随机抽取题目，组成人类试卷（P卷）和MAS试卷（M卷）。为了便于第一作者查看试卷，我将试卷转换为TXT文件，即outputs\report_drafts中的P卷解析标注版和M卷解析标注版。因为QGEval评分和LLM评分具有随机性，所以对于每道题，我们调用了四次deepseek-reasoner模型，获得了四组QGEval评分和LLM评分，所以P卷解析标注版和M卷解析标注版各有四份。

- 五、模拟考试
为了消除考生疲劳的影响，我们将“P卷在前、M卷在后”的考试称为A卷，将“M卷在前、P卷在后”的考试称为B卷，得到了考生的作答数据，即plot\data\exam_responses和plot\data\exam_responses_2。其中，plot\data\exam_responses未标注题型，而plot\data\exam_responses_2标注了题型。

- 六、数据处理和论文绘图
第一作者对我的绘图要求放在plot目录下。plot\docs和plot\assets\visual_reference_previews是五张其他论文的优秀图片，我的绘图质量应对标这五张优秀图片。你会发现现有的P卷解析标注版和M卷解析标注版，以及plot\data\exam_responses和plot\data\exam_responses_2还不能满足第一作者的绘图要求，因此在绘图之前，需要进行数据处理。

注意，第一作者的绘图要求是由AI辅助生成的，各要求之间也许存在consistency问题。因此，你在数据处理和论文绘图之前，必须仔细阅读各个要求文件，充分理解第一作者的真实意图，并解决consistency问题。
