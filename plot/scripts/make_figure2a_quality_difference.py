#!/usr/bin/env python3
from __future__ import annotations

import csv
import math
import posixpath
from collections import defaultdict
from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as ET

import matplotlib as mpl

mpl.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


PLOT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PLOT_ROOT.parent
OUT = PLOT_ROOT / "panels"
DERIVED = PLOT_ROOT / "derived_data"

P_SUMMARY = "P\u6c47\u603b"
M_MERGED = "M-\u5408\u5e76"
M_SUMMARY = "M\u6c47\u603b"
EXPERT_PREFIX = "\u4e13\u5bb6"

XLSX_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
OD_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS = {"m": XLSX_NS, "rel": REL_NS}

Z_975 = 1.959963984540054
PM = "\u00b1"


def read_shared_strings(zf: ZipFile) -> list[str]:
    try:
        root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
    except KeyError:
        return []
    strings: list[str] = []
    for si in root.findall("m:si", NS):
        strings.append("".join(t.text or "" for t in si.findall(".//m:t", NS)))
    return strings


def column_index(cell_ref: str) -> int:
    letters = "".join(ch for ch in cell_ref if ch.isalpha())
    index = 0
    for ch in letters:
        index = index * 26 + ord(ch.upper()) - 64
    return index - 1


def cell_value(cell: ET.Element, shared_strings: list[str]):
    cell_type = cell.attrib.get("t")
    if cell_type == "s":
        value = cell.find("m:v", NS)
        if value is None or value.text is None:
            return None
        return shared_strings[int(value.text)]
    if cell_type == "inlineStr":
        return "".join(t.text or "" for t in cell.findall(".//m:t", NS))

    value = cell.find("m:v", NS)
    if value is None or value.text is None:
        return None
    text = value.text
    if cell_type == "b":
        return bool(int(text))
    try:
        number = float(text)
        return int(number) if number.is_integer() else number
    except ValueError:
        return text


def workbook_sheet_map(zf: ZipFile) -> dict[str, str]:
    workbook = ET.fromstring(zf.read("xl/workbook.xml"))
    rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
    rid_to_target = {
        rel.attrib["Id"]: rel.attrib["Target"]
        for rel in rels.findall("rel:Relationship", NS)
    }

    sheets: dict[str, str] = {}
    for sheet in workbook.findall("m:sheets/m:sheet", NS):
        name = sheet.attrib["name"]
        rel_id = sheet.attrib.get(f"{{{OD_REL_NS}}}id")
        target = rid_to_target[rel_id].lstrip("/")
        if not target.startswith("xl/"):
            target = posixpath.normpath("xl/" + target)
        sheets[name] = target
    return sheets


def read_sheet_rows(path: Path, sheet_name: str) -> list[list[object]]:
    with ZipFile(path) as zf:
        shared_strings = read_shared_strings(zf)
        target = workbook_sheet_map(zf)[sheet_name]
        sheet = ET.fromstring(zf.read(target))

    rows: list[list[object]] = []
    for row in sheet.findall("m:sheetData/m:row", NS):
        values: list[object] = []
        for cell in row.findall("m:c", NS):
            idx = column_index(cell.attrib.get("r", "A1"))
            while len(values) <= idx:
                values.append(None)
            values[idx] = cell_value(cell, shared_strings)
        rows.append(values)
    return rows


def expert_files() -> list[Path]:
    files = [
        path
        for path in REPO_ROOT.glob("*.xlsx")
        if path.name.startswith(EXPERT_PREFIX) and not path.name.startswith("~$")
    ]
    if not files:
        raise FileNotFoundError("No expert-rating workbooks found in repository root.")
    return sorted(files, key=lambda p: p.name)


