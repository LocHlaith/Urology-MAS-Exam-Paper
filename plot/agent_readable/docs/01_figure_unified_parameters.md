# Converted source: `plot/Figure 统一参数.docx`

## Conversion metadata

- Source path: `plot/Figure 统一参数.docx`
- Source SHA256: `af00e49483f91fc8f7a4c34d7fe8552955ac5c99140002997a342c774a92c315`
- Generated at: `2026-05-19T21:04:44`
- Conversion method: pandoc docx -> GitHub-Flavored Markdown (`--wrap=none`)
- Agent rule: treat the section named `Original Extract` as source material. Do not infer missing statistics, panel labels, sample sizes, or figure styles from this file.

## Original Extract

\#\# Figure 统一参数

\* 软件：Python 3.11 + Matplotlib

\* 字体：\*\*DejaVu Sans\*\*

\* 正文字号：\*\*8 pt\*\*

\* Panel 字母：\*\*10 pt bold\*\*

\* 背景：白色、不透明

\* 分辨率：\*\*600 dpi\*\*

\* 输出格式：PNG / PDF / SVG

\* SVG 设置：保留可编辑文字，不转路径

\`\`\`python

mpl.rcParams.update({

"font.family": "DejaVu Sans",

"font.sans-serif": \["DejaVu Sans"\],

"mathtext.fontset": "dejavusans",

"font.size": 8,

"axes.labelsize": 8,

"xtick.labelsize": 8,

"ytick.labelsize": 8,

"legend.fontsize": 8,

"pdf.fonttype": 42,

"ps.fonttype": 42,

"svg.fonttype": "none",

"savefig.dpi": 600,

"savefig.transparent": False,

"figure.facecolor": "white",

"axes.facecolor": "white",

})

\`\`\`

\#\# 基础配色

\`\`\`python

UROMAS\_COLORS = {

"grid": "\#E3DFD8",

"spine": "\#9E9A93",

"text": "\#3E3E3E",

"text\_dark": "\#2A251F",

"tick": "\#4F4F4F",

"border": "\#C8C2B8",

"soft\_separator": "\#D8D2C9",

}

\`\`\`

\#\# UroIPND-20 / Figure 2–3 组别配色

\`\`\`python

PALETTE = {

"UroMAS": "\#B86758",

"Claude Sonnet 4.5": "\#F7AC63",

"GPT-5": "\#75AFCA",

"Human": "\#313E96",

}

PALETTE\_FILL = {

"UroMAS": "\#F2DFDB",

"Claude Sonnet 4.5": "\#FDE9D2",

"GPT-5": "\#DCEAF1",

"Human": "\#D9DCF1",

}

\`\`\`

\#\# Figure 4 模型配色

\`\`\`python

MODEL\_COLORS = {

"UroMAS (DeepSeek-based)": "\#4D6BFE",

"UroMAS (GPT-5-based)": "\#2F3136",

"GPT-5": "\#2F3136",

"Claude Sonnet 4.5": "\#D97757",

"Kimi K2 Thinking": "\#1F1F1F",

"Doubao-Seed-1.6": "\#7C5CFF",

"GLM-4.6": "\#2F5BFF",

"DeepSeek-V3.2": "\#4D6BFE",

}

MODEL\_FILLS = {

"UroMAS (DeepSeek-based)": "\#E1E7FF",

"UroMAS (GPT-5-based)": "\#E8E8E8",

"GPT-5": "\#E8E8E8",

"Claude Sonnet 4.5": "\#F6DED4",

"Kimi K2 Thinking": "\#E6E6E6",

"Doubao-Seed-1.6": "\#E9E2FF",

"GLM-4.6": "\#DDE5FF",

"DeepSeek-V3.2": "\#E1E7FF",

}

\`\`\`

\#\# 可写入 Methods 的简洁表述

Figures were generated using Python 3.11 and Matplotlib with a unified visual style. DejaVu Sans was used throughout; body text, axis labels, tick labels, legends and annotations were set to 8 pt, and panel labels were set to 10 pt bold. A muted colour palette with paired dark strokes and light fills was used consistently across groups, models and endpoints. Figures were exported with a white, non-transparent background at 600 dpi, with editable text preserved in vector outputs where applicable.
