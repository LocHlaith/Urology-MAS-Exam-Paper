"""Shared plotting helpers for manuscript panels.

脚本用途：集中保存 Figure panel 绘图风格、数据读取和 bootstrap 工具。
流程阶段：论文绘图。
主要输入：plot/agent_readable/derived_data 下的 CSV。
主要输出：被 make_manuscript_panels.py 调用的 Matplotlib 对象。
重要边界：这里只提供通用绘图函数，不改变任何分析数据。
"""

from __future__ import annotations

import csv
import hashlib
import math
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "plot" / "agent_readable" / "derived_data"
FIGURE_DIR = PROJECT_ROOT / "plot" / "agent_readable" / "figures"

mpl.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.sans-serif": ["DejaVu Sans"],
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
    }
)

UROMAS_COLORS = {
    "grid": "#E3DFD8",
    "spine": "#9E9A93",
    "text": "#3E3E3E",
    "text_dark": "#2A251F",
    "tick": "#4F4F4F",
    "border": "#C8C2B8",
    "soft_separator": "#D8D2C9",
    "neutral": "#F6F3EE",
    "neutral_dark": "#7B756E",
    "amber": "#B7791F",
    "amber_light": "#F8E8C7",
    "green_light": "#DDEBDF",
}

PALETTE = {
    "Human": "#313E96",
    "MAS": "#B86758",
    "Knowledge": "#5B8CBE",
    "Application": "#6A994E",
    "Reasoning": "#B55D73",
}

PALETTE_FILL = {
    "Human": "#D9DCF1",
    "MAS": "#F2DFDB",
    "Knowledge": "#DCEAF1",
    "Application": "#E0EEDB",
    "Reasoning": "#F1DDE4",
}

COGNITIVE_ORDER = ["knowledge", "application", "reasoning"]


def read_csv_dicts(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def to_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    text = str(value).replace("\ufeff", "").strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def numeric(rows: Iterable[Dict[str, Any]], key: str) -> List[float]:
    values = []
    for row in rows:
        value = to_float(row.get(key))
        if value is not None and math.isfinite(value):
            values.append(value)
    return values


def mean(values: Sequence[float]) -> Optional[float]:
    return statistics.fmean(values) if values else None


def group_rows(rows: Iterable[Dict[str, Any]], key: str) -> Dict[str, List[Dict[str, Any]]]:
    output: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        output[str(row.get(key, ""))].append(row)
    return dict(output)


def _rng_for(values: Sequence[float], extra: str = "") -> np.random.Generator:
    payload = ",".join(f"{v:.8g}" for v in values) + extra
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return np.random.default_rng(int(digest[:8], 16))


def bootstrap_mean_ci(values: Sequence[float], level: float = 0.95, n_boot: int = 2000) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    clean = np.array([v for v in values if v is not None and math.isfinite(v)], dtype=float)
    if clean.size == 0:
        return None, None, None
    point = float(np.mean(clean))
    if clean.size == 1:
        return point, point, point
    rng = _rng_for(clean.tolist(), f"mean-{level}")
    samples = rng.choice(clean, size=(n_boot, clean.size), replace=True).mean(axis=1)
    alpha = (1.0 - level) / 2.0
    return point, float(np.quantile(samples, alpha)), float(np.quantile(samples, 1.0 - alpha))


def bootstrap_diff_ci(
    first: Sequence[float],
    second: Sequence[float],
    level: float = 0.95,
    n_boot: int = 2000,
) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    a = np.array([v for v in first if v is not None and math.isfinite(v)], dtype=float)
    b = np.array([v for v in second if v is not None and math.isfinite(v)], dtype=float)
    if a.size == 0 or b.size == 0:
        return None, None, None
    point = float(np.mean(a) - np.mean(b))
    if a.size == 1 and b.size == 1:
        return point, point, point
    rng = _rng_for([*a.tolist(), *b.tolist()], f"diff-{level}")
    a_samples = rng.choice(a, size=(n_boot, a.size), replace=True).mean(axis=1)
    b_samples = rng.choice(b, size=(n_boot, b.size), replace=True).mean(axis=1)
    samples = a_samples - b_samples
    alpha = (1.0 - level) / 2.0
    return point, float(np.quantile(samples, alpha)), float(np.quantile(samples, 1.0 - alpha))


def style_axes(ax: plt.Axes) -> None:
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(UROMAS_COLORS["spine"])
    ax.spines["bottom"].set_color(UROMAS_COLORS["spine"])
    ax.tick_params(colors=UROMAS_COLORS["tick"], length=3, width=0.7)
    ax.yaxis.grid(True, color=UROMAS_COLORS["grid"], linewidth=0.6, alpha=0.8)
    ax.set_axisbelow(True)


def panel_label(ax: plt.Axes, label: str, title: str = "") -> None:
    ax.text(-0.08, 1.06, label, transform=ax.transAxes, ha="left", va="bottom", fontsize=10, fontweight="bold", color=UROMAS_COLORS["text_dark"])
    if title:
        ax.text(0.04, 1.065, title, transform=ax.transAxes, ha="left", va="bottom", fontsize=8, fontweight="bold", color=UROMAS_COLORS["text_dark"])


def rounded_box(
    ax: plt.Axes,
    xy: Tuple[float, float],
    size: Tuple[float, float],
    title: str,
    body: str = "",
    facecolor: str = "#FFFFFF",
    edgecolor: str = "#BBBBBB",
    icon: str = "",
    radius: float = 0.12,
    shadow: bool = True,
    title_size: float = 7.0,
    body_size: float = 5.6,
) -> None:
    x, y = xy
    width, height = size
    if shadow:
        ax.add_patch(
            FancyBboxPatch(
                (x + 0.04, y - 0.04),
                width,
                height,
                boxstyle=f"round,pad=0.02,rounding_size={radius}",
                linewidth=0,
                facecolor="#000000",
                alpha=0.08,
                zorder=1,
            )
        )
    ax.add_patch(
        FancyBboxPatch(
            xy,
            width,
            height,
            boxstyle=f"round,pad=0.02,rounding_size={radius}",
            linewidth=0.9,
            edgecolor=edgecolor,
            facecolor=facecolor,
            zorder=2,
        )
    )
    text_x = x + 0.18
    if icon:
        ax.text(x + 0.28, y + height / 2, icon, ha="center", va="center", fontsize=5.5, fontweight="bold", color=edgecolor, zorder=3)
        text_x = x + 0.62
    ax.text(text_x, y + height * 0.62, title, ha="left", va="center", fontsize=title_size, fontweight="bold", color=UROMAS_COLORS["text_dark"], zorder=3)
    if body:
        ax.text(text_x, y + height * 0.31, body, ha="left", va="center", fontsize=body_size, color=UROMAS_COLORS["text"], linespacing=1.05, zorder=3)


def draw_box(
    ax: plt.Axes,
    xy: Tuple[float, float],
    size: Tuple[float, float],
    title: str,
    body: str = "",
    facecolor: str = "#FFFFFF",
    edgecolor: Optional[str] = None,
) -> None:
    rounded_box(ax, xy, size, title, body, facecolor, edgecolor or UROMAS_COLORS["border"], radius=0.12, shadow=False)


def arrow(
    ax: plt.Axes,
    start: Tuple[float, float],
    end: Tuple[float, float],
    color: str = "#4F4F4F",
    scale: float = 10,
) -> None:
    ax.add_patch(
        FancyArrowPatch(
            start,
            end,
            arrowstyle="-|>",
            mutation_scale=scale,
            linewidth=1.0,
            color=color,
            shrinkA=0,
            shrinkB=0,
            zorder=4,
        )
    )
