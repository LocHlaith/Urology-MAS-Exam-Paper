# Agent 绘图简报

## 不可协商规则

1. 本仓库 md 说明以中文为主；英文题名、变量名、文件名和统计术语可以保留。
2. 第一作者对图片交付的要求是：所有图片画成可编辑 PDF。CSV 不是第一作者的图片输出要求。
3. 本项目已确认：M卷 = MAS，P卷 = 人类；Form A = Human -> MAS，即 P卷 -> M卷；Form B = MAS -> Human，即 M卷 -> P卷。不要反写。
4. `docs/*` 原文中出现的 `item_master.csv`、`responses.csv` 等表名，只能理解为统计设计或数据字典建议；不要写成仓库现有文件，也不要要求用户按这些名字补齐数据。
5. 使用 `docs/*` 中由 Word 文档或工作簿转换来的原文时，优先引用原文措辞，不要用自己的概括替代。
6. 使用 `manifest.json` 核对每个转换文件来自哪个原始文件。
7. worksheet CSV 只是 Excel 的原始/缓存单元格导出；公式未重新计算，显示格式未保留。不能超出 workbook summary 和原始文件明示内容去发明变量含义。
8. TIF 预览图只作为视觉风格参考，除非原文明确指定它们是某张图的要求。
9. 如果 panel 标签、样本量、统计模型、非劣效界值、颜色、字体或数据来源缺失或矛盾，标记为 `UNKNOWN_OR_CONFLICTING` 并请求澄清。
10. 全局格式以 `Figure 统一参数.docx` / `docs/*figure_unified_parameters.md` 为准，除非某张图有更具体的明确要求。
11. 不要把示例、占位符 `XXX` 或统计 protocol 中的虚构数值当成锁定数据。

## 推荐绘图流程

1. 先读 `manifest.json` 和本简报。
2. 再读 `../../docs/PLOTTING_READINESS_AUDIT.md`，确认当前本地数据能支持哪些面板、哪些仍是缺口。
3. 读取 `docs/*figure_unified_parameters.md`，确认可编辑 PDF、字体、字号、分辨率和背景要求。
4. 读取 `docs/*plot_requirements_v1_0.md`，再读统计 protocol 和 figure/table 视图文档。
5. 如需使用 worksheet CSV，必须写明原始 workbook、sheet 和具体导出文件；CSV 是转换产物或统计整理材料，不是图片交付要求。
6. 作图前建立 panel-to-source 表：panel、原文要求、数据文件/工作表、派生统计量、未解决假设。
7. 代码注释或图形元数据中记录来源路径，不能依赖记忆。
8. 导出 PDF 时检查文字是否仍可编辑，避免字体转路径、整图栅格化或透明背景。
