"""按 panel 粒度导出论文图。

脚本用途：为期刊排版生成每个 panel 一个可编辑 PDF。
流程阶段：论文绘图。
主要输入：plot/data/derived 下的数据处理结果。
主要输出：outputs/figures/panels 下的 Figure1A-Figure5E PDF。
重要边界：这里不再导出整张 Figure 合并 PDF；Figure 4 按需求保留 A-F 六个 panel。
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import matplotlib.pyplot as plt
import numpy as np

import make_manuscript_figures as mf


PANEL_DIR = mf.FIGURE_DIR / "panels"


def save_panel(fig: plt.Figure, filename: str) -> None:
    PANEL_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(PANEL_DIR / filename, bbox_inches="tight")
    plt.close(fig)


def new_panel(size: Tuple[float, float] = (2.7, 2.35)) -> Tuple[plt.Figure, plt.Axes]:
    fig, ax = plt.subplots(figsize=size)
    return fig, ax


def source_rows(rows: List[Dict[str, str]], source: str) -> List[Dict[str, str]]:
    return [row for row in rows if row.get("source_true") == source]


def cognitive_rows(rows: List[Dict[str, str]], level: str) -> List[Dict[str, str]]:
    return [row for row in rows if row.get("cognitive_level") == level]


def plot_error_point(
    ax: plt.Axes,
    x: float,
    y: float,
    lo: float,
    hi: float,
    color: str,
    text: Optional[str] = None,
) -> None:
    ax.errorbar(x, y, xerr=[[x - lo], [hi - x]], fmt="o", color=color, capsize=3, markersize=4)
    if text:
        ax.text(hi, y, text, va="center", ha="left", fontsize=7)


def diff_by_level(rows: List[Dict[str, str]], key: str) -> List[Tuple[str, Optional[float], Optional[float], Optional[float]]]:
    output = []
    for level in mf.COGNITIVE_ORDER:
        level_rows = cognitive_rows(rows, level)
        mas = mf.numeric(source_rows(level_rows, "MAS"), key)
        human = mf.numeric(source_rows(level_rows, "Human"), key)
        output.append((level, *mf.bootstrap_diff_ci(mas, human)))
    return output


# ===== Figure 1 =====

def panel_1a(inventory: Dict[str, Any]) -> None:
    fig, ax = new_panel((6.6, 3.55))
    mf.panel_label(ax, "A", "Inputs and UroEMAS generation")
    ax.set_xlim(0, 13.2)
    ax.set_ylim(0, 6.4)
    ax.axis("off")
    mf.rounded_box(ax, (0.35, 4.85), (3.3, 0.92), "Human bank", f"bank_*.json\nn={inventory.get('human_bank_records_total', '')}", mf.PALETTE_FILL["Human"], mf.PALETTE["Human"], icon="H", radius=0.16, title_size=6.7, body_size=5.4)
    mf.rounded_box(ax, (0.35, 3.52), (3.3, 0.92), "Source materials", "guidelines, textbook\nexam blueprint", mf.UROMAS_COLORS["amber_light"], mf.UROMAS_COLORS["amber"], icon="REF", radius=0.16, title_size=6.7, body_size=5.4)
    mf.rounded_box(ax, (0.35, 2.19), (3.3, 0.92), "Prompt constraints", "item type batches\ncognitive levels", mf.UROMAS_COLORS["green_light"], mf.PALETTE["Knowledge"], icon="P", radius=0.16, title_size=6.7, body_size=5.4)
    mf.rounded_box(ax, (4.55, 4.47), (2.85, 0.88), "Batch builder", "bank_to_new_bank.py", mf.PALETTE_FILL["MAS"], mf.PALETTE["MAS"], icon="01", radius=0.16, title_size=6.4, body_size=5.25)
    mf.rounded_box(ax, (8.25, 4.47), (2.65, 0.88), "Model call", "chat API\nJSON expected", mf.PALETTE_FILL["MAS"], mf.PALETTE["MAS"], icon="API", radius=0.16, title_size=6.4, body_size=5.1)
    mf.rounded_box(ax, (5.15, 3.05), (5.0, 0.90), "JSON extraction and append", f"new_bank_*.json; n={inventory.get('mas_bank_records_total', '')}", mf.PALETTE_FILL["MAS"], mf.PALETTE["MAS"], radius=0.16, title_size=6.4, body_size=5.1)
    mf.rounded_box(ax, (4.55, 1.72), (2.85, 0.88), "Answer pass", "analysis fields", mf.UROMAS_COLORS["amber_light"], mf.UROMAS_COLORS["amber"], icon="ANS", radius=0.16, title_size=6.4, body_size=5.1)
    mf.rounded_box(ax, (8.25, 1.72), (2.65, 0.88), "Text checks", "readability\noverlap", mf.PALETTE_FILL["Application"], mf.PALETTE["Application"], icon="TXT", radius=0.16, title_size=6.4, body_size=5.1)
    mf.rounded_box(ax, (5.15, 0.43), (5.0, 0.84), "Candidate item dataset", "traceable item IDs before safety gate", mf.UROMAS_COLORS["neutral"], mf.UROMAS_COLORS["border"], radius=0.16, title_size=6.4, body_size=5.1)
    mf.arrow(ax, (3.70, 5.30), (4.48, 4.92), color=mf.PALETTE["Human"])
    mf.arrow(ax, (3.70, 3.98), (4.48, 4.82), color=mf.UROMAS_COLORS["amber"])
    mf.arrow(ax, (3.70, 2.65), (4.48, 4.72), color=mf.PALETTE["Knowledge"])
    mf.arrow(ax, (7.45, 4.90), (8.18, 4.90), color=mf.PALETTE["MAS"])
    mf.arrow(ax, (9.35, 4.42), (8.05, 3.98), color=mf.PALETTE["MAS"])
    mf.arrow(ax, (7.00, 3.00), (5.85, 2.64), color=mf.UROMAS_COLORS["amber"])
    mf.arrow(ax, (8.30, 3.00), (9.10, 2.64), color=mf.PALETTE["Application"])
    mf.arrow(ax, (5.95, 1.66), (6.55, 1.31), color=mf.UROMAS_COLORS["amber"])
    mf.arrow(ax, (9.10, 1.66), (8.25, 1.31), color=mf.PALETTE["Application"])
    save_panel(fig, "Figure1A_workflow_inputs.pdf")


def panel_1b(safety_summary: List[Dict[str, str]]) -> None:
    fig, ax = new_panel((4.25, 3.05))
    mf.panel_label(ax, "B", "AI safety-screen statistics")
    panel_domains = [
        ("guideline_consistency", "Guideline\nconsistency"),
        ("single_best_answer", "Single best\nanswer"),
        ("answer_key_validation", "Answer-key\nvalidation"),
        ("distractor_effectiveness", "Distractor\neffectiveness"),
        ("stem_ambiguity_control", "Stem ambiguity\ncontrolled"),
        ("no_critical_defect_flag", "No critical\ndefect flag"),
    ]
    y_positions = np.arange(len(panel_domains))[::-1]
    offsets = {"Human": 0.13, "MAS": -0.13}
    markers = {"Human": "o", "MAS": "s"}
    for source in ["Human", "MAS"]:
        source_rows = [row for row in safety_summary if row.get("source_true") == source]
        for idx, (domain, _) in enumerate(panel_domains):
            if domain == "no_critical_defect_flag":
                values = [1.0 - (mf.to_float(row.get("critical_defect_rate")) or 0.0) for row in source_rows]
            else:
                values = mf.numeric(source_rows, f"{domain}_pass_rate")
            point, lo, hi = mf.bootstrap_mean_ci(values)
            if point is None:
                continue
            x = point * 100
            y = y_positions[idx] + offsets[source]
            ax.errorbar(
                x,
                y,
                xerr=[[(point - lo) * 100], [(hi - point) * 100]],
                fmt=markers[source],
                color=mf.PALETTE[source],
                markerfacecolor=mf.PALETTE_FILL[source],
                markeredgecolor=mf.PALETTE[source],
                capsize=2.5,
                markersize=4.2,
                linewidth=0.9,
                label=("UroEMAS" if source == "MAS" else source) if idx == 0 else None,
            )
    ax.set_yticks(y_positions, [label for _, label in panel_domains])
    ax.set_xlabel("Item-level pass / no-flag fraction (%)")
    ax.set_xlim(0, 104)
    ax.set_ylim(-0.65, len(panel_domains) - 0.35)
    ax.legend(frameon=False, loc="lower right")
    mf.style_axes(ax)
    ax.xaxis.grid(True, color=mf.UROMAS_COLORS["grid"], linewidth=0.6)
    ax.yaxis.grid(False)
    save_panel(fig, "Figure1B_safety_gate.pdf")


def panel_1c(assignments: List[Dict[str, str]]) -> None:
    counts = Counter(row["form"] for row in assignments)
    fig, ax = new_panel((4.8, 2.4))
    mf.panel_label(ax, "C", "Two-sequence order")
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 5)
    ax.axis("off")
    mf.rounded_box(ax, (0.45, 3.25), (1.75, 0.72), f"Form A\nn={counts.get('A', 0)}", "", mf.PALETTE_FILL["Human"], mf.PALETTE["Human"], icon="A", radius=0.16, title_size=6.8)
    mf.rounded_box(ax, (3.0, 3.25), (2.2, 0.72), "Human block", "first", mf.PALETTE_FILL["Human"], mf.PALETTE["Human"], icon="H", radius=0.16, title_size=6.6, body_size=5.1)
    mf.rounded_box(ax, (6.1, 3.25), (2.2, 0.72), "UroEMAS block", "second", mf.PALETTE_FILL["MAS"], mf.PALETTE["MAS"], icon="M", radius=0.16, title_size=6.6, body_size=5.1)
    mf.arrow(ax, (2.25, 3.61), (2.93, 3.61), color=mf.PALETTE["Human"])
    mf.arrow(ax, (5.25, 3.61), (6.02, 3.61), color=mf.UROMAS_COLORS["text_dark"])

    mf.rounded_box(ax, (0.45, 1.55), (1.75, 0.72), f"Form B\nn={counts.get('B', 0)}", "", mf.PALETTE_FILL["MAS"], mf.PALETTE["MAS"], icon="B", radius=0.16, title_size=6.8)
    mf.rounded_box(ax, (3.0, 1.55), (2.2, 0.72), "UroEMAS block", "first", mf.PALETTE_FILL["MAS"], mf.PALETTE["MAS"], icon="M", radius=0.16, title_size=6.6, body_size=5.1)
    mf.rounded_box(ax, (6.1, 1.55), (2.2, 0.72), "Human block", "second", mf.PALETTE_FILL["Human"], mf.PALETTE["Human"], icon="H", radius=0.16, title_size=6.6, body_size=5.1)
    mf.arrow(ax, (2.25, 1.91), (2.93, 1.91), color=mf.PALETTE["MAS"])
    mf.arrow(ax, (5.25, 1.91), (6.02, 1.91), color=mf.UROMAS_COLORS["text_dark"])
    save_panel(fig, "Figure1C_two_sequence_order.pdf")


def panel_1d(assignments: List[Dict[str, str]]) -> None:
    counts = Counter(row["training_setting"] for row in assignments)
    fig, ax = new_panel((2.5, 2.3))
    mf.panel_label(ax, "D")
    labels = ["main", "non_main"]
    values = [counts.get(label, 0) for label in labels]
    ax.bar(labels, values, color=["#D9DCF1", "#F2DFDB"], edgecolor=[mf.PALETTE["Human"], mf.PALETTE["MAS"]], linewidth=1)
    ax.set_ylabel("Examinees")
    ax.set_ylim(0, max(values) + 8)
    for idx, value in enumerate(values):
        ax.text(idx, value + 0.8, str(value), ha="center", va="bottom")
    mf.style_axes(ax)
    save_panel(fig, "Figure1D_training_setting.pdf")


def panel_1e() -> None:
    fig, ax = new_panel((2.7, 2.5))
    mf.panel_label(ax, "E")
    ax.set_xlim(0, 4)
    ax.set_ylim(0, 5)
    ax.axis("off")
    body = "Expert quality\nMajor/critical defects\nCognitive boundaries\nSource detectability\nStudent performance"
    mf.draw_box(ax, (0.25, 0.65), (3.5, 3.7), "Endpoint domains", body, mf.UROMAS_COLORS["neutral"], mf.UROMAS_COLORS["border"])
    save_panel(fig, "Figure1E_endpoint_domains.pdf")


# ===== Figure 2 =====

def panel_2a(item_level: List[Dict[str, str]]) -> None:
    fig, ax = new_panel((2.7, 2.3))
    mf.panel_label(ax, "A")
    metrics = [("Machine proxy\n(QC only)", "machine_proxy_quality_score_mean")]
    y_positions = np.arange(len(metrics))[::-1]
    for y, (label, key) in zip(y_positions, metrics):
        point, lo, hi = mf.bootstrap_diff_ci(mf.numeric(source_rows(item_level, "MAS"), key), mf.numeric(source_rows(item_level, "Human"), key))
        if point is not None:
            plot_error_point(ax, point, y, lo, hi, mf.PALETTE["MAS"], f" {point:.2f}")
    ax.axvline(0, color=mf.UROMAS_COLORS["spine"], linewidth=0.8)
    ax.axvline(-0.30, color=mf.PALETTE["Reasoning"], linestyle="--", linewidth=0.8)
    ax.set_yticks(y_positions, [m[0] for m in metrics])
    ax.set_xlabel("UroEMAS - Human (5-point scale)")
    ax.set_xlim(-0.8, 0.8)
    mf.style_axes(ax)
    save_panel(fig, "Figure2A_quality_difference.pdf")


def panel_2b(item_level: List[Dict[str, str]]) -> None:
    fig, ax = new_panel((3.0, 2.5))
    mf.panel_label(ax, "B")
    dims = [
        "machine_proxy_presentation_clarity_mean",
        "machine_proxy_blueprint_relevance_mean",
        "machine_proxy_answer_validity_mean",
        "machine_proxy_item_design_mean",
        "machine_proxy_cognitive_feedback_mean",
    ]
    labels = ["Clarity", "Blueprint", "Answer", "Design", "Cognition"]
    x = np.arange(len(dims))
    width = 0.36
    for offset, source in [(-width / 2, "Human"), (width / 2, "MAS")]:
        values = [mf.mean(mf.numeric(source_rows(item_level, source), dim)) or 0 for dim in dims]
        ax.bar(x + offset, values, width=width, color=mf.PALETTE_FILL[source], edgecolor=mf.PALETTE[source], linewidth=0.9, label="UroEMAS" if source == "MAS" else source)
    ax.set_xticks(x, labels, rotation=35, ha="right")
    ax.set_ylabel("Dimension score")
    ax.set_ylim(0, 5.4)
    ax.legend(frameon=False)
    mf.style_axes(ax)
    save_panel(fig, "Figure2B_dimension_scores.pdf")


def panel_2c(item_level: List[Dict[str, str]]) -> None:
    fig, ax = new_panel((2.6, 2.35))
    mf.panel_label(ax, "C")
    labels = ["Major\nscreen flag", "Critical\nscreen flag"]
    for idx, key in enumerate(["screen_major_defect_proxy", "screen_critical_defect_proxy"]):
        human = mf.numeric(source_rows(item_level, "Human"), key)
        mas = mf.numeric(source_rows(item_level, "MAS"), key)
        ax.bar(idx - 0.18, (mf.mean(human) or 0) * 100, width=0.34, color=mf.PALETTE_FILL["Human"], edgecolor=mf.PALETTE["Human"], label="Human" if idx == 0 else None)
        ax.bar(idx + 0.18, (mf.mean(mas) or 0) * 100, width=0.34, color=mf.PALETTE_FILL["MAS"], edgecolor=mf.PALETTE["MAS"], label="UroEMAS" if idx == 0 else None)
    ax.set_xticks(range(len(labels)), labels)
    ax.set_ylabel("Items (%)")
    ax.set_ylim(0, 100)
    ax.legend(frameon=False)
    mf.style_axes(ax)
    save_panel(fig, "Figure2C_defect_flags.pdf")


def panel_2d() -> None:
    fig, ax = new_panel((2.6, 2.6))
    mf.panel_label(ax, "D")
    ax.set_xlim(0, 4)
    ax.set_ylim(0, 5)
    ax.axis("off")
    mf.draw_box(ax, (0.2, 3.45), (3.6, 0.8), "Independent screens", "4 machine annotation runs", mf.UROMAS_COLORS["neutral"])
    mf.draw_box(ax, (0.2, 2.15), (3.6, 0.8), "Rule consolidation", "Repeated low rubric scores", mf.UROMAS_COLORS["neutral"])
    mf.draw_box(ax, (0.2, 0.85), (3.6, 0.8), "Item-level status", "Screen major / critical proxy", mf.UROMAS_COLORS["neutral"])
    mf.arrow(ax, (2, 3.42), (2, 2.98))
    mf.arrow(ax, (2, 2.12), (2, 1.68))
    save_panel(fig, "Figure2D_defect_workflow.pdf")


def panel_2e(machine_summary: List[Dict[str, str]]) -> None:
    fig, ax = new_panel((2.6, 2.35))
    mf.panel_label(ax, "E")
    rows_by_source = mf.group_rows(machine_summary, "source_true")
    for source, xpos in [("Human", 0), ("MAS", 1)]:
        sds = mf.numeric(rows_by_source.get(source, []), "machine_proxy_quality_score_sd")
        jitter = np.linspace(-0.08, 0.08, len(sds)) if sds else []
        ax.scatter(np.full(len(sds), xpos) + jitter, sds, s=12, alpha=0.75, color=mf.PALETTE[source])
        point, lo, hi = mf.bootstrap_mean_ci(sds)
        if point is not None:
            ax.errorbar(xpos, point, yerr=[[point - lo], [hi - point]], fmt="D", color="#2A251F", capsize=3, markersize=4)
    ax.set_xticks([0, 1], ["Human", "UroEMAS"])
    ax.set_ylabel("Run-to-run SD")
    mf.style_axes(ax)
    save_panel(fig, "Figure2E_run_consistency.pdf")


# ===== Figure 3 =====

def panel_3a(item_level: List[Dict[str, str]]) -> None:
    fig, ax = new_panel()
    mf.panel_label(ax, "A")
    diffs = diff_by_level(item_level, "machine_proxy_quality_score_mean")
    y = np.arange(len(diffs))[::-1]
    for ypos, (level, point, lo, hi) in zip(y, diffs):
        if point is not None:
            plot_error_point(ax, point, ypos, lo, hi, mf.PALETTE["MAS"])
    ax.axvline(0, color=mf.UROMAS_COLORS["spine"], linewidth=0.8)
    ax.set_yticks(y, [d[0] for d in diffs])
    ax.set_xlabel("Quality difference")
    ax.set_xlim(-1.0, 1.0)
    mf.style_axes(ax)
    save_panel(fig, "Figure3A_quality_by_cognitive_level.pdf")


def panel_3b(item_level: List[Dict[str, str]]) -> None:
    fig, ax = new_panel()
    mf.panel_label(ax, "B")
    diffs = diff_by_level(item_level, "screen_major_defect_proxy")
    y = np.arange(len(diffs))[::-1]
    for ypos, (level, point, lo, hi) in zip(y, diffs):
        if point is not None:
            plot_error_point(ax, point * 100, ypos, lo * 100, hi * 100, mf.PALETTE["Reasoning"])
    ax.axvline(0, color=mf.UROMAS_COLORS["spine"], linewidth=0.8)
    ax.set_yticks(y, [d[0] for d in diffs])
    ax.set_xlabel("Risk difference (pp)")
    ax.set_xlim(-60, 60)
    mf.style_axes(ax)
    save_panel(fig, "Figure3B_defect_risk_by_cognitive_level.pdf")


def panel_3c(item_level: List[Dict[str, str]]) -> None:
    fig, ax = new_panel()
    mf.panel_label(ax, "C")
    diffs = diff_by_level(item_level, "difficulty")
    y = np.arange(len(diffs))[::-1]
    for ypos, (level, point, lo, hi) in zip(y, diffs):
        if point is not None:
            plot_error_point(ax, point * 100, ypos, lo * 100, hi * 100, mf.PALETTE["Application"])
    ax.axvline(0, color=mf.UROMAS_COLORS["spine"], linewidth=0.8)
    ax.set_yticks(y, [d[0] for d in diffs])
    ax.set_xlabel("Correct-rate difference (pp)")
    ax.set_xlim(-45, 45)
    mf.style_axes(ax)
    save_panel(fig, "Figure3C_student_accuracy_by_cognitive_level.pdf")


def panel_3d(item_level: List[Dict[str, str]]) -> None:
    fig, ax = new_panel((2.7, 2.4))
    mf.panel_label(ax, "D")
    quality_diffs = {level: point for level, point, _, _ in diff_by_level(item_level, "machine_proxy_quality_score_mean") if point is not None}
    base = quality_diffs.get("knowledge", 0)
    values = [quality_diffs.get(level, 0) - base for level in mf.COGNITIVE_ORDER]
    ax.bar(mf.COGNITIVE_ORDER, values, color=[mf.PALETTE_FILL["Knowledge"], mf.PALETTE_FILL["Application"], mf.PALETTE_FILL["Reasoning"]], edgecolor=[mf.PALETTE["Knowledge"], mf.PALETTE["Application"], mf.PALETTE["Reasoning"]])
    ax.axhline(0, color=mf.UROMAS_COLORS["spine"], linewidth=0.8)
    ax.set_ylabel("Interaction contrast")
    ax.tick_params(axis="x", rotation=25)
    mf.style_axes(ax)
    save_panel(fig, "Figure3D_source_cognitive_interaction.pdf")


def panel_3e(item_level: List[Dict[str, str]]) -> None:
    fig, ax = new_panel((3.2, 2.35))
    mf.panel_label(ax, "E")
    x = np.arange(len(mf.COGNITIVE_ORDER))
    width = 0.36
    for offset, source in [(-width / 2, "Human"), (width / 2, "MAS")]:
        values = []
        for level in mf.COGNITIVE_ORDER:
            values.append(mf.mean(mf.numeric([r for r in item_level if r["source_true"] == source and r["cognitive_level"] == level], "discrimination")) or 0)
        ax.bar(x + offset, values, width=width, color=mf.PALETTE_FILL[source], edgecolor=mf.PALETTE[source], linewidth=0.9, label="UroEMAS" if source == "MAS" else source)
    ax.axhline(0, color=mf.UROMAS_COLORS["spine"], linewidth=0.8)
    ax.set_xticks(x, mf.COGNITIVE_ORDER)
    ax.set_ylabel("Item-rest discrimination")
    ax.legend(frameon=False)
    mf.style_axes(ax)
    save_panel(fig, "Figure3E_ctt_by_cognitive_level.pdf")


# ===== Figure 4 =====

def panel_4a(source_detection: List[Dict[str, str]]) -> None:
    values = mf.numeric(source_detection, "source_guess_success")
    accuracy, lo, hi = mf.bootstrap_mean_ci(values, level=0.90)
    fig, ax = new_panel()
    mf.panel_label(ax, "A")
    ax.axhspan(45, 55, color=mf.PALETTE_FILL["MAS"], alpha=0.7, zorder=0)
    if accuracy is not None:
        ax.errorbar(0, accuracy * 100, yerr=[[(accuracy - lo) * 100], [(hi - accuracy) * 100]], fmt="o", color=mf.PALETTE["MAS"], capsize=4)
        ax.text(0.12, accuracy * 100, f"{accuracy*100:.1f}%", va="center")
    ax.set_xlim(-0.6, 0.8)
    ax.set_xticks([0], ["Source\njudgment"])
    ax.set_ylabel("Accuracy (%)")
    ax.set_ylim(0, 100)
    mf.style_axes(ax)
    save_panel(fig, "Figure4A_source_detection_accuracy.pdf")


def panel_4b(confusion_rows: List[Dict[str, str]]) -> None:
    labels = ["Human", "MAS"]
    matrix = np.zeros((2, 2))
    for row in confusion_rows:
        if row.get("source_true") in labels and row.get("source_guess") in labels:
            i = labels.index(row["source_true"])
            j = labels.index(row["source_guess"])
            matrix[i, j] = mf.to_float(row.get("n")) or 0
    fig, ax = new_panel((2.6, 2.45))
    mf.panel_label(ax, "B")
    im = ax.imshow(matrix, cmap="Blues")
    ax.set_xticks([0, 1], ["Human", "UroEMAS"])
    ax.set_yticks([0, 1], ["Human", "UroEMAS"])
    ax.set_xlabel("Guessed source")
    ax.set_ylabel("True source")
    for i in range(2):
        for j in range(2):
            ax.text(j, i, f"{int(matrix[i, j])}", ha="center", va="center", color="#2A251F", fontsize=8)
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    save_panel(fig, "Figure4B_source_confusion_matrix.pdf")


def panel_4c(source_detection_metrics: List[Dict[str, str]]) -> None:
    fig, ax = new_panel()
    mf.panel_label(ax, "C")
    wanted = [("balanced_accuracy", "Balanced"), ("sensitivity_mas", "Sens."), ("specificity_human", "Spec.")]
    values = []
    labels = []
    by_metric = {row.get("metric"): row for row in source_detection_metrics}
    for metric, label in wanted:
        value = mf.to_float(by_metric.get(metric, {}).get("estimate"))
        if value is not None:
            labels.append(label)
            values.append(value * 100)
    ax.bar(labels, values, color=mf.PALETTE_FILL["MAS"], edgecolor=mf.PALETTE["MAS"], linewidth=0.9)
    ax.axhspan(45, 55, color=mf.PALETTE_FILL["Application"], alpha=0.65, zorder=0)
    ax.set_ylabel("Source metric (%)")
    ax.set_ylim(0, 100)
    mf.style_axes(ax)
    save_panel(fig, "Figure4C_source_metrics.pdf")


def panel_4_placeholder(label: str, filename: str, body: str) -> None:
    fig, ax = new_panel((3.2, 2.2))
    mf.panel_label(ax, label, "Workflow efficiency placeholder")
    ax.set_xlim(0, 6)
    ax.set_ylim(0, 4)
    ax.axis("off")
    mf.rounded_box(ax, (0.35, 0.65), (5.25, 2.15), "Awaiting workflow-level data", body, mf.UROMAS_COLORS["neutral"], mf.UROMAS_COLORS["border"], icon="DATA", radius=0.16, title_size=6.6, body_size=5.4)
    ax.text(0.55, 0.32, "Reserved only; examinee time is not workflow labor time.", fontsize=5.4, color=mf.UROMAS_COLORS["neutral_dark"], ha="left")
    save_panel(fig, filename)


# ===== Figure 5 =====

def panel_5a() -> None:
    fig, ax = new_panel((2.6, 2.25))
    mf.panel_label(ax, "A")
    ax.set_xlim(0, 4)
    ax.set_ylim(0, 5)
    ax.axis("off")
    mf.draw_box(ax, (0.25, 3.25), (3.5, 1.0), "Form A", "Human -> UroEMAS", mf.PALETTE_FILL["Human"], mf.PALETTE["Human"])
    mf.draw_box(ax, (0.25, 1.25), (3.5, 1.0), "Form B", "UroEMAS -> Human", mf.PALETTE_FILL["MAS"], mf.PALETTE["MAS"])
    save_panel(fig, "Figure5A_order_schema.pdf")


def panel_5b(paired_scores: List[Dict[str, str]]) -> None:
    fig, ax = new_panel((2.8, 2.5))
    mf.panel_label(ax, "B")
    for row in paired_scores:
        color = mf.PALETTE["Human"] if row["form"] == "A" else mf.PALETTE["MAS"]
        y = [mf.to_float(row["human_score"]), mf.to_float(row["mas_score"])]
        if None in y:
            continue
        ax.plot([0, 1], y, color=color, alpha=0.35, linewidth=0.8)
        ax.scatter([0, 1], y, color=color, s=8, alpha=0.6)
    ax.set_xticks([0, 1], ["Human", "UroEMAS"])
    ax.set_ylabel("Block score")
    ax.set_ylim(0, 100)
    mf.style_axes(ax)
    save_panel(fig, "Figure5B_paired_block_scores.pdf")


def panel_5c(paired_scores: List[Dict[str, str]]) -> None:
    fig, ax = new_panel((2.7, 2.5))
    mf.panel_label(ax, "C")
    for xpos, form in enumerate(["A", "B"]):
        vals = mf.numeric([r for r in paired_scores if r["form"] == form], "mas_minus_human_score")
        jitter = np.linspace(-0.08, 0.08, len(vals)) if vals else []
        ax.scatter(np.full(len(vals), xpos) + jitter, vals, color=mf.PALETTE["Human"] if form == "A" else mf.PALETTE["MAS"], alpha=0.75, s=14)
        point, lo, hi = mf.bootstrap_mean_ci(vals)
        if point is not None:
            ax.errorbar(xpos, point, yerr=[[point - lo], [hi - point]], fmt="D", color="#2A251F", capsize=3, markersize=4)
    ax.axhline(0, color=mf.UROMAS_COLORS["spine"], linewidth=0.8)
    ax.set_xticks([0, 1], ["Form A", "Form B"])
    ax.set_ylabel("UroEMAS - Human score")
    mf.style_axes(ax)
    save_panel(fig, "Figure5C_individual_differences.pdf")


def panel_5d(paired_scores: List[Dict[str, str]]) -> None:
    fig, ax = new_panel()
    mf.panel_label(ax, "D")
    rows = [("Overall", paired_scores), ("Form A", [r for r in paired_scores if r["form"] == "A"]), ("Form B", [r for r in paired_scores if r["form"] == "B"])]
    y = np.arange(len(rows))[::-1]
    for ypos, (label, subrows) in zip(y, rows):
        vals = mf.numeric(subrows, "mas_minus_human_correct_rate")
        point, lo, hi = mf.bootstrap_mean_ci(vals)
        if point is not None:
            plot_error_point(ax, point * 100, ypos, lo * 100, hi * 100, mf.PALETTE["MAS"], f" {point*100:.1f}")
    ax.axvline(0, color=mf.UROMAS_COLORS["spine"], linewidth=0.8)
    ax.set_yticks(y, [r[0] for r in rows])
    ax.set_xlabel("Correct-rate difference (pp)")
    ax.set_xlim(-25, 25)
    mf.style_axes(ax)
    save_panel(fig, "Figure5D_adjusted_difference_proxy.pdf")


def panel_5e(paired_scores: List[Dict[str, str]]) -> None:
    fig, ax = new_panel((2.7, 2.5))
    mf.panel_label(ax, "E")
    for xpos, setting in enumerate(["main", "non_main"]):
        vals = mf.numeric([r for r in paired_scores if r["training_setting"] == setting], "mas_minus_human_score")
        jitter = np.linspace(-0.08, 0.08, len(vals)) if vals else []
        ax.scatter(np.full(len(vals), xpos) + jitter, vals, color="#4F4F4F", alpha=0.65, s=14)
        point, lo, hi = mf.bootstrap_mean_ci(vals)
        if point is not None:
            ax.errorbar(xpos, point, yerr=[[point - lo], [hi - point]], fmt="D", color=mf.PALETTE["MAS"], capsize=3, markersize=4)
    ax.axhline(0, color=mf.UROMAS_COLORS["spine"], linewidth=0.8)
    ax.set_xticks([0, 1], ["main", "non_main"])
    ax.set_ylabel("UroEMAS - Human score")
    mf.style_axes(ax)
    save_panel(fig, "Figure5E_training_setting_exploration.pdf")


def main() -> None:
    item_level = mf.read_csv_dicts(mf.DATA_DIR / "item_level_analysis.csv")
    machine_summary = mf.read_csv_dicts(mf.DATA_DIR / "machine_rating_summary.csv")
    safety_summary = mf.read_csv_dicts(mf.DATA_DIR / "machine_safety_screening_summary.csv")
    source_detection = mf.read_csv_dicts(mf.DATA_DIR / "source_detection.csv")
    source_detection_confusion = mf.read_csv_dicts(mf.DATA_DIR / "source_detection_confusion_matrix.csv")
    source_detection_metrics = mf.read_csv_dicts(mf.DATA_DIR / "source_detection_metrics.csv")
    paired_scores = mf.read_csv_dicts(mf.DATA_DIR / "paired_block_scores.csv")
    assignments = mf.read_csv_dicts(mf.DATA_DIR / "exam_form_assignment.csv")
    inventory = json.loads((mf.DATA_DIR / "data_inventory.json").read_text(encoding="utf-8"))

    panel_1a(inventory)
    panel_1b(safety_summary)
    panel_1c(assignments)
    panel_1d(assignments)
    panel_1e()

    panel_2a(item_level)
    panel_2b(item_level)
    panel_2c(item_level)
    panel_2d()
    panel_2e(machine_summary)

    panel_3a(item_level)
    panel_3b(item_level)
    panel_3c(item_level)
    panel_3d(item_level)
    panel_3e(item_level)

    panel_4a(source_detection)
    panel_4b(source_detection_confusion)
    panel_4c(source_detection_metrics)
    panel_4_placeholder("D", "Figure4D_workflow_total_time.pdf", "workflow_total_time_cost.csv\nnot present in current data")
    panel_4_placeholder("E", "Figure4E_quality_adjusted_time.pdf", "Time per final item\nrequires workflow totals")
    panel_4_placeholder("F", "Figure4F_efficiency_sensitivity.pdf", "Sensitivity analysis\nrequires time/cost assumptions")

    panel_5a()
    panel_5b(paired_scores)
    panel_5c(paired_scores)
    panel_5d(paired_scores)
    panel_5e(paired_scores)

    print(f"[OK] Wrote panel PDFs to {PANEL_DIR}")


if __name__ == "__main__":
    main()
