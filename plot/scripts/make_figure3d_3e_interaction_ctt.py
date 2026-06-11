#!/usr/bin/env python3
from __future__ import annotations

import csv
import math
from collections import defaultdict
from pathlib import Path

import matplotlib as mpl

mpl.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy import stats


PLOT_ROOT = Path(__file__).resolve().parents[1]
DERIVED = PLOT_ROOT / "derived_data"
OUT = PLOT_ROOT / "panels"

LEVELS = [
    ("recall", "Knowledge"),
    ("comprehension", "Comprehension"),
    ("application", "Application"),
    ("analysis", "Analysis"),
]
LEVEL_TO_LABEL = dict(LEVELS)
LEVEL_ORDER = {level: i for i, (level, _) in enumerate(LEVELS)}

MAS_COLOR = "#C4776B"
HUMAN_COLOR = "#4B55A4"
TEXT = "#26313B"
SPINE = "#9B9993"
GRID = "#DCD7D0"


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def setup_style() -> None:
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
            "axes.edgecolor": SPINE,
            "axes.labelcolor": TEXT,
            "xtick.color": TEXT,
            "ytick.color": TEXT,
        }
    )


def item_master_lookup() -> dict[str, dict[str, str]]:
    return {row["item_id"]: row for row in read_csv_rows(DERIVED / "item_master.csv")}


def quality_item_rows() -> list[dict[str, object]]:
    item_by_id = item_master_lookup()
    rows: list[dict[str, object]] = []
    for row in read_csv_rows(DERIVED / "expert_rating_item_summary_updated.csv"):
        item = item_by_id.get(row["item_id"])
        if not item:
            continue
        level = item.get("blueprint_cognitive_level", "")
        if level not in LEVEL_ORDER:
            continue
        rows.append(
            {
                "item_id": row["item_id"],
                "source_true": row["source_true"],
                "cognitive_level": level,
                "cognitive_level_label": LEVEL_TO_LABEL[level],
                "quality_score_5": float(row["expert_quality_score_5_mean"]),
            }
        )
    return rows


def design_row(source: str, level: str) -> list[float]:
    is_mas = 1.0 if source == "MAS" else 0.0
    return [
        1.0,
        is_mas,
        1.0 if level == "comprehension" else 0.0,
        1.0 if level == "application" else 0.0,
        1.0 if level == "analysis" else 0.0,
        is_mas if level == "comprehension" else 0.0,
        is_mas if level == "application" else 0.0,
        is_mas if level == "analysis" else 0.0,
    ]


def fit_interaction(rows: list[dict[str, object]]) -> tuple[np.ndarray, np.ndarray, int]:
    x = np.array([design_row(str(row["source_true"]), str(row["cognitive_level"])) for row in rows], dtype=float)
    y = np.array([float(row["quality_score_5"]) for row in rows], dtype=float)
    xtx_inv = np.linalg.pinv(x.T @ x)
    beta = xtx_inv @ x.T @ y
    resid = y - x @ beta
    df = max(len(y) - x.shape[1], 1)
    sigma2 = float(resid.T @ resid / df)
    cov = sigma2 * xtx_inv
    return beta, cov, df


def mean_ci(beta: np.ndarray, cov: np.ndarray, df: int, source: str, level: str) -> tuple[float, float, float, float]:
    x = np.array(design_row(source, level), dtype=float)
    mean = float(x @ beta)
    se = float(math.sqrt(max(x @ cov @ x.T, 0.0)))
    crit = float(stats.t.ppf(0.975, df))
    return mean, se, mean - crit * se, mean + crit * se