def parse_rating_records() -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for path in expert_files():
        with ZipFile(path) as zf:
            sheets = workbook_sheet_map(zf)

        source_sheets = [
            ("Human", P_SUMMARY),
            ("MAS", M_MERGED if M_MERGED in sheets else M_SUMMARY),
        ]
        for source, sheet_name in source_sheets:
            rows = read_sheet_rows(path, sheet_name)
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
                records.append(
                    {
                        "expert_file": path.name,
                        "source": source,
                        "item_seq": seq,
                        "paper_item_no": int(row[1]),
                        "qg_total": float(row[9]),
                        "ulm_total": float(row[26]),
                    }
                )
    return records


def item_means(records: list[dict[str, object]], metric: str) -> dict[str, np.ndarray]:
    out: dict[str, np.ndarray] = {}
    for source in ("Human", "MAS"):
        grouped: dict[int, list[float]] = defaultdict(list)
        for record in records:
            if record["source"] == source:
                grouped[int(record["item_seq"])].append(float(record[metric]))
        out[source] = np.array([np.mean(grouped[i]) for i in sorted(grouped)], dtype=float)
    return out


def endpoint_stats(records: list[dict[str, object]]) -> list[dict[str, float | str | int]]:
    endpoints = [
        ("QGval", "qg_total", 35, -2.0),
        ("ULM", "ulm_total", 76, -4.0),
    ]
    stats: list[dict[str, float | str | int]] = []
    for endpoint, metric, scale_points, margin in endpoints:
        arrays = item_means(records, metric)
        human = arrays["Human"]
        mas = arrays["MAS"]
        diff = float(mas.mean() - human.mean())
        se = float(math.sqrt(mas.var(ddof=1) / len(mas) + human.var(ddof=1) / len(human)))
        stats.append(
            {
                "endpoint": endpoint,
                "metric": metric,
                "scale_points": scale_points,
                "ni_margin": margin,
                "n_per_group": len(mas),
                "mas_mean": float(mas.mean()),
                "mas_sd": float(mas.std(ddof=1)),
                "human_mean": float(human.mean()),
                "human_sd": float(human.std(ddof=1)),
                "diff": diff,
                "ci_low": diff - Z_975 * se,
                "ci_high": diff + Z_975 * se,
            }
        )
    return stats


