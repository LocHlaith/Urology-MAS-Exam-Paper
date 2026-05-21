软件：Python 3.11 + Matplotlib

字体：DejaVu Sans

正文字号：8 pt

Panel 字母：10 pt bold

背景：白色、不透明

分辨率：600 dpi

输出格式：可编辑 PDF

SVG 设置：保留可编辑文字，不转路径

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