def make_figure3d() -> None:
    rows = quality_item_rows()
    beta, cov, df = fit_interaction(rows)
    ci_rows: list[dict[str, object]] = []
    grouped: dict[tuple[str, str], list[float]] = defaultdict(list)
    for row in rows:
        grouped[(str(row["source_true"]), str(row["cognitive_level"]))].append(float(row["quality_score_5"]))

    for level, label in LEVELS:
        for source in ["MAS", "Human"]:
            vals = np.array(grouped[(source, level)], dtype=float)
            estimate, se, ci_low, ci_high = mean_ci(beta, cov, df, source, level)
            ci_rows.append(
                {
                    "source_true": source,
                    "cognitive_level": level,
                    "cognitive_level_label": label,
                    "n_items": int(len(vals)),
                    "raw_mean": float(np.mean(vals)) if len(vals) else float("nan"),
                    "raw_sd": float(np.std(vals, ddof=1)) if len(vals) > 1 else float("nan"),
                    "model_estimate": estimate,
                    "model_se": se,
                    "ci_low": ci_low,
                    "ci_high": ci_high,
                }
            )

    contrast_vector = np.zeros(8, dtype=float)
    contrast_vector[7] = 1.0
    interaction = float(contrast_vector @ beta)
    interaction_se = float(math.sqrt(max(contrast_vector @ cov @ contrast_vector.T, 0.0)))
    crit = float(stats.t.ppf(0.975, df))
    p_value = float(2 * stats.t.sf(abs(interaction / interaction_se), df)) if interaction_se > 0 else float("nan")
    interaction_rows = [
        {
            "contrast": "(MAS-Human at Analysis) - (MAS-Human at Knowledge)",
            "estimate": interaction,
            "se": interaction_se,
            "ci_low": interaction - crit * interaction_se,
            "ci_high": interaction + crit * interaction_se,
            "df": df,
            "p_value": p_value,
        }
    ]

    write_csv(DERIVED / "fig3D_source_cognitive_interaction_model_estimates.csv", ci_rows)
    write_csv(DERIVED / "fig3D_source_cognitive_interaction_contrast.csv", interaction_rows)

    x = np.arange(len(LEVELS), dtype=float)
    by_source = {
        source: [row for row in ci_rows if row["source_true"] == source]
        for source in ["MAS", "Human"]
    }

    fig, ax = plt.subplots(figsize=(7.25, 4.35))
    for source, color, offset in [("MAS", MAS_COLOR, -0.015), ("Human", HUMAN_COLOR, 0.015)]:
        source_rows = sorted(by_source[source], key=lambda row: LEVEL_ORDER[str(row["cognitive_level"])])
        means = np.array([float(row["model_estimate"]) for row in source_rows])
        lows = np.array([float(row["ci_low"]) for row in source_rows])
        highs = np.array([float(row["ci_high"]) for row in source_rows])
        ax.errorbar(
            x + offset,
            means,
            yerr=[means - lows, highs - means],
            color=color,
            ecolor=color,
            marker="o",
            markersize=8.5,
            markeredgewidth=0,
            linewidth=2.25,
            elinewidth=1.8,
            capsize=5,
            capthick=1.7,
            label=source,
            zorder=3 if source == "Human" else 2,
        )

    ax.set_title("Source x cognitive-level interaction", fontsize=17, color=TEXT, pad=12)
    ax.set_ylabel("Expert composite quality (1-5)", fontsize=12, color=TEXT)
    ax.set_xticks(x, [label for _, label in LEVELS], rotation=13, ha="right", fontsize=12)
    ax.tick_params(axis="y", labelsize=11, length=5, width=1.2)
    ax.tick_params(axis="x", length=5, width=1.2)
    for spine in ["left", "bottom"]:
        ax.spines[spine].set_linewidth(1.2)
        ax.spines[spine].set_color(SPINE)

    y_min = min(float(row["ci_low"]) for row in ci_rows) - 0.06
    y_max = max(float(row["ci_high"]) for row in ci_rows) + 0.04
    ax.set_ylim(max(3.85, math.floor(y_min * 10) / 10), min(5.02, math.ceil(y_max * 10) / 10))
    ax.margins(x=0.05)

    ax.legend(loc="lower left", frameon=False, fontsize=12, handlelength=1.6)
    annotation = f"interaction\n(Analysis-Knowledge)\n= {interaction:+.2f}"
    ax.text(
        0.965,
        0.93,
        annotation,
        transform=ax.transAxes,
        ha="right",
        va="top",
        fontsize=10.5,
        color=TEXT,
        bbox=dict(boxstyle="round,pad=0.25,rounding_size=0.12", facecolor="white", edgecolor="#B9B7B2", linewidth=0.9),
    )
    fig.text(0.018, 0.965, "(D)", fontsize=21, fontweight="bold", color="#111111", ha="left", va="top")
    fig.subplots_adjust(left=0.11, right=0.98, top=0.84, bottom=0.20)
    fig.savefig(OUT / "Figure3D_source_cognitive_interaction.pdf", bbox_inches="tight", facecolor="white")
    plt.close(fig)


def item_type_group(item_type: str) -> str:
    if item_type in {"A1", "B"}:
        return "A1/B"
    if item_type in {"A2", "A3/A4"}:
        return "A2/A3/A4"
    return "X"


