#!/usr/bin/env python3
"""Generate every code-rendered manuscript panel from one plotting script.

Figure 5 contains workflow-efficiency analyses and Figure 6 contains the
randomized examination-order/fatigue analyses. All figures are written as
editable PDFs to outputs/figures/panels. Workflow panels 1A, 1B, 2A, 3A,
and 4A are reserved for manual PowerPoint rendering.
"""
from __future__ import annotations

import csv
import itertools
import json
import math
import posixpath
import re
import shutil
import subprocess
import sys
import tempfile
import warnings
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
from matplotlib.lines import Line2D
from matplotlib.patches import FancyBboxPatch, Patch, Rectangle
from patsy import build_design_matrices
from scipy import stats
from statsmodels.genmod.bayes_mixed_glm import BinomialBayesMixedGLM
from statsmodels.stats.proportion import proportion_confint


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from project_paths import (  # noqa: E402
    PANEL_FIGURE_DIR,
    PLOT_DERIVED_DATA_DIR,
    PLOT_DIR,
    PLOT_EXAM_WORKBOOK_DIR,
    PLOT_EXPERT_WORKBOOK_DIR,
    PLOT_RAW_DATA_DIR,
)

PLOT_ROOT = PLOT_DIR
DERIVED = PLOT_DERIVED_DATA_DIR
OUT = PANEL_FIGURE_DIR
SOURCE_WORKBOOK_MANIFEST = DERIVED / "root_xlsx_csv_manifest.csv"
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
    # Keep the declared canvas dimensions exact.  ``bbox_inches='tight'``
    # changes the PDF media box when annotations extend beyond an axis and was
    # the reason the nominal 4.5 x 9.0 Figure 2C was not a strict 1:2 panel.
    fig.savefig(OUT / filename, facecolor="white")
    plt.close(fig)


def save_pdf_rotated_counterclockwise(fig: plt.Figure, filename: str) -> None:
    """Save one intact 9 x 4.5 panel, then rotate the vector page to 4.5 x 9."""
    pdflatex = shutil.which("pdflatex")
    if pdflatex is None:
        raise RuntimeError("pdflatex is required to rotate Figure 2B without rasterizing it.")
    with tempfile.TemporaryDirectory(prefix="uromas_rotate_panel_") as temp_name:
        temp_dir = Path(temp_name)
        source = temp_dir / "source_landscape.pdf"
        fig.savefig(source, facecolor="white")
        plt.close(fig)
        source_tex_path = source.as_posix()
        tex = rf"""\documentclass{{article}}
\usepackage[paperwidth=4.5in,paperheight=9in,margin=0in]{{geometry}}
\usepackage{{graphicx}}
\usepackage{{eso-pic}}
\pagestyle{{empty}}
\begin{{document}}
\thispagestyle{{empty}}
\AddToShipoutPictureFG*{{
  \AtPageLowerLeft{{
    \setlength{{\unitlength}}{{1in}}
    \begin{{picture}}(0,0)
      \put(2.25,4.5){{\makebox(0,0){{\includegraphics[width=9in,height=4.5in,angle=90,origin=c]{{\detokenize{{{source_tex_path}}}}}}}}}
    \end{{picture}}
  }}
}}
\null
\end{{document}}
"""
        tex_path = temp_dir / "rotated.tex"
        tex_path.write_text(tex, encoding="utf-8")
        process = subprocess.run(
            [
                pdflatex,
                "-interaction=nonstopmode",
                "-halt-on-error",
                f"-output-directory={temp_dir}",
                str(tex_path),
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        if process.returncode != 0:
            tail = "\n".join(process.stdout.splitlines()[-30:])
            raise RuntimeError(f"Could not rotate {filename}:\n{tail}")
        shutil.copy2(temp_dir / "rotated.pdf", OUT / filename)


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


def significance_stars(p_value: float) -> str:
    if not np.isfinite(p_value) or p_value >= 0.05:
        return "n.s."
    if p_value < 0.001:
        return "***"
    if p_value < 0.01:
        return "**"
    return "*"


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
            fontsize=8,
            color=UROMAS_BASE_COLORS["text"],
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
    if path.exists():
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

    manifest = source_workbook_manifest()
    match = manifest[
        manifest.workbook_name.eq(path.name)
        & manifest.sheet_name.eq(sheet_name)
    ]
    if match.empty:
        raise FileNotFoundError(
            f"No XLSX or exported CSV found for {path.name}/{sheet_name}."
        )
    csv_path = REPO_ROOT / str(match.iloc[0].csv_path)
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [
            [parse_exported_cell(value) for value in row]
            for row in csv.reader(handle)
        ]


def parse_exported_cell(value: str) -> Any:
    text = value.strip()
    if text == "":
        return None
    if text == "True":
        return True
    if text == "False":
        return False
    try:
        number = float(text)
        return int(number) if number.is_integer() else number
    except ValueError:
        return value


def source_workbook_manifest() -> pd.DataFrame:
    if not SOURCE_WORKBOOK_MANIFEST.exists():
        return pd.DataFrame(
            columns=[
                "workbook_name",
                "sheet_name",
                "csv_path",
                "row_count",
                "column_count",
            ]
        )
    return pd.read_csv(SOURCE_WORKBOOK_MANIFEST, encoding="utf-8-sig")


def source_sheet_names(path: Path) -> set[str]:
    if path.exists():
        with ZipFile(path) as zf:
            return set(workbook_sheet_map(zf))
    manifest = source_workbook_manifest()
    return set(
        manifest.loc[
            manifest.workbook_name.eq(path.name),
            "sheet_name",
        ].astype(str)
    )


def expert_files() -> list[Path]:
    raw_candidates = sorted(
        (
            path
            for path in PLOT_EXPERT_WORKBOOK_DIR.glob("*.xlsx")
            if path.name.startswith(EXPERT_PREFIX) and not path.name.startswith("~$")
        ),
        key=lambda path: path.name,
    )
    required_common = {P_BLOOM, P_TYPE, M_BLOOM, M_TYPE, "图灵测试"}
    files = []
    for path in raw_candidates:
        sheets = source_sheet_names(path)
        has_summary = P_SUMMARY in sheets and (M_MERGED in sheets or M_SUMMARY in sheets)
        if has_summary and required_common.issubset(sheets):
            files.append(path)
    if not files:
        manifest = source_workbook_manifest()
        workbook_names = sorted(
            {
                str(name)
                for name in manifest.workbook_name.dropna()
                if str(name).startswith(EXPERT_PREFIX)
            }
        )
        files = [PLOT_EXPERT_WORKBOOK_DIR / name for name in workbook_names]
    if not files:
        raise FileNotFoundError(
            "No expert-rating XLSX files or exported worksheet CSVs were found."
        )
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
        sheets = source_sheet_names(path)
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
                normalized_component_values = [
                    standardized_dimension_score(row[column], max_score)
                    for _, _, max_score, column in DIMENSIONS
                    if isinstance(row[column], (int, float))
                ]
                records.append(
                    {
                        "expert": expert,
                        "rater_id": expert,
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
                        "quality_score_5": float(np.mean(normalized_component_values)),
                        "qgeval_total": rubric_family_total(row, "QGval"),
                        "qgeval_score_5": rubric_family_score_5(row, "QGval"),
                        "ulm_total": rubric_family_total(row, "ULM"),
                        "ulm_score_5": rubric_family_score_5(row, "ULM"),
                    }
                )
    result = pd.DataFrame(records)
    expected = len(expert_files()) * 140
    if len(result) != expected:
        raise ValueError(f"Parsed {len(result)} expert judgments; expected {expected}.")
    return result


# ---------------------------------------------------------------------------
# Figure 1


def remove_manual_workflow_outputs() -> None:
    """Keep manually rendered workflow panels out of generated outputs."""
    filenames = [
        "Figure1A_workflow_inputs.pdf",
        "Figure1B_safety_gate.pdf",
        "Figure2A_quality_difference.pdf",
        "Figure2A_expert_quality_evaluation_workflow.pdf",
        "Figure3A_quality_by_cognitive_level.pdf",
        "Figure3A_student_testing_workflow.pdf",
        "Figure4A_source_detection_accuracy.pdf",
        "Figure4A_turing_test_workflow.pdf",
    ]
    for filename in filenames:
        remove_output(filename)


def figure1c() -> None:
    """Remove the invalid panel pending complete expert defect data."""
    remove_output("Figure1C_two_sequence_order.pdf")


def figure1d() -> None:
    """Remove the invalid panel pending complete expert defect data."""
    remove_output("Figure1D_training_setting.pdf")


def figure1e() -> None:
    """Remove the invalid panel pending complete expert defect data."""
    remove_output("Figure1E_endpoint_domains.pdf")


# ---------------------------------------------------------------------------
# Figure 2: 2A reserved; old 2A->2B, old 2B->2C, old 3A->2D


def parse_primary_quality_records() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in expert_files():
        sheets = source_sheet_names(path)
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
                        "qg_total": rubric_family_total(row, "QGval"),
                        "ulm_total": rubric_family_total(row, "ULM"),
                        "qg_total_from_sheet": float(row[9]),
                        "ulm_total_from_sheet": float(row[26]),
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
    item_score_rows = []
    for endpoint, metric, scale_points, margin in [
        ("QGval", "qg_total", 35, -2.0),
        ("ULM", "ulm_total", 76, -4.0),
    ]:
        arrays = item_means(records, metric)
        human, mas = arrays["Human"], arrays["MAS"]
        for source in ["Human", "MAS"]:
            for item_seq, value in enumerate(arrays[source], start=1):
                item_score_rows.append(
                    {
                        "endpoint": endpoint,
                        "metric": metric,
                        "source": source,
                        "item_seq": item_seq,
                        "item_mean_score": value,
                        "scale_points": scale_points,
                    }
                )
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
    write_csv(DERIVED / "fig2B_quality_difference_item_scores.csv", item_score_rows)
    write_csv(DERIVED / "fig2B_quality_difference_stats.csv", stats_df)

    # Rotate the data display counterclockwise so all non-header text reads
    # with its letter tops toward the left edge in the portrait slot. The
    # label and title are counter-rotated here so the final portrait page
    # keeps them upright at top left and top center, respectively.
    fig, ax = plt.subplots(figsize=(9.0, 4.5))
    fig.text(
        0.988,
        0.988,
        "(B)",
        ha="left",
        va="top",
        rotation=-90,
        rotation_mode="anchor",
        fontsize=11,
        fontweight="bold",
        color=UROMAS_BASE_COLORS["text_dark"],
    )
    fig.text(
        0.988,
        0.50,
        "Primary endpoint non-inferiority",
        ha="center",
        va="top",
        rotation=-90,
        rotation_mode="anchor",
        fontsize=8,
        fontweight="bold",
        color=UROMAS_BASE_COLORS["text_dark"],
    )
    y = np.array([1.0, 0.0])
    ax.set_xlim(-5.2, 2.25)
    ax.set_ylim(-0.58, 1.58)
    for index, row in stats_df.iterrows():
        pair = OPTIONAL_COLOR_PAIRS[index]
        band_low = y[index] - 0.32
        band_high = y[index] + 0.32
        ax.add_patch(
            Rectangle(
                (-5.2, band_low),
                row.ni_margin + 5.2,
                band_high - band_low,
                facecolor=pair["fill"],
                edgecolor="none",
                alpha=0.70,
                zorder=0,
            )
        )
        ax.vlines(
            row.ni_margin,
            band_low,
            band_high,
            color=pair["color"],
            linestyle="--",
            linewidth=1.2,
        )
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
            y[index] + 0.12,
            f"{row['diff']:.2f} [{row['ci_low']:.2f}, {row['ci_high']:.2f}]",
            ha="center",
            va="bottom",
        )
        ax.text(
            -0.10,
            y[index] + 0.35,
            (
                f"{row['endpoint']}: MAS {row['mas_mean']:.2f} ± {row['mas_sd']:.2f}"
                f"  vs  Human {row['human_mean']:.2f} ± {row['human_sd']:.2f}"
                f"  ({int(row['scale_points'])}-point)"
            ),
            ha="center",
            va="center",
            fontsize=8,
            color=UROMAS_BASE_COLORS["text_dark"],
        )
        ax.text(
            row.ni_margin - 0.08,
            y[index],
            f"NI margin {row.ni_margin:.2f}",
            ha="right",
            va="center",
            rotation=0,
            color=pair["color"],
            fontsize=8,
        )
    ax.axvline(0, color=UROMAS_BASE_COLORS["spine"], linewidth=1)
    ax.set_yticks(y, [f"{row.endpoint}\n(n=70/group)" for row in stats_df.itertuples()])
    ax.set_xlabel("Quality-score difference (MAS − Human)")
    ax.text(
        -0.05,
        -0.43,
        "Non-inferior\n(95% CIs above endpoint-specific NI margins)",
        ha="center",
        va="center",
        fontsize=8,
        color=UROMAS_BASE_COLORS["text_dark"],
    )
    style_axes(ax, "x")
    fig.tight_layout(rect=[0.02, 0.02, 0.94, 0.98])
    save_pdf_rotated_counterclockwise(fig, "Figure2B_quality_difference.pdf")


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

DIMENSION_SCORE_COLUMNS = [
    ("QGval", "Fluency", 5, "qg_fluency"),
    ("QGval", "Clarity", 5, "qg_clarity"),
    ("QGval", "Conciseness", 5, "qg_conciseness"),
    ("QGval", "Relevance", 5, "qg_relevance"),
    ("QGval", "Consistency", 5, "qg_consistency"),
    ("QGval", "Answerability", 5, "qg_answerability"),
    ("QGval", "Answer consistency", 5, "qg_answer_consistency"),
    ("ULM", "Fluency", 5, "llm_fluency"),
    ("ULM", "Exclusiveness", 5, "llm_exclusiveness"),
    ("ULM", "Explicitness", 4, "llm_explicitness"),
    ("ULM", "Goal alignment", 5, "llm_goal_alignment"),
    ("ULM", "Comprehensiveness", 5, "llm_comprehensiveness"),
    ("ULM", "Focus", 5, "llm_focus"),
    ("ULM", "Guess resistance", 5, "llm_guess_resistance"),
    ("ULM", "Completeness", 5, "llm_completeness"),
    ("ULM", "Correctness", 5, "llm_correctness"),
    ("ULM", "Solvability", 5, "llm_solvability"),
    ("ULM", "Absoluteness", 5, "llm_absoluteness"),
    ("ULM", "Plausibility", 5, "llm_plausibility"),
    ("ULM", "Reasoning", 4, "llm_reasoning"),
    ("ULM", "Feedback", 5, "llm_feedback"),
    ("ULM", "Fairness", 3, "llm_fairness"),
    ("ULM", "Explanation score", 5, "llm_explanation_score"),
]


def standardized_dimension_score(value: float, max_score: float) -> float:
    bounded_value = min(float(value), float(max_score))
    return bounded_value / float(max_score) * 5.0


def rubric_family_total(row: Sequence[Any], family_name: str) -> float:
    scores = [
        min(float(row[column]), float(max_score))
        for family, _, max_score, column in DIMENSIONS
        if family == family_name and isinstance(row[column], (int, float))
    ]
    return float(np.sum(scores)) if scores else float("nan")


def rubric_family_score_5(row: Sequence[Any], family_name: str) -> float:
    scores = [
        standardized_dimension_score(row[column], max_score)
        for family, _, max_score, column in DIMENSIONS
        if family == family_name and isinstance(row[column], (int, float))
    ]
    return float(np.mean(scores)) if scores else float("nan")


def figure2c() -> None:
    records: list[dict[str, Any]] = []
    for path in expert_files():
        sheets = source_sheet_names(path)
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
                            "raw_score": float(row[column]),
                            "score_capped_to_max": bool(float(row[column]) > float(max_score)),
                        }
                    )
    data = pd.DataFrame(records)
    item_level = (
        data.groupby(["source", "item_seq", "family", "dimension"], as_index=False)
        .agg(
            max_score=("max_score", "first"),
            raw_score=("raw_score", "mean"),
            any_score_capped_to_max=("score_capped_to_max", "any"),
        )
    )
    summary = (
        item_level.groupby(["family", "dimension", "source"])
        .agg(
            max_score=("max_score", "first"),
            count=("raw_score", "count"),
            mean_raw_score=("raw_score", "mean"),
            sd_raw_score=("raw_score", "std"),
            any_score_capped_to_max=("any_score_capped_to_max", "any"),
        )
        .reset_index()
    )
    write_csv(DERIVED / "fig2C_dimension_scores_item_scores.csv", item_level)
    write_csv(DERIVED / "fig2C_dimension_scores_stats.csv", summary)

    labels = [dimension for _, dimension, _, _ in DIMENSIONS]
    y = np.array([index if index < 7 else index + 0.7 for index in range(len(labels))])
    height = 0.34
    fig, ax = plt.subplots(figsize=(4.5, 9.0))
    add_panel_label(fig, "C")
    for source, offset in [("MAS", -0.18), ("Human", 0.18)]:
        means, sds = [], []
        for family, dimension, _, _ in DIMENSIONS:
            row = summary[
                summary.family.eq(family)
                & summary.dimension.eq(dimension)
                & summary.source.eq(source)
            ].iloc[0]
            means.append(float(row["mean_raw_score"]))
            sds.append(float(row["sd_raw_score"]))
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
    significance_rows = []
    margin_by_scale = {5: 0.30, 4: 0.25, 3: 0.20}
    for index, (family, dimension, max_score, _) in enumerate(DIMENSIONS):
        dimension_rows = item_level[
            item_level.family.eq(family) & item_level.dimension.eq(dimension)
        ]
        mas = dimension_rows.loc[dimension_rows.source.eq("MAS"), "raw_score"].to_numpy()
        human = dimension_rows.loc[dimension_rows.source.eq("Human"), "raw_score"].to_numpy()
        test = stats.ttest_ind(mas, human, equal_var=False)
        p_value = float(test.pvalue)
        difference = float(np.mean(mas) - np.mean(human))
        adverse_margin = margin_by_scale[max_score]
        materially_worse = difference <= -adverse_margin
        label = significance_stars(p_value) if materially_worse else "n.s."
        significance_rows.append(
            {
                "family": family,
                "dimension": dimension,
                "max_score": max_score,
                "n_mas": len(mas),
                "n_human": len(human),
                "difference_mas_minus_human": difference,
                "adverse_difference_margin": -adverse_margin,
                "welch_t_statistic": float(test.statistic),
                "p_value_two_sided": p_value,
                "materially_worse_than_human": materially_worse,
                "annotation_rule": (
                    "Welch two-sample t-test stars are displayed only when MAS is "
                    "lower than Human by at least the prespecified scale-specific margin"
                ),
                "annotation": label,
            }
        )
        ax.text(
            5.56,
            y[index],
            label,
            ha="left",
            va="center",
            fontweight="bold",
            fontsize=8,
            color=UROMAS_BASE_COLORS["text_dark"],
        )
    write_csv(DERIVED / "fig2C_dimension_score_annotations.csv", significance_rows)
    ax.set_xlim(1, 5.85)
    ax.set_xlabel("Mean expert rating (native dimension scale)")
    fig.suptitle("Per-dimension human-expert scores", y=0.99, fontweight="bold")
    ax.legend(frameon=False, ncol=2, loc="lower right")
    ax.text(
        0.50,
        -0.058,
        "Stars: adverse MAS differences significant at P < .05\n"
        "and beyond the prespecified scale-specific margin.",
        transform=ax.transAxes,
        ha="center",
        va="top",
        fontsize=6.5,
        color=UROMAS_BASE_COLORS["text"],
    )
    style_axes(ax, "x")
    fig.subplots_adjust(left=0.40, right=0.96, bottom=0.10, top=0.94)
    save_pdf(fig, "Figure2C_dimension_scores.pdf", tight=False)


