# chart_for_q_and_l.py
# -*- coding: utf-8 -*-
"""
chart_for_q_and_l.py
从旧题库（bank_*.json）与新题库（new_bank_*.json）生成论文例图（QGEval / LLM 总分）：

已有要求（关键点）：
1) 同一组图（例如“QGEval 频数分布直方图”、例如“QGEval vs LLM 散点图”）
   各题型横坐标区间完全相同、纵坐标区间完全相同。
   => 必须先对该组图涉及的所有题型完成统计，得到统一 xlim / ylim（以及 hist bins），再绘图。
2) 频数分布直方图步长为 1（bin 宽 = 1）。

新增功能：
3) 分别对两个题库（old/new），分别对 QGEval、LLM：
   计算总分的均值与标准差，并绘制论文风格图：
   - QGEval 一个图
   - LLM 一个图
   图形模仿 time.py：柱形=均值(#EBE6DE)，圆点=均值±标准差(#D6CDBE)

修改：
4) 需在命令行输出各统计量（不改变既有绘图逻辑）。
5) 模仿 chart.py：输出统计到 statistics_for_qgeval_and_llm.txt
   - 先分别对各个题库的各个题型统计（min/max/mean/std）
   - 再不区分题型、但区分题库统计（min/max/mean/std）
   - 不需要不区分题库的统计

使用示例：
python chart_for_q_and_l.py --input_dir "D:\\Desktop\\当务之急\\EAGLE\\泌尿外科\\泌尿外科专科出卷" --output_dir "./figs_q_and_l"
"""

from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple, Optional

import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt


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
# 配色
# -----------------------------
# 分布图/散点图（延续 chart.py 气质）
COL_HIST_QGEVAL = "#7F8A9B"
COL_HIST_LLM = "#B7CBD5"
COL_SCATTER_QGEVAL = "#5E6C82"
COL_SCATTER_LLM = "#899FB0"

# 新增：均值±标准差图（模仿 time.py）
COL_BAR_MEAN = "#EBE6DE"
COL_DOT_STD = "#D6CDBE"


# -----------------------------
# 工具函数
# -----------------------------
def title_case(s: str) -> str:
    """简易 Title Case，避免全大写/全小写，适合论文图题。"""
    small = {"a", "an", "the", "and", "or", "but", "for", "nor", "as", "at", "by", "in", "of", "on", "per", "to", "vs"}
    words = re.split(r"(\s+)", (s or "").strip())
    out: List[str] = []
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


def nice_int_limits(vmin: float, vmax: float, pad: int = 1) -> Tuple[int, int]:
    """给“整数分数轴”生成统一且合理的范围。"""
    if not (np.isfinite(vmin) and np.isfinite(vmax)):
        return 0, 1
    lo = int(math.floor(vmin)) - pad
    hi = int(math.ceil(vmax)) + pad
    if lo == hi:
        hi = lo + 1
    return lo, hi


def make_int_bins(lo: int, hi: int, step: int = 1) -> np.ndarray:
    """生成整数步长 bins（包含右端点）。"""
    if step <= 0:
        step = 1
    if hi <= lo:
        hi = lo + step
    return np.arange(lo, hi + step, step, dtype=float)


