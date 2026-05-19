# chart.py
# -*- coding: utf-8 -*-
"""
chart.py
用于从同一题库的多个 JSON（A1/A2/A3/A4/B/X）生成论文例图：
1) 各题型 fuzzywuzzy_ratio_max 直方图（跨题型统一 x/y 区间）
2) 各题型 sentencebert_cosine_max 直方图（跨题型统一 x/y 区间）
3) 各题型 3gram_jaccard_max 直方图（跨题型统一 x/y 区间）
4) 各题型 textstat_flesch_reading_ease 直方图（跨题型统一 x/y 区间）
5) 各题型：文本长度 vs 四个指标散点图（已拆成 4 张单纵坐标图；跨题型统一 x/y 区间）
6) 各题型：fuzzywuzzy 为 x，其它三个为 y 的散点图（拆成 3 张；跨题型统一 x/y 区间）
7) 各题型：sentencebert 为 x，其它三个为 y 的散点图（拆成 3 张；跨题型统一 x/y 区间）
8) 各题型：3gram 为 x，其它三个为 y 的散点图（拆成 3 张；跨题型统一 x/y 区间）
9) 各题型：flesch 为 x，其它三个为 y 的散点图（拆成 3 张；跨题型统一 x/y 区间）
10) 各题型：prototype/fuzzy/sentencebert/3gram 四集合韦恩图（统一位置图例）
11) 所有图片 4:3，纯英文，Times New Roman，标题大小写规范
12) 同一组直方图跨题型统一 y 轴范围：先统计再绘图（并统一 x 轴范围）

使用示例：
python scripts/plotting/chart.py --input_dir data/banks --output_dir outputs/figures/similarity

注意：
- 本脚本默认读取 input_dir 下所有 new_bank_*.json
- JSON 为 list[dict]，且同一题库内格式一致（无需 corner case）

修改（新增）：
1) 分别对于各个题型，计算 fuzzywuzzy_ratio_max、sentencebert_cosine_max、3gram_jaccard_max、
   textstat_flesch_reading_ease 的 min、max、mean、std；然后不区分题型，再计算一份全体统计。
2) 输出到 outputs/statistics/statistics_for_similarity.txt
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple, Optional

import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

# 4-set venn：使用 PyPI 包 "venn"
from venn import venn

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from project_paths import BANK_DIR, FIGURE_DIR, STATISTICS_DIR


# -----------------------------
# 统计输出路径（按需求固定到绝对路径）
# -----------------------------
STATISTICS_OUT_PATH = STATISTICS_DIR / "statistics_for_similarity.txt"


# -----------------------------
# 全局样式（Times New Roman + 英文图表风格）
# -----------------------------
def setup_style() -> None:
    mpl.rcParams.update({
        "font.family": "Times New Roman",
        "font.size": 11,
        "axes.titlesize": 14,
        "axes.labelsize": 12,
        "legend.fontsize": 10,
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
        "figure.dpi": 120,
        "savefig.dpi": 300,
        "axes.unicode_minus": False,
    })


# -----------------------------
# 配色（按需求固定）
# -----------------------------
COL_HIST_FUZZY = "#7F8A9B"
COL_HIST_SBERT = "#B7CBD5"
COL_HIST_3GRAM = "#C1DDDB"
COL_HIST_FLESCH = "#D1DED7"

COL_SCATTER_FUZZY = "#5E6C82"
COL_SCATTER_SBERT = "#899FB0"
COL_SCATTER_3GRAM = "#81B3A9"
COL_SCATTER_FLESCH = "#B3C6BB"

COL_VENN_PROTO = "#EBE6DE"
COL_VENN_FUZZY = "#7F8A9B"
COL_VENN_SBERT = "#B7CBD5"
COL_VENN_3GRAM = "#C1DDDB"


# -----------------------------
# 直方图分箱配置
# -----------------------------
BINS_FUZZY = (0, 100, 5)          # [0,100,5]
BINS_SBERT = (0.50, 1.00, 0.05)   # [0.50,1.00,0.05]
BINS_3GRAM = (0, 100, 5)          # [0,100,5]
BINS_FLESCH = (-200, 200, 10)     # [-200,200,10]


# -----------------------------
# 工具函数
# -----------------------------
def title_case(s: str) -> str:
    """简易 Title Case，避免全大写/全小写，适合论文图题。"""
    small = {"a", "an", "the", "and", "or", "but", "for", "nor", "as", "at", "by", "in", "of", "on", "per", "to", "vs"}
    words = re.split(r"(\s+)", s.strip())
    out = []
    for i, w in enumerate(words):
        if w.isspace():
            out.append(w)
            continue
        lw = w.lower()
        if i == 0 or i == len(words) - 1:
            out.append(lw.capitalize())
        else:
            out.append(lw if lw in small else lw.capitalize())
    return "".join(out)


def nice_ylim_max(v: float) -> float:
    """把最大频数抬到“好看”的刻度（向上取整到 1/2/5/10 * 10^k）。"""
    if v <= 0:
        return 1.0
    v = v * 1.10
    mag = 10 ** math.floor(math.log10(v))
    norm = v / mag
    if norm <= 1:
        step = 1
    elif norm <= 2:
        step = 2
    elif norm <= 5:
        step = 5
    else:
        step = 10
    return step * mag


def nice_num_step(v: float) -> float:
    """
    给定一个正数 v（通常是范围或范围的一部分），返回“好看”的步长：1/2/5/10 * 10^k。
    """
    if not np.isfinite(v) or v <= 0:
        return 1.0
    mag = 10 ** math.floor(math.log10(v))
    norm = v / mag
    if norm <= 1:
        step = 1
    elif norm <= 2:
        step = 2
    elif norm <= 5:
        step = 5
    else:
        step = 10
    return step * mag


def nice_axis_limits(vmin: float, vmax: float, pad_ratio: float = 0.05) -> Tuple[float, float]:
    """
    根据数据 min/max 生成“统一且好看”的坐标轴范围：
    - 两端做少量 padding
    - 再按 nice 步长向外取整
    """
    if not (np.isfinite(vmin) and np.isfinite(vmax)):
        return 0.0, 1.0
    if vmin == vmax:
        step = nice_num_step(abs(vmin) if vmin != 0 else 1.0)
        return vmin - step, vmax + step

    span = vmax - vmin
    pad = span * pad_ratio
    a = vmin - pad
    b = vmax + pad

    step = nice_num_step((b - a) / 5.0)  # 期望大概 5 个大刻度区间
    lo = math.floor(a / step) * step
    hi = math.ceil(b / step) * step
    if lo == hi:
        hi = lo + step
    return float(lo), float(hi)


def make_bins(start: float, end: float, step: float) -> np.ndarray:
    """生成直方图 bins，包含右端点。"""
    return np.arange(start, end + step * 0.5, step, dtype=float)


def read_json(path: Path) -> List[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def find_bank_files(input_dir: Path) -> List[Path]:
    files = sorted(input_dir.glob("new_bank_*.json"))
    if not files:
        raise FileNotFoundError(f"No files matched 'new_bank_*.json' in: {input_dir}")
    return files


def strip_ws(text: str) -> str:
    return re.sub(r"\s+", "", text or "")


def options_to_text(options: Dict[str, Any]) -> str:
    """把 options dict 变成可拼接文本。"""
    if not isinstance(options, dict):
        return ""
    parts = []
    for k in sorted(options.keys()):
        parts.append(str(k))
        parts.append(str(options[k]))
    return " ".join(parts)


def calc_text_length_by_type(q: Dict[str, Any]) -> int:
    """
    计算“字数”（这里以去掉空白后的字符数作为长度）：
    - A1/A2/X: stem + options
    - A3: case + stem1 + options1 + stem2 + options2
    - A4: case + stem1 + options1 + stem2 + options2 + stem3 + options3
    - B: options + stem1 + stem2 + stem3
    """
    t = q.get("type", "")

    def join(*xs: str) -> str:
        return strip_ws(" ".join([x for x in xs if x]))

    if t in {"A1", "A2", "X"}:
        text = join(
            str(q.get("stem", "")),
            options_to_text(q.get("options", {})),
        )
        return len(text)

    if t == "A3":
        text = join(
            str(q.get("case", "")),
            str(q.get("stem1", "")),
            options_to_text(q.get("options1", {})),
            str(q.get("stem2", "")),
            options_to_text(q.get("options2", {})),
        )
        return len(text)

    if t == "A4":
        text = join(
            str(q.get("case", "")),
            str(q.get("stem1", "")),
            options_to_text(q.get("options1", {})),
            str(q.get("stem2", "")),
            options_to_text(q.get("options2", {})),
            str(q.get("stem3", "")),
            options_to_text(q.get("options3", {})),
        )
        return len(text)

    if t == "B":
        text = join(
            options_to_text(q.get("options", {})),
            str(q.get("stem1", "")),
            str(q.get("stem2", "")),
            str(q.get("stem3", "")),
        )
        return len(text)

    text = join(json.dumps(q, ensure_ascii=False))
    return len(text)


def safe_float(x: Any) -> float:
    try:
        return float(x)
    except Exception:
        return float("nan")


def finite_minmax(arr: np.ndarray) -> Tuple[float, float]:
    v = arr[np.isfinite(arr)]
    if v.size == 0:
        return float("nan"), float("nan")
    return float(np.min(v)), float(np.max(v))


# -----------------------------
# 数据汇总
# -----------------------------
def load_all_questions(input_dir: Path) -> Dict[str, List[Dict[str, Any]]]:
    """
    读取所有 new_bank_*.json，并按题型 type 分组。
    返回：{ "A1": [...], "A2": [...], ... }
    """
    files = find_bank_files(input_dir)
    by_type: Dict[str, List[Dict[str, Any]]] = {}

    for fp in files:
        data = read_json(fp)
        if not isinstance(data, list):
            continue
        for q in data:
            t = q.get("type", "")
            if not t:
                continue
            by_type.setdefault(t, []).append(q)

    order = ["A1", "A2", "A3", "A4", "B", "X"]
    ordered: Dict[str, List[Dict[str, Any]]] = {}
    for t in order:
        if t in by_type:
            ordered[t] = by_type[t]
    for t in sorted(set(by_type.keys()) - set(order)):
        ordered[t] = by_type[t]

    return ordered


def extract_metric_arrays(qs: List[Dict[str, Any]]) -> Dict[str, np.ndarray]:
    """从某一题型的题目列表中抽取需要绘图的数组。"""
    fuzzy = np.array([safe_float(q.get("fuzzywuzzy_ratio_max")) for q in qs], dtype=float)
    sbert = np.array([safe_float(q.get("sentencebert_cosine_max")) for q in qs], dtype=float)
    gram3 = np.array([safe_float(q.get("3gram_jaccard_max")) for q in qs], dtype=float)
    flesch = np.array([safe_float(q.get("textstat_flesch_reading_ease")) for q in qs], dtype=float)
    length = np.array([float(calc_text_length_by_type(q)) for q in qs], dtype=float)
    return {
        "fuzzy": fuzzy,
        "sbert": sbert,
        "3gram": gram3,
        "flesch": flesch,
        "length": length,
    }


def compute_hist_max_y(by_type_metrics: Dict[str, Dict[str, np.ndarray]]) -> Dict[str, float]:
    """
    为每个指标组计算“跨题型统一 y 轴最大值”。
    返回：{"fuzzy": ymax, "sbert": ymax, "3gram": ymax, "flesch": ymax}
    """
    bins = {
        "fuzzy": make_bins(*BINS_FUZZY),
        "sbert": make_bins(*BINS_SBERT),
        "3gram": make_bins(*BINS_3GRAM),
        "flesch": make_bins(*BINS_FLESCH),
    }

    max_y: Dict[str, float] = {"fuzzy": 0, "sbert": 0, "3gram": 0, "flesch": 0}
    for _, m in by_type_metrics.items():
        for k in ["fuzzy", "sbert", "3gram", "flesch"]:
            arr = m[k]
            arr = arr[np.isfinite(arr)]
            if arr.size == 0:
                continue
            counts, _ = np.histogram(arr, bins=bins[k])
            max_y[k] = max(max_y[k], float(np.max(counts)))

    for k in list(max_y.keys()):
        max_y[k] = nice_ylim_max(max_y[k])

    return max_y


def compute_global_scatter_limits(by_type_metrics: Dict[str, Dict[str, np.ndarray]]) -> Dict[str, Tuple[Tuple[float, float], Tuple[float, float]]]:
    """
    先对“所有题型”做统计，得到每一组散点图的统一 (xlim, ylim)。
    返回 dict：
      key -> ( (xmin,xmax), (ymin,ymax) )
    key 设计与输出文件名一一对应，方便主流程直接取用。
    """
    all_len = np.concatenate([m["length"] for m in by_type_metrics.values()]) if by_type_metrics else np.array([], dtype=float)
    all_fuzzy = np.concatenate([m["fuzzy"] for m in by_type_metrics.values()]) if by_type_metrics else np.array([], dtype=float)
    all_sbert = np.concatenate([m["sbert"] for m in by_type_metrics.values()]) if by_type_metrics else np.array([], dtype=float)
    all_3gram = np.concatenate([m["3gram"] for m in by_type_metrics.values()]) if by_type_metrics else np.array([], dtype=float)
    all_flesch = np.concatenate([m["flesch"] for m in by_type_metrics.values()]) if by_type_metrics else np.array([], dtype=float)

    len_xlim = nice_axis_limits(*finite_minmax(all_len))
    fuzzy_ylim = nice_axis_limits(*finite_minmax(all_fuzzy))
    sbert_ylim = nice_axis_limits(*finite_minmax(all_sbert))
    gram3_ylim = nice_axis_limits(*finite_minmax(all_3gram))
    flesch_ylim = nice_axis_limits(*finite_minmax(all_flesch))

    fuzzy_xlim = nice_axis_limits(*finite_minmax(all_fuzzy))
    sbert_xlim = nice_axis_limits(*finite_minmax(all_sbert))
    gram3_xlim = nice_axis_limits(*finite_minmax(all_3gram))
    flesch_xlim = nice_axis_limits(*finite_minmax(all_flesch))

    limits: Dict[str, Tuple[Tuple[float, float], Tuple[float, float]]] = {}

    limits["length_vs_fuzzy"] = (len_xlim, fuzzy_ylim)
    limits["length_vs_sentencebert"] = (len_xlim, sbert_ylim)
    limits["length_vs_3gram"] = (len_xlim, gram3_ylim)
    limits["length_vs_flesch"] = (len_xlim, flesch_ylim)

    limits["fuzzy_vs_sentencebert"] = (fuzzy_xlim, sbert_ylim)
    limits["fuzzy_vs_3gram"] = (fuzzy_xlim, gram3_ylim)
    limits["fuzzy_vs_flesch"] = (fuzzy_xlim, flesch_ylim)

    limits["sentencebert_vs_fuzzy"] = (sbert_xlim, fuzzy_ylim)
    limits["sentencebert_vs_3gram"] = (sbert_xlim, gram3_ylim)
    limits["sentencebert_vs_flesch"] = (sbert_xlim, flesch_ylim)

    limits["3gram_vs_fuzzy"] = (gram3_xlim, fuzzy_ylim)
    limits["3gram_vs_sentencebert"] = (gram3_xlim, sbert_ylim)
    limits["3gram_vs_flesch"] = (gram3_xlim, flesch_ylim)

    limits["flesch_vs_fuzzy"] = (flesch_xlim, fuzzy_ylim)
    limits["flesch_vs_sentencebert"] = (flesch_xlim, sbert_ylim)
    limits["flesch_vs_3gram"] = (flesch_xlim, gram3_ylim)

    return limits


# -----------------------------
# 统计：min/max/mean/std（按题型 + 全体）
# -----------------------------
def metric_summary(arr: np.ndarray) -> Dict[str, float]:
    """
    返回单个指标的 summary：min/max/mean/std + n（有效样本数）。
    std 使用样本标准差（ddof=1），当 n<2 时 std=nan。
    """
    v = arr[np.isfinite(arr)]
    n = int(v.size)
    if n == 0:
        return {"n": 0, "min": float("nan"), "max": float("nan"), "mean": float("nan"), "std": float("nan")}
    std = float(np.std(v, ddof=1)) if n >= 2 else float("nan")
    return {
        "n": n,
        "min": float(np.min(v)),
        "max": float(np.max(v)),
        "mean": float(np.mean(v)),
        "std": std,
    }


def compute_statistics(by_type_metrics: Dict[str, Dict[str, np.ndarray]]) -> Tuple[Dict[str, Dict[str, Dict[str, float]]], Dict[str, Dict[str, float]]]:
    """
    返回：
    - per_type_stats[type][metric] -> summary dict
    - overall_stats[metric] -> summary dict
    """
    metrics = ["fuzzy", "sbert", "3gram", "flesch"]

    per_type_stats: Dict[str, Dict[str, Dict[str, float]]] = {}
    for t, m in by_type_metrics.items():
        per_type_stats[t] = {}
        for k in metrics:
            per_type_stats[t][k] = metric_summary(m[k])

    # overall
    overall_stats: Dict[str, Dict[str, float]] = {}
    for k in metrics:
        all_arr = np.concatenate([m[k] for m in by_type_metrics.values()]) if by_type_metrics else np.array([], dtype=float)
        overall_stats[k] = metric_summary(all_arr)

    return per_type_stats, overall_stats


def format_float(x: float, digits: int = 6) -> str:
    if not np.isfinite(x):
        return "NA"
    # 兼顾论文观感：去掉 -0.000000
    if abs(x) < 0.5 * 10 ** (-digits):
        x = 0.0
    return f"{x:.{digits}f}"


def write_statistics_txt(
    out_path: Path,
    per_type_stats: Dict[str, Dict[str, Dict[str, float]]],
    overall_stats: Dict[str, Dict[str, float]],
) -> None:
    """
    输出为纯文本，方便直接发给合作者看。
    """
    metric_display = {
        "fuzzy": "fuzzywuzzy_ratio_max",
        "sbert": "sentencebert_cosine_max",
        "3gram": "3gram_jaccard_max",
        "flesch": "textstat_flesch_reading_ease",
    }
    order_metrics = ["fuzzy", "sbert", "3gram", "flesch"]

    lines: List[str] = []
    lines.append("Question Bank Statistics (min/max/mean/std)")
    lines.append("Note: std is sample standard deviation (ddof=1). NA means no valid numeric values.")
    lines.append("")

    # per type
    lines.append("=== By Question Type ===")
    for t in per_type_stats.keys():
        lines.append(f"[Type: {t}]")
        header = f"{'metric':<30}  {'n':>6}  {'min':>14}  {'max':>14}  {'mean':>14}  {'std':>14}"
        lines.append(header)
        lines.append("-" * len(header))
        for k in order_metrics:
            s = per_type_stats[t][k]
            lines.append(
                f"{metric_display[k]:<30}  "
                f"{int(s['n']):>6d}  "
                f"{format_float(s['min']):>14}  "
                f"{format_float(s['max']):>14}  "
                f"{format_float(s['mean']):>14}  "
                f"{format_float(s['std']):>14}"
            )
        lines.append("")

    # overall
    lines.append("=== Overall (All Types Combined) ===")
    header = f"{'metric':<30}  {'n':>6}  {'min':>14}  {'max':>14}  {'mean':>14}  {'std':>14}"
    lines.append(header)
    lines.append("-" * len(header))
    for k in order_metrics:
        s = overall_stats[k]
        lines.append(
            f"{metric_display[k]:<30}  "
            f"{int(s['n']):>6d}  "
            f"{format_float(s['min']):>14}  "
            f"{format_float(s['max']):>14}  "
            f"{format_float(s['mean']):>14}  "
            f"{format_float(s['std']):>14}"
        )
    lines.append("")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")


# -----------------------------
# 绘图：直方图
# -----------------------------
def plot_histogram(
    values: np.ndarray,
    bins: np.ndarray,
    color: str,
    xlabel: str,
    title: str,
    out_path: Path,
    ylim_max: float,
    xlim: Optional[Tuple[float, float]] = None,
) -> None:
    fig, ax = plt.subplots(figsize=(8, 6))  # 4:3
    v = values[np.isfinite(values)]
    ax.hist(v, bins=bins, color=color, edgecolor="white", linewidth=0.6)

    ax.set_xlabel(xlabel)
    ax.set_ylabel("Frequency")
    ax.set_title(title_case(title))
    ax.set_ylim(0, ylim_max)
    if xlim is not None:
        ax.set_xlim(xlim)

    ax.grid(axis="y", alpha=0.25, linestyle="--", linewidth=0.7)
    fig.tight_layout()
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)


# -----------------------------
# 绘图：散点图（单纵坐标版 + 统一轴范围）
# -----------------------------
def plot_scatter_length_vs_one_metric(
    length: np.ndarray,
    metric: np.ndarray,
    metric_label: str,
    metric_color: str,
    qtype: str,
    out_path: Path,
    xlim: Tuple[float, float],
    ylim: Tuple[float, float],
) -> None:
    fig, ax = plt.subplots(figsize=(8, 6))  # 4:3
    mask = np.isfinite(length) & np.isfinite(metric)

    ax.scatter(length[mask], metric[mask], s=18, c=metric_color, alpha=0.75)
    ax.set_xlabel("Text Length (Characters)")
    ax.set_ylabel(metric_label)
    ax.set_title(title_case(f"Text Length Vs {metric_label} ({qtype})"))
    ax.set_xlim(xlim)
    ax.set_ylim(ylim)
    ax.grid(alpha=0.25, linestyle="--", linewidth=0.7)

    fig.tight_layout()
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)


def plot_scatter_pair(
    x: np.ndarray,
    y: np.ndarray,
    x_label: str,
    y_label: str,
    color: str,
    title: str,
    out_path: Path,
    xlim: Tuple[float, float],
    ylim: Tuple[float, float],
) -> None:
    fig, ax = plt.subplots(figsize=(8, 6))  # 4:3
    mask = np.isfinite(x) & np.isfinite(y)

    ax.scatter(x[mask], y[mask], s=18, c=color, alpha=0.75)
    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)
    ax.set_title(title_case(title))
    ax.set_xlim(xlim)
    ax.set_ylim(ylim)
    ax.grid(alpha=0.25, linestyle="--", linewidth=0.7)

    fig.tight_layout()
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)


# -----------------------------
# 绘图：韦恩图（四集合，元素为 (qid, predicted_id) + 统一位置图例）
# -----------------------------
def plot_venn_agreement(
    qs: List[Dict[str, Any]],
    qtype: str,
    out_path: Path,
) -> None:
    """
    用四集合韦恩图展示 prototype/fuzzy/sbert/3gram 的“相同预测”重叠。
    关键设计：每个方法集合的元素定义为 (question_id, method_value)。
    这样当两个方法对同一题给出相同的 id 时，元素完全相同 -> 自动落在重叠区域。
    """
    proto_set = set()
    fuzzy_set = set()
    sbert_set = set()
    gram3_set = set()

    for q in qs:
        qid = str(q.get("id", ""))
        proto = str(q.get("prototype", ""))
        fz = str(q.get("fuzzywuzzy_doubt", ""))
        sb = str(q.get("sentencebert_doubt", ""))
        g3 = str(q.get("3gram_doubt", ""))

        proto_set.add((qid, proto))
        fuzzy_set.add((qid, fz))
        sbert_set.add((qid, sb))
        gram3_set.add((qid, g3))

    data = {
        "Prototype": proto_set,
        "FuzzyWuzzy": fuzzy_set,
        "Sentence-BERT": sbert_set,
        "3-gram": gram3_set,
    }

    fig, ax = plt.subplots(figsize=(8, 6))  # 4:3
    ax.set_title(title_case(f"Agreement Venn Diagram ({qtype})"))

    venn(
        data,
        ax=ax,
        cmap=[COL_VENN_PROTO, COL_VENN_FUZZY, COL_VENN_SBERT, COL_VENN_3GRAM],
        fontsize=10,
        legend_loc=None
    )

    ax.set_axis_off()

    handles = [
        mpatches.Patch(facecolor=COL_VENN_PROTO, edgecolor="none", label="Prototype"),
        mpatches.Patch(facecolor=COL_VENN_FUZZY, edgecolor="none", label="FuzzyWuzzy"),
        mpatches.Patch(facecolor=COL_VENN_SBERT, edgecolor="none", label="Sentence-BERT"),
        mpatches.Patch(facecolor=COL_VENN_3GRAM, edgecolor="none", label="3-gram"),
    ]
    ax.legend(
        handles=handles,
        loc="center left",
        bbox_to_anchor=(1.02, 0.5),
        frameon=False,
        borderaxespad=0.0,
        handlelength=1.2,
        handleheight=1.2,
    )

    fig.tight_layout(rect=[0, 0, 0.82, 1])
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)


# -----------------------------
# 主流程
# -----------------------------
def main() -> None:
    setup_style()

    parser = argparse.ArgumentParser(description="Generate paper-ready charts from question bank JSON files.")
    parser.add_argument("--input_dir", type=str, default=str(BANK_DIR), help="Directory containing new_bank_*.json files.")
    parser.add_argument("--output_dir", type=str, default=str(FIGURE_DIR / "similarity"), help="Output directory for figures.")
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 读取并分题型
    by_type = load_all_questions(input_dir)

    # 抽取指标数组（先统计）
    by_type_metrics: Dict[str, Dict[str, np.ndarray]] = {}
    for t, qs in by_type.items():
        by_type_metrics[t] = extract_metric_arrays(qs)

    # === 新增：统计输出（按题型 + 全体） ===
    per_type_stats, overall_stats = compute_statistics(by_type_metrics)
    write_statistics_txt(STATISTICS_OUT_PATH, per_type_stats, overall_stats)

    # 计算直方图：统一 y 上限
    hist_ymax = compute_hist_max_y(by_type_metrics)

    # 直方图：bins（也决定统一 x 区间）
    bins_fuzzy = make_bins(*BINS_FUZZY)
    bins_sbert = make_bins(*BINS_SBERT)
    bins_3gram = make_bins(*BINS_3GRAM)
    bins_flesch = make_bins(*BINS_FLESCH)

    # 直方图：统一 x 区间（由 bins 直接给定，保证完全一致）
    hist_xlim = {
        "fuzzy": (float(bins_fuzzy[0]), float(bins_fuzzy[-1])),
        "sbert": (float(bins_sbert[0]), float(bins_sbert[-1])),
        "3gram": (float(bins_3gram[0]), float(bins_3gram[-1])),
        "flesch": (float(bins_flesch[0]), float(bins_flesch[-1])),
    }

    # 散点图：统一 x/y 区间（数据驱动统计后固定）
    scatter_limits = compute_global_scatter_limits(by_type_metrics)

    # 分题型绘图
    for t, qs in by_type.items():
        m = by_type_metrics[t]

        # --- 1) fuzzy 直方图
        plot_histogram(
            values=m["fuzzy"],
            bins=bins_fuzzy,
            color=COL_HIST_FUZZY,
            xlabel="FuzzyWuzzy Ratio Max",
            title=f"FuzzyWuzzy Ratio Max Distribution ({t})",
            out_path=output_dir / f"hist_fuzzy_ratio_max_{t}.png",
            ylim_max=hist_ymax["fuzzy"],
            xlim=hist_xlim["fuzzy"],
        )

        # --- 2) sbert 直方图
        plot_histogram(
            values=m["sbert"],
            bins=bins_sbert,
            color=COL_HIST_SBERT,
            xlabel="Sentence-BERT Cosine Max",
            title=f"Sentence-BERT Cosine Max Distribution ({t})",
            out_path=output_dir / f"hist_sentencebert_cosine_max_{t}.png",
            ylim_max=hist_ymax["sbert"],
            xlim=hist_xlim["sbert"],
        )

        # --- 3) 3gram 直方图
        plot_histogram(
            values=m["3gram"],
            bins=bins_3gram,
            color=COL_HIST_3GRAM,
            xlabel="3-gram Jaccard Max",
            title=f"3-gram Jaccard Max Distribution ({t})",
            out_path=output_dir / f"hist_3gram_jaccard_max_{t}.png",
            ylim_max=hist_ymax["3gram"],
            xlim=hist_xlim["3gram"],
        )

        # --- 4) flesch 直方图
        plot_histogram(
            values=m["flesch"],
            bins=bins_flesch,
            color=COL_HIST_FLESCH,
            xlabel="Flesch Reading Ease",
            title=f"Flesch Reading Ease Distribution ({t})",
            out_path=output_dir / f"hist_flesch_reading_ease_{t}.png",
            ylim_max=hist_ymax["flesch"],
            xlim=hist_xlim["flesch"],
        )

        # --- 5) 文本长度 vs 四指标（拆成 4 张单纵坐标图，且跨题型统一轴）
        xlim, ylim = scatter_limits["length_vs_fuzzy"]
        plot_scatter_length_vs_one_metric(
            length=m["length"],
            metric=m["fuzzy"],
            metric_label="FuzzyWuzzy Ratio Max",
            metric_color=COL_SCATTER_FUZZY,
            qtype=t,
            out_path=output_dir / f"scatter_length_vs_fuzzy_{t}.png",
            xlim=xlim,
            ylim=ylim,
        )

        xlim, ylim = scatter_limits["length_vs_sentencebert"]
        plot_scatter_length_vs_one_metric(
            length=m["length"],
            metric=m["sbert"],
            metric_label="Sentence-BERT Cosine Max",
            metric_color=COL_SCATTER_SBERT,
            qtype=t,
            out_path=output_dir / f"scatter_length_vs_sentencebert_{t}.png",
            xlim=xlim,
            ylim=ylim,
        )

        xlim, ylim = scatter_limits["length_vs_3gram"]
        plot_scatter_length_vs_one_metric(
            length=m["length"],
            metric=m["3gram"],
            metric_label="3-gram Jaccard Max",
            metric_color=COL_SCATTER_3GRAM,
            qtype=t,
            out_path=output_dir / f"scatter_length_vs_3gram_{t}.png",
            xlim=xlim,
            ylim=ylim,
        )

        xlim, ylim = scatter_limits["length_vs_flesch"]
        plot_scatter_length_vs_one_metric(
            length=m["length"],
            metric=m["flesch"],
            metric_label="Flesch Reading Ease",
            metric_color=COL_SCATTER_FLESCH,
            qtype=t,
            out_path=output_dir / f"scatter_length_vs_flesch_{t}.png",
            xlim=xlim,
            ylim=ylim,
        )

        # --- 6) x=fuzzy，y=其它三个（跨题型统一轴）
        xlim, ylim = scatter_limits["fuzzy_vs_sentencebert"]
        plot_scatter_pair(
            x=m["fuzzy"], y=m["sbert"],
            x_label="FuzzyWuzzy Ratio Max", y_label="Sentence-BERT Cosine Max",
            color=COL_SCATTER_SBERT,
            title=f"FuzzyWuzzy Ratio Max Vs Sentence-BERT Cosine Max ({t})",
            out_path=output_dir / f"scatter_fuzzy_vs_sentencebert_{t}.png",
            xlim=xlim, ylim=ylim,
        )

        xlim, ylim = scatter_limits["fuzzy_vs_3gram"]
        plot_scatter_pair(
            x=m["fuzzy"], y=m["3gram"],
            x_label="FuzzyWuzzy Ratio Max", y_label="3-gram Jaccard Max",
            color=COL_SCATTER_3GRAM,
            title=f"FuzzyWuzzy Ratio Max Vs 3-gram Jaccard Max ({t})",
            out_path=output_dir / f"scatter_fuzzy_vs_3gram_{t}.png",
            xlim=xlim, ylim=ylim,
        )

        xlim, ylim = scatter_limits["fuzzy_vs_flesch"]
        plot_scatter_pair(
            x=m["fuzzy"], y=m["flesch"],
            x_label="FuzzyWuzzy Ratio Max", y_label="Flesch Reading Ease",
            color=COL_SCATTER_FLESCH,
            title=f"FuzzyWuzzy Ratio Max Vs Flesch Reading Ease ({t})",
            out_path=output_dir / f"scatter_fuzzy_vs_flesch_{t}.png",
            xlim=xlim, ylim=ylim,
        )

        # --- 7) x=sbert，y=其它三个（跨题型统一轴）
        xlim, ylim = scatter_limits["sentencebert_vs_fuzzy"]
        plot_scatter_pair(
            x=m["sbert"], y=m["fuzzy"],
            x_label="Sentence-BERT Cosine Max", y_label="FuzzyWuzzy Ratio Max",
            color=COL_SCATTER_FUZZY,
            title=f"Sentence-BERT Cosine Max Vs FuzzyWuzzy Ratio Max ({t})",
            out_path=output_dir / f"scatter_sentencebert_vs_fuzzy_{t}.png",
            xlim=xlim, ylim=ylim,
        )

        xlim, ylim = scatter_limits["sentencebert_vs_3gram"]
        plot_scatter_pair(
            x=m["sbert"], y=m["3gram"],
            x_label="Sentence-BERT Cosine Max", y_label="3-gram Jaccard Max",
            color=COL_SCATTER_3GRAM,
            title=f"Sentence-BERT Cosine Max Vs 3-gram Jaccard Max ({t})",
            out_path=output_dir / f"scatter_sentencebert_vs_3gram_{t}.png",
            xlim=xlim, ylim=ylim,
        )

        xlim, ylim = scatter_limits["sentencebert_vs_flesch"]
        plot_scatter_pair(
            x=m["sbert"], y=m["flesch"],
            x_label="Sentence-BERT Cosine Max", y_label="Flesch Reading Ease",
            color=COL_SCATTER_FLESCH,
            title=f"Sentence-BERT Cosine Max Vs Flesch Reading Ease ({t})",
            out_path=output_dir / f"scatter_sentencebert_vs_flesch_{t}.png",
            xlim=xlim, ylim=ylim,
        )

        # --- 8) x=3gram，y=其它三个（跨题型统一轴）
        xlim, ylim = scatter_limits["3gram_vs_fuzzy"]
        plot_scatter_pair(
            x=m["3gram"], y=m["fuzzy"],
            x_label="3-gram Jaccard Max", y_label="FuzzyWuzzy Ratio Max",
            color=COL_SCATTER_FUZZY,
            title=f"3-gram Jaccard Max Vs FuzzyWuzzy Ratio Max ({t})",
            out_path=output_dir / f"scatter_3gram_vs_fuzzy_{t}.png",
            xlim=xlim, ylim=ylim,
        )

        xlim, ylim = scatter_limits["3gram_vs_sentencebert"]
        plot_scatter_pair(
            x=m["3gram"], y=m["sbert"],
            x_label="3-gram Jaccard Max", y_label="Sentence-BERT Cosine Max",
            color=COL_SCATTER_SBERT,
            title=f"3-gram Jaccard Max Vs Sentence-BERT Cosine Max ({t})",
            out_path=output_dir / f"scatter_3gram_vs_sentencebert_{t}.png",
            xlim=xlim, ylim=ylim,
        )

        xlim, ylim = scatter_limits["3gram_vs_flesch"]
        plot_scatter_pair(
            x=m["3gram"], y=m["flesch"],
            x_label="3-gram Jaccard Max", y_label="Flesch Reading Ease",
            color=COL_SCATTER_FLESCH,
            title=f"3-gram Jaccard Max Vs Flesch Reading Ease ({t})",
            out_path=output_dir / f"scatter_3gram_vs_flesch_{t}.png",
            xlim=xlim, ylim=ylim,
        )

        # --- 9) x=flesch，y=其它三个（跨题型统一轴）
        xlim, ylim = scatter_limits["flesch_vs_fuzzy"]
        plot_scatter_pair(
            x=m["flesch"], y=m["fuzzy"],
            x_label="Flesch Reading Ease", y_label="FuzzyWuzzy Ratio Max",
            color=COL_SCATTER_FUZZY,
            title=f"Flesch Reading Ease Vs FuzzyWuzzy Ratio Max ({t})",
            out_path=output_dir / f"scatter_flesch_vs_fuzzy_{t}.png",
            xlim=xlim, ylim=ylim,
        )

        xlim, ylim = scatter_limits["flesch_vs_sentencebert"]
        plot_scatter_pair(
            x=m["flesch"], y=m["sbert"],
            x_label="Flesch Reading Ease", y_label="Sentence-BERT Cosine Max",
            color=COL_SCATTER_SBERT,
            title=f"Flesch Reading Ease Vs Sentence-BERT Cosine Max ({t})",
            out_path=output_dir / f"scatter_flesch_vs_sentencebert_{t}.png",
            xlim=xlim, ylim=ylim,
        )

        xlim, ylim = scatter_limits["flesch_vs_3gram"]
        plot_scatter_pair(
            x=m["flesch"], y=m["3gram"],
            x_label="Flesch Reading Ease", y_label="3-gram Jaccard Max",
            color=COL_SCATTER_3GRAM,
            title=f"Flesch Reading Ease Vs 3-gram Jaccard Max ({t})",
            out_path=output_dir / f"scatter_flesch_vs_3gram_{t}.png",
            xlim=xlim, ylim=ylim,
        )

        # --- 10) 四集合韦恩图（一致性重叠）+ 统一位置图例
        plot_venn_agreement(
            qs=qs,
            qtype=t,
            out_path=output_dir / f"venn_agreement_{t}.png",
        )


if __name__ == "__main__":
    main()