def figure2d() -> None:
    level_map = [("记忆", "Knowledge"), ("理解", "Comprehension"), ("应用", "Application"), ("分析", "Analysis")]
    metric_specs = {
        "QGval": {"family": "QGval", "margin": -0.30, "pair": OPTIONAL_COLOR_PAIRS[0]},
        "ULM": {"family": "ULM", "margin": -0.25, "pair": OPTIONAL_COLOR_PAIRS[1]},
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
                                "score": rubric_family_score_5(row, spec["family"]),
                                "score_scale": "mean of component scores standardized to 5 points",
                            }
                        )
    data = pd.DataFrame(records)
    item_level = (
        data.groupby(["source", "cognitive_level", "item_seq", "metric"], as_index=False)
        .agg(
            score=("score", "mean"),
            score_scale=("score_scale", "first"),
        )
    )
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

    fig, ax = plt.subplots(figsize=(9.0, 4.5))
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
        ax.text(
            spec["margin"],
            0.90,
            f"{metric} NI {spec['margin']:.2f}",
            transform=ax.get_xaxis_transform(),
            ha="right",
            va="bottom",
            rotation=90,
            color=spec["pair"]["color"],
            fontsize=8,
        )
        for row_index, row in enumerate(sub.itertuples()):
            ax.text(
                0.505,
                y[row_index] + offset,
                f"{row.diff:.2f}",
                ha="left",
                va="center",
                color=spec["pair"]["color"],
                fontsize=8,
            )
    ax.axvline(0, color=UROMAS_BASE_COLORS["spine"], linewidth=1)
    ax.set_yticks(y, [label for _, label in level_map])
    ax.invert_yaxis()
    ax.set_xlim(-0.43, 0.60)
    ax.set_xlabel("Mean quality-score difference (MAS − Human)")
    fig.suptitle("Expert quality gap by cognitive level", y=0.99, fontweight="bold")
    ax.legend(
        frameon=False,
        ncol=2,
        loc="upper center",
        bbox_to_anchor=(0.50, -0.13),
    )
    style_axes(ax, "x")
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    # Figure 2D and 2E share the same two assembled columns.
    fig.subplots_adjust(left=0.12, right=0.985, bottom=0.18, top=0.88)
    save_pdf(fig, "Figure2D_quality_by_cognitive_level.pdf", tight=False)


EXPERT_QUALITY_NI_MARGIN = -0.25
EXPERT_QUALITY_SCORE_FORMULA = (
    "quality_score_5 is the unweighted mean of 23 expert rubric component "
    "scores after each component is standardized to a 5-point scale using its "
    "own maximum score: 7 QGval components plus 16 ULM components. ULM "
    "Explicitness and Reasoning have 4-point maxima, and ULM Fairness has a "
    "3-point maximum; all other components have 5-point maxima. "
    "qgeval_score_5 and llm_score_5 are the corresponding family-level means "
    "of standardized component scores."
)


def expert_quality_interaction_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, str]:
    data = parse_expert_judgments()[
        [
            "rater_id",
            "source_true",
            "item_key",
            "item_type",
            "cognitive_level",
            "quality_score_5",
            "qgeval_score_5",
            "ulm_score_5",
        ]
    ].copy()
    data = data.dropna(
        subset=["quality_score_5", "source_true", "cognitive_level", "rater_id", "item_key"]
    )
    data["source_true"] = pd.Categorical(data["source_true"], ["Human", "MAS"])
    data["cognitive_level"] = pd.Categorical(data["cognitive_level"], LEVELS_4)
    data["item_type"] = pd.Categorical(data["item_type"])
    data["rating_order"] = data.groupby(["rater_id", "source_true"], observed=True).cumcount() + 1
    data["rating_order_z"] = (
        data["rating_order"] - data["rating_order"].mean()
    ) / data["rating_order"].std(ddof=1)
    data["all_observations"] = "all"

    formula = (
        "quality_score_5 ~ C(source_true, Treatment(reference='Human'))"
        " * C(cognitive_level, Treatment(reference='recall'))"
        " + rating_order_z"
    )
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        model = smf.mixedlm(
            formula,
            data,
            groups=data["all_observations"],
            vc_formula={
                "rater": "0 + C(rater_id)",
                "item": "0 + C(item_key)",
            },
            re_formula="0",
        )
        fit = model.fit(method="lbfgs", maxiter=500, reml=False, disp=False)
        if not fit.converged:
            fit = model.fit(method="powell", maxiter=1000, reml=False, disp=False)
    if not fit.converged:
        raise RuntimeError("Figure 2E expert-quality mixed model did not converge.")

    fixed_names = list(fit.fe_params.index)
    beta = fit.fe_params.to_numpy(dtype=float)
    covariance = fit.cov_params().loc[fixed_names, fixed_names].to_numpy(dtype=float)
    design_info = fit.model.data.design_info
    contrast_rows: list[dict[str, Any]] = []
    for level in LEVELS_4:
        scenario_human = data.copy()
        scenario_mas = data.copy()
        scenario_human["source_true"] = "Human"
        scenario_mas["source_true"] = "MAS"
        scenario_human["cognitive_level"] = level
        scenario_mas["cognitive_level"] = level
        x_human = np.asarray(build_design_matrices([design_info], scenario_human)[0])
        x_mas = np.asarray(build_design_matrices([design_info], scenario_mas)[0])
        gradient = (x_mas - x_human).mean(axis=0)
        estimate = float(gradient @ beta)
        se = float(math.sqrt(max(gradient @ covariance @ gradient.T, 0.0)))
        z_value = estimate / se if se > 0 else float("nan")
        p_value_two_sided = float(2 * stats.norm.sf(abs(z_value))) if np.isfinite(z_value) else float("nan")
        z_noninferiority = (estimate - EXPERT_QUALITY_NI_MARGIN) / se if se > 0 else float("nan")
        p_value_noninferiority = (
            float(stats.norm.sf(z_noninferiority))
            if np.isfinite(z_noninferiority)
            else float("nan")
        )
        ci_low = estimate - Z_975 * se
        ci_high = estimate + Z_975 * se
        contrast_rows.append(
            {
                "cognitive_level": level,
                "cognitive_level_label": LEVEL_LABELS_4[level],
                "estimate_mas_minus_human": estimate,
                "se": se,
                "ci_low": ci_low,
                "ci_high": ci_high,
                "ni_margin": EXPERT_QUALITY_NI_MARGIN,
                "noninferior_95ci": bool(ci_low > EXPERT_QUALITY_NI_MARGIN),
                "z_noninferiority": z_noninferiority,
                "p_value_noninferiority": p_value_noninferiority,
                "p_value_two_sided": p_value_two_sided,
                "model_formula": formula,
                "covariates": "rating order within source and rater (standardized)",
                "random_effects": "(1|rater_id) + (1|item_key)",
                "score_formula": EXPERT_QUALITY_SCORE_FORMULA,
                "data_source": "plot/data/raw/expert_rating_workbooks",
            }
        )

    fixed_rows = []
    fixed_table = fit.summary().tables[1]
    for term in fixed_names:
        fixed_rows.append(
            {
                "term": term,
                "estimate": float(fit.fe_params[term]),
                "se": float(fixed_table.loc[term, "Std.Err."]),
                "z": float(fixed_table.loc[term, "z"]),
                "p_value": float(fixed_table.loc[term, "P>|z|"]),
                "ci_low": float(fixed_table.loc[term, "[0.025"]),
                "ci_high": float(fixed_table.loc[term, "0.975]"]),
                "model_formula": formula,
                "covariates": "rating order within source and rater (standardized)",
                "random_effects": "(1|rater_id) + (1|item_key)",
                "score_formula": EXPERT_QUALITY_SCORE_FORMULA,
                "data_source": "plot/data/raw/expert_rating_workbooks",
            }
        )
    plot_data = (
        data.groupby(["source_true", "cognitive_level", "item_key"], observed=True)
        .agg(
            quality_score=("quality_score_5", "mean"),
            n_raters=("rater_id", "nunique"),
        )
        .reset_index()
    )
    return data, plot_data, pd.DataFrame(contrast_rows), pd.DataFrame(fixed_rows), formula


def figure2e() -> None:
    data, plot_data, contrasts, fixed_effects, _ = expert_quality_interaction_data()
    write_csv(DERIVED / "fig2E_expert_quality_interaction_model_input.csv", data)
    write_csv(DERIVED / "fig2E_expert_quality_interaction_plot_data.csv", plot_data)
    write_csv(DERIVED / "fig2E_expert_quality_interaction_contrasts.csv", contrasts)
    write_csv(DERIVED / "fig2E_expert_quality_interaction_fixed_effects.csv", fixed_effects)

    fig, ax = plt.subplots(figsize=(9.0, 4.5))
    add_panel_label(fig, "E")
    x = np.arange(len(LEVELS_4), dtype=float)
    offsets = {"Human": -0.17, "MAS": 0.17}
    for source in ["Human", "MAS"]:
        arrays = [
            plot_data.loc[
                plot_data.source_true.eq(source) & plot_data.cognitive_level.eq(level),
                "quality_score",
            ].to_numpy()
            for level in LEVELS_4
        ]
        box = ax.boxplot(
            arrays,
            positions=x + offsets[source],
            widths=0.26,
            patch_artist=True,
            showfliers=False,
            medianprops={"color": CORE_COLORS[source], "linewidth": 1.2},
            whiskerprops={"color": CORE_COLORS[source], "linewidth": 0.8},
            capprops={"color": CORE_COLORS[source], "linewidth": 0.8},
        )
        for patch in box["boxes"]:
            patch.set_facecolor(CORE_FILLS[source])
            patch.set_edgecolor(CORE_COLORS[source])
            patch.set_alpha(0.88)
        means = np.array([np.mean(values) for values in arrays])
        ax.plot(
            x + offsets[source],
            means,
            color=CORE_COLORS[source],
            marker="o",
            markersize=4,
            linewidth=1.2,
            label=f"{source} item mean",
            zorder=4,
        )
    y_min = float(plot_data.quality_score.min())
    y_max = float(plot_data.quality_score.max())
    annotation_base = y_max + 0.08
    for index, row in enumerate(contrasts.itertuples()):
        left = x[index] + offsets["Human"]
        right = x[index] + offsets["MAS"]
        y_pos = annotation_base + 0.04 * (index % 2)
        ax.plot(
            [left, left, right, right],
            [y_pos - 0.015, y_pos, y_pos, y_pos - 0.015],
            color=UROMAS_BASE_COLORS["text_dark"],
            linewidth=0.8,
        )
        ax.text(
            x[index],
            y_pos + 0.012,
            significance_stars(row.p_value_two_sided),
            ha="center",
            va="bottom",
            fontsize=8,
            fontweight="bold",
        )
    ax.set_xticks(x, [LEVEL_LABELS_4[level] for level in LEVELS_4])
    ax.set_ylabel("Expert quality score (standardized 5-point mean)")
    ax.set_ylim(max(1.0, y_min - 0.12), annotation_base + 0.16)
    fig.suptitle("Expert quality by source and cognitive level", y=0.99, fontweight="bold")
    # Match Figure 3D's compact arrangement: keep the legend inside the data
    # area and place the model note directly beneath the axis.
    ax.legend(frameon=False, ncol=2, loc="lower left")
    # Match Figure 2D's left/right plot bounds and Figure 2F's baseline.
    fig.subplots_adjust(left=0.12, right=0.985, bottom=0.20, top=0.88)
    fig.text(
        0.985,
        0.045,
        "Mixed model: source × cognitive level + rating order, with crossed random rater and item intercepts; stars show adjusted source contrasts.",
        ha="right",
        va="bottom",
        fontsize=6.5,
        color=UROMAS_BASE_COLORS["text"],
    )
    style_axes(ax)
    save_pdf(fig, "Figure2E_expert_quality_source_cognitive_interaction.pdf", tight=False)