def read_json(path: Path) -> List[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def parse_total_score(s: Any) -> float:
    """
    从类似 "35: 5,5,5" / "68: ..." 中提取冒号前总分。
    """
    if s is None:
        return float("nan")
    if isinstance(s, (int, float)):
        return float(s)

    text = str(s).strip()
    if not text:
        return float("nan")

    if ":" in text:
        left = text.split(":", 1)[0].strip()
        try:
            return float(left)
        except Exception:
            pass

    m = re.search(r"-?\d+(?:\.\d+)?", text)
    if not m:
        return float("nan")
    return safe_float(m.group(0))


# -----------------------------
# 统计（模仿 chart.py）：min/max/mean/std
# -----------------------------
def metric_summary(arr: np.ndarray) -> Dict[str, float]:
    """
    返回：n/min/max/mean/std
    std 使用样本标准差（ddof=1），当 n<2 时 std=nan。
    """
    v = np.asarray(arr, dtype=float)
    v = v[np.isfinite(v)]
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


def format_float(x: float, digits: int = 6) -> str:
    if not np.isfinite(x):
        return "NA"
    if abs(x) < 0.5 * 10 ** (-digits):
        x = 0.0
    return f"{x:.{digits}f}"


def compute_statistics_by_bank_and_type(
    banks_by_type_metrics: Dict[str, Dict[str, Dict[str, np.ndarray]]]
) -> Tuple[
    Dict[str, Dict[str, Dict[str, Dict[str, float]]]],
    Dict[str, Dict[str, Dict[str, float]]],
]:
    """
    输入结构：
      banks_by_type_metrics[bank][type] -> {"qgeval": arr, "llm": arr}

    输出：
      per_bank_per_type_stats[bank][type][metric] -> summary
      per_bank_overall_stats[bank][metric] -> summary  (bank 内不分题型汇总)
    """
    metrics = ["qgeval", "llm"]

    per_bank_per_type_stats: Dict[str, Dict[str, Dict[str, Dict[str, float]]]] = {}
    per_bank_overall_stats: Dict[str, Dict[str, Dict[str, float]]] = {}

    for bank, by_type in banks_by_type_metrics.items():
        per_bank_per_type_stats[bank] = {}
        # per type
        for t, m in by_type.items():
            per_bank_per_type_stats[bank][t] = {}
            for k in metrics:
                per_bank_per_type_stats[bank][t][k] = metric_summary(m[k])

        # overall within bank (concat all types)
        per_bank_overall_stats[bank] = {}
        for k in metrics:
            all_arr = np.concatenate([m[k] for m in by_type.values()]) if by_type else np.array([], dtype=float)
            per_bank_overall_stats[bank][k] = metric_summary(all_arr)

    return per_bank_per_type_stats, per_bank_overall_stats


def write_statistics_txt(
    out_path: Path,
    per_bank_per_type_stats: Dict[str, Dict[str, Dict[str, Dict[str, float]]]],
    per_bank_overall_stats: Dict[str, Dict[str, Dict[str, float]]],
) -> None:
    metric_display = {
        "qgeval": "QGEval Total Score",
        "llm": "LLM Total Score",
    }
    order_metrics = ["qgeval", "llm"]

    lines: List[str] = []
    lines.append("QGEval / LLM Statistics (min/max/mean/std)")
    lines.append("Note: std is sample standard deviation (ddof=1). NA means no valid numeric values.")
    lines.append("")

    for bank in ["old", "new"]:
        if bank not in per_bank_per_type_stats:
            continue

        lines.append(f"=== Bank: {bank.upper()} ===")
        lines.append("")

        # by type
        lines.append("---- By Question Type ----")
        for t in per_bank_per_type_stats[bank].keys():
            lines.append(f"[Type: {t}]")
            header = f"{'metric':<22}  {'n':>6}  {'min':>14}  {'max':>14}  {'mean':>14}  {'std':>14}"
            lines.append(header)
            lines.append("-" * len(header))
            for k in order_metrics:
                s = per_bank_per_type_stats[bank][t][k]
                lines.append(
                    f"{metric_display[k]:<22}  "
                    f"{int(s['n']):>6d}  "
                    f"{format_float(s['min']):>14}  "
                    f"{format_float(s['max']):>14}  "
                    f"{format_float(s['mean']):>14}  "
                    f"{format_float(s['std']):>14}"
                )
            lines.append("")

        # overall in bank
        lines.append("---- Overall (All Types Combined, Within This Bank) ----")
        header = f"{'metric':<22}  {'n':>6}  {'min':>14}  {'max':>14}  {'mean':>14}  {'std':>14}"
        lines.append(header)
        lines.append("-" * len(header))
        for k in order_metrics:
            s = per_bank_overall_stats[bank][k]
            lines.append(
                f"{metric_display[k]:<22}  "
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
# 命令行统计输出（不改变既有绘图逻辑）
# -----------------------------
def describe_array_cli(arr: np.ndarray) -> Dict[str, float]:
    """
    命令行输出用：返回 N、有效N、mean、std、min、max。
    std 使用样本标准差（ddof=1），与 statistics.txt 一致。
    """
    arr = np.asarray(arr, dtype=float)
    finite = arr[np.isfinite(arr)]
    out: Dict[str, float] = {
        "n_total": float(arr.size),
        "n_finite": float(finite.size),
        "mean": float("nan"),
        "std": float("nan"),
        "min": float("nan"),
        "max": float("nan"),
    }
    if finite.size:
        out["mean"] = float(np.mean(finite))
        out["std"] = float(np.std(finite, ddof=1)) if finite.size >= 2 else float("nan")
        out["min"] = float(np.min(finite))
        out["max"] = float(np.max(finite))
    return out


def fmt_stats_line(name: str, st: Dict[str, float]) -> str:
    def f(x: float) -> str:
        return "nan" if not np.isfinite(x) else f"{x:.3f}"
    return (
        f"{name}: "
        f"N={int(st['n_total'])}, valid={int(st['n_finite'])}, "
        f"mean={f(st['mean'])}, std={f(st['std'])}, "
        f"min={f(st['min'])}, max={f(st['max'])}"
    )


# -----------------------------
# 数据加载：新库 / 旧库
# -----------------------------
def find_new_bank_files(input_dir: Path) -> List[Path]:
    files = sorted(input_dir.glob("new_bank_*.json"))
    if not files:
        raise FileNotFoundError(f"No files matched 'new_bank_*.json' in: {input_dir}")
    return files


def load_questions_from_files(files: List[Path]) -> Dict[str, List[Dict[str, Any]]]:
    """读取多个 JSON 文件，并按题型 type 分组。"""
    by_type: Dict[str, List[Dict[str, Any]]] = {}
    for fp in files:
        data = read_json(fp)
        if not isinstance(data, list):
            continue
        for q in data:
            if not isinstance(q, dict):
                continue
            t = str(q.get("type", "")).strip()
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


def extract_qgeval_llm_arrays(qs: List[Dict[str, Any]]) -> Dict[str, np.ndarray]:
    qgeval = np.array([parse_total_score(q.get("QGEval")) for q in qs], dtype=float)
    llm = np.array([parse_total_score(q.get("LLM")) for q in qs], dtype=float)
    return {"qgeval": qgeval, "llm": llm}


def concat_all_types(by_type_metrics: Dict[str, Dict[str, np.ndarray]], key: str) -> np.ndarray:
    if not by_type_metrics:
        return np.array([], dtype=float)
    return np.concatenate([m[key] for m in by_type_metrics.values()])


# -----------------------------
# 统计：统一 bins / 统一 y 上限 / 统一散点轴范围
# -----------------------------
def compute_global_hist_config(
    by_type_metrics: Dict[str, Dict[str, np.ndarray]],
    key: str,
    step: int = 1,
) -> Tuple[np.ndarray, Tuple[float, float], float]:
    """
    针对某指标（qgeval/llm）：
    - 跨题型统计统一 xlim（整数范围）与 bins（步长固定为 1）
    - 跨题型统计统一 ylim_max（最大频数 -> nice）
    返回：(bins, xlim, ylim_max)
    """
    all_vals = concat_all_types(by_type_metrics, key)
    vmin, vmax = finite_minmax(all_vals)
    lo, hi = nice_int_limits(vmin, vmax, pad=1)
    bins = make_int_bins(lo, hi, step=step)
    xlim = (float(bins[0]), float(bins[-1]))

    max_y = 0.0
    for m in by_type_metrics.values():
        arr = m[key]
        arr = arr[np.isfinite(arr)]
        if arr.size == 0:
            continue
        counts, _ = np.histogram(arr, bins=bins)
        if counts.size:
            max_y = max(max_y, float(np.max(counts)))
    ylim_max = nice_ylim_max(max_y)
    return bins, xlim, ylim_max


def compute_global_scatter_config(
    by_type_metrics: Dict[str, Dict[str, np.ndarray]],
    x_key: str,
    y_key: str,
) -> Tuple[Tuple[float, float], Tuple[float, float]]:
    """
    针对某组散点图：
    - 跨题型统计统一 xlim / ylim（整数范围，方便论文对齐）
    """
    all_x = concat_all_types(by_type_metrics, x_key)
    all_y = concat_all_types(by_type_metrics, y_key)

    xmin, xmax = finite_minmax(all_x)
    ymin, ymax = finite_minmax(all_y)

    xlo, xhi = nice_int_limits(xmin, xmax, pad=1)
    ylo, yhi = nice_int_limits(ymin, ymax, pad=1)
    return (float(xlo), float(xhi)), (float(ylo), float(yhi))


def mean_std_population(arr: np.ndarray) -> Tuple[float, float]:
    """
    用于“均值±标准差”图（模仿 time.py 的视觉含义）：
    这里采用总体标准差（ddof=0）。
    """
    v = arr[np.isfinite(arr)]
    if v.size == 0:
        return float("nan"), float("nan")
    mu = float(np.mean(v))
    sd = float(np.std(v, ddof=0))
    return mu, sd


# -----------------------------
# 绘图：直方图（步长=1）
# -----------------------------
def plot_histogram(
    values: np.ndarray,
    bins: np.ndarray,
    color: str,
    xlabel: str,
    title: str,
    out_path: Path,
    xlim: Tuple[float, float],
    ylim_max: float,
) -> None:
    fig, ax = plt.subplots(figsize=(8, 6))  # 4:3
    v = values[np.isfinite(values)]
    ax.hist(v, bins=bins, color=color, edgecolor="white", linewidth=0.6)

    ax.set_xlabel(xlabel)
    ax.set_ylabel("Frequency")
    ax.set_title(title_case(title))
    ax.set_xlim(xlim)
    ax.set_ylim(0, ylim_max)

    ax.grid(axis="y", alpha=0.25, linestyle="--", linewidth=0.7)
    fig.tight_layout()
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)


# -----------------------------
# 绘图：散点图（统一轴范围）
# -----------------------------
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
# 新增绘图：两个题库的均值±标准差（模仿 time.py）
# -----------------------------
def plot_bank_mean_std(
    bank_order: List[str],
    bank_to_values: Dict[str, np.ndarray],
    ylabel: str,
    title: str,
    out_path: Path,
) -> None:
    """
    横轴：Bank（Old/New）
    纵轴：Score
    柱形：均值（#EBE6DE）
    圆点：均值±标准差（#D6CDBE）
    """
    labels: List[str] = []
    means: List[float] = []
    stds: List[float] = []

    for bk in bank_order:
        arr = bank_to_values.get(bk, np.array([], dtype=float))
        mu, sd = mean_std_population(arr)
        labels.append("Old Bank" if bk == "old" else "New Bank" if bk == "new" else bk.capitalize())
        means.append(mu)
        stds.append(sd)

    x = np.arange(len(labels), dtype=float)

    # y 轴范围：用 mean±std 的全局 min/max 做 nice_int_limits（整数化更利于排版一致）
    y_candidates: List[float] = []
    for mu, sd in zip(means, stds):
        if np.isfinite(mu) and np.isfinite(sd):
            y_candidates.extend([mu - sd, mu + sd])
        elif np.isfinite(mu):
            y_candidates.append(mu)

    if y_candidates:
        ymin = float(np.min(y_candidates))
        ymax = float(np.max(y_candidates))
        ylo, yhi = nice_int_limits(ymin, ymax, pad=1)
        ylim = (float(ylo), float(yhi))
    else:
        ylim = (0.0, 1.0)

    fig, ax = plt.subplots(figsize=(8, 6))  # 4:3
    ax.bar(x, means, color=COL_BAR_MEAN, edgecolor="white", linewidth=0.8)

    for xi, mu, sd in zip(x, means, stds):
        if not (np.isfinite(mu) and np.isfinite(sd)):
            continue
        ax.scatter([xi, xi], [mu - sd, mu + sd], c=COL_DOT_STD, s=28, zorder=3)

    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_xlabel("Bank")
    ax.set_ylabel(ylabel)
    ax.set_title(title_case(title))
    ax.set_ylim(ylim)
    ax.grid(axis="y", alpha=0.25, linestyle="--", linewidth=0.7)

    fig.tight_layout()
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)


