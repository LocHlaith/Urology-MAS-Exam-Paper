#!/usr/bin/env python3
from __future__ import annotations

import csv
import math
from collections import defaultdict
from pathlib import Path
from zipfile import ZipFile

import matplotlib as mpl

mpl.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import make_figure2a_quality_difference as xlsx


PLOT_ROOT = Path(__file__).resolve().parents[1]
OUT = PLOT_ROOT / "panels"
DERIVED = PLOT_ROOT / "derived_data"

Z_975 = 1.959963984540054

MAS_COLOR = "#C4776B"
HUMAN_COLOR = "#4B55A4"
TEXT = "#26313B"
SPINE = "#9B9993"
ERR = "#4C4A46"
LIGHT = "#E7E2DB"


DIMENSIONS = [
    {"family": "QGval", "label": "Fluency", "max_score": 5, "col": 2},
    {"family": "QGval", "label": "Clarity", "max_score": 5, "col": 3},
    {"family": "QGval", "label": "Conciseness", "max_score": 5, "col": 4},
    {"family": "QGval", "label": "Relevance", "max_score": 5, "col": 5},
    {"family": "QGval", "label": "Consistency", "max_score": 5, "col": 6},
    {"family": "QGval", "label": "Answerability", "max_score": 5, "col": 7},
    {"family": "QGval", "label": "Answer consistency", "max_score": 5, "col": 8},
    {"family": "ULM", "label": "Fluency", "max_score": 5, "col": 10},
    {"family": "ULM", "label": "Exclusiveness", "max_score": 5, "col": 11},
    {"family": "ULM", "label": "Explicitness", "max_score": 4, "col": 12},
    {"family": "ULM", "label": "Goal alignment", "max_score": 5, "col": 13},
    {"family": "ULM", "label": "Comprehensiveness", "max_score": 5, "col": 14},
    {"family": "ULM", "label": "Focus", "max_score": 5, "col": 15},
    {"family": "ULM", "label": "Guess resistance", "max_score": 5, "col": 16},
    {"family": "ULM", "label": "Completeness", "max_score": 5, "col": 17},
    {"family": "ULM", "label": "Correctness", "max_score": 5, "col": 18},
    {"family": "ULM", "label": "Solvability", "max_score": 5, "col": 19},
    {"family": "ULM", "label": "Absoluteness", "max_score": 5, "col": 20},
    {"family": "ULM", "label": "Plausibility", "max_score": 5, "col": 21},
    {"family": "ULM", "label": "Reasoning", "max_score": 4, "col": 22},
    {"family": "ULM", "label": "Feedback", "max_score": 5, "col": 23},
    {"family": "ULM", "label": "Fairness", "max_score": 3, "col": 24},
    {"family": "ULM", "label": "Explanation score", "max_score": 5, "col": 25},
]


def ni_margin(max_score: int) -> float:
    return {5: -0.30, 4: -0.25, 3: -0.20}[max_score]


def margin_label(diff: float, margin: float) -> str:
    return "n.s." if diff > margin else "***"


def parse_dimension_records() -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for path in xlsx.expert_files():
        with ZipFile(path) as zf:
            sheets = xlsx.workbook_sheet_map(zf)
        source_sheets = [
            ("Human", xlsx.P_SUMMARY),
            ("MAS", xlsx.M_MERGED if xlsx.M_MERGED in sheets else xlsx.M_SUMMARY),
        ]
        for source, sheet_name in source_sheets:
            rows = xlsx.read_sheet_rows(path, sheet_name)
            item_rows = [
                row
                for row in rows
                if len(row) > 26
                and isinstance(row[1], (int, float))
                and isinstance(row[9], (int, float))
                and isinstance(row[26], (int, float))
            ]
            if len(item_rows) != 70:
                raise ValueError(f"{path.name} / {sheet_name} has {len(item_rows)} item rows, expected 70.")
            for seq, row in enumerate(item_rows, start=1):
                for dim in DIMENSIONS:
                    records.append(
                        {
                            "expert_file": path.name,
                            "source": source,
                            "item_seq": seq,
                            "family": dim["family"],
                            "dimension": dim["label"],
                            "max_score": dim["max_score"],
                            "score": float(row[int(dim["col"])]),
                        }
                    )
    return records


def item_level_arrays(records: list[dict[str, object]], family: str, dimension: str) -> dict[str, np.ndarray]:
    arrays: dict[str, np.ndarray] = {}
    for source in ("Human", "MAS"):
        grouped: dict[int, list[float]] = defaultdict(list)
        for record in records:
            if record["source"] == source and record["family"] == family and record["dimension"] == dimension:
                grouped[int(record["item_seq"])].append(float(record["score"]))
        arrays[source] = np.array([np.mean(grouped[i]) for i in sorted(grouped)], dtype=float)
    return arrays


def summarize(records: list[dict[str, object]]) -> list[dict[str, float | str | int | bool]]:
    rows: list[dict[str, float | str | int | bool]] = []
    for order, dim in enumerate(DIMENSIONS, start=1):
        family = str(dim["family"])
        dimension = str(dim["label"])
        max_score = int(dim["max_score"])
        arrays = item_level_arrays(records, family, dimension)
        human = arrays["Human"]
        mas = arrays["MAS"]
        diff = float(mas.mean() - human.mean())
        se = float(math.sqrt(mas.var(ddof=1) / len(mas) + human.var(ddof=1) / len(human)))
        ci_low = diff - Z_975 * se
        ci_high = diff + Z_975 * se
        margin = ni_margin(max_score)
        mean_above_margin = diff > margin
        rows.append(
            {
                "order": order,
                "family": family,
                "dimension": dimension,
                "max_score": max_score,
                "ni_margin": margin,
                "n_per_group": len(mas),
                "mas_mean": float(mas.mean()),
                "mas_sd": float(mas.std(ddof=1)),
                "human_mean": float(human.mean()),
                "human_sd": float(human.std(ddof=1)),
                "diff": diff,
                "ci_low": float(ci_low),
                "ci_high": float(ci_high),
                "se": se,
                "mean_above_margin": bool(mean_above_margin),
                "label": margin_label(diff, margin),
            }
        )
    return rows