def icc_2_absolute_agreement(values: np.ndarray) -> dict[str, float]:
    matrix = np.asarray(values, dtype=float)
    matrix = matrix[~np.isnan(matrix).any(axis=1)]
    n_targets, n_raters = matrix.shape
    if n_targets < 2 or n_raters < 2:
        return {
            "n_targets": n_targets,
            "n_raters": n_raters,
            "ms_target": float("nan"),
            "ms_rater": float("nan"),
            "ms_error": float("nan"),
            "icc_2_1": float("nan"),
            "icc_2_k": float("nan"),
            "icc_c_1": float("nan"),
            "icc_c_k": float("nan"),
        }
    target_means = matrix.mean(axis=1, keepdims=True)
    rater_means = matrix.mean(axis=0, keepdims=True)
    grand_mean = matrix.mean()
    ss_target = n_raters * ((target_means - grand_mean) ** 2).sum()
    ss_rater = n_targets * ((rater_means - grand_mean) ** 2).sum()
    ss_total = ((matrix - grand_mean) ** 2).sum()
    ss_error = ss_total - ss_target - ss_rater
    ms_target = ss_target / (n_targets - 1)
    ms_rater = ss_rater / (n_raters - 1)
    ms_error = ss_error / ((n_targets - 1) * (n_raters - 1))
    def safe_ratio(numerator: float, denominator: float) -> float:
        if not np.isfinite(denominator) or abs(denominator) < 1e-12:
            return float("nan")
        return float(numerator / denominator)

    icc_2_1 = safe_ratio(
        ms_target - ms_error,
        ms_target
        + (n_raters - 1) * ms_error
        + n_raters * (ms_rater - ms_error) / n_targets,
    )
    icc_2_k = safe_ratio(
        ms_target - ms_error,
        ms_target + (ms_rater - ms_error) / n_targets,
    )
    icc_c_1 = safe_ratio(
        ms_target - ms_error,
        ms_target + (n_raters - 1) * ms_error,
    )
    icc_c_k = safe_ratio(ms_target - ms_error, ms_target)
    return {
        "n_targets": int(n_targets),
        "n_raters": int(n_raters),
        "ms_target": float(ms_target),
        "ms_rater": float(ms_rater),
        "ms_error": float(ms_error),
        "icc_2_1": float(icc_2_1),
        "icc_2_k": float(icc_2_k),
        "icc_c_1": float(icc_c_1),
        "icc_c_k": float(icc_c_k),
    }


def nanquantile_or_nan(values: Sequence[float], quantile: float) -> float:
    array = np.asarray(values, dtype=float)
    array = array[np.isfinite(array)]
    if array.size == 0:
        return float("nan")
    return float(np.quantile(array, quantile))


def _deprecated_source_stratified_icc_data(
    reps: int = 3000,
    seed: int = 20260628,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    raise RuntimeError("Use expert_inter_rater_endpoint_icc_data with the raw expert workbooks.")
    ratings = parse_expert_judgments()
    ratings = ratings.dropna(subset=["source_true", "rater_id", "excel_row", "quality_score_5"]).copy()
    ratings["target_id"] = (
        ratings["source_true"].astype(str)
        + "_row_"
        + ratings["excel_row"].astype(int).astype(str).str.zfill(3)
    )
    raw_score_columns = [
        "source_true",
        "target_id",
        "item_id",
        "paper_item_no",
        "excel_row",
        "rater_id",
        "source_file",
        "sheet",
        "match_score",
        "item_type_from_sheet",
        "quality_score_5",
        *[column for _, _, _, column in DIMENSION_SCORE_COLUMNS],
    ]
    raw_scores = ratings[[column for column in raw_score_columns if column in ratings.columns]].rename(
        columns={
            "source_true": "source",
            "paper_item_no": "paper_item_no_from_match",
        }
    )
    item_score_rows: list[dict[str, Any]] = []
    stat_rows: list[dict[str, Any]] = []
    boot_rows: list[dict[str, Any]] = []
    dimension_score_rows: list[dict[str, Any]] = []
    dimension_stat_rows: list[dict[str, Any]] = []
    dimension_boot_rows: list[dict[str, Any]] = []
    rng = np.random.default_rng(seed)
    for source in ["Human", "MAS"]:
        source_ratings = ratings[ratings.source_true.eq(source)]
        wide = (
            source_ratings
            .pivot(index="target_id", columns="rater_id", values="quality_score_5")
            .sort_index()
        )
        for target_id, row in wide.iterrows():
            target_rows = ratings[ratings.target_id.eq(target_id)]
            item_id = target_rows.item_id.dropna().astype(str).iloc[0] if target_rows.item_id.notna().any() else ""
            paper_item_no = target_rows.paper_item_no.dropna().iloc[0] if target_rows.paper_item_no.notna().any() else np.nan
            excel_row = target_rows.excel_row.dropna().iloc[0] if target_rows.excel_row.notna().any() else np.nan
            for rater_id, score in row.items():
                item_score_rows.append(
                    {
                        "source": source,
                        "target_id": target_id,
                        "item_id": item_id,
                        "paper_item_no_from_match": paper_item_no,
                        "excel_row": excel_row,
                        "rater_id": rater_id,
                        "expert_quality_score_5": score,
                    }
                )
        estimate = icc_2_absolute_agreement(wide.to_numpy())
        boot_icc_2_1: list[float] = []
        boot_icc_2_k: list[float] = []
        boot_icc_c_1: list[float] = []
        boot_icc_c_k: list[float] = []
        matrix = wide.to_numpy(float)
        n_targets = matrix.shape[0]
        for rep in range(reps):
            sampled = matrix[rng.integers(0, n_targets, size=n_targets), :]
            boot = icc_2_absolute_agreement(sampled)
            boot_icc_2_1.append(boot["icc_2_1"])
            boot_icc_2_k.append(boot["icc_2_k"])
            boot_icc_c_1.append(boot["icc_c_1"])
            boot_icc_c_k.append(boot["icc_c_k"])
            boot_rows.append(
                {
                    "source": source,
                    "bootstrap_replicate": rep + 1,
                    "icc_2_1": boot["icc_2_1"],
                    "icc_2_k": boot["icc_2_k"],
                    "icc_c_1": boot["icc_c_1"],
                    "icc_c_k": boot["icc_c_k"],
                }
            )
        stat_rows.append(
            {
                "source": source,
                **estimate,
                "icc_2_1_ci_low": nanquantile_or_nan(boot_icc_2_1, 0.025),
                "icc_2_1_ci_high": nanquantile_or_nan(boot_icc_2_1, 0.975),
                "icc_2_k_ci_low": nanquantile_or_nan(boot_icc_2_k, 0.025),
                "icc_2_k_ci_high": nanquantile_or_nan(boot_icc_2_k, 0.975),
                "icc_c_1_ci_low": nanquantile_or_nan(boot_icc_c_1, 0.025),
                "icc_c_1_ci_high": nanquantile_or_nan(boot_icc_c_1, 0.975),
                "icc_c_k_ci_low": nanquantile_or_nan(boot_icc_c_k, 0.025),
                "icc_c_k_ci_high": nanquantile_or_nan(boot_icc_c_k, 0.975),
                "ci_method": f"item bootstrap, {reps} replicates",
                "icc_model": "two-way random-effects ICC; icc_2_* columns are absolute agreement, icc_c_* columns are consistency; plotted statistic is average-measure consistency ICC(C,k) across three experts",
                "target_alignment": "source-specific expert worksheet rows",
                "score_column": "quality_score_5",
            }
        )
    dimension_rng = np.random.default_rng(seed + 1)
    for source in ["Human", "MAS"]:
        source_ratings = ratings[ratings.source_true.eq(source)]
        for family, dimension, max_score, score_column in DIMENSION_SCORE_COLUMNS:
            dimension_wide = (
                source_ratings
                .pivot(index="target_id", columns="rater_id", values=score_column)
                .sort_index()
            )
            for target_id, row in dimension_wide.iterrows():
                target_rows = source_ratings[source_ratings.target_id.eq(target_id)]
                item_id = target_rows.item_id.dropna().astype(str).iloc[0] if target_rows.item_id.notna().any() else ""
                paper_item_no = target_rows.paper_item_no.dropna().iloc[0] if target_rows.paper_item_no.notna().any() else np.nan
                excel_row = target_rows.excel_row.dropna().iloc[0] if target_rows.excel_row.notna().any() else np.nan
                for rater_id, score in row.items():
                    dimension_score_rows.append(
                        {
                            "source": source,
                            "target_id": target_id,
                            "item_id": item_id,
                            "paper_item_no_from_match": paper_item_no,
                            "excel_row": excel_row,
                            "rater_id": rater_id,
                            "family": family,
                            "dimension": dimension,
                            "score_column": score_column,
                            "max_score": max_score,
                            "expert_dimension_score_raw": score,
                            "expert_dimension_score_5": float(score) / max_score * 5 if pd.notna(score) else np.nan,
                        }
                    )
            estimate = icc_2_absolute_agreement(dimension_wide.to_numpy())
            boot_icc_2_1 = []
            boot_icc_2_k = []
            boot_icc_c_1 = []
            boot_icc_c_k = []
            matrix = dimension_wide.to_numpy(float)
            n_targets = matrix.shape[0]
            for rep in range(reps):
                sampled = matrix[dimension_rng.integers(0, n_targets, size=n_targets), :]
                boot = icc_2_absolute_agreement(sampled)
                boot_icc_2_1.append(boot["icc_2_1"])
                boot_icc_2_k.append(boot["icc_2_k"])
                boot_icc_c_1.append(boot["icc_c_1"])
                boot_icc_c_k.append(boot["icc_c_k"])
                dimension_boot_rows.append(
                    {
                        "source": source,
                        "family": family,
                        "dimension": dimension,
                        "score_column": score_column,
                        "bootstrap_replicate": rep + 1,
                        "icc_2_1": boot["icc_2_1"],
                        "icc_2_k": boot["icc_2_k"],
                        "icc_c_1": boot["icc_c_1"],
                        "icc_c_k": boot["icc_c_k"],
                    }
                )
            dimension_stat_rows.append(
                {
                    "source": source,
                    "family": family,
                    "dimension": dimension,
                    "score_column": score_column,
                    "max_score": max_score,
                    **estimate,
                    "icc_2_1_ci_low": nanquantile_or_nan(boot_icc_2_1, 0.025),
                    "icc_2_1_ci_high": nanquantile_or_nan(boot_icc_2_1, 0.975),
                    "icc_2_k_ci_low": nanquantile_or_nan(boot_icc_2_k, 0.025),
                    "icc_2_k_ci_high": nanquantile_or_nan(boot_icc_2_k, 0.975),
                    "icc_c_1_ci_low": nanquantile_or_nan(boot_icc_c_1, 0.025),
                    "icc_c_1_ci_high": nanquantile_or_nan(boot_icc_c_1, 0.975),
                    "icc_c_k_ci_low": nanquantile_or_nan(boot_icc_c_k, 0.025),
                    "icc_c_k_ci_high": nanquantile_or_nan(boot_icc_c_k, 0.975),
                    "ci_method": f"item bootstrap, {reps} replicates",
                    "icc_model": "two-way random-effects ICC; icc_2_* columns are absolute agreement, icc_c_* columns are consistency; plotted statistic is average-measure consistency ICC(C,k) across three experts",
                    "target_alignment": "source-specific expert worksheet rows",
                }
            )
    return (
        raw_scores,
        pd.DataFrame(item_score_rows),
        pd.DataFrame(stat_rows),
        pd.DataFrame(boot_rows),
        pd.DataFrame(dimension_score_rows),
        pd.DataFrame(dimension_stat_rows),
        pd.DataFrame(dimension_boot_rows),
    )


def expert_inter_rater_endpoint_icc_data(
    reps: int = 3000,
    seed: int = 20260715,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    ratings = parse_expert_judgments()[
        [
            "source_true",
            "item_key",
            "item_type",
            "cognitive_level",
            "rater_id",
            "qgeval_total",
            "ulm_total",
        ]
    ].copy()
    raw_scores = ratings.rename(columns={"item_key": "target_id"})
    item_score_rows: list[dict[str, Any]] = []
    stat_rows: list[dict[str, Any]] = []
    boot_rows: list[dict[str, Any]] = []
    rng = np.random.default_rng(seed)
    for endpoint, score_column, scale_points in [
        ("QGEval", "qgeval_total", 35),
        ("ULM", "ulm_total", 76),
    ]:
        wide = ratings.pivot(index="item_key", columns="rater_id", values=score_column).sort_index()
        if wide.shape != (140, 3) or wide.isna().any().any():
            raise ValueError(
                f"Figure 2F {endpoint}: expected a complete 140-item × 3-expert matrix, found {wide.shape}."
            )
        for target_id, row in wide.iterrows():
            for rater_id, score in row.items():
                item_score_rows.append(
                    {
                        "endpoint": endpoint,
                        "scale_points": scale_points,
                        "target_id": target_id,
                        "rater_id": rater_id,
                        "score": score,
                    }
                )
        matrix = wide.to_numpy(float)
        estimate = icc_2_absolute_agreement(matrix)
        boot_estimates: list[float] = []
        for replicate in range(1, reps + 1):
            sampled = matrix[rng.integers(0, matrix.shape[0], size=matrix.shape[0]), :]
            value = icc_2_absolute_agreement(sampled)["icc_c_k"]
            boot_estimates.append(value)
            boot_rows.append(
                {
                    "endpoint": endpoint,
                    "bootstrap_replicate": replicate,
                    "icc_c_k": value,
                }
            )
        stat_rows.append(
            {
                "endpoint": endpoint,
                "scale_points": scale_points,
                **estimate,
                "icc_c_k_ci_low": nanquantile_or_nan(boot_estimates, 0.025),
                "icc_c_k_ci_high": nanquantile_or_nan(boot_estimates, 0.975),
                "ci_method": f"item bootstrap, {reps} replicates",
                "icc_model": (
                    "two-way random-effects average-measure consistency ICC(C,k) across three experts"
                ),
                "target_alignment": "source + item type + original item number + occurrence",
                "data_source": "plot/data/raw/expert_rating_workbooks",
            }
        )
    return (
        raw_scores,
        pd.DataFrame(item_score_rows),
        pd.DataFrame(stat_rows),
        pd.DataFrame(boot_rows),
    )


def figure2f() -> None:
    remove_output("Figure2E_run_consistency.pdf")
    for obsolete in [
        DERIVED / "fig2F_run_consistency_stats.csv",
        DERIVED / "fig2F_machine_rating_icc_item_scores.csv",
        DERIVED / "fig2F_machine_rating_icc_stats.csv",
        DERIVED / "fig2F_machine_rating_icc_bootstrap.csv",
    ]:
        if obsolete.exists():
            obsolete.unlink()
    raw_scores, item_scores, stats_df, boot = expert_inter_rater_endpoint_icc_data()
    write_csv(DERIVED / "fig2F_expert_inter_rater_raw_scores.csv", raw_scores)
    write_csv(DERIVED / "fig2F_expert_inter_rater_item_scores.csv", item_scores)
    write_csv(DERIVED / "fig2F_expert_inter_rater_icc_stats.csv", stats_df)
    write_csv(DERIVED / "fig2F_expert_inter_rater_icc_bootstrap.csv", boot)
    for obsolete in [
        DERIVED / "fig2F_subdimension_inter_rater_item_scores.csv",
        DERIVED / "fig2F_subdimension_inter_rater_icc_stats.csv",
        DERIVED / "fig2F_subdimension_inter_rater_icc_bootstrap.csv",
    ]:
        if obsolete.exists():
            obsolete.unlink()
    remove_output("Figure2F_run_consistency.pdf")
    remove_output("Figure2F_expert_inter_rater_reliability.pdf")

    fig, ax = plt.subplots(figsize=(4.5, 4.5))
    add_panel_label(fig, "F")
    y = np.arange(len(stats_df))[::-1]
    colors = [OPTIONAL_COLOR_PAIRS[index]["color"] for index in range(len(stats_df))]
    for ypos, row, color in zip(y, stats_df.itertuples(), colors):
        ax.errorbar(
            row.icc_c_k,
            ypos,
            xerr=[[row.icc_c_k - row.icc_c_k_ci_low], [row.icc_c_k_ci_high - row.icc_c_k]],
            fmt="o",
            color=color,
            ecolor=color,
            capsize=4,
            markersize=6,
            linewidth=1.2,
        )
        ax.text(
            row.icc_c_k_ci_high + 0.025,
            ypos,
            f"{row.icc_c_k:.3f} [{row.icc_c_k_ci_low:.3f}, {row.icc_c_k_ci_high:.3f}]",
            ha="left",
            va="center",
            fontsize=8,
        )
    ax.axvline(0, color=UROMAS_BASE_COLORS["spine"], linewidth=0.8)
    ax.set_yticks(y, stats_df.endpoint)
    ax.set_xlim(-0.05, 1.05)
    ax.set_xlabel("Average-measure consistency ICC(C,k), 95% CI")
    fig.suptitle("Expert inter-rater reliability", y=0.99, fontweight="bold")
    ax.text(
        0.50,
        -0.20,
        "Two-way random consistency ICC; k=3 experts. Points show ICC(C,k).",
        transform=ax.transAxes,
        ha="center",
        va="top",
        fontsize=6.5,
        color=UROMAS_BASE_COLORS["text"],
    )
    style_axes(ax)
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    # Match adjacent Figure 2E at both the top and bottom of the data area.
    fig.subplots_adjust(bottom=0.20, top=0.88)
    save_pdf(fig, "Figure2F_expert_inter_rater_reliability.pdf", tight=False)


# ---------------------------------------------------------------------------
# Figure 3


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


def independent_comparison(
    mas: np.ndarray,
    human: np.ndarray,
) -> tuple[str, float, str, float, float]:
    """Apply the prespecified KS-normality decision rule for Figures 3B/3C."""
    mas = np.asarray(mas, dtype=float)
    human = np.asarray(human, dtype=float)

    def ks_normality_p(values: np.ndarray) -> float:
        sd = float(np.std(values, ddof=1))
        if len(values) < 3 or not np.isfinite(sd) or sd == 0:
            return 0.0
        standardized = (values - float(np.mean(values))) / sd
        return float(stats.kstest(standardized, "norm").pvalue)

    mas_ks_p = ks_normality_p(mas)
    human_ks_p = ks_normality_p(human)
    if mas_ks_p >= 0.05 and human_ks_p >= 0.05:
        result = stats.ttest_ind(mas, human, equal_var=False)
        method = "Independent-samples Welch t-test"
    else:
        result = stats.mannwhitneyu(mas, human, alternative="two-sided")
        method = "Mann-Whitney U test"
    p_value = float(result.pvalue)
    return method, p_value, significance_stars(p_value), mas_ks_p, human_ks_p


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
        method, p_value, label, mas_ks_p, human_ks_p = independent_comparison(
            wide["MAS"].to_numpy(),
            wide["Human"].to_numpy(),
        )
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
                "mas_ks_normality_p": mas_ks_p,
                "human_ks_normality_p": human_ks_p,
                "p_value": p_value,
                "significance_label": label,
            }
        )
        for student_id, row in wide.iterrows():
            for source in ["Human", "MAS"]:
                raw_rows.append({"panel": panel, "student_id": student_id, "source_true": source, "correct_rate": row[source]})
    write_csv(DERIVED / "fig3B_student_correct_rate_stats.csv", stat_rows)
    write_csv(DERIVED / "fig3B_student_correct_rate_raw.csv", raw_rows)

    fig, axes = plt.subplots(1, 3, figsize=(9.0, 4.5), sharey=True)
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
            body.set_alpha(0.78)
            q1, median, q3 = np.percentile(values, [25, 50, 75])
            ax.hlines(
                [q1, q3],
                position - 0.20,
                position + 0.20,
                color=CORE_COLORS[source],
                linewidth=0.9,
                linestyle=":",
            )
            ax.hlines(
                median,
                position - 0.20,
                position + 0.20,
                color=CORE_COLORS[source],
                linewidth=1.5,
            )
            ax.scatter(rng.normal(position, 0.035, len(values)), values, s=9, color=CORE_COLORS[source], alpha=0.45, linewidths=0)
        ymax = max(sub.correct_rate.max() + 0.06, 0.93)
        ax.plot([1, 1, 2, 2], [ymax - 0.01, ymax, ymax, ymax - 0.01], color=UROMAS_BASE_COLORS["text_dark"], linewidth=0.8)
        ax.text(1.5, ymax + 0.015, stat_row["significance_label"], ha="center", fontweight="bold", fontsize=8)
        ax.text(
            1.5,
            0.285,
            f"{stat_row['method']}\nP={stat_row['p_value']:.3f}",
            ha="center",
            va="bottom",
            fontsize=6.5,
        )
        ax.set_title(stat_row["panel"])
        ax.set_xticks([1, 2], ["MAS", "Human"])
        ax.tick_params(axis="x", rotation=35)
        ax.set_xlabel("MCQ source", fontweight="bold")
        ax.set_ylim(0.25, 1.08)
        style_axes(ax)
    axes[0].set_ylabel("Correct response rate")
    fig.suptitle("Student overall correct rate by source", y=0.985)
    fig.legend(
        handles=[
            Patch(facecolor=CORE_FILLS["MAS"], edgecolor=CORE_COLORS["MAS"], label="MAS"),
            Patch(facecolor=CORE_FILLS["Human"], edgecolor=CORE_COLORS["Human"], label="Human"),
        ],
        frameon=False,
        loc="upper right",
        bbox_to_anchor=(0.995, 0.965),
    )
    # Figure 3B, 3D, and 3F occupy the same assembled columns; align their
    # left and right plot bounds while retaining the three internal panels.
    fig.subplots_adjust(left=0.148, right=0.985, bottom=0.22, top=0.78, wspace=0.34)
    save_pdf(fig, "Figure3B_student_correct_rate.pdf", tight=False)


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
            method, p_value, label, mas_ks_p, human_ks_p = independent_comparison(
                wide["MAS"].to_numpy(),
                wide["Human"].to_numpy(),
            )
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
                        "mas_ks_normality_p": mas_ks_p,
                        "human_ks_normality_p": human_ks_p,
                        "p_value": p_value,
                        "significance_label": label,
                    }
                )
    plot_df = pd.DataFrame(plot_rows)
    write_csv(DERIVED / "fig3C_student_accuracy_horizontal_stats.csv", plot_df)
    write_csv(DERIVED / "fig3C_student_accuracy_student_rates.csv", rates)

    fig, axes = plt.subplots(1, 3, figsize=(9.0, 4.5), sharey=True)
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
            ax.text(103, ypos, label, ha="left", va="center", fontsize=8)
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
    # Figure 3C and 3E share the same assembled columns.
    fig.subplots_adjust(left=0.12, right=0.985, bottom=0.182)
    save_pdf(fig, "Figure3C_student_accuracy_by_cognitive_level.pdf", tight=False)


