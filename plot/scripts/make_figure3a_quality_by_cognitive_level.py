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

import make_figure2a_quality_difference as xlsx


PLOT_ROOT = Path(__file__).resolve().parents[1]
OUT = PLOT_ROOT / "panels"
DERIVED = PLOT_ROOT / "derived_data"

P_BLOOM = "P\u5e03\u9c81\u59c6\u5206\u7c7b"
M_BLOOM = "M\u5e03\u9c81\u59c6\u5206\u7c7b"

LEVELS = [
    ("\u8bb0\u5fc6", "Knowledge"),
    ("\u7406\u89e3", "Comprehension"),
    ("\u5e94\u7528", "Application"),
    ("\u5206\u6790", "Analysis"),
]

METRICS = {
    "QGval": {"col": 9, "scale": 7.0, "margin": -0.30, "color": "#C73C32"},
    "ULM": {"col": 26, "scale": 16.0, "margin": -0.25, "color": "#2B6CB0"},
}

Z_975 = 1.959963984540054
TEXT = "#26313B"
SPINE = "#9B9993"


def parse_records() -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    valid_levels = {level for level, _ in LEVELS}
    for path in xlsx.expert_files():
        for source, sheet_name in (("Human", P_BLOOM), ("MAS", M_BLOOM)):
            rows = xlsx.read_sheet_rows(path, sheet_name)
            current_level: str | None = None
            item_seq = 0
            for row in rows:
                if row and isinstance(row[0], str) and row[0] in valid_levels:
                    current_level = row[0]
                if (
                    len(row) > 26
                    and isinstance(row[1], (int, float))
                    and isinstance(row[9], (int, float))
                    and isinstance(row[26], (int, float))
                ):
                    item_seq += 1
                    if current_level is None:
                        raise ValueError(f"Missing Bloom level in {path.name} / {sheet_name}, item row {item_seq}.")
                    records.append(
                        {
                            "expert_file": path.name,
                            "source": source,
                            "cognitive_level": current_level,
                            "item_seq": item_seq,
                            "paper_item_no": int(row[1]),
                            "qg_score": float(row[9]) / float(METRICS["QGval"]["scale"]),
                            "ulm_score": float(row[26]) / float(METRICS["ULM"]["scale"]),
                        }
                    )
            if item_seq != 70:
                raise ValueError(f"{path.name} / {sheet_name} has {item_seq} item rows, expected 70.")
    return records


def item_arrays(records: list[dict[str, object]], level: str, metric_key: str) -> dict[str, np.ndarray]:
    score_col = "qg_score" if metric_key == "QGval" else "ulm_score"
    arrays: dict[str, np.ndarray] = {}
    for source in ("Human", "MAS"):
        grouped: dict[int, list[float]] = defaultdict(list)
        for record in records:
            if record["source"] == source and record["cognitive_level"] == level:
                grouped[int(record["item_seq"])].append(float(record[score_col]))
        arrays[source] = np.array([np.mean(vals) for _, vals in sorted(grouped.items())], dtype=float)
    return arrays


def summarize(records: list[dict[str, object]]) -> list[dict[str, float | str | int]]:
    rows: list[dict[str, float | str | int]] = []
    for order, (level, label) in enumerate(LEVELS, start=1):
        for metric_key, metric in METRICS.items():
            arrays = item_arrays(records, level, metric_key)
            human = arrays["Human"]
            mas = arrays["MAS"]
            diff = float(mas.mean() - human.mean())
            if len(human) > 1 and len(mas) > 1:
                se = float(math.sqrt(mas.var(ddof=1) / len(mas) + human.var(ddof=1) / len(human)))
                ci_low = diff - Z_975 * se
                ci_high = diff + Z_975 * se
            else:
                se = ci_low = ci_high = float("nan")
            rows.append(
                {
                    "order": order,
                    "cognitive_level": level,
                    "cognitive_level_label": label,
                    "metric": metric_key,
                    "ni_margin": float(metric["margin"]),
                    "n_mas": len(mas),
                    "n_human": len(human),
                    "mas_mean": float(mas.mean()),
                    "mas_sd": float(mas.std(ddof=1)) if len(mas) > 1 else float("nan"),
                    "human_mean": float(human.mean()),
                    "human_sd": float(human.std(ddof=1)) if len(human) > 1 else float("nan"),
                    "diff": diff,
                    "ci_low": float(ci_low),
                    "ci_high": float(ci_high),
                    "se": se,
                    "noninferior_95ci": bool(ci_low > float(metric["margin"])) if not math.isnan(ci_low) else False,
                }
            )
    return rows


