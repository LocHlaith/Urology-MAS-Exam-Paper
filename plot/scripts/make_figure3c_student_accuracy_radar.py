#!/usr/bin/env python3
from __future__ import annotations

import csv
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

MAS_COLOR = "#C4776B"
HUMAN_COLOR = "#4B55A4"
TEXT = "#26313B"
GRID = "#DCD7D0"


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


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


def enriched_responses() -> list[dict[str, object]]:
    item_master = read_csv_rows(DERIVED / "item_master.csv")
    level_by_item = {row["item_id"]: row["blueprint_cognitive_level"] for row in item_master}
    responses = read_csv_rows(DERIVED / "responses.csv")
    rows: list[dict[str, object]] = []
    valid_levels = {level for level, _ in LEVELS}
    for row in responses:
        level = level_by_item.get(row["item_id"])
        if level not in valid_levels:
            continue
        rows.append(
            {
                "student_id": row["student_id"],
                "training_setting": row["training_setting"],
                "source_true": row["source_true"],
                "cognitive_level": level,
                "correct": float(row["correct"]),
            }
        )
    return rows


def student_level_rates(rows: list[dict[str, object]], panel: str) -> list[dict[str, object]]:
    if panel == "Overall":
        subset = rows
    elif panel == "Main campus":
        subset = [row for row in rows if row["training_setting"] == "main"]
    else:
        subset = [row for row in rows if row["training_setting"] == "non_main"]

    grouped: dict[tuple[str, str, str, str], list[float]] = defaultdict(list)
    setting_by_student: dict[str, str] = {}
    for row in subset:
        key = (
            str(row["student_id"]),
            str(row["training_setting"]),
            str(row["source_true"]),
            str(row["cognitive_level"]),
        )
        grouped[key].append(float(row["correct"]))
        setting_by_student[str(row["student_id"])] = str(row["training_setting"])

    out: list[dict[str, object]] = []
    for (student_id, setting, source, level), values in grouped.items():
        out.append(
            {
                "panel": panel,
                "student_id": student_id,
                "training_setting": setting,
                "source_true": source,
                "cognitive_level": level,
                "n_items": len(values),
                "correct_rate": float(np.mean(values)),
            }
        )
    return out


def build_data() -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    responses = enriched_responses()
    panels = ["Overall", "Main campus", "Non-main campus"]
    rate_rows: list[dict[str, object]] = []
    stat_rows: list[dict[str, object]] = []

    for panel_order, panel in enumerate(panels, start=1):
        panel_rates = student_level_rates(responses, panel)
        rate_rows.extend(panel_rates)
        for level_order, (level, label) in enumerate(LEVELS, start=1):
            mas = np.array(
                [float(row["correct_rate"]) for row in panel_rates if row["source_true"] == "MAS" and row["cognitive_level"] == level],
                dtype=float,
            )
            human = np.array(
                [float(row["correct_rate"]) for row in panel_rates if row["source_true"] == "Human" and row["cognitive_level"] == level],
                dtype=float,
            )
            comp = compare_groups(mas, human)
            stat_rows.append(
                {
                    "panel_order": panel_order,
                    "panel": panel,
                    "level_order": level_order,
                    "cognitive_level": level,
                    "cognitive_level_label": label,
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
    return stat_rows, rate_rows


def write_tables(stat_rows: list[dict[str, object]], rate_rows: list[dict[str, object]]) -> None:
    DERIVED.mkdir(parents=True, exist_ok=True)
    with (DERIVED / "fig3C_student_accuracy_radar_stats.csv").open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(stat_rows[0].keys()))
        writer.writeheader()
        writer.writerows(stat_rows)
    with (DERIVED / "fig3C_student_accuracy_radar_student_rates.csv").open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rate_rows[0].keys()))
        writer.writeheader()
        writer.writerows(rate_rows)


def closed(values: list[float]) -> list[float]:
    return values + values[:1]