def write_source_tables(records: list[dict[str, object]], stats: list[dict[str, float | str | int | bool]]) -> None:
    DERIVED.mkdir(parents=True, exist_ok=True)
    with (DERIVED / "fig2B_dimension_scores_stats.csv").open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(stats[0].keys()))
        writer.writeheader()
        writer.writerows(stats)

    item_rows = []
    for dim in DIMENSIONS:
        arrays = item_level_arrays(records, str(dim["family"]), str(dim["label"]))
        for source in ("Human", "MAS"):
            for seq, score in enumerate(arrays[source], start=1):
                item_rows.append(
                    {
                        "family": dim["family"],
                        "dimension": dim["label"],
                        "source": source,
                        "item_seq": seq,
                        "expert_mean_score": float(score),
                    }
                )
    with (DERIVED / "fig2B_dimension_scores_item_scores.csv").open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(item_rows[0].keys()))
        writer.writeheader()
        writer.writerows(item_rows)


def draw_figure(stats: list[dict[str, float | str | int | bool]]) -> None:
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

    y_positions = np.array([i if i < 7 else i + 0.72 for i in range(len(stats))], dtype=float)
    mas_y = y_positions - 0.19
    human_y = y_positions + 0.19
    bar_height = 0.36

    fig, ax = plt.subplots(figsize=(11.8, 14.8))
    ax.barh(mas_y, [float(r["mas_mean"]) for r in stats], height=bar_height, color=MAS_COLOR, label="MAS")
    ax.barh(human_y, [float(r["human_mean"]) for r in stats], height=bar_height, color=HUMAN_COLOR, label="Human")

    for y, mean, sd in zip(mas_y, [float(r["mas_mean"]) for r in stats], [float(r["mas_sd"]) for r in stats]):
        ax.errorbar(mean, y, xerr=sd, fmt="none", ecolor=ERR, elinewidth=2.2, capsize=6, capthick=2.2, zorder=4)
    for y, mean, sd in zip(human_y, [float(r["human_mean"]) for r in stats], [float(r["human_sd"]) for r in stats]):
        ax.errorbar(mean, y, xerr=sd, fmt="none", ecolor=ERR, elinewidth=2.2, capsize=6, capthick=2.2, zorder=4)

    ax.set_yticks(y_positions, [str(r["dimension"]) for r in stats], fontsize=20, color=TEXT)
    ax.invert_yaxis()
    ax.set_xlim(1.0, 5.90)
    ax.set_xticks([1, 2, 3, 4, 5])
    ax.tick_params(axis="x", colors="#4A4A4A", labelsize=20, width=2.2, length=8)
    ax.tick_params(axis="y", colors=TEXT, labelsize=20, width=2.2, length=8)
    ax.set_xlabel("Mean expert rating (raw rubric scale)", fontsize=21, color=TEXT, labelpad=12)
    ax.set_title("Per-dimension scores (human-expert rubric)", fontsize=24, color=TEXT, pad=20)

    for side in ("left", "bottom"):
        ax.spines[side].set_color(SPINE)
        ax.spines[side].set_linewidth(2.0)

    gap_y = (y_positions[6] + y_positions[7]) / 2
    ax.axhline(gap_y, color=LIGHT, linewidth=1.1, zorder=0)

    for row, y in zip(stats, y_positions):
        label = str(row["label"])
        color = "#C73C32" if label != "n.s." else TEXT
        ax.text(5.55, y, label, ha="left", va="center", fontsize=19, color=color)

    legend = ax.legend(
        loc="upper left",
        bbox_to_anchor=(-0.33, -0.058),
        ncol=2,
        frameon=False,
        fontsize=19,
        handlelength=1.8,
        columnspacing=1.9,
    )
    for txt in legend.get_texts():
        txt.set_color(TEXT)

    fig.text(0.018, 0.975, "(B)", fontsize=29, fontweight="bold", color="#111111", ha="left", va="top")
    fig.subplots_adjust(left=0.27, right=0.94, top=0.93, bottom=0.10)
    fig.savefig(OUT / "Figure2B_dimension_scores.pdf", bbox_inches="tight", facecolor="white")
    plt.close(fig)


def main() -> None:
    records = parse_dimension_records()
    stats = summarize(records)
    write_source_tables(records, stats)
    draw_figure(stats)
    for row in stats:
        print(
            f"{row['family']} {row['dimension']}: "
            f"MAS {float(row['mas_mean']):.2f} +/- {float(row['mas_sd']):.2f}; "
            f"Human {float(row['human_mean']):.2f} +/- {float(row['human_sd']):.2f}; "
            f"diff {float(row['diff']):+.2f} [{float(row['ci_low']):+.2f}, {float(row['ci_high']):+.2f}] "
            f"delta {float(row['ni_margin']):.2f} {row['label']}"
        )
    print(f"Wrote {OUT / 'Figure2B_dimension_scores.pdf'}")


if __name__ == "__main__":
    main()
