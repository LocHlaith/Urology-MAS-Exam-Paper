#!/usr/bin/env python3
"""Generate every manuscript panel from one authoritative plotting script.

The panel numbering follows 图片大改.md:
Figure 2A, Figure 3A, and Figure 4A are intentionally reserved empty slots.
All figures are written as editable PDFs to plot/panels.
"""
from __future__ import annotations

import csv
import json
import math
import posixpath
import re
from collections import Counter, defaultdict, deque
from pathlib import Path
from typing import Any, Iterable, Sequence
from xml.etree import ElementTree as ET
from zipfile import ZipFile

import matplotlib as mpl

mpl.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
from patsy import build_design_matrices
from scipy import stats
from statsmodels.genmod.bayes_mixed_glm import BinomialBayesMixedGLM
from statsmodels.stats.proportion import proportion_confint


PLOT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PLOT_ROOT.parent
DERIVED = PLOT_ROOT / "derived_data"
OUT = PLOT_ROOT / "panels"
OUT.mkdir(parents=True, exist_ok=True)
DERIVED.mkdir(parents=True, exist_ok=True)

UROMAS_BASE_COLORS = {
    "grid": "#E3DFD8",
    "spine": "#9E9A93",
    "text": "#3E3E3E",
    "text_dark": "#2A251F",
    "tick": "#4F4F4F",
    "border": "#C8C2B8",
    "soft_separator": "#D8D2C9",
}
CORE_COLORS = {"MAS": "#B86758", "Human": "#313E96"}
CORE_FILLS = {"MAS": "#F2DFDB", "Human": "#D9DCF1"}
OPTIONAL_COLOR_PAIRS = [
    {"color": "#7C5CFF", "fill": "#E9E2FF"},
    {"color": "#B8954B", "fill": "#F1E6C8"},
    {"color": "#D97757", "fill": "#F6DED4"},
    {"color": "#2F8F83", "fill": "#DCEFEB"},
    {"color": "#6F6F6F", "fill": "#E8E8E8"},
    {"color": "#4D6BFE", "fill": "#E1E7FF"},
    {"color": "#A66A2C", "fill": "#EAD8C3"},
    {"color": "#C85A9A", "fill": "#F2DDEC"},
]

FORM_COLORS = {"A": OPTIONAL_COLOR_PAIRS[0], "B": OPTIONAL_COLOR_PAIRS[1]}
LEVELS_4 = ["recall", "comprehension", "application", "analysis"]
LEVEL_LABELS_4 = {
    "recall": "Knowledge",
    "comprehension": "Comprehension",
    "application": "Application",
    "analysis": "Analysis",
}
LEVELS_3 = ["knowledge", "application", "reasoning"]
LEVEL_LABELS_3 = {
    "knowledge": "Knowledge",
    "application": "Clinical application",
    "reasoning": "Clinical reasoning",
}

P_SUMMARY = "P汇总"
M_MERGED = "M-合并"
M_SUMMARY = "M汇总"
P_BLOOM = "P布鲁姆分类"
M_BLOOM = "M布鲁姆分类"
P_TYPE = "P-分题型"
M_TYPE = "M合并-分题型"
EXPERT_PREFIX = "专家"

XLSX_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
OD_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS = {"m": XLSX_NS, "rel": REL_NS}
Z_975 = 1.959963984540054


def setup_style() -> None:
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
            "axes.spines.top": False,
            "axes.spines.right": False,
        }
    )


def style_axes(ax: plt.Axes, grid_axis: str = "y") -> None:
    ax.spines["left"].set_color(UROMAS_BASE_COLORS["spine"])
    ax.spines["bottom"].set_color(UROMAS_BASE_COLORS["spine"])
    ax.tick_params(colors=UROMAS_BASE_COLORS["tick"], length=3, width=0.7)
    ax.set_axisbelow(True)
    if grid_axis:
        ax.grid(
            axis=grid_axis,
            color=UROMAS_BASE_COLORS["grid"],
            linewidth=0.6,
            alpha=0.85,
        )


def add_panel_label(fig: plt.Figure, label: str, x: float = 0.012, y: float = 0.988) -> None:
    fig.text(
        x,
        y,
        f"({label.upper()})",
        ha="left",
        va="top",
        fontsize=11,
        fontweight="bold",
        color=UROMAS_BASE_COLORS["text_dark"],
    )