def permutation_mean_difference_pvalue(
    first: np.ndarray,
    second: np.ndarray,
    seed: int,
    max_exact: int = 200_000,
    n_resamples: int = 100_000,
) -> tuple[float, str, int]:
    first = np.asarray(first, dtype=float)
    second = np.asarray(second, dtype=float)
    values = np.concatenate([first, second])
    n_first = len(first)
    observed = float(first.mean() - second.mean())
    total = math.comb(len(values), n_first)
    tolerance = 1e-12

    if total <= max_exact:
        count = 0
        indices = np.arange(len(values))
        for chosen in itertools.combinations(indices, n_first):
            mask = np.zeros(len(values), dtype=bool)
            mask[list(chosen)] = True
            difference = float(values[mask].mean() - values[~mask].mean())
            if abs(difference) >= abs(observed) - tolerance:
                count += 1
        return count / total, f"exact permutation ({total} labelings)", total

    rng = np.random.default_rng(seed)
    count = 0
    for _ in range(n_resamples):
        permuted = rng.permutation(values)
        difference = float(permuted[:n_first].mean() - permuted[n_first:].mean())
        if abs(difference) >= abs(observed) - tolerance:
            count += 1
    return (count + 1) / (n_resamples + 1), f"Monte Carlo permutation ({n_resamples} draws)", n_resamples


def adjusted_interaction_data() -> tuple[pd.DataFrame, pd.DataFrame, str]:
    responses = pd.read_csv(DERIVED / "responses.csv")
    item = pd.read_csv(DERIVED / "item_master.csv")[
        ["item_id", "blueprint_cognitive_level", "topic"]
    ]
    data = responses.merge(item, on="item_id", how="left")
    formula = (
        "correct ~ C(item_id) + C(block_position) + C(training_setting)"
        " + C(training_year) + C(form)"
    )
    fit = smf.glm(formula, data=data, family=sm.families.Binomial()).fit(
        maxiter=200,
    )
    if not fit.converged:
        raise RuntimeError("Figure 3D covariate-standardized item GLM did not converge.")

    adjusted_rows: list[dict[str, Any]] = []
    student_covariates = (
        data[["student_id", "training_setting", "training_year", "form"]]
        .drop_duplicates()
        .sort_values("student_id")
        .reset_index(drop=True)
    )
    block_positions = sorted(data.block_position.dropna().unique())
    item_meta = (
        data[
            [
                "item_id",
                "paper",
                "paper_item_no",
                "source_true",
                "blueprint_cognitive_level",
                "topic",
            ]
        ]
        .drop_duplicates()
        .sort_values(["source_true", "paper_item_no", "item_id"])
    )
    adjustment_note = (
        "Item-level probabilities were standardized after a binomial GLM with item "
        "fixed effects, block position, training setting/campus, training year, "
        "and randomized form. The standardization averages each item over all "
        "students and both block positions."
    )

    for row in item_meta.itertuples(index=False):
        scenarios = []
        for block_position in block_positions:
            scenario = student_covariates.copy()
            scenario["item_id"] = row.item_id
            scenario["block_position"] = block_position
            scenarios.append(scenario)
        scenario_data = pd.concat(scenarios, ignore_index=True)
        probabilities = fit.predict(scenario_data)
        adjusted_rows.append(
            {
                "item_id": row.item_id,
                "paper": row.paper,
                "paper_item_no": row.paper_item_no,
                "source_true": row.source_true,
                "cognitive_level": row.blueprint_cognitive_level,
                "topic": row.topic,
                "adjusted_correct_probability": float(np.mean(probabilities)),
                "min_standardized_probability": float(np.min(probabilities)),
                "max_standardized_probability": float(np.max(probabilities)),
                "n_standardization_students": int(student_covariates.student_id.nunique()),
                "n_standardization_scenarios": int(len(scenario_data)),
                "standardized_block_positions": ";".join(map(str, block_positions)),
                "model_formula": formula,
                "adjustment_note": adjustment_note,
            }
        )

    adjusted = pd.DataFrame(adjusted_rows)
    contrast_rows: list[dict[str, Any]] = []
    for level in LEVELS_4:
        human = adjusted[
            adjusted.source_true.eq("Human") & adjusted.cognitive_level.eq(level)
        ].adjusted_correct_probability.to_numpy(float)
        mas = adjusted[
            adjusted.source_true.eq("MAS") & adjusted.cognitive_level.eq(level)
        ].adjusted_correct_probability.to_numpy(float)
        estimate = float(mas.mean() - human.mean())
        n_mas = len(mas)
        n_human = len(human)
        var_mas = float(np.var(mas, ddof=1)) if n_mas > 1 else 0.0
        var_human = float(np.var(human, ddof=1)) if n_human > 1 else 0.0
        se = float(math.sqrt(var_mas / n_mas + var_human / n_human))
        if se > 0:
            numerator = (var_mas / n_mas + var_human / n_human) ** 2
            denominator = 0.0
            if n_mas > 1 and var_mas > 0:
                denominator += (var_mas / n_mas) ** 2 / (n_mas - 1)
            if n_human > 1 and var_human > 0:
                denominator += (var_human / n_human) ** 2 / (n_human - 1)
            welch_df = numerator / denominator if denominator > 0 else float("nan")
            t_value = estimate / se
            welch_p_value = float(2 * stats.t.sf(abs(t_value), welch_df))
            t_critical = float(stats.t.ppf(0.975, welch_df))
        else:
            welch_df = float("nan")
            t_value = float("nan")
            welch_p_value = float("nan")
            t_critical = float("nan")
        permutation_p_value, permutation_method, n_permutations = (
            permutation_mean_difference_pvalue(mas, human, seed=530 + LEVELS_4.index(level))
        )
        contrast_rows.append(
            {
                "cognitive_level": level,
                "estimate_mas_minus_human": estimate,
                "welch_se": se,
                "welch_df": welch_df,
                "welch_t": t_value,
                "welch_ci_low": estimate - t_critical * se if np.isfinite(t_critical) else float("nan"),
                "welch_ci_high": estimate + t_critical * se if np.isfinite(t_critical) else float("nan"),
                "welch_p_value": welch_p_value,
                "p_value": permutation_p_value,
                "comparison_method": permutation_method,
                "n_permutation_labelings_or_draws": n_permutations,
                "n_mas_items": n_mas,
                "n_human_items": n_human,
                "n_students": data.student_id.nunique(),
                "n_responses": len(data),
                "model_formula": formula,
                "adjustment_note": adjustment_note,
            }
        )
    return adjusted, pd.DataFrame(contrast_rows), formula