# -----------------------------
# 主流程
# -----------------------------
def default_old_bank_files() -> List[Path]:
    return [
        Path(r"D:\Desktop\当务之急\EAGLE\泌尿外科\泌尿外科专科出卷\bank_a1.json"),
        Path(r"D:\Desktop\当务之急\EAGLE\泌尿外科\泌尿外科专科出卷\bank_a2.json"),
        Path(r"D:\Desktop\当务之急\EAGLE\泌尿外科\泌尿外科专科出卷\bank_a3.json"),
        Path(r"D:\Desktop\当务之急\EAGLE\泌尿外科\泌尿外科专科出卷\bank_a4.json"),
        Path(r"D:\Desktop\当务之急\EAGLE\泌尿外科\泌尿外科专科出卷\bank_b.json"),
        Path(r"D:\Desktop\当务之急\EAGLE\泌尿外科\泌尿外科专科出卷\bank_x.json"),
    ]


def main() -> None:
    setup_style()

    parser = argparse.ArgumentParser(description="Generate paper-ready charts for QGEval/LLM (old bank vs new bank).")
    parser.add_argument("--input_dir", type=str, required=True, help="Directory containing new_bank_*.json files.")
    parser.add_argument("--output_dir", type=str, required=True, help="Output directory for figures.")
    parser.add_argument(
        "--old_bank_files",
        nargs="*",
        default=None,
        help="Optional override: explicit paths for old bank json files (space-separated).",
    )
    parser.add_argument(
        "--stats_out",
        type=str,
        default=None,
        help="Optional override: output path for statistics_for_qgeval_and_llm.txt (default: <input_dir>/statistics_for_qgeval_and_llm.txt).",
    )
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    stats_out_path = Path(args.stats_out) if args.stats_out else (input_dir / "statistics_for_qgeval_and_llm.txt")

    # 旧库
    old_files = [Path(p) for p in args.old_bank_files] if args.old_bank_files else default_old_bank_files()
    missing = [str(p) for p in old_files if not p.exists()]
    if missing:
        raise FileNotFoundError("Missing old bank files:\n" + "\n".join(missing))

    # 新库
    new_files = find_new_bank_files(input_dir)

    # 加载并分题型
    banks_questions: Dict[str, Dict[str, List[Dict[str, Any]]]] = {
        "old": load_questions_from_files(old_files),
        "new": load_questions_from_files(new_files),
    }

    # 抽取指标数组（bank -> type -> arrays）
    banks_by_type_metrics: Dict[str, Dict[str, Dict[str, np.ndarray]]] = {}
    for bank_kind, by_type in banks_questions.items():
        banks_by_type_metrics[bank_kind] = {}
        for t, qs in by_type.items():
            banks_by_type_metrics[bank_kind][t] = extract_qgeval_llm_arrays(qs)

    # 输出 statistics_for_qgeval_and_llm.txt（按 bank×type + 按 bank overall）
    per_bank_per_type_stats, per_bank_overall_stats = compute_statistics_by_bank_and_type(banks_by_type_metrics)
    write_statistics_txt(stats_out_path, per_bank_per_type_stats, per_bank_overall_stats)

    # 为“均值±标准差图”准备两库的全量数组（bank 内合并所有 type）
    bank_all_scores: Dict[str, Dict[str, np.ndarray]] = {}
    for bank_kind, by_type_metrics in banks_by_type_metrics.items():
        bank_all_scores[bank_kind] = {
            "qgeval": np.concatenate([m["qgeval"] for m in by_type_metrics.values()]) if by_type_metrics else np.array([], dtype=float),
            "llm": np.concatenate([m["llm"] for m in by_type_metrics.values()]) if by_type_metrics else np.array([], dtype=float),
        }

    # -----------------------------
    # 命令行输出：按 bank overall（不分题型）+ 每个 bank 的每题型
    # -----------------------------
    print("\n========== Statistics Output ==========")
    print(f"Saved statistics to: {stats_out_path.resolve()}")

    print("\n========== Overall Within Each Bank (All Types Combined) ==========")
    for bk in ["old", "new"]:
        q_arr = bank_all_scores.get(bk, {}).get("qgeval", np.array([], dtype=float))
        l_arr = bank_all_scores.get(bk, {}).get("llm", np.array([], dtype=float))
        print(f"\n--- {bk.upper()} BANK ---")
        print(fmt_stats_line("QGEval Total Score", describe_array_cli(q_arr)))
        print(fmt_stats_line("LLM   Total Score", describe_array_cli(l_arr)))

    print("\n========== Per-Type Within Each Bank ==========")
    for bk in ["old", "new"]:
        if bk not in banks_by_type_metrics:
            continue
        print(f"\n--- {bk.upper()} BANK ---")
        for t, m in banks_by_type_metrics[bk].items():
            print(f"[{t}]")
            print(fmt_stats_line("  QGEval", describe_array_cli(m["qgeval"])))
            print(fmt_stats_line("  LLM  ", describe_array_cli(m["llm"])))

    # 新增：两个题库的均值±标准差（QGEval / LLM 各一张）
    plot_bank_mean_std(
        bank_order=["old", "new"],
        bank_to_values={bk: bank_all_scores.get(bk, {}).get("qgeval", np.array([], dtype=float)) for bk in ["old", "new"]},
        ylabel="QGEval Total Score",
        title="Qgeval Total Score Mean and Standard Deviation by Bank",
        out_path=output_dir / "bank_mean_std_qgeval.png",
    )
    plot_bank_mean_std(
        bank_order=["old", "new"],
        bank_to_values={bk: bank_all_scores.get(bk, {}).get("llm", np.array([], dtype=float)) for bk in ["old", "new"]},
        ylabel="LLM Total Score",
        title="Llm Total Score Mean and Standard Deviation by Bank",
        out_path=output_dir / "bank_mean_std_llm.png",
    )

    # 分新/旧分别处理：保证“同一组图跨题型完全一致坐标”
    for bank_kind, by_type_metrics in banks_by_type_metrics.items():
        # 先统计：直方图统一配置（步长=1）
        bins_q, xlim_q, ymax_q = compute_global_hist_config(by_type_metrics, key="qgeval", step=1)
        bins_l, xlim_l, ymax_l = compute_global_hist_config(by_type_metrics, key="llm", step=1)

        # 先统计：散点图统一配置
        xlim_q_vs_l, ylim_q_vs_l = compute_global_scatter_config(by_type_metrics, x_key="qgeval", y_key="llm")
        xlim_l_vs_q, ylim_l_vs_q = compute_global_scatter_config(by_type_metrics, x_key="llm", y_key="qgeval")

        # 命令行输出：该 bank 的“统一坐标/分箱”配置
        print(f"\n========== {bank_kind.upper()} BANK: Global Plot Config ==========")

        def _bins_brief(bins: np.ndarray) -> str:
            if bins.size == 0:
                return "bins=[]"
            bw = bins[1] - bins[0] if bins.size >= 2 else float("nan")
            return f"bins=[{bins[0]:.0f}..{bins[-1]:.0f}], count={bins.size}, bin_width={bw:.0f}"

        print("\n-- Histogram Config --")
        print(f"QGEval: xlim={xlim_q}, ylim=(0, {ymax_q:.0f}), {_bins_brief(bins_q)}")
        print(f"LLM  : xlim={xlim_l}, ylim=(0, {ymax_l:.0f}), {_bins_brief(bins_l)}")

        print("\n-- Scatter Config --")
        print(f"QGEval vs LLM  : xlim={xlim_q_vs_l}, ylim={ylim_q_vs_l}")
        print(f"LLM   vs QGEval: xlim={xlim_l_vs_q}, ylim={ylim_l_vs_q}")

        # 再绘图：逐题型输出
        for t, m in by_type_metrics.items():
            # QGEval hist
            plot_histogram(
                values=m["qgeval"],
                bins=bins_q,
                color=COL_HIST_QGEVAL,
                xlabel="QGEval Total Score",
                title=f"Qgeval Total Score Distribution ({bank_kind} Bank, {t})",
                out_path=output_dir / f"hist_qgeval_total_{bank_kind}_{t}.png",
                xlim=xlim_q,
                ylim_max=ymax_q,
            )

            # LLM hist
            plot_histogram(
                values=m["llm"],
                bins=bins_l,
                color=COL_HIST_LLM,
                xlabel="LLM Total Score",
                title=f"Llm Total Score Distribution ({bank_kind} Bank, {t})",
                out_path=output_dir / f"hist_llm_total_{bank_kind}_{t}.png",
                xlim=xlim_l,
                ylim_max=ymax_l,
            )

            # Scatter: QGEval vs LLM
            plot_scatter_pair(
                x=m["qgeval"],
                y=m["llm"],
                x_label="QGEval Total Score",
                y_label="LLM Total Score",
                color=COL_SCATTER_LLM,
                title=f"Qgeval Total Score Vs Llm Total Score ({bank_kind} Bank, {t})",
                out_path=output_dir / f"scatter_qgeval_vs_llm_{bank_kind}_{t}.png",
                xlim=xlim_q_vs_l,
                ylim=ylim_q_vs_l,
            )

            # Scatter: LLM vs QGEval
            plot_scatter_pair(
                x=m["llm"],
                y=m["qgeval"],
                x_label="LLM Total Score",
                y_label="QGEval Total Score",
                color=COL_SCATTER_QGEVAL,
                title=f"Llm Total Score Vs Qgeval Total Score ({bank_kind} Bank, {t})",
                out_path=output_dir / f"scatter_llm_vs_qgeval_{bank_kind}_{t}.png",
                xlim=xlim_l_vs_q,
                ylim=ylim_l_vs_q,
            )

    print(f"\nDone. Figures saved to: {output_dir.resolve()}\n")


if __name__ == "__main__":
    main()