def draw_figure(stat_rows: list[dict[str, object]]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    mpl.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.sans-serif": ["DejaVu Sans"],
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
        }
    )

    panels = ["Overall", "Main campus", "Non-main campus"]
    vertex = np.array(
        [
            [0.0, 1.0],
            [1.0, 0.0],
            [0.0, -1.0],
            [-1.0, 0.0],
        ],
        dtype=float,
    )
    label_pos = {
        "Knowledge": (0.0, 1.13, "center", "bottom"),
        "Comprehension": (1.10, 0.0, "left", "center"),
        "Application": (0.0, -1.13, "center", "top"),
        "Analysis": (-1.10, 0.0, "right", "center"),
    }
    sig_pos = {
        "Knowledge": (0.0, 0.89),
        "Comprehension": (0.88, -0.08),
        "Application": (0.0, -0.89),
        "Analysis": (-0.88, -0.08),
    }

    fig, axes = plt.subplots(1, 3, figsize=(12.8, 4.6))
    for ax, panel in zip(axes, panels):
        rows = [row for row in stat_rows if row["panel"] == panel]
        rows = sorted(rows, key=lambda row: int(row["level_order"]))
        mas = [float(row["mas_mean"]) for row in rows]
        human = [float(row["human_mean"]) for row in rows]
        mas_xy = vertex * np.array(mas)[:, None]
        human_xy = vertex * np.array(human)[:, None]

        ax.set_aspect("equal")
        ax.set_xlim(-1.28, 1.28)
        ax.set_ylim(-1.28, 1.28)
        ax.axis("off")

        for radius in [0.25, 0.50, 0.75, 1.00]:
            xy = vertex * radius
            ax.plot(
                np.r_[xy[:, 0], xy[0, 0]],
                np.r_[xy[:, 1], xy[0, 1]],
                color=GRID,
                linewidth=0.8,
                zorder=0,
            )
        for x, y in vertex:
            ax.plot([0, x], [0, y], color=GRID, linewidth=0.8, zorder=0)
        outer = vertex * 1.0
        ax.plot(
            np.r_[outer[:, 0], outer[0, 0]],
            np.r_[outer[:, 1], outer[0, 1]],
            color="#A7A39D",
            linewidth=1.2,
            zorder=0,
        )

        ax.plot(
            np.r_[mas_xy[:, 0], mas_xy[0, 0]],
            np.r_[mas_xy[:, 1], mas_xy[0, 1]],
            color=MAS_COLOR,
            linewidth=2.4,
            marker="o",
            markersize=5.5,
            zorder=3,
            label="MAS",
        )
        ax.fill(np.r_[mas_xy[:, 0], mas_xy[0, 0]], np.r_[mas_xy[:, 1], mas_xy[0, 1]], color=MAS_COLOR, alpha=0.15, zorder=1)
        ax.plot(
            np.r_[human_xy[:, 0], human_xy[0, 0]],
            np.r_[human_xy[:, 1], human_xy[0, 1]],
            color=HUMAN_COLOR,
            linewidth=2.4,
            marker="o",
            markersize=5.5,
            zorder=4,
            label="Human",
        )
        ax.fill(
            np.r_[human_xy[:, 0], human_xy[0, 0]],
            np.r_[human_xy[:, 1], human_xy[0, 1]],
            color=HUMAN_COLOR,
            alpha=0.15,
            zorder=2,
        )

        ax.text(0.08, 0.50, "0.5", fontsize=7.5, color="#5A5A5A", ha="left", va="bottom")
        ax.text(0.08, 1.00, "1.0", fontsize=7.5, color="#5A5A5A", ha="left", va="bottom")
        ax.set_title(panel, fontsize=13.5, color=TEXT, pad=16)

        for row in rows:
            level_label = str(row["cognitive_level_label"])
            x, y, ha, va = label_pos[level_label]
            ax.text(x, y, level_label, ha=ha, va=va, fontsize=9.5, color=TEXT, clip_on=False)
            label = str(row["significance_label"])
            color = "#C73C32" if label != "n.s." else TEXT
            sx, sy = sig_pos[level_label]
            ax.text(
                sx,
                sy,
                label,
                ha="center",
                va="center",
                fontsize=8.5,
                color=color,
                fontweight="bold" if label != "n.s." else "normal",
                zorder=5,
            )

    handles = [
        mpl.lines.Line2D([0], [0], color=MAS_COLOR, lw=2.5, marker="o", label="MAS"),
        mpl.lines.Line2D([0], [0], color=HUMAN_COLOR, lw=2.5, marker="o", label="Human"),
    ]
    fig.legend(handles=handles, loc="upper right", bbox_to_anchor=(0.985, 0.93), frameon=False, fontsize=11)
    fig.suptitle("Student correct rate by cognitive level", fontsize=17, color=TEXT, y=0.99)
    fig.text(0.018, 0.965, "(C)", fontsize=24, fontweight="bold", color="#111111", ha="left", va="top")
    fig.subplots_adjust(left=0.055, right=0.91, top=0.78, bottom=0.08, wspace=0.48)
    fig.savefig(OUT / "Figure3C_student_accuracy_by_cognitive_level.pdf", bbox_inches="tight", facecolor="white")
    plt.close(fig)


def main() -> None:
    stat_rows, rate_rows = build_data()
    write_tables(stat_rows, rate_rows)
    draw_figure(stat_rows)
    for row in stat_rows:
        print(
            f"{row['panel']} {row['cognitive_level_label']}: "
            f"MAS {float(row['mas_mean']):.3f}, Human {float(row['human_mean']):.3f}; "
            f"{row['comparison_method']} P={float(row['p_value']):.4g} {row['significance_label']}; "
            f"KS MAS P={float(row['mas_ks_p_value']):.4g}, Human P={float(row['human_ks_p_value']):.4g}"
        )
    print(f"Wrote {OUT / 'Figure3C_student_accuracy_by_cognitive_level.pdf'}")


if __name__ == "__main__":
    main()