def figure3d_adjusted() -> None:
    for obsolete in [
        DERIVED / "fig3D_student_level_source_cognitive_rates.csv",
        DERIVED / "fig3D_source_cognitive_paired_comparisons.csv",
        DERIVED / "fig3D_adjusted_student_probabilities.csv",
    ]:
        if obsolete.exists():
            obsolete.unlink()
    adjusted, contrasts, _ = adjusted_interaction_data()
    summary = (
        adjusted.groupby(["source_true", "cognitive_level"], observed=True)
        .agg(
            n_items=("item_id", "count"),
            mean_adjusted_correct_probability=("adjusted_correct_probability", "mean"),
            sd_adjusted_correct_probability=("adjusted_correct_probability", "std"),
            q1_adjusted_correct_probability=(
                "adjusted_correct_probability",
                lambda values: values.quantile(0.25),
            ),
            median_adjusted_correct_probability=("adjusted_correct_probability", "median"),
            q3_adjusted_correct_probability=(
                "adjusted_correct_probability",
                lambda values: values.quantile(0.75),
            ),
            min_adjusted_correct_probability=("adjusted_correct_probability", "min"),
            max_adjusted_correct_probability=("adjusted_correct_probability", "max"),
        )
        .reset_index()
    )
    write_csv(DERIVED / "fig3D_adjusted_item_probabilities.csv", adjusted)
    write_csv(DERIVED / "fig3D_adjusted_probability_summary.csv", summary)
    write_csv(DERIVED / "fig3D_source_cognitive_interaction_contrasts.csv", contrasts)

    fig, ax = plt.subplots(figsize=(9.0, 4.5))
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
            ].adjusted_correct_probability.to_numpy(float)
            for level in LEVELS_4
        ]
        positions = x + offsets[source]
        box = ax.boxplot(
            groups,
            positions=positions,
            widths=width,
            patch_artist=True,
            showfliers=False,
            whis=(0, 100),
            medianprops={"color": CORE_COLORS[source], "linewidth": 0.0},
            whiskerprops={"color": CORE_COLORS[source], "linewidth": 0.8},
            capprops={"color": CORE_COLORS[source], "linewidth": 0.8},
        )
        for patch in box["boxes"]:
            patch.set_facecolor(CORE_FILLS[source])
            patch.set_edgecolor(CORE_COLORS[source])
            patch.set_alpha(0.94)
            patch.set_linewidth(1.0)
        means = [float(np.mean(group)) for group in groups]
        mean_lines[source] = means
        for position, mean in zip(positions, means):
            ax.hlines(
                mean,
                position - width / 2,
                position + width / 2,
                color=UROMAS_BASE_COLORS["text_dark"],
                linewidth=1.15,
                zorder=4,
            )
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
    y_min = max(
        0.0,
        float(adjusted.adjusted_correct_probability.min()) - 0.06,
    )
    y_max = min(
        1.10,
        float(adjusted.adjusted_correct_probability.max()) + 0.10,
    )
    for index, row in contrasts.iterrows():
        p_value = row["p_value"]
        label = "P<0.001" if p_value < 0.001 else f"P={p_value:.3f}"
        upper = max(
            adjusted[adjusted.cognitive_level.eq(row.cognitive_level)].adjusted_correct_probability.max(),
            mean_lines["Human"][index],
            mean_lines["MAS"][index],
            summary[summary.cognitive_level.eq(row.cognitive_level)].max_adjusted_correct_probability.max(),
        )
        ax.text(index, min(y_max - 0.03, upper + 0.04), label, ha="center", va="bottom", fontsize=8)
    ax.set_xticks(x, [LEVEL_LABELS_4[level] for level in LEVELS_4])
    ax.set_ylim(y_min, y_max)
    ax.set_ylabel("Adjusted correct-answer probability")
    fig.suptitle("Adjusted source x cognitive-level interaction", y=0.99, fontweight="bold")
    ax.legend(frameon=False, ncol=2, loc="lower left")
    fig.text(
        0.98,
        0.035,
        "Item-level boxes use min-max whiskers; dark bars and connected dots are means.",
        ha="right",
        va="bottom",
        fontsize=6.5,
        color=UROMAS_BASE_COLORS["text"],
    )
    style_axes(ax)
    fig.tight_layout(rect=[0, 0.08, 1, 0.93])
    # Align with Figure 3C horizontally and with Figure 3B/3F vertically.
    fig.subplots_adjust(left=0.148, right=0.985, bottom=0.182)
    save_pdf(fig, "Figure3D_source_cognitive_interaction.pdf", tight=False)