def write_source_tables(records: list[dict[str, object]], stats: list[dict[str, float | str | int]]) -> None:
    DERIVED.mkdir(parents=True, exist_ok=True)
    with (DERIVED / "fig2A_quality_difference_stats.csv").open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(stats[0].keys()))
        writer.writeheader()
        writer.writerows(stats)

    qg = item_means(records, "qg_total")
    ulm = item_means(records, "ulm_total")
    rows = []
    for source in ("Human", "MAS"):
        for i, (qg_value, ulm_value) in enumerate(zip(qg[source], ulm[source]), start=1):
            rows.append(
                {
                    "source": source,
                    "item_seq": i,
                    "qg_total_mean_across_experts": float(qg_value),
                    "ulm_total_mean_across_experts": float(ulm_value),
                }
            )
    with (DERIVED / "fig2A_quality_difference_item_scores.csv").open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


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

    color_map = {
        "QGval": {"line": "#C73C32", "fill": "#FAEEEE", "y": 0.92},
        "ULM": {"line": "#2B6CB0", "fill": "#EDF4FB", "y": 0.05},
    }
    text = "#26313B"
    spine = "#9B9993"
    black = "#23201B"
    x_min, x_max = -5.05, 2.25
    y_min, y_max = -0.86, 1.62
    lane_half_height = 0.39

    fig, ax = plt.subplots(figsize=(9.7, 8.0))
    ax.set_xlim(x_min, x_max)
    ax.set_ylim(y_min, y_max)

    for row in stats:
        endpoint = str(row["endpoint"])
        y = color_map[endpoint]["y"]
        ymin = (y - lane_half_height - y_min) / (y_max - y_min)
        ymax = (y + lane_half_height - y_min) / (y_max - y_min)
        ax.axvspan(
            x_min,
            float(row["ni_margin"]),
            ymin=ymin,
            ymax=ymax,
            color=color_map[endpoint]["fill"],
            zorder=0,
        )
        ax.vlines(
            float(row["ni_margin"]),
            y - lane_half_height,
            y + lane_half_height,
            color=color_map[endpoint]["line"],
            linewidth=2.8,
            linestyles="--",
            zorder=1,
        )
        ax.text(
            float(row["ni_margin"]) - 0.08,
            y,
            f"NI margin {fmt(float(row['ni_margin']))}",
            rotation=90,
            color=color_map[endpoint]["line"],
            fontsize=14,
            ha="right",
            va="center",
        )

    ax.axvline(0, color=spine, linewidth=2.7, zorder=1)

    for row in stats:
        endpoint = str(row["endpoint"])
        y = color_map[endpoint]["y"]
        ax.hlines(
            y,
            float(row["ci_low"]),
            float(row["ci_high"]),
            color=black,
            linewidth=6.2,
            zorder=3,
        )
        ax.scatter(
            [float(row["diff"])],
            [y],
            marker="D",
            s=780,
            color=black,
            edgecolor=black,
            zorder=4,
        )

        score_label = (
            f"{endpoint}: MAS {fmt(float(row['mas_mean']))} {PM} {fmt(float(row['mas_sd']))}  "
            f"vs  Human {fmt(float(row['human_mean']))} {PM} {fmt(float(row['human_sd']))}  "
            f"({int(row['scale_points'])}-point)"
        )
        ax.text(0.42, y + 0.36, score_label, fontsize=17, color=text, ha="center", va="center")
        ax.text(
            float(row["diff"]),
            y + 0.20,
            f"{fmt(float(row['diff']))}  [{fmt(float(row['ci_low']))}, {fmt(float(row['ci_high']))}]",
            fontsize=19,
            color=text,
            ha="center",
            va="center",
        )

    ax.text(
        -0.10,
        -0.58,
        "Non-inferior\n(95% CIs above endpoint-specific NI margins)",
        fontsize=18,
        color=text,
        ha="center",
        va="center",
    )

    ax.set_yticks(
        [color_map["QGval"]["y"], color_map["ULM"]["y"]],
        ["QGval\n(n=70/group)", "ULM\n(n=70/group)"],
        color=text,
        fontsize=20,
    )
    ax.set_xticks([-5, -4, -3, -2, -1, 0, 1, 2])
    ax.tick_params(axis="x", colors="#4A4A4A", labelsize=20, width=2.3, length=9)
    ax.tick_params(axis="y", colors=text, labelsize=20, width=2.3, length=10)
    ax.set_xlabel("Quality-score diff. (MAS - Human)", fontsize=22, color=text, labelpad=13)
    ax.set_title("Primary endpoint (non-inferiority)", fontsize=25, color=text, pad=20)

    for side in ("left", "bottom"):
        ax.spines[side].set_color(spine)
        ax.spines[side].set_linewidth(2.2)

    fig.text(0.018, 0.955, "(A)", fontsize=29, fontweight="bold", color="#111111", ha="left", va="top")
    fig.subplots_adjust(left=0.245, right=0.985, top=0.875, bottom=0.165)
    fig.savefig(OUT / "Figure2A_quality_difference.pdf", bbox_inches="tight", facecolor="white")
    plt.close(fig)


def main() -> None:
    records = parse_rating_records()
    stats = endpoint_stats(records)
    write_source_tables(records, stats)
    draw_figure(stats)
    for row in stats:
        print(
            f"{row['endpoint']}: MAS {float(row['mas_mean']):.2f} {PM} {float(row['mas_sd']):.2f} "
            f"vs Human {float(row['human_mean']):.2f} {PM} {float(row['human_sd']):.2f}; "
            f"diff {float(row['diff']):.2f} [{float(row['ci_low']):.2f}, {float(row['ci_high']):.2f}]"
        )
    print(f"Wrote {OUT / 'Figure2A_quality_difference.pdf'}")


if __name__ == "__main__":
    main()
