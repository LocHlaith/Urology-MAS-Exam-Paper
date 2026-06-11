#!/usr/bin/env python3
from __future__ import annotations

import csv
from pathlib import Path

import matplotlib as mpl

mpl.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy import stats


PLOT_ROOT = Path(__file__).resolve().parents[1]
DERIVED = PLOT_ROOT / "derived_data"
OUT = PLOT_ROOT / "panels"

HUMAN_COLOR = "#4B55A4"
MAS_COLOR = "#C4776B"
TEXT = "#26313B"
SPINE = "#9B9993"
GRID = "#E7E2DB"


def ks_normality(values: np.ndarray) -> tuple[float, float]:
    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values)]
    if len(values) < 3 or np.std(values, ddof=1) == 0:
        return float("nan"), 0.0
    z = (values - values.mean()) / values.std(ddof=1)
    res = stats.kstest(z, "norm")
    return float(res.statistic), float(res.pvalue)


def compare_groups(mas: np.ndarray, human: np.ndarray) -> dict[str, float | str | bool]:
    mas = np.asarray(mas, dtype=float)
    human = np.asarray(human, dtype=float)
    mas_ks, mas_norm_p = ks_normality(mas)
    human_ks, human_norm_p = ks_normality(human)
    normal = bool(mas_norm_p >= 0.05 and human_norm_p >= 0.05)
    if normal:
        test = stats.ttest_ind(mas, human, equal_var=False, nan_policy="omit")
        method = "Welch t-test"
        statistic = float(test.statistic)
        p_value = float(test.pvalue)
    else:
        test = stats.mannwhitneyu(mas, human, alternative="two-sided", method="auto")
        method = "Mann-Whitney U"
        statistic = float(test.statistic)
        p_value = float(test.pvalue)
    return {
        "mas_ks_statistic": mas_ks,
        "mas_ks_p_value": mas_norm_p,
        "human_ks_statistic": human_ks,
        "human_ks_p_value": human_norm_p,
        "normal_by_ks": normal,
        "comparison_method": method,
        "test_statistic": statistic,
        "p_value": p_value,
    }


def p_label(p_value: float) -> str:
    if p_value < 0.001:
        return "***"
    if p_value < 0.01:
        return "**"
    if p_value < 0.05:
        return "*"
    return "n.s."


def build_panel_data() -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    with (DERIVED / "block_scores.csv").open(newline="", encoding="utf-8-sig") as f:
        block = list(csv.DictReader(f))
    panels = [
        ("Overall", block),
        ("Main campus", [row for row in block if row["training_setting"] == "main"]),
        ("Non-main campus", [row for row in block if row["training_setting"] == "non_main"]),
    ]
    stats_rows: list[dict[str, object]] = []
    raw_rows: list[dict[str, object]] = []
    for panel_order, (panel, data) in enumerate(panels, start=1):
        mas = np.array([float(row["correct_rate"]) for row in data if row["source_true"] == "MAS"], dtype=float)
        human = np.array([float(row["correct_rate"]) for row in data if row["source_true"] == "Human"], dtype=float)
        comp = compare_groups(mas, human)
        stats_rows.append(
            {
                "panel_order": panel_order,
                "panel": panel,
                "n_mas": len(mas),
                "n_human": len(human),
                "mas_mean": float(np.mean(mas)),
                "mas_sd": float(np.std(mas, ddof=1)),
                "human_mean": float(np.mean(human)),
                "human_sd": float(np.std(human, ddof=1)),
                "mean_difference_mas_minus_human": float(np.mean(mas) - np.mean(human)),
                **comp,
                "significance_label": p_label(float(comp["p_value"])),
            }
        )
        for row in data:
            raw_rows.append(
                {
                    "panel": panel,
                    "student_id": row["student_id"],
                    "training_setting": row["training_setting"],
                    "source_true": row["source_true"],
                    "correct_rate": float(row["correct_rate"]),
                    "score_percent": float(row["score_percent"]),
                }
            )
    return stats_rows, raw_rows


def write_tables(stats_rows: list[dict[str, object]], raw_rows: list[dict[str, object]]) -> None:
    DERIVED.mkdir(parents=True, exist_ok=True)
    with (DERIVED / "fig3B_student_correct_rate_stats.csv").open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(stats_rows[0].keys()))
        writer.writeheader()
        writer.writerows(stats_rows)
    with (DERIVED / "fig3B_student_correct_rate_raw.csv").open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(raw_rows[0].keys()))
        writer.writeheader()
        writer.writerows(raw_rows)