def figure3d_paired_unused() -> None:
    for obsolete in [
        DERIVED / "fig3D_adjusted_student_probabilities.csv",
        DERIVED / "fig3D_source_cognitive_interaction_contrasts.csv",
    ]:
        if obsolete.exists():
            obsolete.unlink()

    rates = student_level_rates()
    rate_rows: list[dict[str, Any]] = []
    comparison_rows: list[dict[str, Any]] = []
    for level_index, level in enumerate(LEVELS_4):
        wide = (
            rates[rates.blueprint_cognitive_level.eq(level)]
            .pivot(index="student_id", columns="source_true", values="correct_rate")
            .dropna()
        )
        method, p_value, _ = paired_comparison(wide["MAS"].to_numpy(), wide["Human"].to_numpy())
        label = "n.s."
        human_mean, human_low, human_high = bootstrap_mean_ci(
            wide["Human"].to_numpy(),
            seed=430 + level_index * 4,
        )
        mas_mean, mas_low, mas_high = bootstrap_mean_ci(
            wide["MAS"].to_numpy(),
            seed=431 + level_index * 4,
        )
        diff = wide["MAS"].to_numpy() - wide["Human"].to_numpy()
        diff_mean, diff_low, diff_high = bootstrap_mean_ci(
            diff,
            seed=432 + level_index * 4,
        )
        comparison_rows.append(
            {
                "cognitive_level": level,
                "cognitive_level_label": LEVEL_LABELS_4[level],
                "n_students": len(wide),
                "human_mean_correct_rate": human_mean,
                "human_ci_low": human_low,
                "human_ci_high": human_high,
                "mas_mean_correct_rate": mas_mean,
                "mas_ci_low": mas_low,
                "mas_ci_high": mas_high,
                "mean_difference_mas_minus_human": diff_mean,
                "difference_ci_low": diff_low,
                "difference_ci_high": diff_high,
                "comparison_method": method,
                "p_value": p_value,
                "significance_label": label,
                "analysis_note": "Same student-level paired comparison as Figure 3C; no covariate adjustment.",
            }
        )
        for student_id, row in wide.iterrows():
            for source in ["Human", "MAS"]:
                rate_rows.append(
                    {
                        "student_id": student_id,
                        "cognitive_level": level,
                        "source_true": source,
                        "correct_rate": row[source],
                    }
                )

    plot_rates = pd.DataFrame(rate_rows)
    comparisons = pd.DataFrame(comparison_rows)
    write_csv(DERIVED / "fig3D_student_level_source_cognitive_rates.csv", plot_rates)
    write_csv(DERIVED / "fig3D_source_cognitive_paired_comparisons.csv", comparisons)

    fig, ax = plt.subplots(figsize=(9.0, 4.5))
    add_panel_label(fig, "D")
    x = np.arange(len(LEVELS_4), dtype=float)
    offsets = {"Human": -0.18, "MAS": 0.18}
    width = 0.30
    mean_lines: dict[str, list[float]] = {}
    for source in ["Human", "MAS"]:
        groups = [
            plot_rates[
                plot_rates.source_true.eq(source)
                & plot_rates.cognitive_level.eq(level)
            ].correct_rate.to_numpy()
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
    for index, row in comparisons.iterrows():
        upper = max(
            plot_rates[plot_rates.cognitive_level.eq(row.cognitive_level)].correct_rate.max(),
            mean_lines["Human"][index],
            mean_lines["MAS"][index],
        )
        ax.text(index, min(1.03, upper + 0.05), row["significance_label"], ha="center", va="bottom", fontsize=8)
    ax.set_xticks(x, [LEVEL_LABELS_4[level] for level in LEVELS_4])
    ax.set_ylim(0.18, 1.08)
    ax.set_ylabel("Student-level correct-answer rate")
    ax.set_title("Student source × cognitive-level comparison", fontweight="bold")
    ax.legend(frameon=False, ncol=2, loc="lower left")
    ax.text(
        0.98,
        0.04,
        "Same method as Figure 3C: paired student-level comparison;\nno covariate adjustment.",
        transform=ax.transAxes,
        ha="right",
        va="bottom",
        fontsize=6.5,
        color=UROMAS_BASE_COLORS["text"],
    )
    style_axes(ax)
    save_pdf(fig, "Figure3D_source_cognitive_interaction.pdf")


def figure3d() -> None:
    figure3d_adjusted()


def ctt_upper_lower_data() -> pd.DataFrame:
    responses = pd.read_csv(DERIVED / "responses.csv")
    item = pd.read_csv(DERIVED / "item_master.csv")[
        ["item_id", "source_true", "blueprint_cognitive_level", "item_type"]
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


def figure3e_old_boxplots_unused() -> None:
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

    fig, axes = plt.subplots(1, 2, figsize=(9.0, 4.5))
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


def figure3e_upper_lower_unused() -> None:
    ctt = ctt_upper_lower_data()
    ctt["item_type_group"] = np.select(
        [
            ctt.item_type.isin(["A1", "B"]),
            ctt.item_type.isin(["A2", "A3", "A4"]),
            ctt.item_type.eq("X"),
        ],
        ["A1/B", "A2/A3/A4", "X"],
        default=ctt.item_type.astype(str),
    )
    summary = (
        ctt.groupby(["source_true", "blueprint_cognitive_level", "item_type_group"])
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

    fit_data = ctt[["difficulty", "discrimination_upper_minus_lower"]].dropna()
    slope, intercept = np.polyfit(
        fit_data.difficulty.to_numpy(),
        fit_data.discrimination_upper_minus_lower.to_numpy(),
        deg=1,
    )
    correlation = stats.pearsonr(
        fit_data.difficulty.to_numpy(),
        fit_data.discrimination_upper_minus_lower.to_numpy(),
    )
    write_csv(
        DERIVED / "fig3E_ctt_linear_fit.csv",
        [
            {
                "model": "ordinary least-squares line",
                "formula": "discrimination_upper_minus_lower ~ difficulty",
                "slope": slope,
                "intercept": intercept,
                "pearson_r": correlation.statistic,
                "pearson_p_value": correlation.pvalue,
                "n_items": len(fit_data),
            }
        ],
    )

    fig, ax = plt.subplots(figsize=(9.0, 4.5))
    add_panel_label(fig, "E")
    marker_map = {"A1/B": "o", "A2/A3/A4": "s", "X": "^"}
    for source in ["MAS", "Human"]:
        for marker_group, marker in marker_map.items():
            sub = ctt[ctt.source_true.eq(source) & ctt.item_type_group.eq(marker_group)]
            ax.scatter(
                sub.difficulty,
                sub.discrimination_upper_minus_lower,
                marker=marker,
                s=36,
                color=CORE_COLORS[source],
                alpha=0.72,
                edgecolors="white",
                linewidths=0.35,
            )
    x_line = np.linspace(0, 1, 200)
    ax.plot(
        x_line,
        intercept + slope * x_line,
        color=UROMAS_BASE_COLORS["text_dark"],
        linewidth=1.4,
        linestyle="-",
        zorder=3,
    )
    ax.axhline(0.20, color=UROMAS_BASE_COLORS["spine"], linestyle=":", linewidth=1.0)
    ax.axvline(0.50, color=UROMAS_BASE_COLORS["spine"], linestyle=":", linewidth=1.0)
    ax.set_xlim(0, 1.02)
    ax.set_ylim(-0.36, 0.62)
    ax.set_xlabel("Item difficulty (proportion correct)")
    ax.set_ylabel("Discrimination (upper 27% − lower 27%)")
    ax.set_title("Exploratory CTT (objective items)", fontweight="bold")
    source_handles = [
        Line2D([0], [0], marker="o", color="none", markerfacecolor=CORE_COLORS["MAS"], markeredgecolor="white", markersize=6, label="MAS"),
        Line2D([0], [0], marker="o", color="none", markerfacecolor=CORE_COLORS["Human"], markeredgecolor="white", markersize=6, label="Human"),
    ]
    marker_handles = [
        Line2D([0], [0], marker=marker, color=UROMAS_BASE_COLORS["tick"], linestyle="none", markersize=6, label=label)
        for label, marker in marker_map.items()
    ]
    fit_handle = Line2D([0], [0], color=UROMAS_BASE_COLORS["text_dark"], linewidth=1.4, label="Linear fit")
    ax.legend(handles=source_handles + marker_handles + [fit_handle], frameon=False, loc="lower left")
    slope_text = f"+ {slope:.2f}x" if slope >= 0 else f"− {abs(slope):.2f}x"
    ax.text(
        0.98,
        0.05,
        f"Fit: y = {intercept:.2f} {slope_text}\nr={correlation.statistic:.2f}",
        transform=ax.transAxes,
        ha="right",
        va="bottom",
        fontsize=6.5,
        color=UROMAS_BASE_COLORS["text"],
    )
    style_axes(ax)
    save_pdf(fig, "Figure3E_ctt_by_cognitive_level.pdf")


def figure3e() -> None:
    ctt = pd.read_csv(DERIVED / "ctt_item_analysis.csv").merge(
        pd.read_csv(DERIVED / "item_master.csv")[["item_id", "item_type", "blueprint_cognitive_level"]],
        on="item_id",
        how="left",
        validate="one_to_one",
    )
    ctt["item_type_group"] = np.select(
        [
            ctt.item_type.isin(["A1", "B"]),
            ctt.item_type.isin(["A2", "A3", "A4", "A3/A4"]),
            ctt.item_type.eq("X"),
        ],
        ["A1/B", "A2/A3/A4", "X"],
        default=ctt.item_type.astype(str),
    )
    ctt["cognitive_level"] = ctt["blueprint_cognitive_level"]
    ctt["cognitive_level_label"] = ctt.cognitive_level.map(LEVEL_LABELS_4)
    write_csv(DERIVED / "fig3E_ctt_scatter_item_data.csv", ctt)
    ctt = ctt.dropna(subset=["difficulty", "discrimination"]).copy()
    ctt["item_type_group"] = pd.Categorical(
        ctt["item_type_group"],
        ["A1/B", "A2/A3/A4", "X"],
        ordered=True,
    )
    summary = (
        ctt.groupby(["source_true", "item_type_group"], observed=True)
        .agg(
            n_items=("item_id", "count"),
            mean_difficulty=("difficulty", "mean"),
            sd_difficulty=("difficulty", "std"),
            mean_item_rest_discrimination=("discrimination", "mean"),
            sd_item_rest_discrimination=("discrimination", "std"),
        )
        .reset_index()
    )
    write_csv(DERIVED / "fig3E_ctt_scatter_summary.csv", summary)

    fit_x = summary.mean_difficulty.to_numpy(float)
    fit_y = summary.mean_item_rest_discrimination.to_numpy(float)
    fit_result = stats.linregress(fit_x, fit_y)
    write_csv(
        DERIVED / "fig3E_ctt_linear_fit.csv",
        [
            {
                "model": "ordinary least-squares line with intercept fitted to source x item-type mean points",
                "formula": "mean_item_rest_discrimination = k * mean_difficulty + b",
                "slope_k": fit_result.slope,
                "intercept_b": fit_result.intercept,
                "pearson_r": fit_result.rvalue,
                "pearson_p_value": fit_result.pvalue,
                "n_fit_points": len(summary),
                "n_items_underlying": len(ctt),
                "fit_data_source": "fig3E_ctt_scatter_summary.csv; grouped by source_true x item_type_group",
            }
        ],
    )

    fig, ax = plt.subplots(figsize=(9.0, 4.5))
    add_panel_label(fig, "E")
    marker_map = {"A1/B": "o", "A2/A3/A4": "s", "X": "^"}
    for source in ["MAS", "Human"]:
        for marker_group, marker in marker_map.items():
            sub = ctt[ctt.source_true.eq(source) & ctt.item_type_group.eq(marker_group)]
            ax.scatter(
                sub.difficulty,
                sub.discrimination,
                marker=marker,
                s=40,
                color=CORE_COLORS[source],
                alpha=0.72,
                edgecolors="white",
                linewidths=0.25,
            )
    for source in ["MAS", "Human"]:
        sub_summary = summary[summary.source_true.eq(source)]
        ax.scatter(
            sub_summary.mean_difficulty,
            sub_summary.mean_item_rest_discrimination,
            marker="D",
            s=68,
            facecolors="white",
            edgecolors=CORE_COLORS[source],
            linewidths=1.1,
            zorder=5,
        )
    x_line = np.linspace(0, 1.0, 200)
    ax.plot(
        x_line,
        fit_result.intercept + fit_result.slope * x_line,
        color=UROMAS_BASE_COLORS["text_dark"],
        linewidth=1.3,
        linestyle="-",
        zorder=3,
    )
    ax.axhline(0.20, color=UROMAS_BASE_COLORS["spine"], linestyle=":", linewidth=1.3)
    ax.axvline(0.50, color=UROMAS_BASE_COLORS["spine"], linestyle=":", linewidth=1.3)
    ax.set_xlim(0, 1.02)
    ax.set_ylim(-0.36, 0.62)
    ax.set_xlabel("Item difficulty (prop. correct)")
    ax.set_ylabel("Discrimination (item-rest $r$)")
    ax.set_title("Exploratory CTT (objective items)", fontweight="bold")
    source_handles = [
        Line2D([0], [0], marker="o", color="none", markerfacecolor=CORE_COLORS["MAS"], markeredgecolor="white", markersize=6.5, label="MAS"),
        Line2D([0], [0], marker="o", color="none", markerfacecolor=CORE_COLORS["Human"], markeredgecolor="white", markersize=6.5, label="Human"),
    ]
    marker_handles = [
        Line2D([0], [0], marker=marker, color=UROMAS_BASE_COLORS["tick"], linestyle="none", markersize=6.5, label=label)
        for label, marker in marker_map.items()
    ]
    mean_handle = Line2D(
        [0],
        [0],
        marker="D",
        color=UROMAS_BASE_COLORS["text_dark"],
        markerfacecolor="white",
        linestyle="none",
        markersize=6,
        label="Group means",
    )
    fit_handle = Line2D([0], [0], color=UROMAS_BASE_COLORS["text_dark"], linewidth=1.3, label="Fit: y = kx + b")
    ax.legend(handles=source_handles + marker_handles + [mean_handle, fit_handle], frameon=False, loc="lower left")
    ax.text(
        0.98,
        0.05,
        f"Group-mean fit: y = {fit_result.slope:.2f}x + {fit_result.intercept:.2f}\nr={fit_result.rvalue:.2f}",
        transform=ax.transAxes,
        ha="right",
        va="bottom",
        fontsize=6.5,
        color=UROMAS_BASE_COLORS["text"],
    )
    style_axes(ax)
    fig.tight_layout()
    fig.subplots_adjust(left=0.12, right=0.985)
    save_pdf(fig, "Figure3E_ctt_by_cognitive_level.pdf", tight=False)


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

    fig, ax = plt.subplots(figsize=(9.0, 4.5))
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
    fig.tight_layout()
    fig.subplots_adjust(left=0.148, right=0.985)
    save_pdf(fig, "Figure3F_reliability.pdf", tight=False)


# ---------------------------------------------------------------------------
# Figure 4: 4A reserved; old 4A->4B, old 4B->4C, new 4D and 4E


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
                "ci_method": "Wilson 90% CI",
            }
        )
    stats_df = pd.DataFrame(rows)
    write_csv(DERIVED / "fig4B_expert_source_identification_accuracy.csv", stats_df)

    fig = plt.figure(figsize=(9.0, 4.5))
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
    table.set_fontsize(6.5)
    table.scale(1.0, 1.35)
    # Match the horizontal-axis baseline of adjacent Figure 4C.
    fig.subplots_adjust(bottom=0.22, top=0.93)
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

    fig, ax = plt.subplots(figsize=(4.5, 4.5))
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
                ax.text(xpos, base + value / 2, f"{value:.1f}%", ha="center", va="center", color="white", fontsize=8)
        bottom += values
    ax.set_xticks(x, ["Human-authored items", "MAS-generated items"])
    ax.set_ylabel("Expert judgments (%)")
    ax.set_ylim(0, 100)
    ax.set_title("Expert source-judgment confusion matrix", fontweight="bold")
    ax.legend(frameon=False, ncol=2, loc="upper center", bbox_to_anchor=(0.5, -0.18))
    style_axes(ax)
    fig.tight_layout()
    # Figure 4C and 4F share a column; reserve the same left/right bounds.
    fig.subplots_adjust(left=0.227, right=0.973, bottom=0.22, top=0.93)
    save_pdf(fig, "Figure4C_expert_source_confusion_matrix.pdf", tight=False)


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

    fig, ax = plt.subplots(figsize=(4.5, 4.5))
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
    plt.setp(
        ax.get_yticklabels(),
        rotation=25,
        ha="right",
        va="center",
        rotation_mode="anchor",
        fontsize=6.5,
    )
    ax.set_xlabel("Odds ratio for being guessed as MAS\n(95% credible interval)")
    ax.set_title("Expert guessed-MAS mixed model", fontweight="bold")
    style_axes(ax, "x")
    fig.subplots_adjust(left=0.42, right=0.96, bottom=0.20, top=0.88)
    save_pdf(fig, "Figure4D_expert_guessed_MAS_model_forest.pdf", tight=False)


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

    fig = plt.figure(figsize=(9.0, 4.5))
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
    table.set_fontsize(6.5)
    table.scale(1.0, 1.4)
    # Figure 4D-F form one row; keep their horizontal axes collinear.
    fig.subplots_adjust(bottom=0.20, top=0.88)
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
    fig, ax = plt.subplots(figsize=(4.5, 4.5))
    add_panel_label(fig, "F")
    y = np.arange(len(scenarios))[::-1]
    ax.barh(y, scenarios.minutes_per_item.iloc[::-1], color=OPTIONAL_COLOR_PAIRS[2]["color"])
    ax.set_yticks(y, scenarios.scenario.iloc[::-1])
    ax.set_xlabel("Minutes per generated item")
    ax.set_title("MAS timing sensitivity", fontweight="bold")
    style_axes(ax, "x")
    fig.tight_layout()
    fig.subplots_adjust(left=0.227, right=0.973, bottom=0.20, top=0.88)
    save_pdf(fig, "Figure4F_efficiency_sensitivity.pdf", tight=False)


# ---------------------------------------------------------------------------
# Figure 5: workflow efficiency


EFFICIENCY_TYPES = ["A1", "A2", "A3/A4", "B", "X"]
EFFICIENCY_TYPE_COLORS = {
    # Figure 5A uses an ordered monochromatic green ramp for item types.
    "A1": {"color": "#0B4F3A", "fill": "#DCEFE7"},
    "A2": {"color": "#197257", "fill": "#D5EAE1"},
    "A3/A4": {"color": "#2F9470", "fill": "#C8E2D5"},
    "B": {"color": "#66B58D", "fill": "#D8EBDD"},
    "X": {"color": "#A7D7BC", "fill": "#E8F4ED"},
}
FINAL_ITEM_COUNTS = {"A1": 7, "A2": 18, "A3/A4": 14, "B": 3, "X": 8}
DEEPSEEK_PRICING_SOURCE = "https://api-docs.deepseek.com/quick_start/pricing"
DEEPSEEK_PRICES_USD_PER_M = {
    "deepseek-v4-flash": {"input": 0.14, "output": 0.28},
    "deepseek-v4-pro": {"input": 0.435, "output": 0.87},
}
USD_TO_CNY_FOR_FIG5 = 6.80


def parse_sum_expression(value: Any) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    parts = re.findall(r"\d+(?:\.\d+)?", str(value))
    return float(sum(float(part) for part in parts))


def read_docx_text(path: Path) -> str:
    with ZipFile(path) as archive:
        root = ET.fromstring(archive.read("word/document.xml"))
    return "\n".join(
        "".join(node.text or "" for node in paragraph.iter() if node.tag.endswith("}t"))
        for paragraph in root.iter()
        if paragraph.tag.endswith("}p")
    )


def efficiency_time_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = read_sheet_rows(PLOT_RAW_DATA_DIR / "效率分析.xlsx", "Sheet1")
    row_map: dict[str, list[Any]] = {}
    for row in rows:
        if not row or row[0] is None:
            continue
        key = str(row[0]).strip()
        if key == "A3/4":
            key = "A3/A4"
        if key not in row_map:
            row_map[key] = row
        if (
            key in EFFICIENCY_TYPES
            and len(row) > 3
            and isinstance(row[2], (int, float))
            and isinstance(row[3], (int, float))
        ):
            row_map[key] = row
    human_rows = []
    for item_type in EFFICIENCY_TYPES:
        row = row_map[item_type]
        human_rows.append(
            {
                "item_type": item_type,
                "final_items": FINAL_ITEM_COUNTS[item_type],
                "human_selected_seconds": float(row[2]),
                "human_source_workbook_average_seconds_per_authored_item": float(row[3]),
            }
        )
    human = pd.DataFrame(human_rows)
    human["human_selected_seconds_per_final_item"] = (
        human.human_selected_seconds / human.final_items
    )

    efficiency_docx = PLOT_RAW_DATA_DIR / "人工卷用时及成本.docx"
    if not efficiency_docx.exists():
        raise FileNotFoundError(f"Missing efficiency cross-check source: {efficiency_docx}")
    efficiency_docx_text = read_docx_text(efficiency_docx)
    expected_selected_seconds = {
        row.item_type: int(row.human_selected_seconds)
        for row in human.itertuples()
    }
    for item_type, seconds in expected_selected_seconds.items():
        if str(seconds) not in efficiency_docx_text:
            raise ValueError(
                f"Efficiency sources disagree: {item_type} selected time {seconds} s is absent from the DOCX."
            )
    if int(human.human_selected_seconds.sum()) != 77538 or "77538" not in efficiency_docx_text:
        raise ValueError("Efficiency sources disagree on the 50 selected Human items' total time.")

    timing = pd.read_csv(DERIVED / "mas_question_generation_time.csv")
    timing["bank_type"] = timing.bank_type.astype(str)
    observed = {
        row.bank_type: float(row.seconds_per_item)
        for row in timing.itertuples()
    }
    a34_generated = timing[timing.bank_type.isin(["A3", "A4"])]
    a34_seconds = float(a34_generated.total_generation_seconds.sum())
    a34_items = float(a34_generated.generated_items.sum())
    observed["A3/A4"] = a34_seconds / a34_items

    invocation_path = (
        REPO_ROOT
        / "timing_runs"
        / "20260522_095242"
        / "mas_question_generation_time_invocations.csv"
    )
    if invocation_path.exists():
        invocations = pd.read_csv(invocation_path)
        structured_call_seconds = float(
            invocations.loc[
                invocations.phase.eq("add_test_point"),
                "elapsed_seconds",
            ].mean()
        )
    else:
        structured_call_seconds = 40.225227

    # Four independent QGval runs plus four independent ULM runs, with the
    # scripts processing each item-type bank as one call per run.
    rating_calls = {"A1": 8, "A2": 8, "A3/A4": 16, "B": 8, "X": 8}
    local_check_seconds_total = 60.0
    mas_rows = []
    for item_type in EFFICIENCY_TYPES:
        count = FINAL_ITEM_COUNTS[item_type]
        generation_seconds = observed[item_type] * count
        automated_rating_seconds = rating_calls[item_type] * structured_call_seconds
        local_seconds = local_check_seconds_total * count / 50.0
        total_seconds = generation_seconds + automated_rating_seconds + local_seconds
        mas_rows.append(
            {
                "item_type": item_type,
                "final_items": count,
                "mas_observed_generation_seconds": generation_seconds,
                "mas_automated_rating_seconds": automated_rating_seconds,
                "mas_local_checks_and_audit_seconds": local_seconds,
                "mas_total_seconds": total_seconds,
                "mas_seconds_per_final_item": total_seconds / count,
                "rating_calls": rating_calls[item_type],
                "rating_call_seconds_assumption": structured_call_seconds,
            }
        )
    mas = pd.DataFrame(mas_rows)
    detail = human.merge(mas, on=["item_type", "final_items"])
    detail["human_minutes"] = detail.human_selected_seconds / 60.0
    detail["mas_minutes"] = detail.mas_total_seconds / 60.0
    detail["human_minutes_per_item"] = detail.human_selected_seconds_per_final_item / 60.0
    detail["mas_minutes_per_item"] = detail.mas_seconds_per_final_item / 60.0
    detail["time_basis"] = (
        "Human: selected-item authoring time from efficiency workbook. "
        "MAS: observed generation/explanation/test-point time + 4 QGval and "
        "4 ULM calls per item-type bank + 60 s local checks/audit for 50 items."
    )
    write_csv(DERIVED / "fig5_workflow_time_by_item_type.csv", detail)

    shared_hours = sum(
        parse_sum_expression(row_map[label][1])
        for label in ["考试蓝图制定", "专业审核与命题规范审核", "终审与组卷"]
    )
    notes = " ".join(
        str(cell)
        for row in rows
        for cell in row
        if cell is not None
    )
    cost_match = re.search(r"50道入卷人工题为\s*(\d+(?:\.\d+)?)\s*元", notes)
    human_cost_cny = float(cost_match.group(1)) if cost_match else 9562.0
    if "9562" not in efficiency_docx_text or human_cost_cny != 9562.0:
        raise ValueError("Efficiency sources disagree on the Human 50-item workflow cost.")
    summary = pd.DataFrame(
        [
            {
                "workflow": "Human",
                "total_minutes": detail.human_minutes.sum(),
                "final_items": 50,
                "usable_items": 50,
                "minutes_per_usable_item": detail.human_minutes.sum() / 50,
                "common_manual_workflow_minutes_excluded_equally": shared_hours * 60,
                "labor_cost_cny": human_cost_cny,
            },
            {
                "workflow": "MAS",
                "total_minutes": detail.mas_minutes.sum(),
                "final_items": 50,
                "usable_items": 50,
                "minutes_per_usable_item": detail.mas_minutes.sum() / 50,
                "common_manual_workflow_minutes_excluded_equally": shared_hours * 60,
                "labor_cost_cny": 0.0,
            },
        ]
    )
    write_csv(DERIVED / "fig5_workflow_summary.csv", summary)
    return detail, summary


def estimated_tokens(text: str) -> float:
    total = 0.0
    for character in text:
        if "\u4e00" <= character <= "\u9fff":
            total += 0.6
        elif character.isspace():
            continue
        else:
            total += 0.3
    return total


def token_cost_data() -> pd.DataFrame:
    detailed_counts = {"A1": 7, "A2": 18, "A3": 7, "A4": 7, "B": 3, "X": 8}
    stems = {"A1": "a1", "A2": "a2", "A3": "a3", "A4": "a4", "B": "b", "X": "x"}
    generation_batch = {"A1": 20, "A2": 10, "A3": 10, "A4": 10, "B": 10, "X": 20}
    enrichment_batch = {"A1": 100, "A2": 100, "A3": 50, "A4": 30, "B": 30, "X": 100}
    analysis_fields = {"analysis", "analysis1", "analysis2", "analysis3"}
    derived_fields = {
        "prototype",
        "fuzzywuzzy_doubt",
        "fuzzywuzzy_ratio_max",
        "sentencebert_doubt",
        "sentencebert_cosine_max",
        "3gram_doubt",
        "3gram_jaccard_max",
        "textstat_flesch_reading_ease",
        "QGEval",
        "LLM",
    }

    def dumped_tokens(value: Any) -> float:
        return estimated_tokens(json.dumps(value, ensure_ascii=False, indent=4))

    stage_rows: list[dict[str, Any]] = []
    for item_type, count in detailed_counts.items():
        stem = stems[item_type]
        new_items = json.loads(
            (REPO_ROOT / "data" / "banks" / f"new_bank_{stem}.json").read_text(encoding="utf-8")
        )[:count]
        source_items: list[dict[str, Any]] = []
        for other_type, other_stem in stems.items():
            if other_type != item_type:
                source_items.extend(
                    json.loads(
                        (REPO_ROOT / "data" / "banks" / f"bank_{other_stem}.json").read_text(
                            encoding="utf-8"
                        )
                    )
                )
        source_tokens_per_item = np.mean([dumped_tokens(item) for item in source_items])
        core_items = [
            {
                key: value
                for key, value in item.items()
                if key not in derived_fields | analysis_fields | {"test_point"}
            }
            for item in new_items
        ]
        complete_items = [
            {key: value for key, value in item.items() if key not in derived_fields}
            for item in new_items
        ]
        no_analysis_items = [
            {
                key: value
                for key, value in item.items()
                if key not in derived_fields | analysis_fields
            }
            for item in new_items
        ]
        analysis_outputs = []
        for item in new_items:
            output = {"id": item.get("id")}
            for field in analysis_fields:
                if field in item:
                    output[field] = item[field]
            analysis_outputs.append(output)
        test_point_outputs = [
            {"id": item.get("id"), "test_point": item.get("test_point")}
            for item in new_items
        ]

        generation_prompt = (
            REPO_ROOT
            / "prompts"
            / "generation"
            / f"prompts_for_bank_to_new_bank_{stem}.txt"
        ).read_text(encoding="utf-8")
        explanation_prompt = (
            REPO_ROOT
            / "prompts"
            / "generation"
            / f"prompts_for_new_bank_answer_explanation_{stem}.txt"
        ).read_text(encoding="utf-8")
        test_point_prompt = (
            REPO_ROOT / "prompts" / "generation" / "prompt_for_test_point.txt"
        ).read_text(encoding="utf-8")
        qgval_prompt = (
            REPO_ROOT / "prompts" / "evaluation" / "prompt_for_qgeval.txt"
        ).read_text(encoding="utf-8")
        ulm_prompt = (
            REPO_ROOT / "prompts" / "evaluation" / "prompt_for_llm.txt"
        ).read_text(encoding="utf-8")

        estimates = [
            (
                "Generation",
                "deepseek-v4-pro",
                count
                * (
                    estimated_tokens(generation_prompt) / generation_batch[item_type]
                    + source_tokens_per_item
                ),
                sum(dumped_tokens(item) for item in core_items),
            ),
            (
                "Answer explanation",
                "deepseek-v4-pro",
                count
                * estimated_tokens(explanation_prompt)
                / enrichment_batch[item_type]
                + sum(dumped_tokens(item) for item in core_items),
                sum(dumped_tokens(item) for item in analysis_outputs),
            ),
            (
                "Test-point restoration",
                "deepseek-v4-flash",
                count
                * estimated_tokens(test_point_prompt)
                / enrichment_batch[item_type]
                + sum(dumped_tokens(item) for item in no_analysis_items),
                sum(dumped_tokens(item) for item in test_point_outputs),
            ),
            (
                "QGval ×4",
                "deepseek-v4-pro",
                4
                * (
                    estimated_tokens(qgval_prompt)
                    + sum(dumped_tokens(item) for item in complete_items)
                ),
                4
                * count
                * estimated_tokens("[" + ",".join(["9999"] + ["5"] * 7) + "]"),
            ),
            (
                "ULM ×4",
                "deepseek-v4-pro",
                4
                * (
                    estimated_tokens(ulm_prompt)
                    + sum(dumped_tokens(item) for item in complete_items)
                ),
                4
                * count
                * estimated_tokens("[" + ",".join(["9999"] + ["5"] * 16) + "]"),
            ),
        ]
        for stage, model, input_tokens, output_tokens in estimates:
            prices = DEEPSEEK_PRICES_USD_PER_M[model]
            stage_rows.append(
                {
                    "item_type": item_type,
                    "stage": stage,
                    "model": model,
                    "input_tokens_estimated": input_tokens,
                    "output_tokens_estimated": output_tokens,
                    "input_price_usd_per_million": prices["input"],
                    "output_price_usd_per_million": prices["output"],
                    "input_cost_usd": input_tokens / 1_000_000 * prices["input"],
                    "output_cost_usd": output_tokens / 1_000_000 * prices["output"],
                    "pricing_source": DEEPSEEK_PRICING_SOURCE,
                    "pricing_checked_date": "2026-06-22",
                    "token_method": (
                        "Official DeepSeek approximation: Chinese character≈0.6 token; "
                        "other non-space character≈0.3 token; cache-miss pricing."
                    ),
                }
            )
    detail = pd.DataFrame(stage_rows)
    write_csv(DERIVED / "fig5_token_cost_estimate_by_type_stage.csv", detail)
    summary = (
        detail.groupby(["stage", "model"], as_index=False)[
            [
                "input_tokens_estimated",
                "output_tokens_estimated",
                "input_cost_usd",
                "output_cost_usd",
            ]
        ]
        .sum()
    )
    summary["total_cost_usd"] = summary.input_cost_usd + summary.output_cost_usd
    summary["pricing_source"] = DEEPSEEK_PRICING_SOURCE
    summary["pricing_checked_date"] = "2026-06-22"
    write_csv(DERIVED / "fig5_api_cost_by_stage.csv", summary)
    return summary


def figure5a() -> None:
    detail, summary = efficiency_time_data()
    fig, ax = plt.subplots(figsize=(9.0, 4.5))
    add_panel_label(fig, "A")
    bottoms = np.zeros(2)
    for item_type in EFFICIENCY_TYPES:
        row = detail[detail.item_type.eq(item_type)].iloc[0]
        values = np.array([row.human_minutes, row.mas_minutes])
        pair = EFFICIENCY_TYPE_COLORS[item_type]
        ax.bar(
            [0, 1],
            values,
            bottom=bottoms,
            width=0.48,
            color=pair["color"],
            edgecolor="white",
            linewidth=0.7,
            label=(
                f"{item_type}: {row.human_minutes_per_item:.1f} vs "
                f"{row.mas_minutes_per_item:.2f} min/item"
            ),
        )
        if values[0] > 35:
            label_color = "white" if item_type != "X" else UROMAS_BASE_COLORS["text_dark"]
            ax.text(
                0,
                bottoms[0] + values[0] / 2,
                f"{values[0]:.0f}",
                ha="center",
                va="center",
                fontsize=8,
                color=label_color,
                fontweight="bold",
            )
        bottoms += values
    human_total = float(summary.loc[summary.workflow.eq("Human"), "total_minutes"].iloc[0])
    mas_total = float(summary.loc[summary.workflow.eq("MAS"), "total_minutes"].iloc[0])
    ax.text(
        0,
        human_total + 35,
        f"{human_total:.0f} min\n({human_total/60:.1f} h)",
        ha="center",
        color=CORE_COLORS["Human"],
        fontweight="bold",
    )
    ax.text(1, mas_total + 35, f"{mas_total:.1f} min", ha="center", color=CORE_COLORS["MAS"], fontweight="bold")
    ax.set_xticks([0, 1], ["Human", "MAS"])
    ax.get_xticklabels()[0].set_color(CORE_COLORS["Human"])
    ax.get_xticklabels()[1].set_color(CORE_COLORS["MAS"])
    ax.set_ylabel("Total time for the 50-item exam (min)")
    ax.set_ylim(0, human_total * 1.16)
    ax.set_title("Total item-production workflow time", fontweight="bold")
    ax.legend(
        frameon=False,
        loc="upper right",
        title="Item type: Human vs MAS",
        fontsize=6.5,
        title_fontsize=8,
    )
    ax.text(
        0.50,
        -0.14,
        "Shared blueprint/review/assembly time (11 h) excluded equally.",
        transform=ax.transAxes,
        ha="center",
        va="top",
        fontsize=6.5,
        color=UROMAS_BASE_COLORS["text"],
    )
    style_axes(ax)
    fig.tight_layout()
    # Figure 5A and 5D share the same assembled columns.
    fig.subplots_adjust(left=0.155, right=0.985, bottom=0.155)
    save_pdf(fig, "Figure5A_total_workflow_time.pdf", tight=False)


def figure5b() -> None:
    _, summary = efficiency_time_data()
    values = [
        float(summary.loc[summary.workflow.eq(workflow), "minutes_per_usable_item"].iloc[0])
        for workflow in ["Human", "MAS"]
    ]
    ratio = values[0] / values[1]
    fig, ax = plt.subplots(figsize=(4.5, 4.5))
    add_panel_label(fig, "B")
    bars = ax.bar(
        [0, 1],
        values,
        width=0.48,
        color=[CORE_COLORS["Human"], CORE_COLORS["MAS"]],
    )
    for bar, value in zip(bars, values):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            value + 0.8,
            f"{value:.1f}\nmin/item",
            ha="center",
            va="bottom",
            fontweight="bold",
        )
    ax.text(
        0.5,
        max(values) * 0.90,
        f"{ratio:.0f}× less human time",
        ha="center",
        color=CORE_COLORS["MAS"],
        fontsize=8,
    )
    ax.set_xticks([0, 1], ["Human\n50/50 usable", "MAS\n50/50 usable"])
    ax.set_ylabel("Workflow time per usable item (min)")
    ax.set_ylim(0, max(values) * 1.18)
    ax.set_title("Time per usable final item", fontweight="bold")
    style_axes(ax)
    fig.tight_layout()
    # Match the horizontal-axis baseline of adjacent Figure 5A.
    fig.subplots_adjust(bottom=0.155)
    save_pdf(fig, "Figure5B_time_per_usable_item.pdf", tight=False)