def write_source_tables(records: list[dict[str, object]], stats: list[dict[str, float | str | int]]) -> None:
    DERIVED.mkdir(parents=True, exist_ok=True)
    with (DERIVED / "fig3A_quality_by_cognitive_level_qg_ulm_stats.csv").open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(stats[0].keys()))
        writer.writeheader()
        writer.writerows(stats)

    item_rows = []
    for level, label in LEVELS:
        for metric_key in METRICS:
            arrays = item_arrays(records, level, metric_key)
            for source in ("Human", "MAS"):
                for i, value in enumerate(arrays[source], start=1):
                    item_rows.append(
                        {
                            "cognitive_level": level,
                            "cognitive_level_label": label,
                            "metric": metric_key,
                            "source": source,
                            "within_sheet_item_seq": i,
                            "expert_mean_score": float(value),
                        }
                    )
    with (DERIVED / "fig3A_quality_by_cognitive_level_qg_ulm_item_scores.csv").open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(item_rows[0].keys()))
        writer.writeheader()
        writer.writerows(item_rows)


def fmt(value: float) -> str:
    return f"{value:.2f}"


def draw_figure(stats: list[dict[str, float | str | int]]) -> None:
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

    fig, ax = plt.subplots(figsize=(10.6, 7.6))
    y_base = np.arange(len(LEVELS), dtype=float)
    offsets = {"QGval": -0.075, "ULM": 0.075}

    ax.axvline(0, color=SPINE, linewidth=2.5, zorder=0)
    for metric_key, metric in METRICS.items():
        margin = float(metric["margin"])
        color = str(metric["color"])
        ax.axvline(margin, color=color, linewidth=2.7, linestyle="--", zorder=0)
        ax.text(
            margin - 0.014,
            -0.55,
            f"{metric_key} NI {margin:.2f}",
            rotation=90,
            ha="right",
            va="bottom",
            color=color,
            fontsize=16,
        )

    for metric_key, metric in METRICS.items():
        color = str(metric["color"])
        sub = [row for row in stats if row["metric"] == metric_key]
        ys = y_base + offsets[metric_key]
        estimates = np.array([float(row["diff"]) for row in sub])
        lows = np.array([float(row["ci_low"]) for row in sub])
        highs = np.array([float(row["ci_high"]) for row in sub])
        ax.hlines(ys, lows, highs, color=color, linewidth=3.2, alpha=0.82, zorder=2)
        ax.scatter(estimates, ys, s=260, color=color, edgecolor=color, zorder=3, label=metric_key)
        for estimate, y in zip(estimates, ys):
            ax.text(0.47, y, fmt(estimate), color=color, ha="left", va="center", fontsize=16)

    ax.set_yticks(y_base, [label for _, label in LEVELS], fontsize=20, color=TEXT)
    ax.invert_yaxis()
    ax.set_xlim(-0.43, 0.58)
    ax.set_xticks([-0.4, -0.2, 0.0, 0.2, 0.4, 0.6])
    ax.tick_params(axis="x", colors="#4A4A4A", labelsize=18, width=2.0, length=8)
    ax.tick_params(axis="y", colors=TEXT, labelsize=20, width=2.0, length=8)
    ax.set_xlabel("Mean quality-score diff. (MAS - Human)", fontsize=20, color=TEXT, labelpad=10)
    ax.set_title("Expert quality gap by cognitive level", fontsize=24, color=TEXT, pad=18)

    for side in ("left", "bottom"):
        ax.spines[side].set_color(SPINE)
        ax.spines[side].set_linewidth(2.0)

    legend = ax.legend(
        loc="upper right",
        bbox_to_anchor=(0.95, 1.05),
        ncol=2,
        frameon=False,
        fontsize=16,
        handlelength=1.5,
        columnspacing=1.6,
    )
    for text in legend.get_texts():
        text.set_color(TEXT)

    fig.text(0.02, 0.94, "(A)", fontsize=28, fontweight="bold", color="#111111", ha="left", va="top")
    fig.subplots_adjust(left=0.18, right=0.96, top=0.86, bottom=0.15)
    fig.savefig(OUT / "Figure3A_quality_by_cognitive_level.pdf", bbox_inches="tight", facecolor="white")
    plt.close(fig)


def main() -> None:
    records = parse_records()
    stats = summarize(records)
    write_source_tables(records, stats)
    draw_figure(stats)
    for row in stats:
        print(
            f"{row['metric']} {row['cognitive_level_label']}: diff {float(row['diff']):+.2f} "
            f"[{float(row['ci_low']):+.2f}, {float(row['ci_high']):+.2f}], "
            f"margin {float(row['ni_margin']):+.2f}, n={int(row['n_mas'])}/{int(row['n_human'])}"
        )
    print(f"Wrote {OUT / 'Figure3A_quality_by_cognitive_level.pdf'}")


if __name__ == "__main__":
    main()