def save_pdf(fig: plt.Figure, filename: str, *, tight: bool = True) -> None:
    if tight:
        fig.tight_layout()
    fig.savefig(OUT / filename, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def remove_output(filename: str) -> None:
    path = OUT / filename
    if path.exists():
        path.unlink()


def write_csv(path: Path, rows: pd.DataFrame | Sequence[dict[str, Any]]) -> None:
    if isinstance(rows, pd.DataFrame):
        rows.to_csv(path, index=False, encoding="utf-8-sig")
    else:
        pd.DataFrame(rows).to_csv(path, index=False, encoding="utf-8-sig")


def bootstrap_mean_ci(
    values: Sequence[float],
    *,
    level: float = 0.95,
    reps: int = 3000,
    seed: int = 1,
) -> tuple[float, float, float]:
    clean = np.asarray(pd.Series(values).dropna(), dtype=float)
    if len(clean) == 0:
        return float("nan"), float("nan"), float("nan")
    if len(clean) == 1:
        return float(clean[0]), float(clean[0]), float(clean[0])
    rng = np.random.default_rng(seed)
    boots = rng.choice(clean, size=(reps, len(clean)), replace=True).mean(axis=1)
    alpha = (1.0 - level) / 2.0
    return (
        float(clean.mean()),
        float(np.quantile(boots, alpha)),
        float(np.quantile(boots, 1.0 - alpha)),
    )


def rounded_box(
    ax: plt.Axes,
    xy: tuple[float, float],
    size: tuple[float, float],
    title: str,
    body: str = "",
    facecolor: str = "white",
    edgecolor: str = UROMAS_BASE_COLORS["border"],
) -> None:
    x, y = xy
    width, height = size
    ax.add_patch(
        FancyBboxPatch(
            (x, y),
            width,
            height,
            boxstyle="round,pad=0.03,rounding_size=0.12",
            linewidth=0.9,
            edgecolor=edgecolor,
            facecolor=facecolor,
        )
    )
    ax.text(
        x + 0.14,
        y + height * 0.64,
        title,
        ha="left",
        va="center",
        fontweight="bold",
        color=UROMAS_BASE_COLORS["text_dark"],
    )
    if body:
        ax.text(
            x + 0.14,
            y + height * 0.31,
            body,
            ha="left",
            va="center",
            fontsize=7,
            color=UROMAS_BASE_COLORS["text"],
        )


def arrow(
    ax: plt.Axes,
    start: tuple[float, float],
    end: tuple[float, float],
    color: str = UROMAS_BASE_COLORS["tick"],
) -> None:
    ax.add_patch(
        FancyArrowPatch(
            start,
            end,
            arrowstyle="-|>",
            mutation_scale=10,
            linewidth=0.9,
            color=color,
            shrinkA=0,
            shrinkB=0,
        )
    )


# ---------------------------------------------------------------------------
# XLSX readers shared by Figures 2 and 4


def read_shared_strings(zf: ZipFile) -> list[str]:
    try:
        root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
    except KeyError:
        return []
    return [
        "".join(t.text or "" for t in si.findall(".//m:t", NS))
        for si in root.findall("m:si", NS)
    ]


def column_index(cell_ref: str) -> int:
    letters = "".join(ch for ch in cell_ref if ch.isalpha())
    index = 0
    for ch in letters:
        index = index * 26 + ord(ch.upper()) - 64
    return index - 1


def cell_value(cell: ET.Element, shared_strings: list[str]) -> Any:
    cell_type = cell.attrib.get("t")
    if cell_type == "s":
        value = cell.find("m:v", NS)
        return None if value is None or value.text is None else shared_strings[int(value.text)]
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
        rel_id = sheet.attrib.get(f"{{{OD_REL_NS}}}id")
        target = rid_to_target[rel_id].lstrip("/")
        if not target.startswith("xl/"):
            target = posixpath.normpath("xl/" + target)
        sheets[sheet.attrib["name"]] = target
    return sheets


def read_sheet_rows(path: Path, sheet_name: str) -> list[list[Any]]:
    with ZipFile(path) as zf:
        shared_strings = read_shared_strings(zf)
        target = workbook_sheet_map(zf)[sheet_name]
        sheet = ET.fromstring(zf.read(target))
    rows: list[list[Any]] = []
    for row in sheet.findall("m:sheetData/m:row", NS):
        values: list[Any] = []
        for cell in row.findall("m:c", NS):
            idx = column_index(cell.attrib.get("r", "A1"))
            while len(values) <= idx:
                values.append(None)
            values[idx] = cell_value(cell, shared_strings)
        rows.append(values)
    return rows


def expert_files() -> list[Path]:
    files = sorted(
        (
            path
            for path in REPO_ROOT.glob("*.xlsx")
            if path.name.startswith(EXPERT_PREFIX) and not path.name.startswith("~$")
        ),
        key=lambda path: path.name,
    )
    if not files:
        raise FileNotFoundError("No expert-rating workbooks were found in the repository root.")
    return files


def is_rating_row(row: Sequence[Any]) -> bool:
    return (
        len(row) > 26
        and isinstance(row[1], (int, float))
        and isinstance(row[9], (int, float))
        and isinstance(row[26], (int, float))
    )


def parse_yes_no(value: Any) -> int | None:
    if value is None:
        return None
    text = str(value).strip()
    if text in {"是", "AI", "ai", "人工智能"}:
        return 1
    if text in {"否", "人工", "Human", "human"}:
        return 0
    return None


def normalize_item_type(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip().replace(",", "/").replace("-", "/")
    mapping = {
        "A1": "A1",
        "A2": "A2",
        "A3/4": "A3/A4",
        "A3/A4": "A3/A4",
        "B": "B",
        "X": "X",
        "多项选择题": "X",
    }
    return mapping.get(text)


def row_signature(row: Sequence[Any]) -> tuple[Any, ...]:
    # Exclude the source-guess column because several workbooks retain it only
    # on the summary sheet, while the score columns remain identical.
    values = list(row[1:27])
    return tuple("" if value is None else str(value).strip() for value in values)


def classified_rows(
    rows: Sequence[Sequence[Any]],
    labels: dict[str, str],
) -> list[dict[str, Any]]:
    current: str | None = None
    output: list[dict[str, Any]] = []
    for row in rows:
        first = str(row[0]).strip() if row and row[0] is not None else ""
        if first in labels:
            current = labels[first]
        if is_rating_row(row):
            if current is None:
                raise ValueError("Classification heading missing before an expert-rating row.")
            output.append({"signature": row_signature(row), "classification": current, "row": row})
    return output


def parse_expert_judgments() -> pd.DataFrame:
    bloom_map = {"记忆": "recall", "理解": "comprehension", "应用": "application", "分析": "analysis"}
    type_map = {
        "A1": "A1",
        "A2": "A2",
        "A3,4": "A3/A4",
        "A3-4": "A3/A4",
        "B": "B",
        "X": "X",
        "多项选择题": "X",
    }
    records: list[dict[str, Any]] = []
    for path in expert_files():
        expert_match = re.search(r"专家\s*(\d+)", path.name)
        expert = f"Expert {expert_match.group(1)}" if expert_match else path.stem
        with ZipFile(path) as zf:
            sheets = workbook_sheet_map(zf)
        for source, summary_sheet, bloom_sheet, type_sheet in [
            ("Human", P_SUMMARY, P_BLOOM, P_TYPE),
            (
                "MAS",
                M_MERGED if M_MERGED in sheets else M_SUMMARY,
                M_BLOOM,
                M_TYPE,
            ),
        ]:
            if (
                summary_sheet not in sheets
                or bloom_sheet not in sheets
                or type_sheet not in sheets
            ):
                raise KeyError(
                    f"{path.name} lacks {summary_sheet}, {bloom_sheet}, or {type_sheet}."
                )
            bloom = classified_rows(read_sheet_rows(path, bloom_sheet), bloom_map)
            typed = classified_rows(read_sheet_rows(path, type_sheet), type_map)
            summary_rows = [
                row
                for row in read_sheet_rows(path, summary_sheet)
                if is_rating_row(row)
            ]
            bloom_queues: dict[tuple[Any, ...], deque[str]] = defaultdict(deque)
            for record in bloom:
                bloom_queues[record["signature"]].append(
                    str(record["classification"])
                )
            type_queues: dict[tuple[Any, ...], deque[str]] = defaultdict(deque)
            for record in typed:
                type_queues[record["signature"]].append(str(record["classification"]))

            occurrence: Counter[tuple[str, int]] = Counter()
            for row in summary_rows:
                guessed_mas = parse_yes_no(row[27] if len(row) > 27 else None)
                if guessed_mas is None:
                    continue
                signature = row_signature(row)
                cognitive_level = (
                    bloom_queues[signature].popleft()
                    if bloom_queues[signature]
                    else None
                )
                item_type = type_queues[signature].popleft() if type_queues[signature] else None
                if cognitive_level is None:
                    raise ValueError(
                        f"Could not align a cognitive level for {path.name}/{summary_sheet}."
                    )
                item_no = int(row[1])
                item_type = item_type or normalize_item_type(row[0]) or "Unknown"
                base_key = (item_type, item_no)
                occurrence[base_key] += 1
                item_key = f"{source}_{item_type}_{item_no:03d}_{occurrence[base_key]}"
                component_values = [
                    float(value)
                    for value in list(row[2:9]) + list(row[10:26])
                    if isinstance(value, (int, float))
                ]
                records.append(
                    {
                        "expert": expert,
                        "source_true": source,
                        "item_key": item_key,
                        "item_no": item_no,
                        "item_type": item_type,
                        "cognitive_level": cognitive_level,
                        "guessed_mas": guessed_mas,
                        "correct_source_guess": int(
                            (source == "MAS" and guessed_mas == 1)
                            or (source == "Human" and guessed_mas == 0)
                        ),
                        "quality_score": float(np.mean(component_values)),
                    }
                )
    result = pd.DataFrame(records)
    expected = len(expert_files()) * 140
    if len(result) != expected:
        raise ValueError(f"Parsed {len(result)} expert judgments; expected {expected}.")
    return result


# ---------------------------------------------------------------------------
# Figure 1


def figure1a() -> None:
    inventory = json.loads((DERIVED / "data_inventory.json").read_text(encoding="utf-8"))
    fig, ax = plt.subplots(figsize=(6.6, 3.5))
    add_panel_label(fig, "A")
    ax.set_xlim(0, 13)
    ax.set_ylim(0, 6)
    ax.axis("off")
    rounded_box(
        ax,
        (0.3, 4.55),
        (3.0, 0.9),
        "Human expert bank",
        f"n={inventory['human_bank_records_total']}",
        CORE_FILLS["Human"],
        CORE_COLORS["Human"],
    )
    rounded_box(
        ax,
        (0.3, 3.15),
        (3.0, 0.9),
        "Authorized references",
        "Guidelines, textbook, syllabus",
        OPTIONAL_COLOR_PAIRS[1]["fill"],
        OPTIONAL_COLOR_PAIRS[1]["color"],
    )
    rounded_box(
        ax,
        (0.3, 1.75),
        (3.0, 0.9),
        "Blueprint constraints",
        "Item type and cognitive level",
        OPTIONAL_COLOR_PAIRS[3]["fill"],
        OPTIONAL_COLOR_PAIRS[3]["color"],
    )
    rounded_box(
        ax,
        (4.25, 4.1),
        (2.6, 0.9),
        "Batch builder",
        "Prompted item generation",
        CORE_FILLS["MAS"],
        CORE_COLORS["MAS"],
    )
    rounded_box(
        ax,
        (7.55, 4.1),
        (2.5, 0.9),
        "MAS generation",
        "Structured JSON output",
        CORE_FILLS["MAS"],
        CORE_COLORS["MAS"],
    )
    rounded_box(
        ax,
        (5.0, 2.65),
        (4.3, 0.9),
        "Answer, explanation, and test-point pass",
        "Traceable item IDs",
        OPTIONAL_COLOR_PAIRS[2]["fill"],
        OPTIONAL_COLOR_PAIRS[2]["color"],
    )
    rounded_box(
        ax,
        (5.0, 1.15),
        (4.3, 0.9),
        "MAS candidate bank",
        f"n={inventory['mas_bank_records_total']}",
        CORE_FILLS["MAS"],
        CORE_COLORS["MAS"],
    )
    for start, end, color in [
        ((3.35, 5.0), (4.18, 4.65), CORE_COLORS["Human"]),
        ((3.35, 3.6), (4.18, 4.55), OPTIONAL_COLOR_PAIRS[1]["color"]),
        ((3.35, 2.2), (4.18, 4.45), OPTIONAL_COLOR_PAIRS[3]["color"]),
        ((6.9, 4.55), (7.48, 4.55), CORE_COLORS["MAS"]),
        ((8.8, 4.05), (7.8, 3.6), CORE_COLORS["MAS"]),
        ((7.15, 2.6), (7.15, 2.1), CORE_COLORS["MAS"]),
    ]:
        arrow(ax, start, end, color)
    ax.set_title("Inputs and MAS generation workflow", pad=8, fontweight="bold")
    save_pdf(fig, "Figure1A_workflow_inputs.pdf", tight=False)


def figure1b() -> None:
    safety = pd.read_csv(DERIVED / "machine_safety_screening_summary.csv")
    domains = [
        ("guideline_consistency_pass_rate", "Guideline consistency"),
        ("single_best_answer_pass_rate", "Single best answer"),
        ("answer_key_validation_pass_rate", "Answer-key validation"),
        ("distractor_effectiveness_pass_rate", "Distractor effectiveness"),
        ("stem_ambiguity_control_pass_rate", "Stem ambiguity control"),
    ]
    fig, ax = plt.subplots(figsize=(4.7, 3.0))
    add_panel_label(fig, "B")
    y = np.arange(len(domains))[::-1]
    for source, offset in [("Human", 0.12), ("MAS", -0.12)]:
        means = [
            safety.loc[safety.source_true.eq(source), column].astype(float).mean() * 100
            for column, _ in domains
        ]
        ax.scatter(
            means,
            y + offset,
            color=CORE_COLORS[source],
            facecolor=CORE_FILLS[source],
            edgecolor=CORE_COLORS[source],
            label=source,
            zorder=3,
        )
    ax.set_yticks(y, [label for _, label in domains])
    ax.set_xlim(0, 103)
    ax.set_xlabel("Items passing machine safety screen (%)")
    ax.set_title("Machine safety-screening domains", fontweight="bold")
    ax.legend(frameon=False, loc="lower right")
    style_axes(ax, "x")
    save_pdf(fig, "Figure1B_safety_gate.pdf")


def figure1c() -> None:
    assign = pd.read_csv(DERIVED / "exam_form_assignment.csv")
    counts = assign.form.value_counts().to_dict()
    fig, ax = plt.subplots(figsize=(4.8, 2.4))
    add_panel_label(fig, "C")
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 5)
    ax.axis("off")
    for y, form, first, second in [
        (3.1, "A", "Human block", "MAS block"),
        (1.3, "B", "MAS block", "Human block"),
    ]:
        pair = FORM_COLORS[form]
        rounded_box(ax, (0.35, y), (1.7, 0.75), f"Form {form}", f"n={counts.get(form, 0)}", pair["fill"], pair["color"])
        first_source = "Human" if first.startswith("Human") else "MAS"
        second_source = "Human" if second.startswith("Human") else "MAS"
        rounded_box(ax, (2.8, y), (2.3, 0.75), first, "First", CORE_FILLS[first_source], CORE_COLORS[first_source])
        rounded_box(ax, (6.1, y), (2.3, 0.75), second, "Second", CORE_FILLS[second_source], CORE_COLORS[second_source])
        arrow(ax, (2.1, y + 0.38), (2.72, y + 0.38), pair["color"])
        arrow(ax, (5.15, y + 0.38), (6.02, y + 0.38))
    ax.set_title("Randomized two-sequence examination", fontweight="bold")
    save_pdf(fig, "Figure1C_two_sequence_order.pdf", tight=False)


def figure1d() -> None:
    assign = pd.read_csv(DERIVED / "exam_form_assignment.csv")
    counts = assign.training_setting.value_counts()
    labels = ["Main campus", "Non-main campus"]
    values = [counts.get("main", 0), counts.get("non_main", 0)]
    colors = [OPTIONAL_COLOR_PAIRS[3], OPTIONAL_COLOR_PAIRS[4]]
    fig, ax = plt.subplots(figsize=(2.8, 2.4))
    add_panel_label(fig, "D")
    bars = ax.bar(
        labels,
        values,
        color=[pair["fill"] for pair in colors],
        edgecolor=[pair["color"] for pair in colors],
        linewidth=1,
    )
    ax.bar_label(bars, padding=2)
    ax.set_ylabel("Students")
    ax.set_ylim(0, max(values) + 7)
    ax.tick_params(axis="x", rotation=18)
    ax.set_title("Training setting", fontweight="bold")
    style_axes(ax)
    save_pdf(fig, "Figure1D_training_setting.pdf")


def figure1e() -> None:
    fig, ax = plt.subplots(figsize=(3.0, 2.6))
    add_panel_label(fig, "E")
    ax.set_xlim(0, 4)
    ax.set_ylim(0, 5)
    ax.axis("off")
    rounded_box(
        ax,
        (0.25, 0.55),
        (3.5, 3.8),
        "Endpoint domains",
        "Expert quality\nMajor/critical defects\nCognitive-level performance\nSource detectability\nStudent performance",
        OPTIONAL_COLOR_PAIRS[4]["fill"],
        OPTIONAL_COLOR_PAIRS[4]["color"],
    )
    save_pdf(fig, "Figure1E_endpoint_domains.pdf", tight=False)


# ---------------------------------------------------------------------------
# Figure 2: 2A reserved; old 2A->2B, old 2B->2C, old 3A->2D


def figure2a() -> None:
    """Reserved empty panel after renumbering."""
    remove_output("Figure2A_quality_difference.pdf")


def parse_primary_quality_records() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in expert_files():
        with ZipFile(path) as zf:
            sheets = workbook_sheet_map(zf)
        for source, sheet_name in [
            ("Human", P_SUMMARY),
            ("MAS", M_MERGED if M_MERGED in sheets else M_SUMMARY),
        ]:
            item_rows = [row for row in read_sheet_rows(path, sheet_name) if is_rating_row(row)]
            if len(item_rows) != 70:
                raise ValueError(f"{path.name}/{sheet_name}: expected 70 rows, found {len(item_rows)}.")
            for seq, row in enumerate(item_rows, start=1):
                records.append(
                    {
                        "expert_file": path.name,
                        "source": source,
                        "item_seq": seq,
                        "qg_total": float(row[9]),
                        "ulm_total": float(row[26]),
                    }
                )
    return records


def item_means(records: Sequence[dict[str, Any]], metric: str) -> dict[str, np.ndarray]:
    arrays: dict[str, np.ndarray] = {}
    for source in ["Human", "MAS"]:
        grouped: dict[int, list[float]] = defaultdict(list)
        for record in records:
            if record["source"] == source:
                grouped[int(record["item_seq"])].append(float(record[metric]))
        arrays[source] = np.array([np.mean(grouped[index]) for index in sorted(grouped)])
    return arrays


def figure2b() -> None:
    records = parse_primary_quality_records()
    rows = []
    for endpoint, metric, scale_points, margin in [
        ("QGval", "qg_total", 35, -2.0),
        ("ULM", "ulm_total", 76, -4.0),
    ]:
        arrays = item_means(records, metric)
        human, mas = arrays["Human"], arrays["MAS"]
        diff = float(mas.mean() - human.mean())
        se = math.sqrt(mas.var(ddof=1) / len(mas) + human.var(ddof=1) / len(human))
        rows.append(
            {
                "endpoint": endpoint,
                "scale_points": scale_points,
                "ni_margin": margin,
                "n_per_group": len(mas),
                "mas_mean": mas.mean(),
                "mas_sd": mas.std(ddof=1),
                "human_mean": human.mean(),
                "human_sd": human.std(ddof=1),
                "diff": diff,
                "ci_low": diff - Z_975 * se,
                "ci_high": diff + Z_975 * se,
            }
        )
    stats_df = pd.DataFrame(rows)
    write_csv(DERIVED / "fig2B_quality_difference_stats.csv", stats_df)

    fig, ax = plt.subplots(figsize=(6.2, 3.35))
    add_panel_label(fig, "B")
    y = np.array([1.0, 0.0])
    for index, row in stats_df.iterrows():
        pair = OPTIONAL_COLOR_PAIRS[index]
        ax.axvspan(
            ax.get_xlim()[0] if ax.get_xlim()[0] < row.ni_margin else -5.3,
            row.ni_margin,
            ymin=max(0.0, (y[index] - 0.27) / 1.5),
            ymax=min(1.0, (y[index] + 0.42) / 1.5),
            color=pair["fill"],
            alpha=0.7,
            zorder=0,
        )
        ax.vlines(row.ni_margin, y[index] - 0.28, y[index] + 0.28, color=pair["color"], linestyle="--", linewidth=1.2)
        ax.errorbar(
            row["diff"],
            y[index],
            xerr=[[row["diff"] - row["ci_low"]], [row["ci_high"] - row["diff"]]],
            fmt="D",
            color=UROMAS_BASE_COLORS["text_dark"],
            ecolor=UROMAS_BASE_COLORS["text_dark"],
            capsize=4,
            markersize=5,
        )
        ax.text(
            row["diff"],
            y[index] + 0.20,
            f"{row['diff']:.2f} [{row['ci_low']:.2f}, {row['ci_high']:.2f}]",
            ha="center",
            va="bottom",
        )
    ax.axvline(0, color=UROMAS_BASE_COLORS["spine"], linewidth=1)
    ax.set_xlim(-5.2, 2.25)
    ax.set_ylim(-0.55, 1.55)
    ax.set_yticks(y, [f"{row.endpoint}\n(n=70/group)" for row in stats_df.itertuples()])
    ax.set_xlabel("Quality-score difference (MAS − Human)")
    ax.set_title("Primary endpoint non-inferiority", fontweight="bold")
    style_axes(ax, "x")
    save_pdf(fig, "Figure2B_quality_difference.pdf")


DIMENSIONS = [
    ("QGval", "Fluency", 5, 2),
    ("QGval", "Clarity", 5, 3),
    ("QGval", "Conciseness", 5, 4),
    ("QGval", "Relevance", 5, 5),
    ("QGval", "Consistency", 5, 6),
    ("QGval", "Answerability", 5, 7),
    ("QGval", "Answer consistency", 5, 8),
    ("ULM", "Fluency", 5, 10),
    ("ULM", "Exclusiveness", 5, 11),
    ("ULM", "Explicitness", 4, 12),
    ("ULM", "Goal alignment", 5, 13),
    ("ULM", "Comprehensiveness", 5, 14),
    ("ULM", "Focus", 5, 15),
    ("ULM", "Guess resistance", 5, 16),
    ("ULM", "Completeness", 5, 17),
    ("ULM", "Correctness", 5, 18),
    ("ULM", "Solvability", 5, 19),
    ("ULM", "Absoluteness", 5, 20),
    ("ULM", "Plausibility", 5, 21),
    ("ULM", "Reasoning", 4, 22),
    ("ULM", "Feedback", 5, 23),
    ("ULM", "Fairness", 3, 24),
    ("ULM", "Explanation score", 5, 25),
]


def figure2c() -> None:
    records: list[dict[str, Any]] = []
    for path in expert_files():
        with ZipFile(path) as zf:
            sheets = workbook_sheet_map(zf)
        for source, sheet_name in [
            ("Human", P_SUMMARY),
            ("MAS", M_MERGED if M_MERGED in sheets else M_SUMMARY),
        ]:
            item_rows = [row for row in read_sheet_rows(path, sheet_name) if is_rating_row(row)]
            for seq, row in enumerate(item_rows, start=1):
                for family, dimension, max_score, column in DIMENSIONS:
                    records.append(
                        {
                            "source": source,
                            "item_seq": seq,
                            "family": family,
                            "dimension": dimension,
                            "max_score": max_score,
                            "score": float(row[column]),
                        }
                    )
    data = pd.DataFrame(records)
    item_level = data.groupby(["source", "item_seq", "family", "dimension"], as_index=False).score.mean()
    summary = (
        item_level.groupby(["family", "dimension", "source"])
        .score.agg(["count", "mean", "std"])
        .reset_index()
    )
    write_csv(DERIVED / "fig2C_dimension_scores_item_scores.csv", item_level)
    write_csv(DERIVED / "fig2C_dimension_scores_stats.csv", summary)

    labels = [dimension for _, dimension, _, _ in DIMENSIONS]
    y = np.array([index if index < 7 else index + 0.7 for index in range(len(labels))])
    height = 0.34
    fig, ax = plt.subplots(figsize=(6.4, 7.9))
    add_panel_label(fig, "C")
    for source, offset in [("MAS", -0.18), ("Human", 0.18)]:
        means, sds = [], []
        for family, dimension, _, _ in DIMENSIONS:
            row = summary[
                summary.family.eq(family)
                & summary.dimension.eq(dimension)
                & summary.source.eq(source)
            ].iloc[0]
            means.append(float(row["mean"]))
            sds.append(float(row["std"]))
        ax.barh(
            y + offset,
            means,
            height=height,
            color=CORE_COLORS[source],
            label=source,
            alpha=0.9,
        )
        ax.errorbar(means, y + offset, xerr=sds, fmt="none", ecolor=UROMAS_BASE_COLORS["text_dark"], capsize=2, linewidth=0.8)
    ax.axhline((y[6] + y[7]) / 2, color=UROMAS_BASE_COLORS["soft_separator"], linewidth=0.8)
    ax.set_yticks(y, labels)
    ax.invert_yaxis()
    ax.set_xlim(1, 5.8)
    ax.set_xlabel("Mean expert rating (raw rubric scale)")
    ax.set_title("Per-dimension human-expert scores", fontweight="bold")
    ax.legend(frameon=False, ncol=2, loc="lower right")
    style_axes(ax, "x")
    save_pdf(fig, "Figure2C_dimension_scores.pdf")


def figure2d() -> None:
    level_map = [("记忆", "Knowledge"), ("理解", "Comprehension"), ("应用", "Application"), ("分析", "Analysis")]
    metric_specs = {
        "QGval": {"column": 9, "scale": 7.0, "margin": -0.30, "pair": OPTIONAL_COLOR_PAIRS[0]},
        "ULM": {"column": 26, "scale": 16.0, "margin": -0.25, "pair": OPTIONAL_COLOR_PAIRS[1]},
    }
    records: list[dict[str, Any]] = []
    for path in expert_files():
        for source, sheet_name in [("Human", P_BLOOM), ("MAS", M_BLOOM)]:
            rows = read_sheet_rows(path, sheet_name)
            current_level: str | None = None
            seq = 0
            for row in rows:
                if row and row[0] in dict(level_map):
                    current_level = str(row[0])
                if is_rating_row(row):
                    seq += 1
                    for metric, spec in metric_specs.items():
                        records.append(
                            {
                                "source": source,
                                "cognitive_level": current_level,
                                "item_seq": seq,
                                "metric": metric,
                                "score": float(row[spec["column"]]) / spec["scale"],
                            }
                        )
    data = pd.DataFrame(records)
    item_level = data.groupby(["source", "cognitive_level", "item_seq", "metric"], as_index=False).score.mean()
    stat_rows = []
    for level, label in level_map:
        for metric, spec in metric_specs.items():
            sub = item_level[item_level.cognitive_level.eq(level) & item_level.metric.eq(metric)]
            mas = sub.loc[sub.source.eq("MAS"), "score"].to_numpy()
            human = sub.loc[sub.source.eq("Human"), "score"].to_numpy()
            diff = mas.mean() - human.mean()
            se = math.sqrt(mas.var(ddof=1) / len(mas) + human.var(ddof=1) / len(human))
            stat_rows.append(
                {
                    "cognitive_level": level,
                    "cognitive_level_label": label,
                    "metric": metric,
                    "n_mas": len(mas),
                    "n_human": len(human),
                    "diff": diff,
                    "ci_low": diff - Z_975 * se,
                    "ci_high": diff + Z_975 * se,
                    "ni_margin": spec["margin"],
                }
            )
    stats_df = pd.DataFrame(stat_rows)
    write_csv(DERIVED / "fig2D_quality_by_cognitive_level_stats.csv", stats_df)
    write_csv(DERIVED / "fig2D_quality_by_cognitive_level_item_scores.csv", item_level)

    fig, ax = plt.subplots(figsize=(6.1, 3.6))
    add_panel_label(fig, "D")
    y = np.arange(len(level_map))
    for metric, offset in [("QGval", -0.08), ("ULM", 0.08)]:
        spec = metric_specs[metric]
        sub = stats_df[stats_df.metric.eq(metric)]
        ax.axvline(spec["margin"], color=spec["pair"]["color"], linestyle="--", linewidth=1)
        ax.errorbar(
            sub["diff"],
            y + offset,
            xerr=[sub["diff"] - sub["ci_low"], sub["ci_high"] - sub["diff"]],
            fmt="o",
            color=spec["pair"]["color"],
            ecolor=spec["pair"]["color"],
            capsize=3,
            label=metric,
        )
    ax.axvline(0, color=UROMAS_BASE_COLORS["spine"], linewidth=1)
    ax.set_yticks(y, [label for _, label in level_map])
    ax.invert_yaxis()
    ax.set_xlim(-0.43, 0.60)
    ax.set_xlabel("Mean quality-score difference (MAS − Human)")
    ax.set_title("Expert quality gap by cognitive level", fontweight="bold")
    ax.legend(frameon=False, ncol=2)
    style_axes(ax, "x")
    save_pdf(fig, "Figure2D_quality_by_cognitive_level.pdf")


def figure2e() -> None:
    summary = pd.read_csv(DERIVED / "machine_rating_summary.csv")
    fig, ax = plt.subplots(figsize=(3.0, 2.5))
    add_panel_label(fig, "E")
    rng = np.random.default_rng(20260621)
    for position, source in enumerate(["Human", "MAS"]):
        values = summary.loc[summary.source_true.eq(source), "machine_proxy_quality_score_sd"].dropna().to_numpy()
        ax.scatter(
            rng.normal(position, 0.045, len(values)),
            values,
            color=CORE_COLORS[source],
            s=12,
            alpha=0.55,
            linewidths=0,
        )
        mean, low, high = bootstrap_mean_ci(values, seed=position + 70)
        ax.errorbar(position, mean, yerr=[[mean - low], [high - mean]], fmt="D", color=UROMAS_BASE_COLORS["text_dark"], capsize=3)
    ax.set_xticks([0, 1], ["Human", "MAS"])
    ax.set_ylabel("Run-to-run SD")
    ax.set_title("Machine-rating run consistency", fontweight="bold")
    style_axes(ax)
    save_pdf(fig, "Figure2E_run_consistency.pdf")


# ---------------------------------------------------------------------------
# Figure 3


def figure3a() -> None:
    """Reserved empty panel after Figure 3A moved to Figure 2D."""
    remove_output("Figure3A_quality_by_cognitive_level.pdf")


def paired_comparison(mas: np.ndarray, human: np.ndarray) -> tuple[str, float, str]:
    diff = np.asarray(mas, dtype=float) - np.asarray(human, dtype=float)
    if len(diff) < 3 or np.std(diff, ddof=1) == 0:
        p_value = 1.0
        method = "Paired comparison"
    else:
        normal_p = stats.shapiro(diff).pvalue
        if normal_p >= 0.05:
            result = stats.ttest_rel(mas, human)
            p_value = float(result.pvalue)
            method = "Paired t-test"
        else:
            try:
                result = stats.wilcoxon(mas, human, zero_method="wilcox")
                p_value = float(result.pvalue)
            except ValueError:
                p_value = 1.0
            method = "Wilcoxon signed-rank"
    label = "***" if p_value < 0.001 else "**" if p_value < 0.01 else "*" if p_value < 0.05 else "n.s."
    return method, p_value, label


def figure3b() -> None:
    block = pd.read_csv(DERIVED / "block_scores.csv")
    panels = [
        ("Overall", block),
        ("Main campus", block[block.training_setting.eq("main")]),
        ("Non-main campus", block[block.training_setting.eq("non_main")]),
    ]
    raw_rows: list[dict[str, Any]] = []
    stat_rows: list[dict[str, Any]] = []
    for panel, data in panels:
        wide = data.pivot(index="student_id", columns="source_true", values="correct_rate").dropna()
        method, p_value, label = paired_comparison(wide["MAS"].to_numpy(), wide["Human"].to_numpy())
        stat_rows.append(
            {
                "panel": panel,
                "n_students": len(wide),
                "mas_mean": wide["MAS"].mean(),
                "mas_sd": wide["MAS"].std(ddof=1),
                "human_mean": wide["Human"].mean(),
                "human_sd": wide["Human"].std(ddof=1),
                "mean_difference_mas_minus_human": (wide["MAS"] - wide["Human"]).mean(),
                "method": method,
                "p_value": p_value,
                "significance_label": label,
            }
        )
        for student_id, row in wide.iterrows():
            for source in ["Human", "MAS"]:
                raw_rows.append({"panel": panel, "student_id": student_id, "source_true": source, "correct_rate": row[source]})
    write_csv(DERIVED / "fig3B_student_correct_rate_stats.csv", stat_rows)
    write_csv(DERIVED / "fig3B_student_correct_rate_raw.csv", raw_rows)

    fig, axes = plt.subplots(1, 3, figsize=(8.3, 3.2), sharey=True)
    add_panel_label(fig, "B")
    rng = np.random.default_rng(202606)
    for ax, stat_row in zip(axes, stat_rows):
        sub = pd.DataFrame(raw_rows)
        sub = sub[sub.panel.eq(stat_row["panel"])]
        for position, source in [(1, "MAS"), (2, "Human")]:
            values = sub.loc[sub.source_true.eq(source), "correct_rate"].to_numpy()
            violin = ax.violinplot([values], positions=[position], widths=0.55, showextrema=False)
            body = violin["bodies"][0]
            body.set_facecolor(CORE_FILLS[source])
            body.set_edgecolor(CORE_COLORS[source])
            body.set_alpha(0.9)
            q1, median, q3 = np.percentile(values, [25, 50, 75])
            ax.vlines(position, q1, q3, color=CORE_COLORS[source], linewidth=3)
            ax.scatter(rng.normal(position, 0.035, len(values)), values, s=9, color=CORE_COLORS[source], alpha=0.45, linewidths=0)
            ax.scatter(position, median, s=13, color=UROMAS_BASE_COLORS["text_dark"], zorder=4)
        ymax = max(sub.correct_rate.max() + 0.06, 0.86)
        ax.plot([1, 1, 2, 2], [ymax - 0.01, ymax, ymax, ymax - 0.01], color=UROMAS_BASE_COLORS["text_dark"], linewidth=0.8)
        ax.text(1.5, ymax + 0.012, stat_row["significance_label"], ha="center", fontweight="bold")
        ax.set_title(stat_row["panel"], fontweight="bold")
        ax.set_xticks([1, 2], ["MAS", "Human"])
        ax.set_ylim(0.2, 1.04)
        style_axes(ax)
    axes[0].set_ylabel("Correct response rate")
    fig.suptitle("Student overall correct rate by source", y=0.99, fontweight="bold")
    save_pdf(fig, "Figure3B_student_correct_rate.pdf")


def student_level_rates() -> pd.DataFrame:
    responses = pd.read_csv(DERIVED / "responses.csv")
    item = pd.read_csv(DERIVED / "item_master.csv")[["item_id", "blueprint_cognitive_level"]]
    data = responses.merge(item, on="item_id", how="left")
    return (
        data.groupby(
            ["student_id", "training_setting", "source_true", "blueprint_cognitive_level"],
            as_index=False,
        )
        .correct.agg(["count", "mean"])
        .reset_index()
        .rename(columns={"count": "n_items", "mean": "correct_rate"})
    )


def figure3c() -> None:
    rates = student_level_rates()
    panels = [
        ("Overall", rates),
        ("Main campus", rates[rates.training_setting.eq("main")]),
        ("Non-main campus", rates[rates.training_setting.eq("non_main")]),
    ]
    plot_rows: list[dict[str, Any]] = []
    for panel_index, (panel, data) in enumerate(panels):
        for level_index, level in enumerate(LEVELS_4):
            wide = (
                data[data.blueprint_cognitive_level.eq(level)]
                .pivot(index="student_id", columns="source_true", values="correct_rate")
                .dropna()
            )
            method, p_value, label = paired_comparison(wide["MAS"].to_numpy(), wide["Human"].to_numpy())
            for source_index, source in enumerate(["Human", "MAS"]):
                mean, low, high = bootstrap_mean_ci(
                    wide[source].to_numpy(),
                    seed=300 + panel_index * 20 + level_index * 2 + source_index,
                )
                plot_rows.append(
                    {
                        "panel": panel,
                        "cognitive_level": level,
                        "source_true": source,
                        "n_students": len(wide),
                        "mean_correct_rate": mean,
                        "ci_low": low,
                        "ci_high": high,
                        "comparison_method": method,
                        "p_value": p_value,
                        "significance_label": label,
                    }
                )
    plot_df = pd.DataFrame(plot_rows)
    write_csv(DERIVED / "fig3C_student_accuracy_horizontal_stats.csv", plot_df)
    write_csv(DERIVED / "fig3C_student_accuracy_student_rates.csv", rates)

    fig, axes = plt.subplots(1, 3, figsize=(9.0, 3.6), sharey=True)
    add_panel_label(fig, "C")
    y = np.arange(len(LEVELS_4))
    height = 0.34
    for ax, (panel, _) in zip(axes, panels):
        sub = plot_df[plot_df.panel.eq(panel)]
        for source, offset in [("Human", 0.18), ("MAS", -0.18)]:
            source_rows = sub[sub.source_true.eq(source)].set_index("cognitive_level").loc[LEVELS_4]
            means = source_rows.mean_correct_rate.to_numpy() * 100
            low = source_rows.ci_low.to_numpy() * 100
            high = source_rows.ci_high.to_numpy() * 100
            ax.barh(y + offset, means, height=height, color=CORE_COLORS[source], label=source)
            ax.errorbar(
                means,
                y + offset,
                xerr=[means - low, high - means],
                fmt="none",
                ecolor=UROMAS_BASE_COLORS["text_dark"],
                capsize=2,
                linewidth=0.8,
            )
        sig_rows = sub[sub.source_true.eq("Human")].set_index("cognitive_level").loc[LEVELS_4]
        for ypos, label in zip(y, sig_rows.significance_label):
            ax.text(103, ypos, label, ha="left", va="center", fontsize=7)
        ax.set_title(panel, fontweight="bold")
        ax.set_xlim(0, 112)
        ax.set_xlabel("Correct rate (%)")
        style_axes(ax, "x")
    axes[0].set_yticks(y, [LEVEL_LABELS_4[level] for level in LEVELS_4])
    axes[0].invert_yaxis()
    handles = [
        mpl.patches.Patch(color=CORE_COLORS["Human"], label="Human"),
        mpl.patches.Patch(color=CORE_COLORS["MAS"], label="MAS"),
    ]
    fig.legend(handles=handles, frameon=False, ncol=2, loc="lower center", bbox_to_anchor=(0.5, 0.005))
    fig.suptitle("Student correct rate by cognitive level", y=0.99, fontweight="bold")
    fig.tight_layout(rect=[0, 0.08, 1, 0.93])
    save_pdf(fig, "Figure3C_student_accuracy_by_cognitive_level.pdf", tight=False)


def adjusted_interaction_data() -> tuple[pd.DataFrame, pd.DataFrame, str]:
    responses = pd.read_csv(DERIVED / "responses.csv")
    item = pd.read_csv(DERIVED / "item_master.csv")[
        ["item_id", "blueprint_cognitive_level", "topic"]
    ]
    data = responses.merge(item, on="item_id", how="left")
    formula = (
        "correct ~ C(source_true) * C(blueprint_cognitive_level)"
        " + C(block_position) + C(training_setting) + C(training_year)"
        " + C(form) + C(topic)"
    )
    fit = smf.glm(formula, data=data, family=sm.families.Binomial()).fit(
        cov_type="cluster",
        cov_kwds={"groups": data["student_id"]},
    )
    if not fit.converged:
        raise RuntimeError("Figure 3D adjusted binomial GLM did not converge.")
    data = data.copy()
    data["fitted_probability"] = fit.predict(data)
    data["response_residual"] = data["correct"] - data["fitted_probability"]

    adjusted_rows: list[dict[str, Any]] = []
    contrast_rows: list[dict[str, Any]] = []
    design_info = fit.model.data.design_info
    beta = np.asarray(fit.params)
    covariance = np.asarray(fit.cov_params())

    for level in LEVELS_4:
        scenario_design: dict[str, np.ndarray] = {}
        scenario_probability: dict[str, np.ndarray] = {}
        for source in ["Human", "MAS"]:
            scenario = data.copy()
            scenario["source_true"] = source
            scenario["blueprint_cognitive_level"] = level
            matrix = np.asarray(build_design_matrices([design_info], scenario)[0])
            probability = 1.0 / (1.0 + np.exp(-(matrix @ beta)))
            scenario_design[source] = matrix
            scenario_probability[source] = probability
            marginal_by_student = (
                pd.DataFrame({"student_id": data.student_id, "probability": probability})
                .groupby("student_id")
                .probability.mean()
            )
            actual = data[
                data.source_true.eq(source)
                & data.blueprint_cognitive_level.eq(level)
            ]
            residual_by_student = actual.groupby("student_id").response_residual.mean()
            adjusted = (marginal_by_student + residual_by_student).clip(0, 1)
            for student_id, value in adjusted.dropna().items():
                adjusted_rows.append(
                    {
                        "student_id": student_id,
                        "source_true": source,
                        "cognitive_level": level,
                        "adjusted_correct_probability": value,
                    }
                )

        p_mas = scenario_probability["MAS"]
        p_human = scenario_probability["Human"]
        estimate = float(np.mean(p_mas - p_human))
        gradient = np.mean(
            p_mas[:, None] * (1 - p_mas[:, None]) * scenario_design["MAS"]
            - p_human[:, None] * (1 - p_human[:, None]) * scenario_design["Human"],
            axis=0,
        )
        se = float(math.sqrt(max(gradient @ covariance @ gradient.T, 0.0)))
        z_value = estimate / se if se > 0 else float("nan")
        p_value = float(2 * stats.norm.sf(abs(z_value))) if np.isfinite(z_value) else float("nan")
        contrast_rows.append(
            {
                "cognitive_level": level,
                "estimate_mas_minus_human": estimate,
                "se": se,
                "ci_low": estimate - Z_975 * se,
                "ci_high": estimate + Z_975 * se,
                "p_value": p_value,
                "n_students": data.student_id.nunique(),
                "n_responses": len(data),
                "model_formula": formula,
                "covariance": "cluster-robust by student",
            }
        )
    return pd.DataFrame(adjusted_rows), pd.DataFrame(contrast_rows), formula


def figure3d() -> None:
    adjusted, contrasts, _ = adjusted_interaction_data()
    write_csv(DERIVED / "fig3D_adjusted_student_probabilities.csv", adjusted)
    write_csv(DERIVED / "fig3D_source_cognitive_interaction_contrasts.csv", contrasts)

    fig, ax = plt.subplots(figsize=(7.0, 4.0))
    add_panel_label(fig, "D")
    x = np.arange(len(LEVELS_4), dtype=float)
    offsets = {"Human": -0.18, "MAS": 0.18}
    width = 0.30
    mean_lines: dict[str, list[float]] = {}
    for source in ["Human", "MAS"]:
        groups = [
            adjusted[
                adjusted.source_true.eq(source)
                & adjusted.cognitive_level.eq(level)
            ].adjusted_correct_probability.to_numpy()
            for level in LEVELS_4
        ]
        positions = x + offsets[source]
        box = ax.boxplot(
            groups,
            positions=positions,
            widths=width,
            patch_artist=True,
            showfliers=False,
            medianprops={"color": UROMAS_BASE_COLORS["text_dark"], "linewidth": 1},
            whiskerprops={"color": CORE_COLORS[source], "linewidth": 0.8},
            capprops={"color": CORE_COLORS[source], "linewidth": 0.8},
        )
        for patch in box["boxes"]:
            patch.set_facecolor(CORE_FILLS[source])
            patch.set_edgecolor(CORE_COLORS[source])
        means = [float(np.mean(group)) for group in groups]
        mean_lines[source] = means
        ax.plot(
            positions,
            means,
            color=CORE_COLORS[source],
            marker="o",
            linewidth=1.5,
            markersize=4,
            label=source,
            zorder=4,
        )
    for index, row in contrasts.iterrows():
        p_value = row["p_value"]
        label = "P<0.001" if p_value < 0.001 else f"P={p_value:.3f}"
        upper = max(
            adjusted[adjusted.cognitive_level.eq(row.cognitive_level)].adjusted_correct_probability.max(),
            mean_lines["Human"][index],
            mean_lines["MAS"][index],
        )
        ax.text(index, min(1.03, upper + 0.05), label, ha="center", va="bottom", fontsize=7)
    ax.set_xticks(x, [LEVEL_LABELS_4[level] for level in LEVELS_4])
    ax.set_ylim(0.18, 1.08)
    ax.set_ylabel("Adjusted correct-answer probability")
    ax.set_title("Adjusted source × cognitive-level interaction", fontweight="bold")
    ax.legend(frameon=False, ncol=2, loc="lower left")
    style_axes(ax)
    save_pdf(fig, "Figure3D_source_cognitive_interaction.pdf")


def ctt_upper_lower_data() -> pd.DataFrame:
    responses = pd.read_csv(DERIVED / "responses.csv")
    item = pd.read_csv(DERIVED / "item_master.csv")[
        ["item_id", "source_true", "blueprint_cognitive_level"]
    ]
    matrix = responses.pivot(index="student_id", columns="item_id", values="correct")
    total_score = matrix.sum(axis=1)
    group_n = int(math.ceil(0.27 * len(total_score)))
    upper = total_score.sort_values(ascending=False).head(group_n).index
    lower = total_score.sort_values(ascending=True).head(group_n).index
    rows = []
    for item_id in matrix.columns:
        rows.append(
            {
                "item_id": item_id,
                "n_responses": int(matrix[item_id].notna().sum()),
                "difficulty": float(matrix[item_id].mean()),
                "upper_27_correct_rate": float(matrix.loc[upper, item_id].mean()),
                "lower_27_correct_rate": float(matrix.loc[lower, item_id].mean()),
                "discrimination_upper_minus_lower": float(
                    matrix.loc[upper, item_id].mean() - matrix.loc[lower, item_id].mean()
                ),
                "upper_group_n": group_n,
                "lower_group_n": group_n,
            }
        )
    return pd.DataFrame(rows).merge(item, on="item_id", how="left")


def grouped_boxplot_with_means(
    ax: plt.Axes,
    data: pd.DataFrame,
    value_column: str,
    ylabel: str,
) -> None:
    x = np.arange(len(LEVELS_4), dtype=float)
    offsets = {"Human": -0.18, "MAS": 0.18}
    for source in ["Human", "MAS"]:
        groups = [
            data[
                data.source_true.eq(source)
                & data.blueprint_cognitive_level.eq(level)
            ][value_column].to_numpy()
            for level in LEVELS_4
        ]
        positions = x + offsets[source]
        box = ax.boxplot(
            groups,
            positions=positions,
            widths=0.30,
            patch_artist=True,
            showfliers=False,
            medianprops={"color": UROMAS_BASE_COLORS["text_dark"], "linewidth": 1},
            whiskerprops={"color": CORE_COLORS[source], "linewidth": 0.8},
            capprops={"color": CORE_COLORS[source], "linewidth": 0.8},
        )
        for patch in box["boxes"]:
            patch.set_facecolor(CORE_FILLS[source])
            patch.set_edgecolor(CORE_COLORS[source])
        means = [np.mean(group) for group in groups]
        ax.plot(positions, means, color=CORE_COLORS[source], marker="o", linewidth=1.3, markersize=3.5, label=source)
    ax.set_xticks(x, [LEVEL_LABELS_4[level] for level in LEVELS_4], rotation=18, ha="right")
    ax.set_ylabel(ylabel)
    style_axes(ax)


def figure3e() -> None:
    ctt = ctt_upper_lower_data()
    summary = (
        ctt.groupby(["source_true", "blueprint_cognitive_level"])
        .agg(
            n_items=("item_id", "count"),
            mean_difficulty=("difficulty", "mean"),
            sd_difficulty=("difficulty", "std"),
            mean_discrimination=("discrimination_upper_minus_lower", "mean"),
            sd_discrimination=("discrimination_upper_minus_lower", "std"),
        )
        .reset_index()
    )
    write_csv(DERIVED / "fig3E_ctt_upper_lower_item_data.csv", ctt)
    write_csv(DERIVED / "fig3E_ctt_by_cognitive_level_summary.csv", summary)

    fig, axes = plt.subplots(1, 2, figsize=(8.0, 3.7))
    add_panel_label(fig, "E")
    grouped_boxplot_with_means(axes[0], ctt, "difficulty", "Correct-answer rate")
    axes[0].set_ylim(0, 1.02)
    axes[0].set_title("Item difficulty", fontweight="bold")
    grouped_boxplot_with_means(
        axes[1],
        ctt,
        "discrimination_upper_minus_lower",
        "Discrimination (upper 27% − lower 27%)",
    )
    axes[1].axhline(0, color=UROMAS_BASE_COLORS["spine"], linewidth=0.8)
    axes[1].set_title("Upper–lower discrimination", fontweight="bold")
    axes[1].legend(frameon=False, ncol=2, loc="lower right")
    fig.suptitle("Classical test theory by cognitive level", y=0.99, fontweight="bold")
    save_pdf(fig, "Figure3E_ctt_by_cognitive_level.pdf")


def cronbach_alpha(matrix: np.ndarray) -> float:
    values = np.asarray(matrix, dtype=float)
    k = values.shape[1]
    if k < 2:
        return float("nan")
    total_variance = values.sum(axis=1).var(ddof=1)
    if total_variance <= 0:
        return float("nan")
    return float(
        k / (k - 1)
        * (1 - values.var(axis=0, ddof=1).sum() / total_variance)
    )


def figure3f() -> None:
    responses = pd.read_csv(DERIVED / "responses.csv")
    matrix = responses.pivot(index="student_id", columns="item_id", values="correct")
    rng = np.random.default_rng(20260306)
    rows = []
    specifications = [
        ("Overall examination", list(matrix.columns), OPTIONAL_COLOR_PAIRS[0]["color"]),
        ("Human block", [column for column in matrix.columns if column.startswith("H")], CORE_COLORS["Human"]),
        ("UroEMAS block", [column for column in matrix.columns if column.startswith("M")], CORE_COLORS["MAS"]),
    ]
    for label, columns, color in specifications:
        values = matrix[columns].to_numpy(dtype=float)
        estimate = cronbach_alpha(values)
        boots = []
        for _ in range(3000):
            sample_index = rng.integers(0, len(values), len(values))
            alpha = cronbach_alpha(values[sample_index])
            if np.isfinite(alpha):
                boots.append(alpha)
        low, high = np.quantile(boots, [0.025, 0.975])
        rows.append(
            {
                "scale": label,
                "n_students": values.shape[0],
                "n_items": values.shape[1],
                "kr20_cronbach_alpha": estimate,
                "ci_low": low,
                "ci_high": high,
                "bootstrap_reps": len(boots),
                "color": color,
            }
        )
    stats_df = pd.DataFrame(rows)
    write_csv(DERIVED / "fig3F_reliability_bootstrap_ci.csv", stats_df.drop(columns="color"))

    fig, ax = plt.subplots(figsize=(5.7, 2.7))
    add_panel_label(fig, "F")
    y = np.arange(len(stats_df))[::-1]
    for ypos, row in zip(y, stats_df.itertuples()):
        ax.errorbar(
            row.kr20_cronbach_alpha,
            ypos,
            xerr=[
                [row.kr20_cronbach_alpha - row.ci_low],
                [row.ci_high - row.kr20_cronbach_alpha],
            ],
            fmt="o",
            color=row.color,
            ecolor=row.color,
            capsize=3,
            markersize=5,
        )
        ax.text(row.ci_high + 0.015, ypos, f"{row.kr20_cronbach_alpha:.2f}", va="center")
    ax.axvline(0.70, color=UROMAS_BASE_COLORS["spine"], linestyle=":", linewidth=0.9)
    ax.set_yticks(y, stats_df.scale)
    ax.set_xlim(0, 1.02)
    ax.set_xticks([0.0, 0.5, 0.7, 1.0])
    ax.set_xlabel("KR-20 / Cronbach's alpha (95% bootstrap CI)")
    ax.set_title("Internal consistency reliability", fontweight="bold")
    style_axes(ax, "x")
    save_pdf(fig, "Figure3F_reliability.pdf")


# ---------------------------------------------------------------------------
# Figure 4: 4A reserved; old 4A->4B, old 4B->4C, new 4D and 4E


def figure4a() -> None:
    """Reserved empty panel after renumbering."""
    remove_output("Figure4A_source_detection_accuracy.pdf")


def accuracy_band_axis(ax: plt.Axes) -> None:
    loose = OPTIONAL_COLOR_PAIRS[3]["fill"]
    strict = OPTIONAL_COLOR_PAIRS[5]["fill"]
    ax.axvspan(40, 45, color=loose, alpha=0.95, zorder=0)
    ax.axvspan(45, 55, color=strict, alpha=0.95, zorder=0)
    ax.axvspan(55, 60, color=loose, alpha=0.95, zorder=0)
    ax.axvline(50, color=UROMAS_BASE_COLORS["text_dark"], linewidth=0.8)
    ax.set_xlim(0, 100)
    ax.set_xlabel("Source-identification accuracy (%)")
    style_axes(ax, "x")


def figure4b(expert_judgments: pd.DataFrame) -> None:
    rows = []
    for path in expert_files():
        expert_match = re.search(r"专家\s*(\d+)", path.name)
        expert = f"Expert {expert_match.group(1)}" if expert_match else path.stem
        turing_rows = read_sheet_rows(path, "图灵测试")
        summary_row = next(
            (
                row
                for row in turing_rows
                if row
                and isinstance(row[0], str)
                and "总正确率" in row[0]
                and len(row) > 1
                and isinstance(row[1], (int, float))
            ),
            None,
        )
        if summary_row is None:
            raise ValueError(f"{path.name}/图灵测试 lacks a total-accuracy row.")
        correct = int(summary_row[1])
        # The 图灵测试 sheet contains 70 Human and 70 MAS judgments. One
        # workbook has a denominator typo in its display string, so use the
        # actual design denominator rather than the formatted text.
        n = 140
        low, high = proportion_confint(correct, n, alpha=0.10, method="wilson")
        rows.append(
            {
                "expert": expert,
                "correct": correct,
                "n": n,
                "accuracy": correct / n,
                "ci_low": low,
                "ci_high": high,
            }
        )
    stats_df = pd.DataFrame(rows)
    write_csv(DERIVED / "fig4B_expert_source_identification_accuracy.csv", stats_df)

    fig = plt.figure(figsize=(8.5, 3.0))
    add_panel_label(fig, "B")
    grid = fig.add_gridspec(1, 2, width_ratios=[1.45, 1.25], wspace=0.08)
    ax = fig.add_subplot(grid[0, 0])
    table_ax = fig.add_subplot(grid[0, 1])
    colors = [OPTIONAL_COLOR_PAIRS[index]["color"] for index in [0, 1, 3]]
    y = np.arange(len(stats_df))[::-1]
    accuracy_band_axis(ax)
    for ypos, row, color in zip(y, stats_df.itertuples(), colors):
        estimate = row.accuracy * 100
        ax.errorbar(
            estimate,
            ypos,
            xerr=[[estimate - row.ci_low * 100], [row.ci_high * 100 - estimate]],
            fmt="o",
            color=color,
            ecolor=color,
            capsize=3,
            markersize=5,
        )
    ax.set_yticks(y, stats_df.expert)
    ax.set_title("Expert source-identification accuracy", fontweight="bold")
    table_ax.axis("off")
    cell_text = [
        [
            row.expert,
            f"{row.correct}/{row.n}",
            f"{row.accuracy*100:.1f}% ({row.ci_low*100:.1f}–{row.ci_high*100:.1f})",
        ]
        for row in stats_df.itertuples()
    ]
    table = table_ax.table(
        cellText=cell_text,
        colLabels=["Expert", "Correct/N", "Accuracy, 90% CI"],
        loc="center",
        cellLoc="center",
        colWidths=[0.25, 0.22, 0.53],
    )
    table.auto_set_font_size(False)
    table.set_fontsize(6.7)
    table.scale(1.0, 1.35)
    save_pdf(fig, "Figure4B_expert_source_identification_accuracy.pdf", tight=False)


def figure4c(expert_judgments: pd.DataFrame) -> None:
    counts = (
        expert_judgments.groupby(["source_true", "guessed_mas"])
        .size()
        .unstack(fill_value=0)
        .reindex(index=["Human", "MAS"], columns=[0, 1], fill_value=0)
    )
    counts.columns = ["Guessed Human", "Guessed MAS"]
    proportions = counts.div(counts.sum(axis=1), axis=0) * 100
    counts.reset_index().to_csv(DERIVED / "fig4C_expert_source_confusion_counts.csv", index=False, encoding="utf-8-sig")

    fig, ax = plt.subplots(figsize=(4.0, 3.0))
    add_panel_label(fig, "C")
    x = np.arange(2)
    bottom = np.zeros(2)
    for column, color in [
        ("Guessed Human", CORE_COLORS["Human"]),
        ("Guessed MAS", CORE_COLORS["MAS"]),
    ]:
        values = proportions[column].to_numpy()
        ax.bar(x, values, bottom=bottom, color=color, width=0.58, label=column)
        for xpos, value, base in zip(x, values, bottom):
            if value >= 7:
                ax.text(xpos, base + value / 2, f"{value:.1f}%", ha="center", va="center", color="white", fontsize=7)
        bottom += values
    ax.set_xticks(x, ["Human-authored items", "MAS-generated items"])
    ax.set_ylabel("Expert judgments (%)")
    ax.set_ylim(0, 100)
    ax.set_title("Expert source-judgment confusion matrix", fontweight="bold")
    ax.legend(frameon=False, ncol=2, loc="upper center", bbox_to_anchor=(0.5, -0.18))
    style_axes(ax)
    save_pdf(fig, "Figure4C_expert_source_confusion_matrix.pdf")


def figure4d(expert_judgments: pd.DataFrame) -> None:
    data = expert_judgments.copy()
    data["source_true"] = pd.Categorical(data["source_true"], ["Human", "MAS"])
    data["cognitive_level"] = pd.Categorical(data["cognitive_level"], LEVELS_4)
    formula = (
        "guessed_mas ~ C(source_true, Treatment(reference='Human'))"
        " * C(cognitive_level, Treatment(reference='recall'))"
    )
    model = BinomialBayesMixedGLM.from_formula(
        formula,
        {"expert": "0 + C(expert)", "item": "0 + C(item_key)"},
        data,
    )
    fit = model.fit_vb()
    term_rows = []
    for term, mean, sd in zip(model.exog_names, fit.fe_mean, fit.fe_sd):
        if term == "Intercept":
            continue
        if ":" in term:
            if "comprehension" in term:
                label = "MAS × Comprehension interaction"
            elif "application" in term:
                label = "MAS × Application interaction"
            else:
                label = "MAS × Analysis interaction"
        elif "source_true" in term:
            label = "MAS vs Human (at Knowledge)"
        elif "comprehension" in term:
            label = "Comprehension vs Knowledge"
        elif "application" in term:
            label = "Application vs Knowledge"
        else:
            label = "Analysis vs Knowledge"
        low = mean - Z_975 * sd
        high = mean + Z_975 * sd
        term_rows.append(
            {
                "term": term,
                "label": label,
                "log_odds": mean,
                "posterior_sd": sd,
                "odds_ratio": math.exp(mean),
                "ci_low": math.exp(low),
                "ci_high": math.exp(high),
                "model_formula": formula,
                "random_effects": "random intercepts for expert and item",
            }
        )
    forest = pd.DataFrame(term_rows)
    write_csv(DERIVED / "fig4D_expert_guessed_mas_model_input.csv", expert_judgments)
    write_csv(DERIVED / "fig4D_expert_guessed_mas_model_forest.csv", forest)

    fig, ax = plt.subplots(figsize=(7.1, 3.9))
    add_panel_label(fig, "D")
    plot = forest.iloc[::-1].reset_index(drop=True)
    y = np.arange(len(plot))
    ax.axvline(1, color=UROMAS_BASE_COLORS["text_dark"], linewidth=0.9)
    ax.errorbar(
        plot.odds_ratio,
        y,
        xerr=[plot.odds_ratio - plot.ci_low, plot.ci_high - plot.odds_ratio],
        fmt="o",
        color=OPTIONAL_COLOR_PAIRS[0]["color"],
        ecolor=OPTIONAL_COLOR_PAIRS[0]["color"],
        capsize=3,
        markersize=4.5,
    )
    ax.set_xscale("log")
    ax.set_yticks(y, plot.label)
    ax.set_xlabel("Odds ratio for being guessed as MAS (95% credible interval)")
    ax.set_title("Expert guessed-MAS mixed model", fontweight="bold")
    style_axes(ax, "x")
    save_pdf(fig, "Figure4D_expert_guessed_MAS_model_forest.pdf")


def figure4e() -> None:
    source = pd.read_csv(DERIVED / "source_detection.csv")
    correct = int(source.source_guess_success.sum())
    n = len(source)
    low, high = proportion_confint(correct, n, alpha=0.10, method="wilson")
    row = pd.DataFrame(
        [
            {
                "group": "Students",
                "correct": correct,
                "n": n,
                "accuracy": correct / n,
                "ci_low": low,
                "ci_high": high,
                "ci_method": "Wilson 90% CI",
            }
        ]
    )
    write_csv(DERIVED / "fig4E_student_source_identification_accuracy.csv", row)

    fig = plt.figure(figsize=(7.2, 2.7))
    add_panel_label(fig, "E")
    grid = fig.add_gridspec(1, 2, width_ratios=[1.35, 1.15], wspace=0.08)
    ax = fig.add_subplot(grid[0, 0])
    table_ax = fig.add_subplot(grid[0, 1])
    accuracy_band_axis(ax)
    estimate = correct / n * 100
    ax.errorbar(
        estimate,
        0,
        xerr=[[estimate - low * 100], [high * 100 - estimate]],
        fmt="o",
        color=OPTIONAL_COLOR_PAIRS[5]["color"],
        ecolor=OPTIONAL_COLOR_PAIRS[5]["color"],
        capsize=4,
        markersize=5,
    )
    ax.set_yticks([0], ["48 students"])
    ax.set_ylim(-0.7, 0.7)
    ax.set_title("Student source-identification accuracy", fontweight="bold")
    table_ax.axis("off")
    table = table_ax.table(
        cellText=[["Students", f"{correct}/{n}", f"{estimate:.1f}% ({low*100:.1f}–{high*100:.1f})"]],
        colLabels=["Group", "Correct/N", "Accuracy, 90% CI"],
        loc="center",
        cellLoc="center",
        colWidths=[0.28, 0.24, 0.48],
    )
    table.auto_set_font_size(False)
    table.set_fontsize(6.7)
    table.scale(1.0, 1.4)
    save_pdf(fig, "Figure4E_student_source_identification_accuracy.pdf", tight=False)


def figure4f() -> None:
    timing = pd.read_csv(DERIVED / "mas_question_generation_time.csv")
    values = timing["minutes_per_item"].astype(float)
    observed = float(values.mean())
    scenarios = pd.DataFrame(
        {
            "scenario": ["MAS −20%", "Observed MAS", "MAS +20%"],
            "minutes_per_item": [observed * 0.8, observed, observed * 1.2],
        }
    )
    write_csv(DERIVED / "fig4F_mas_timing_sensitivity.csv", scenarios)
    fig, ax = plt.subplots(figsize=(3.8, 2.7))
    add_panel_label(fig, "F")
    y = np.arange(len(scenarios))[::-1]
    ax.barh(y, scenarios.minutes_per_item.iloc[::-1], color=OPTIONAL_COLOR_PAIRS[2]["color"])
    ax.set_yticks(y, scenarios.scenario.iloc[::-1])
    ax.set_xlabel("Minutes per generated item")
    ax.set_title("MAS timing sensitivity", fontweight="bold")
    style_axes(ax, "x")
    save_pdf(fig, "Figure4F_efficiency_sensitivity.pdf")


# ---------------------------------------------------------------------------
# Figure 5


def figure5a() -> None:
    fig, ax = plt.subplots(figsize=(3.0, 2.4))
    add_panel_label(fig, "A")
    ax.set_xlim(0, 4)
    ax.set_ylim(0, 5)
    ax.axis("off")
    rounded_box(ax, (0.25, 3.15), (3.5, 1.0), "Form A", "Human → MAS", FORM_COLORS["A"]["fill"], FORM_COLORS["A"]["color"])
    rounded_box(ax, (0.25, 1.20), (3.5, 1.0), "Form B", "MAS → Human", FORM_COLORS["B"]["fill"], FORM_COLORS["B"]["color"])
    ax.set_title("Examination order schema", fontweight="bold")
    save_pdf(fig, "Figure5A_order_schema.pdf", tight=False)


def paired_scores_wide() -> pd.DataFrame:
    block = pd.read_csv(DERIVED / "block_scores.csv")
    wide = block.pivot_table(
        index=["student_id", "form", "training_setting"],
        columns="source_true",
        values="score_percent",
    ).reset_index()
    wide["mas_minus_human"] = wide["MAS"] - wide["Human"]
    return wide


def figure5b() -> None:
    wide = paired_scores_wide()
    write_csv(DERIVED / "fig5B_paired_block_scores.csv", wide)
    fig, ax = plt.subplots(figsize=(3.6, 3.0))
    add_panel_label(fig, "B")
    for form in ["A", "B"]:
        pair = FORM_COLORS[form]
        sub = wide[wide.form.eq(form)]
        for row in sub.itertuples():
            ax.plot([0, 1], [row.Human, row.MAS], color=pair["color"], alpha=0.28, linewidth=0.8)
        ax.scatter(np.zeros(len(sub)), sub.Human, color=pair["color"], s=12, alpha=0.65, label=f"Form {form}")
        ax.scatter(np.ones(len(sub)), sub.MAS, color=pair["color"], s=12, alpha=0.65)
    ax.set_xticks([0, 1], ["Human block", "MAS block"])
    ax.set_ylabel("Block score (%)")
    ax.set_title("Paired block scores by sequence", fontweight="bold")
    ax.legend(frameon=False)
    style_axes(ax)
    save_pdf(fig, "Figure5B_paired_block_scores.pdf")


def figure5c() -> None:
    wide = paired_scores_wide()
    fig, ax = plt.subplots(figsize=(3.2, 2.8))
    add_panel_label(fig, "C")
    groups = [wide.loc[wide.form.eq(form), "mas_minus_human"].to_numpy() for form in ["A", "B"]]
    box = ax.boxplot(groups, positions=[0, 1], widths=0.48, patch_artist=True, showfliers=False)
    for patch, form in zip(box["boxes"], ["A", "B"]):
        patch.set_facecolor(FORM_COLORS[form]["fill"])
        patch.set_edgecolor(FORM_COLORS[form]["color"])
    for median in box["medians"]:
        median.set_color(UROMAS_BASE_COLORS["text_dark"])
    rng = np.random.default_rng(95)
    for position, form, values in zip([0, 1], ["A", "B"], groups):
        ax.scatter(rng.normal(position, 0.04, len(values)), values, s=11, color=FORM_COLORS[form]["color"], alpha=0.55, linewidths=0)
    ax.axhline(0, color=UROMAS_BASE_COLORS["spine"], linewidth=0.9)
    ax.set_xticks([0, 1], ["Form A\nHuman → MAS", "Form B\nMAS → Human"])
    ax.set_ylabel("MAS − Human block score")
    ax.set_title("Within-participant differences by sequence", fontweight="bold")
    style_axes(ax)
    save_pdf(fig, "Figure5C_individual_differences_by_sequence.pdf")


def figure5d() -> None:
    responses = pd.read_csv(DERIVED / "responses.csv")
    item = pd.read_csv(DERIVED / "item_master.csv")[["item_id", "topic", "cognitive_level"]]
    data = responses.merge(item, on="item_id", how="left")
    data["is_mas"] = data.source_true.eq("MAS").astype(int)
    formula = (
        "correct ~ is_mas + C(block_position) + C(form) + C(training_setting)"
        " + C(training_year) + C(cognitive_level) + C(topic)"
    )
    fit = smf.ols(formula, data=data).fit(
        cov_type="cluster",
        cov_kwds={"groups": data.student_id},
    )
    rows = [
        {
            "contrast": "Overall adjusted",
            "estimate": fit.params["is_mas"] * 100,
            "ci_low": fit.conf_int().loc["is_mas", 0] * 100,
            "ci_high": fit.conf_int().loc["is_mas", 1] * 100,
            "n_students": data.student_id.nunique(),
            "n_responses": len(data),
            "method": formula,
        }
    ]
    wide = paired_scores_wide()
    rng = np.random.default_rng(101)
    for form, label in [("A", "Form A (Human → MAS)"), ("B", "Form B (MAS → Human)")]:
        values = wide.loc[wide.form.eq(form), "mas_minus_human"].to_numpy()
        boots = rng.choice(values, size=(3000, len(values)), replace=True).mean(axis=1)
        rows.append(
            {
                "contrast": label,
                "estimate": values.mean(),
                "ci_low": np.quantile(boots, 0.025),
                "ci_high": np.quantile(boots, 0.975),
                "n_students": len(values),
                "n_responses": len(values) * 100,
                "method": "Paired participant bootstrap",
            }
        )
    result = pd.DataFrame(rows)
    write_csv(DERIVED / "fig5D_adjusted_correct_rate_difference.csv", result)

    fig, ax = plt.subplots(figsize=(4.8, 2.8))
    add_panel_label(fig, "D")
    plot = result.iloc[::-1].reset_index(drop=True)
    y = np.arange(len(plot))
    ax.axvline(0, color=UROMAS_BASE_COLORS["text_dark"], linewidth=0.9)
    ax.errorbar(
        plot.estimate,
        y,
        xerr=[plot.estimate - plot.ci_low, plot.ci_high - plot.estimate],
        fmt="o",
        color=OPTIONAL_COLOR_PAIRS[5]["color"],
        ecolor=OPTIONAL_COLOR_PAIRS[5]["color"],
        capsize=3,
    )
    ax.set_yticks(y, plot.contrast)
    ax.set_xlabel("Correct-rate difference, MAS − Human (percentage points)")
    ax.set_title("Adjusted and sequence-stratified source difference", fontweight="bold")
    style_axes(ax, "x")
    save_pdf(fig, "Figure5D_adjusted_correct_rate_difference.pdf")


def figure5e() -> None:
    wide = paired_scores_wide()
    groups = [
        wide.loc[wide.training_setting.eq(setting), "mas_minus_human"].to_numpy()
        for setting in ["main", "non_main"]
    ]
    colors = [OPTIONAL_COLOR_PAIRS[3], OPTIONAL_COLOR_PAIRS[4]]
    fig, ax = plt.subplots(figsize=(3.2, 2.8))
    add_panel_label(fig, "E")
    box = ax.boxplot(groups, positions=[0, 1], widths=0.48, patch_artist=True, showfliers=False)
    for patch, pair in zip(box["boxes"], colors):
        patch.set_facecolor(pair["fill"])
        patch.set_edgecolor(pair["color"])
    rng = np.random.default_rng(102)
    for position, values, pair in zip([0, 1], groups, colors):
        ax.scatter(rng.normal(position, 0.04, len(values)), values, s=11, color=pair["color"], alpha=0.55, linewidths=0)
    ax.axhline(0, color=UROMAS_BASE_COLORS["spine"], linewidth=0.9)
    ax.set_xticks([0, 1], [f"Main campus\nn={len(groups[0])}", f"Non-main campus\nn={len(groups[1])}"])
    ax.set_ylabel("MAS − Human block score")
    ax.set_title("Setting-stratified score differences", fontweight="bold")
    style_axes(ax)
    save_pdf(fig, "Figure5E_setting_stratified_differences.pdf")


def cleanup_obsolete_outputs() -> None:
    obsolete = [
        "Figure2B_dimension_scores.pdf",
        "Figure2C_defect_flags.pdf",
        "Figure2D_defect_workflow.pdf",
        "Figure3B_defect_risk_by_cognitive_level.pdf",
        "Figure4B_source_judgment_confusion_matrix.pdf",
        "Figure4C_source_task_ratings.pdf",
        "Figure4D_workflow_total_time.pdf",
        "Figure4E_quality_adjusted_time.pdf",
    ]
    for filename in obsolete:
        remove_output(filename)


def main() -> None:
    setup_style()
    expert_judgments = parse_expert_judgments()

    figure1a()
    figure1b()
    figure1c()
    figure1d()
    figure1e()

    figure2a()
    figure2b()
    figure2c()
    figure2d()
    figure2e()

    figure3a()
    figure3b()
    figure3c()
    figure3d()
    figure3e()
    figure3f()

    figure4a()
    figure4b(expert_judgments)
    figure4c(expert_judgments)
    figure4d(expert_judgments)
    figure4e()
    figure4f()

    figure5a()
    figure5b()
    figure5c()
    figure5d()
    figure5e()

    cleanup_obsolete_outputs()
    print(f"Wrote all manuscript panel PDFs to {OUT}")


if __name__ == "__main__":
    main()