def figure5c() -> None:
    _, summary = efficiency_time_data()
    human = float(summary.loc[summary.workflow.eq("Human"), "total_minutes"].iloc[0])
    mas = float(summary.loc[summary.workflow.eq("MAS"), "total_minutes"].iloc[0])
    sensitivity = pd.DataFrame(
        [
            {"workflow": "Human", "estimate": human, "low": human * 0.8, "high": human * 1.2},
            {"workflow": "MAS", "estimate": mas, "low": mas * 0.8, "high": mas * 1.2},
        ]
    )
    sensitivity["sensitivity"] = "±20%"
    write_csv(DERIVED / "fig5_time_sensitivity.csv", sensitivity)
    worst_ratio = human * 0.8 / (mas * 1.2)

    fig, ax = plt.subplots(figsize=(4.5, 4.5))
    add_panel_label(fig, "C")
    for position, row in enumerate(sensitivity.itertuples()):
        source = row.workflow
        ax.errorbar(
            position,
            row.estimate,
            yerr=[[row.estimate - row.low], [row.high - row.estimate]],
            fmt="o",
            color=CORE_COLORS[source],
            ecolor=CORE_COLORS[source],
            elinewidth=2,
            capsize=7,
            markersize=8,
        )
        ax.text(
            position + 0.14,
            row.estimate,
            f"{row.estimate:.0f} min\n[{row.low:.0f}, {row.high:.0f}]",
            ha="left",
            va="center",
        )
    ax.set_yscale("log")
    ax.set_xticks([0, 1], ["Human", "MAS"])
    ax.set_ylabel("Total workflow time per exam (min, log)")
    ax.set_title("Sensitivity: workflow time ±20%", fontweight="bold")
    ax.text(
        0.50,
        0.50,
        (
            "Worst case: Human −20% vs MAS +20%\n"
            f"{human*0.8:.0f} vs {mas*1.2:.0f} min ≈ {worst_ratio:.0f}×"
        ),
        transform=ax.transAxes,
        ha="center",
        va="center",
        bbox={"boxstyle": "round,pad=0.25", "facecolor": "white", "edgecolor": UROMAS_BASE_COLORS["border"]},
    )
    ax.set_xlim(-0.15, 1.30)
    style_axes(ax, "")
    fig.tight_layout()
    # Match the horizontal-axis baseline of adjacent Figure 5A-B.
    fig.subplots_adjust(bottom=0.155)
    save_pdf(fig, "Figure5C_time_sensitivity.pdf", tight=False)


def figure5d() -> None:
    costs = token_cost_data()
    stage_order = [
        "Test-point restoration",
        "Generation",
        "Answer explanation",
        "QGval ×4",
        "ULM ×4",
    ]
    plot = costs.set_index("stage").loc[stage_order].reset_index()
    y = np.arange(len(plot))
    fig, ax = plt.subplots(figsize=(9.0, 4.5))
    add_panel_label(fig, "D")
    input_color = OPTIONAL_COLOR_PAIRS[5]["fill"]
    output_color = OPTIONAL_COLOR_PAIRS[1]["color"]
    ax.barh(y, plot.input_cost_usd, color=input_color, edgecolor="none", label="Input tokens")
    ax.barh(
        y,
        plot.output_cost_usd,
        left=plot.input_cost_usd,
        color=output_color,
        edgecolor="none",
        label="Output tokens",
    )
    for position, row in enumerate(plot.itertuples()):
        total = row.total_cost_usd
        ax.text(total + 0.0015, position, f"${total:.3f}", ha="left", va="center")
    total_cost = float(plot.total_cost_usd.sum())
    labels = [
        f"{row.stage}\n({row.model.replace('deepseek-', '')})"
        for row in plot.itertuples()
    ]
    ax.set_yticks(y, labels)
    ax.set_xlabel("API cost per 50-item exam (USD)")
    ax.set_title("MAS API cost (compute component)", fontweight="bold")
    ax.legend(frameon=False, loc="lower right")
    ax.text(
        0.98,
        0.38,
        f"Total ${total_cost:.3f}/exam\nHuman labor benchmark: CNY 9,562",
        transform=ax.transAxes,
        ha="right",
        va="center",
        color=OPTIONAL_COLOR_PAIRS[5]["color"],
        fontweight="bold",
        bbox={
            "boxstyle": "round,pad=0.22",
            "facecolor": "white",
            "edgecolor": UROMAS_BASE_COLORS["border"],
            "alpha": 0.94,
        },
    )
    ax.text(
        0.50,
        -0.22,
        "DeepSeek V4 cache-miss prices checked 2026-06-22",
        transform=ax.transAxes,
        ha="center",
        va="top",
        fontsize=6.5,
        color=UROMAS_BASE_COLORS["text"],
    )
    ax.set_xlim(0, max(plot.total_cost_usd.max() * 1.55, 0.06))
    style_axes(ax, "x")
    fig.tight_layout()
    # Match the horizontal-axis baseline of adjacent Figure 5E.
    fig.subplots_adjust(left=0.155, right=0.985, bottom=0.216)
    save_pdf(fig, "Figure5D_api_cost.pdf", tight=False)


def figure5e() -> None:
    _, workflow_summary = efficiency_time_data()
    token_costs = token_cost_data()
    human_cost_cny = float(
        workflow_summary.loc[workflow_summary.workflow.eq("Human"), "labor_cost_cny"].iloc[0]
    )
    token_estimated_usd = float(token_costs.total_cost_usd.sum())
    token_estimated_cny = token_estimated_usd * USD_TO_CNY_FOR_FIG5
    observed_ai_cost_cny = float("nan")
    observed_path = DERIVED / "ai_efficiency_filled_from_update.csv"
    if observed_path.exists():
        observed = pd.read_csv(observed_path)
        total = observed[observed.scope.astype(str).str.upper().eq("TOTAL")]
        if not total.empty and "api_cost_total_cny" in total.columns:
            observed_ai_cost_cny = float(total.api_cost_total_cny.dropna().iloc[0])
    ai_total_cny = observed_ai_cost_cny if np.isfinite(observed_ai_cost_cny) else token_estimated_cny
    rows = pd.DataFrame(
        [
            {
                "workflow": "Human",
                "cost_component": "labor",
                "cost_cny": human_cost_cny,
                "cost_usd": np.nan,
                "source": "efficiency analysis workbook",
                "plotted": True,
            },
            {
                "workflow": "AI",
                "cost_component": "total_api_cost_user_provided",
                "cost_cny": observed_ai_cost_cny,
                "cost_usd": np.nan,
                "source": "plot/data/derived/ai_efficiency_filled_from_update.csv",
                "plotted": bool(np.isfinite(observed_ai_cost_cny)),
            },
            {
                "workflow": "AI",
                "cost_component": "total_api_cost_token_estimated",
                "cost_cny": token_estimated_cny,
                "cost_usd": token_estimated_usd,
                "source": DEEPSEEK_PRICING_SOURCE,
                "plotted": not bool(np.isfinite(observed_ai_cost_cny)),
            },
        ]
    )
    ratio = human_cost_cny / ai_total_cny if ai_total_cny > 0 else float("nan")
    rows["human_to_ai_cost_ratio_for_plotted_values"] = ratio
    rows["usd_to_cny_display_rate_for_token_estimate"] = USD_TO_CNY_FOR_FIG5
    write_csv(DERIVED / "fig5E_total_cost_comparison.csv", rows)

    fig, ax = plt.subplots(figsize=(4.5, 4.5))
    add_panel_label(fig, "E")
    values = [human_cost_cny, ai_total_cny]
    bars = ax.bar(
        [0, 1],
        values,
        width=0.50,
        color=[CORE_COLORS["Human"], CORE_COLORS["MAS"]],
        edgecolor="white",
        linewidth=0.8,
    )
    for bar, value in zip(bars, values):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            value * 1.18,
            f"¥{value:,.2f}" if value < 100 else f"¥{value:,.0f}",
            ha="center",
            va="bottom",
            fontweight="bold",
        )
    ax.set_yscale("log")
    ax.set_xticks([0, 1], ["Human\nlabor", "AI\nAPI total"])
    ax.set_ylabel("Cost per 50-item exam (CNY, log scale)")
    ax.set_title("Human labor cost vs AI total cost", fontweight="bold")
    ax.text(
        0.5,
        0.88,
        f"≈{ratio:,.0f}× lower AI cost",
        transform=ax.transAxes,
        ha="center",
        va="center",
        color=CORE_COLORS["MAS"],
        fontweight="bold",
    )
    ax.text(
        0.50,
        -0.22,
        f"AI bar uses user-provided API total (¥{ai_total_cny:.2f}); token estimate: "
        f"${token_estimated_usd:.3f} ≈ ¥{token_estimated_cny:.2f}.",
        transform=ax.transAxes,
        ha="center",
        va="top",
        fontsize=6.5,
        color=UROMAS_BASE_COLORS["text"],
    )
    ax.set_ylim(max(min(values) / 2, 0.1), max(values) * 2.6)
    style_axes(ax)
    save_pdf(fig, "Figure5E_total_cost_comparison.pdf")