def draw_violin(ax, values: np.ndarray, pos: float, color: str, rng: np.random.Generator) -> None:
    parts = ax.violinplot([values], positions=[pos], widths=0.55, showmeans=False, showmedians=False, showextrema=False)
    body = parts["bodies"][0]
    body.set_facecolor(color)
    body.set_edgecolor(color)
    body.set_alpha(0.28)
    body.set_linewidth(1.8)

    q1, med, q3 = np.percentile(values, [25, 50, 75])
    ax.hlines([q1, med, q3], pos - 0.21, pos + 0.21, colors=color, linewidth=[1.2, 2.0, 1.2], linestyles=["dotted", "solid", "dotted"])
    jitter = rng.normal(pos, 0.035, len(values))
    ax.scatter(jitter, values, s=16, color=color, alpha=0.62, edgecolors="none", zorder=3)


def draw_figure(stats_rows: list[dict[str, object]], raw_rows: list[dict[str, object]]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    mpl.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.sans-serif": ["DejaVu Sans"],
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "axes.spines.top": False,
            "axes.spines.right": False,
        }
    )

    fig, axes = plt.subplots(1, 3, figsize=(10.8, 4.4), sharey=True)
    rng = np.random.default_rng(202606)
    panel_titles = ["Overall", "Main campus", "Non-main campus"]

    for ax, title, stat_row in zip(axes, panel_titles, stats_rows):
        sub = [row for row in raw_rows if row["panel"] == title]
        mas = np.array([float(row["correct_rate"]) for row in sub if row["source_true"] == "MAS"], dtype=float)
        human = np.array([float(row["correct_rate"]) for row in sub if row["source_true"] == "Human"], dtype=float)
        draw_violin(ax, mas, 1, MAS_COLOR, rng)
        draw_violin(ax, human, 2, HUMAN_COLOR, rng)

        ymax = max(float(np.max(mas)), float(np.max(human)))
        bracket_y = min(1.04, ymax + 0.075)
        ax.plot([1, 1, 2, 2], [bracket_y - 0.015, bracket_y, bracket_y, bracket_y - 0.015], color="#111111", lw=1.7)
        ax.text(1.5, bracket_y + 0.015, str(stat_row["significance_label"]), ha="center", va="bottom", fontsize=16, color="#111111", fontweight="bold")
        ax.text(
            1.5,
            0.245,
            f"{stat_row['comparison_method']}\nP={float(stat_row['p_value']):.3g}",
            ha="center",
            va="bottom",
            fontsize=8,
            color=TEXT,
        )

        ax.set_title(title, fontsize=13, color=TEXT, pad=10)
        ax.set_xticks([1, 2], ["MAS", "Human"], rotation=35, ha="right")
        ax.set_xlabel("MCQ source", fontsize=11, color=TEXT, fontweight="bold")
        ax.set_xlim(0.45, 2.55)
        ax.set_ylim(0.25, 1.08)
        ax.grid(axis="y", color=GRID, linewidth=0.7, alpha=0.8)
        ax.tick_params(axis="both", colors=TEXT, labelsize=11, width=1.4, length=5)
        for side in ("left", "bottom"):
            ax.spines[side].set_color(SPINE)
            ax.spines[side].set_linewidth(1.5)

    axes[0].set_ylabel("Correct response rate", fontsize=13, color=TEXT, fontweight="bold")
    handles = [
        mpl.patches.Patch(facecolor=MAS_COLOR, edgecolor=MAS_COLOR, alpha=0.35, label="MAS"),
        mpl.patches.Patch(facecolor=HUMAN_COLOR, edgecolor=HUMAN_COLOR, alpha=0.35, label="Human"),
    ]
    fig.legend(handles=handles, loc="upper right", bbox_to_anchor=(0.98, 0.96), frameon=False, fontsize=12)
    fig.suptitle("Student overall correct rate by source", fontsize=17, color=TEXT, y=0.99)
    fig.text(0.018, 0.965, "(B)", fontsize=24, fontweight="bold", color="#111111", ha="left", va="top")
    fig.subplots_adjust(left=0.08, right=0.90, top=0.82, bottom=0.22, wspace=0.34)
    fig.savefig(OUT / "Figure3B_defect_risk_by_cognitive_level.pdf", bbox_inches="tight", facecolor="white")
    plt.close(fig)


def main() -> None:
    stats_rows, raw_rows = build_panel_data()
    write_tables(stats_rows, raw_rows)
    draw_figure(stats_rows, raw_rows)
    for row in stats_rows:
        print(
            f"{row['panel']}: MAS {float(row['mas_mean']):.3f} +/- {float(row['mas_sd']):.3f}, "
            f"Human {float(row['human_mean']):.3f} +/- {float(row['human_sd']):.3f}; "
            f"{row['comparison_method']} P={float(row['p_value']):.4g} {row['significance_label']}; "
            f"KS MAS P={float(row['mas_ks_p_value']):.4g}, Human P={float(row['human_ks_p_value']):.4g}"
        )
    print(f"Wrote {OUT / 'Figure3B_defect_risk_by_cognitive_level.pdf'}")


if __name__ == "__main__":
    main()