def make_figure3e() -> None:
    item_by_id = item_master_lookup()
    rows: list[dict[str, object]] = []
    for row in read_csv_rows(DERIVED / "ctt_item_analysis.csv"):
        item = item_by_id.get(row["item_id"])
        if not item:
            continue
        level = item.get("blueprint_cognitive_level", "")
        if level not in LEVEL_ORDER:
            continue
        rows.append(
            {
                "item_id": row["item_id"],
                "source_true": row["source_true"],
                "item_type": item.get("item_type", ""),
                "item_type_group": item_type_group(item.get("item_type", "")),
                "cognitive_level": level,
                "cognitive_level_label": LEVEL_TO_LABEL[level],
                "difficulty": float(row["difficulty"]),
                "discrimination": float(row["discrimination"]),
                "n_responses": int(float(row["n_responses"])),
            }
        )
    write_csv(DERIVED / "fig3E_ctt_scatter_item_data.csv", rows)

    summary_rows: list[dict[str, object]] = []
    for level, label in LEVELS:
        for source in ["MAS", "Human"]:
            sub = [row for row in rows if row["cognitive_level"] == level and row["source_true"] == source]
            if not sub:
                continue
            difficulty = np.array([float(row["difficulty"]) for row in sub], dtype=float)
            discrimination = np.array([float(row["discrimination"]) for row in sub], dtype=float)
            summary_rows.append(
                {
                    "source_true": source,
                    "cognitive_level": level,
                    "cognitive_level_label": label,
                    "n_items": len(sub),
                    "mean_difficulty": float(np.mean(difficulty)),
                    "sd_difficulty": float(np.std(difficulty, ddof=1)) if len(difficulty) > 1 else float("nan"),
                    "mean_discrimination": float(np.mean(discrimination)),
                    "sd_discrimination": float(np.std(discrimination, ddof=1)) if len(discrimination) > 1 else float("nan"),
                }
            )
    write_csv(DERIVED / "fig3E_ctt_by_cognitive_level_summary.csv", summary_rows)

    fig, ax = plt.subplots(figsize=(7.25, 4.35))
    ax.axhline(0.20, color=SPINE, linestyle=":", linewidth=1.4, zorder=0)
    ax.axvline(0.50, color=SPINE, linestyle=":", linewidth=1.4, zorder=0)

    source_colors = {"MAS": MAS_COLOR, "Human": HUMAN_COLOR}
    marker_map = {"A1/B": "o", "A2/A3/A4": "s", "X": "^"}
    for source in ["MAS", "Human"]:
        for group, marker in marker_map.items():
            sub = [row for row in rows if row["source_true"] == source and row["item_type_group"] == group]
            if not sub:
                continue
            ax.scatter(
                [float(row["difficulty"]) for row in sub],
                [float(row["discrimination"]) for row in sub],
                s=52,
                marker=marker,
                color=source_colors[source],
                alpha=0.86,
                edgecolors="white",
                linewidths=0.45,
                zorder=3,
            )

    ax.set_xlim(0.0, 1.02)
    ax.set_ylim(-0.36, 0.60)
    ax.set_xlabel("Item difficulty (prop. correct)", fontsize=12, color=TEXT)
    ax.set_ylabel("Discrimination (item-rest $r$)", fontsize=12, color=TEXT)
    ax.set_title("Exploratory CTT (objective items)", fontsize=17, color=TEXT, pad=12)
    ax.tick_params(axis="both", labelsize=11, length=5, width=1.2)
    for spine in ["left", "bottom"]:
        ax.spines[spine].set_linewidth(1.2)
        ax.spines[spine].set_color(SPINE)

    color_handles = [
        mpl.lines.Line2D([0], [0], marker="o", linestyle="", markerfacecolor=MAS_COLOR, markeredgecolor=MAS_COLOR, markersize=7, label="MAS"),
        mpl.lines.Line2D([0], [0], marker="o", linestyle="", markerfacecolor=HUMAN_COLOR, markeredgecolor=HUMAN_COLOR, markersize=7, label="Human"),
    ]
    shape_handles = [
        mpl.lines.Line2D([0], [0], marker="o", linestyle="", color="#666666", markerfacecolor="#666666", markersize=7, label="A1/B"),
        mpl.lines.Line2D([0], [0], marker="s", linestyle="", color="#666666", markerfacecolor="#666666", markersize=7, label="A2/A3/A4"),
        mpl.lines.Line2D([0], [0], marker="^", linestyle="", color="#666666", markerfacecolor="#666666", markersize=7, label="X"),
    ]
    ax.legend(handles=color_handles + shape_handles, frameon=False, loc="lower left", fontsize=10.5, handletextpad=0.6)

    fig.text(0.018, 0.965, "(E)", fontsize=21, fontweight="bold", color="#111111", ha="left", va="top")
    fig.subplots_adjust(left=0.12, right=0.98, top=0.84, bottom=0.18)
    fig.savefig(OUT / "Figure3E_ctt_by_cognitive_level.pdf", bbox_inches="tight", facecolor="white")
    plt.close(fig)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    DERIVED.mkdir(parents=True, exist_ok=True)
    setup_style()
    make_figure3d()
    make_figure3e()
    print(f"Wrote {OUT / 'Figure3D_source_cognitive_interaction.pdf'}")
    print(f"Wrote {OUT / 'Figure3E_ctt_by_cognitive_level.pdf'}")


if __name__ == "__main__":
    main()