# ---------------------------------------------------------------------------
# Figure 6: randomized order / fatigue analysis


def fatigue_order_data() -> pd.DataFrame:
    rows = read_sheet_rows(
        PLOT_EXAM_WORKBOOK_DIR / "试卷作答情况 - 2.xlsx",
        "疲劳性探索与总时长",
    )
    students: dict[int, dict[str, Any]] = {}
    for row in rows:
        if (
            len(row) >= 8
            and row[0] in {"A", "B"}
            and isinstance(row[3], (int, float))
            and isinstance(row[4], (int, float))
            and isinstance(row[5], (int, float))
            and isinstance(row[7], (int, float))
        ):
            student_id = int(row[3])
            students.setdefault(
                student_id,
                {
                    "student_id": student_id,
                    "form": str(row[0]),
                    "training_year": int(row[1]),
                    "campus": str(row[2]),
                    "mas_score": float(row[4]),
                    "human_score": float(row[5]),
                    "mas_minus_human": float(row[4]) - float(row[5]),
                    "total_duration_seconds": float(row[7]),
                },
            )
    data = pd.DataFrame(students.values()).sort_values("student_id").reset_index(drop=True)
    if len(data) != 50:
        raise ValueError(f"Expected 50 unique fatigue-analysis students, found {len(data)}.")
    data["first_source"] = np.where(data.form.eq("A"), "Human", "MAS")
    data["second_source"] = np.where(data.form.eq("A"), "MAS", "Human")
    data["first_score"] = np.where(data.form.eq("A"), data.human_score, data.mas_score)
    data["second_score"] = np.where(data.form.eq("A"), data.mas_score, data.human_score)
    data["second_minus_first"] = data.second_score - data.first_score
    data["total_duration_minutes"] = data.total_duration_seconds / 60.0
    write_csv(DERIVED / "fig6_fatigue_order_student_data.csv", data)
    return data


def figure6a() -> None:
    data = fatigue_order_data()
    counts = data.form.value_counts().to_dict()
    fig, ax = plt.subplots(figsize=(4.5, 4.5))
    add_panel_label(fig, "A")
    ax.set_xlim(0, 4)
    ax.set_ylim(0, 5)
    ax.axis("off")
    rounded_box(ax, (0.25, 3.15), (3.5, 1.0), "Form A", f"Human → MAS  (n={counts.get('A', 0)})", FORM_COLORS["A"]["fill"], FORM_COLORS["A"]["color"])
    rounded_box(ax, (0.25, 1.20), (3.5, 1.0), "Form B", f"MAS → Human  (n={counts.get('B', 0)})", FORM_COLORS["B"]["fill"], FORM_COLORS["B"]["color"])
    fig.suptitle("Randomized examination order", y=0.99, fontweight="bold")
    save_pdf(fig, "Figure6A_order_schema.pdf", tight=False)


def figure6b() -> None:
    data = fatigue_order_data()
    method, p_value, label = paired_comparison(
        data.second_score.to_numpy(),
        data.first_score.to_numpy(),
    )
    write_csv(
        DERIVED / "fig6B_first_second_score_stats.csv",
        [
            {
                "n_students": len(data),
                "first_mean": data.first_score.mean(),
                "first_sd": data.first_score.std(ddof=1),
                "second_mean": data.second_score.mean(),
                "second_sd": data.second_score.std(ddof=1),
                "second_minus_first_mean": data.second_minus_first.mean(),
                "method": method,
                "p_value": p_value,
                "significance_label": label,
            }
        ],
    )
    fig, ax = plt.subplots(figsize=(4.5, 4.5))
    add_panel_label(fig, "B")
    for form in ["A", "B"]:
        sub = data[data.form.eq(form)]
        pair = FORM_COLORS[form]
        for row in sub.itertuples():
            ax.plot([0, 1], [row.first_score, row.second_score], color=pair["color"], alpha=0.28, linewidth=0.8)
        ax.scatter(np.zeros(len(sub)), sub.first_score, color=pair["color"], s=13, alpha=0.65, label=f"Form {form}")
        ax.scatter(np.ones(len(sub)), sub.second_score, color=pair["color"], s=13, alpha=0.65)
    ymax = max(data.first_score.max(), data.second_score.max()) + 5
    ax.plot([0, 0, 1, 1], [ymax - 1, ymax, ymax, ymax - 1], color=UROMAS_BASE_COLORS["text_dark"], linewidth=0.8)
    ax.text(0.5, ymax + 0.8, label, ha="center", fontweight="bold")
    ax.text(0.5, 24, f"{method}\nP={p_value:.3f}", ha="center", va="bottom", fontsize=6.5)
    ax.set_xticks([0, 1], ["First block", "Second block"])
    # Keep the endpoint labels inside the square panel without changing the
    # aligned axis bounds: the left label grows rightward and the right label
    # grows leftward from their ticks.
    ax.get_xticklabels()[0].set_ha("left")
    ax.get_xticklabels()[1].set_ha("right")
    ax.set_ylabel("Block score (%)")
    ax.set_ylim(20, min(105, ymax + 7))
    ax.set_title("Student scores by block position", fontweight="bold")
    ax.legend(frameon=False)
    style_axes(ax)
    fig.tight_layout()
    # Match the horizontal-axis baseline of adjacent Figure 6C.
    fig.subplots_adjust(left=0.133, right=0.973, bottom=0.093)
    save_pdf(fig, "Figure6B_scores_by_block_position.pdf", tight=False)


def figure6c() -> None:
    data = fatigue_order_data()
    groups = [
        data.loc[data.form.eq(form), "second_minus_first"].to_numpy()
        for form in ["A", "B"]
    ]
    rows = []
    for index, form in enumerate(["A", "B"]):
        mean, low, high = bootstrap_mean_ci(groups[index], seed=610 + index)
        rows.append(
            {
                "form": form,
                "sequence": "Human → MAS" if form == "A" else "MAS → Human",
                "n_students": len(groups[index]),
                "mean_second_minus_first": mean,
                "ci_low": low,
                "ci_high": high,
                "source_position_note": "Source and position are confounded within each sequence.",
            }
        )
    write_csv(DERIVED / "fig6C_position_difference_by_sequence.csv", rows)
    fig, ax = plt.subplots(figsize=(4.5, 4.5))
    add_panel_label(fig, "C")
    box = ax.boxplot(groups, positions=[0, 1], widths=0.48, patch_artist=True, showfliers=False)
    for patch, form in zip(box["boxes"], ["A", "B"]):
        patch.set_facecolor(FORM_COLORS[form]["fill"])
        patch.set_edgecolor(FORM_COLORS[form]["color"])
    rng = np.random.default_rng(611)
    for position, form, values in zip([0, 1], ["A", "B"], groups):
        ax.scatter(rng.normal(position, 0.04, len(values)), values, s=11, color=FORM_COLORS[form]["color"], alpha=0.55, linewidths=0)
    ax.axhline(0, color=UROMAS_BASE_COLORS["spine"], linewidth=0.9)
    ax.set_xticks([0, 1], ["Form A\nHuman → MAS", "Form B\nMAS → Human"])
    ax.set_ylabel("Second − first block score (points)")
    ax.set_title("Within-student position differences", fontweight="bold")
    style_axes(ax)
    save_pdf(fig, "Figure6C_position_difference_by_sequence.pdf")


def figure6d() -> None:
    data = fatigue_order_data()
    long_rows = []
    for row in data.itertuples():
        long_rows.extend(
            [
                {
                    "student_id": row.student_id,
                    "form": row.form,
                    "training_year": row.training_year,
                    "campus": row.campus,
                    "source": row.first_source,
                    "is_mas": int(row.first_source == "MAS"),
                    "is_second": 0,
                    "score": row.first_score,
                },
                {
                    "student_id": row.student_id,
                    "form": row.form,
                    "training_year": row.training_year,
                    "campus": row.campus,
                    "source": row.second_source,
                    "is_mas": int(row.second_source == "MAS"),
                    "is_second": 1,
                    "score": row.second_score,
                },
            ]
        )
    long = pd.DataFrame(long_rows)
    formula = "score ~ is_mas + is_second + C(training_year) + C(campus)"
    fit = smf.ols(formula, data=long).fit(
        cov_type="cluster",
        cov_kwds={"groups": long.student_id},
    )
    rows = [
        {
            "contrast": "Adjusted second − first",
            "estimate": fit.params["is_second"],
            "ci_low": fit.conf_int().loc["is_second", 0],
            "ci_high": fit.conf_int().loc["is_second", 1],
            "method": formula + "; cluster-robust SE by student",
        },
        {
            "contrast": "Adjusted MAS − Human",
            "estimate": fit.params["is_mas"],
            "ci_low": fit.conf_int().loc["is_mas", 0],
            "ci_high": fit.conf_int().loc["is_mas", 1],
            "method": formula + "; cluster-robust SE by student",
        },
    ]
    for form, label in [("A", "Form A observed second − first"), ("B", "Form B observed second − first")]:
        values = data.loc[data.form.eq(form), "second_minus_first"].to_numpy()
        mean, low, high = bootstrap_mean_ci(values, seed=620 + ord(form))
        rows.append(
            {
                "contrast": label,
                "estimate": mean,
                "ci_low": low,
                "ci_high": high,
                "method": "Participant bootstrap; source and position confounded within sequence",
            }
        )
    result = pd.DataFrame(rows)
    write_csv(DERIVED / "fig6D_adjusted_fatigue_effect.csv", result)
    plot = result.iloc[::-1].reset_index(drop=True)
    y = np.arange(len(plot))
    fig, ax = plt.subplots(figsize=(9.0, 4.5))
    add_panel_label(fig, "D")
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
    ax.set_xlabel("Score difference (percentage points)")
    ax.set_title("Adjusted fatigue and source effects", fontweight="bold")
    style_axes(ax, "x")
    save_pdf(fig, "Figure6D_adjusted_fatigue_effect.pdf")


def figure6e() -> None:
    data = fatigue_order_data()
    a = data.loc[data.form.eq("A"), "total_duration_minutes"].to_numpy()
    b = data.loc[data.form.eq("B"), "total_duration_minutes"].to_numpy()
    test = stats.ttest_ind(a, b, equal_var=False)
    rows = [
        {
            "form": form,
            "n_students": len(values),
            "mean_minutes": np.mean(values),
            "sd_minutes": np.std(values, ddof=1),
            "welch_p_value_form_a_vs_b": float(test.pvalue),
        }
        for form, values in [("A", a), ("B", b)]
    ]
    write_csv(DERIVED / "fig6E_total_duration_by_sequence.csv", rows)
    fig, ax = plt.subplots(figsize=(4.5, 4.5))
    add_panel_label(fig, "E")
    rng = np.random.default_rng(630)
    for position, form, values in [(0, "A", a), (1, "B", b)]:
        pair = FORM_COLORS[form]
        violin = ax.violinplot([values], positions=[position], widths=0.62, showextrema=False)
        body = violin["bodies"][0]
        body.set_facecolor(pair["fill"])
        body.set_edgecolor(pair["color"])
        body.set_alpha(0.9)
        ax.scatter(rng.normal(position, 0.045, len(values)), values, s=11, color=pair["color"], alpha=0.55, linewidths=0)
        mean, low, high = bootstrap_mean_ci(values, seed=631 + position)
        ax.errorbar(position, mean, yerr=[[mean - low], [high - mean]], fmt="D", color=UROMAS_BASE_COLORS["text_dark"], capsize=3)
    ymax = max(a.max(), b.max()) + 5
    ax.plot([0, 0, 1, 1], [ymax - 1, ymax, ymax, ymax - 1], color=UROMAS_BASE_COLORS["text_dark"], linewidth=0.8)
    significance = "***" if test.pvalue < 0.001 else "**" if test.pvalue < 0.01 else "*" if test.pvalue < 0.05 else "n.s."
    ax.text(0.5, ymax + 1, significance, ha="center", fontweight="bold")
    ax.text(0.5, min(a.min(), b.min()) - 2, f"Welch t-test  P={test.pvalue:.3f}", ha="center", va="top", fontsize=6.5)
    ax.set_xticks([0, 1], ["Form A\nHuman → MAS", "Form B\nMAS → Human"])
    ax.set_ylabel("Total examination duration (min)")
    ax.set_title("Total duration by randomized sequence", fontweight="bold")
    style_axes(ax)
    fig.tight_layout()
    # Figure 6C and 6E share a column; align their left axes. The bottom
    # matches adjacent Figure 6D without moving any annotation off-canvas.
    fig.subplots_adjust(left=0.133, right=0.973, bottom=0.104)
    save_pdf(fig, "Figure6E_total_duration_by_sequence.pdf", tight=False)


def cleanup_obsolete_outputs() -> None:
    obsolete = [
        "Figure2B_dimension_scores.pdf",
        "Figure2C_defect_flags.pdf",
        "Figure2D_defect_workflow.pdf",
        "Figure2E_run_consistency.pdf",
        "Figure3B_defect_risk_by_cognitive_level.pdf",
        "Figure4B_source_judgment_confusion_matrix.pdf",
        "Figure4C_source_task_ratings.pdf",
        "Figure4D_workflow_total_time.pdf",
        "Figure4E_quality_adjusted_time.pdf",
        "Figure5A_order_schema.pdf",
        "Figure5B_paired_block_scores.pdf",
        "Figure5C_individual_differences_by_sequence.pdf",
        "Figure5D_adjusted_correct_rate_difference.pdf",
        "Figure5E_setting_stratified_differences.pdf",
    ]
    for filename in obsolete:
        remove_output(filename)


def main() -> None:
    setup_style()
    remove_manual_workflow_outputs()
    expert_judgments = parse_expert_judgments()

    figure1c()
    figure1d()
    figure1e()

    figure2b()
    figure2c()
    figure2d()
    figure2e()
    figure2f()

    figure3b()
    figure3c()
    figure3d()
    figure3e()
    figure3f()

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

    figure6a()
    figure6b()
    figure6c()
    figure6d()
    figure6e()

    cleanup_obsolete_outputs()
    print(f"Wrote all manuscript panel PDFs to {OUT}")


if __name__ == "__main__":
    main()
