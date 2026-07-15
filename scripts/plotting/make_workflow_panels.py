#!/usr/bin/env python3
"""Trace the five GPT concept workflow panels as editable mixed-media PDFs.

Labels, connectors, containers, and elementary flow shapes are PDF vectors.
Iconography is embedded only as small text-free PNG screenshots cropped from
the supplied concepts, as requested by the author.  The declared manuscript
canvas is preserved exactly for assembly by ``assemble_final_figures.py``.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import matplotlib as mpl

mpl.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from matplotlib.patches import (
    Arc,
    Circle,
    Ellipse,
    FancyArrowPatch,
    FancyBboxPatch,
    PathPatch,
    Polygon,
    Rectangle,
)
from matplotlib.path import Path as MplPath
from matplotlib.textpath import TextPath
from matplotlib.transforms import Affine2D


REPO_ROOT = Path(__file__).resolve().parents[2]
OUT = REPO_ROOT / "outputs" / "figures" / "panels"
ICON_DIR = REPO_ROOT / "assets" / "workflow_icons"
_ICON_CACHE: dict[str, object] = {}

BASE = {
    "grid": "#E3DFD8",
    "spine": "#9E9A93",
    "text": "#3E3E3E",
    "dark": "#2A251F",
    "tick": "#4F4F4F",
    "border": "#C8C2B8",
    "separator": "#D8D2C9",
}
COLOR = {
    "human": "#313E96",
    "mas": "#B86758",
    "purple": "#7C5CFF",
    "ochre": "#B8954B",
    "teal": "#2F8F83",
    "gray": "#6F6F6F",
    "green": "#2E8B57",
}
FILL = {
    "human": "#D9DCF1",
    "mas": "#F2DFDB",
    "purple": "#E9E2FF",
    "ochre": "#F1E6C8",
    "teal": "#DCEFEB",
    "gray": "#E8E8E8",
    "bluepurple": "#E1E7FF",
    "white": "#FFFFFF",
}


def setup_style() -> None:
    mpl.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.sans-serif": ["DejaVu Sans"],
            "mathtext.fontset": "dejavusans",
            "font.size": 8,
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "savefig.dpi": 600,
            "savefig.transparent": False,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "image.composite_image": False,
        }
    )


def canvas(width_in: float, height_in: float = 4.5):
    fig = plt.figure(figsize=(width_in, height_in))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, width_in * 10)
    ax.set_ylim(0, height_in * 10)
    ax.set_aspect("equal")
    ax.axis("off")
    return fig, ax


def save(fig, filename: str) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / filename, facecolor="white")
    plt.close(fig)


def rounded(
    ax,
    x,
    y,
    w,
    h,
    edge=BASE["border"],
    fill="white",
    lw=0.8,
    radius=0.8,
    linestyle="-",
    zorder=1,
):
    patch = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle=f"round,pad=0.06,rounding_size={radius}",
        linewidth=lw,
        edgecolor=edge,
        facecolor=fill,
        linestyle=linestyle,
        zorder=zorder,
    )
    ax.add_patch(patch)
    return patch


def txt(
    ax,
    x,
    y,
    s,
    *,
    size=6.5,
    color=BASE["text"],
    weight="normal",
    ha="center",
    va="center",
    style="normal",
    rotation=0,
    linespacing=1.18,
    stretch="normal",
    xscale=1.0,
    zorder=6,
):
    transform = ax.transData
    if xscale != 1.0:
        transform = (
            Affine2D()
            .translate(-x, -y)
            .scale(xscale, 1.0)
            .translate(x, y)
            + ax.transData
        )
    return ax.text(
        x,
        y,
        s,
        fontsize=size,
        color=color,
        fontweight=weight,
        ha=ha,
        va=va,
        fontstyle=style,
        rotation=rotation,
        linespacing=linespacing,
        fontstretch=stretch,
        transform=transform,
        zorder=zorder,
    )


def path_txt(
    ax,
    x,
    y,
    s,
    *,
    size=6.5,
    color=BASE["text"],
    weight="normal",
    ha="center",
    linespacing=1.0,
    xscale=1.0,
    zorder=6,
) -> None:
    """Draw condensed PDF-vector text as glyph paths at an unchanged point size.

    The 4.5-inch square workflow contains long mandatory labels.  Horizontal
    glyph scaling keeps the allowed 6.5-point height while preventing label
    collisions; unlike a bitmap label, the result remains PDF path content.
    """
    unit = 10.0 / 72.0  # panel coordinates per typographic point
    font = FontProperties(family="DejaVu Sans", weight=weight)
    lines = s.split("\n")
    gap = size * unit * linespacing
    centers = [y + (len(lines) - 1 - 2 * i) * gap / 2 for i in range(len(lines))]
    for label, cy in zip(lines, centers):
        if not label:
            continue
        path = TextPath((0, 0), label, size=size, prop=font, usetex=False)
        bbox = path.get_extents()
        sx, sy = unit * xscale, unit
        if ha == "left":
            tx = x - bbox.x0 * sx
        elif ha == "right":
            tx = x - bbox.x1 * sx
        else:
            tx = x - (bbox.x0 + bbox.x1) * sx / 2
        ty = cy - (bbox.y0 + bbox.y1) * sy / 2
        transformed = path.transformed(Affine2D().scale(sx, sy).translate(tx, ty))
        glyph_patch = PathPatch(transformed, facecolor=color, edgecolor="none", lw=0, zorder=zorder)
        glyph_patch._workflow_text = label
        ax.add_patch(glyph_patch)


def panel_title(ax, label: str, title: str, width: float) -> None:
    txt(ax, 0.8, 43.7, f"({label})", size=11, color=BASE["dark"], weight="bold", ha="left")
    txt(ax, width / 2, 43.7, title, size=11, color=BASE["dark"], weight="bold")


def header(ax, x, y, w, h, label, color, *, radius=0.8, size=8) -> None:
    rounded(ax, x, y, w, h, edge=color, fill=color, lw=0, radius=radius, zorder=2)
    txt(ax, x + w / 2, y + h / 2, label, size=size, color="white", weight="bold", linespacing=1.0)


def separator(ax, x1, y1, x2, y2) -> None:
    ax.plot([x1, x2], [y1, y2], color=BASE["spine"], lw=0.65, ls=(0, (2, 2)), zorder=0)


def arrow(ax, points, color=BASE["dark"], lw=0.8, head=6, linestyle="-") -> None:
    codes = [MplPath.MOVETO] + [MplPath.LINETO] * (len(points) - 1)
    path = MplPath(points, codes)
    patch = FancyArrowPatch(
        path=path,
        arrowstyle="-|>",
        mutation_scale=head,
        linewidth=lw,
        color=color,
        linestyle=linestyle,
        shrinkA=0,
        shrinkB=0,
        zorder=4,
        joinstyle="miter",
    )
    ax.add_patch(patch)


def line(ax, points, color=BASE["dark"], lw=0.7, linestyle="-", zorder=3) -> None:
    xs, ys = zip(*points)
    ax.plot(xs, ys, color=color, lw=lw, ls=linestyle, zorder=zorder)


def raster_icon(ax, name: str, x, y, w, h, *, zorder=5) -> None:
    """Place one cropped icon screenshot without stretching its aspect ratio."""
    if name not in _ICON_CACHE:
        _ICON_CACHE[name] = plt.imread(ICON_DIR / f"{name}.png")
    image = _ICON_CACHE[name]
    ih, iw = image.shape[:2]
    scale = min(w / iw, h / ih)
    draw_w, draw_h = iw * scale, ih * scale
    left = x + (w - draw_w) / 2
    bottom = y + (h - draw_h) / 2
    ax.imshow(
        image,
        extent=(left, left + draw_w, bottom, bottom + draw_h),
        interpolation="none",
        aspect="auto",
        zorder=zorder,
    )


def color_is(color: str, key: str) -> bool:
    return str(color).lower() == COLOR[key].lower()


def document_icon(ax, x, y, w, h, color, *, checklist=False, zorder=5) -> None:
    if checklist and color_is(color, "mas"):
        name = "document_check_mas"
    elif checklist and color_is(color, "teal"):
        name = "document_teal_check"
    elif color_is(color, "human"):
        name = "document_human_clean"
    elif color_is(color, "mas"):
        name = "document_mas_clean"
    elif color_is(color, "teal"):
        name = "document_teal_check"
    else:
        name = "document_gray"
    raster_icon(ax, name, x, y, w, h, zorder=zorder)


def database_icon(ax, x, y, w, h, color, *, lock=False) -> None:
    if color_is(color, "human"):
        name = "database_human"
    elif color_is(color, "mas"):
        name = "database_mas"
    elif color_is(color, "teal"):
        name = "database_teal_locked"
    else:
        name = "database_gray_locked"
    raster_icon(ax, name, x, y, w, h)


def lock_icon(ax, x, y, w, h, color, *, open_lock=False) -> None:
    if color_is(color, "human"):
        name = "lock_human"
    elif color_is(color, "mas"):
        name = "lock_mas"
    elif color_is(color, "teal"):
        name = "lock_teal_open" if open_lock else "lock_teal"
    else:
        name = "lock_gray"
    raster_icon(ax, name, x, y, w, h, zorder=6)


def person_icon(ax, x, y, w, h, color=BASE["text"], *, doctor=False) -> None:
    if color_is(color, "ochre"):
        name = "doctor_ochre"
    elif color_is(color, "teal"):
        name = "person_teal"
    elif color_is(color, "purple"):
        name = "clock_purple"
    else:
        name = "doctor_gray" if doctor else "person_teal"
    raster_icon(ax, name, x, y, w, h)


def group_icon(ax, x, y, w, h, color=BASE["text"], count=3) -> None:
    name = "group_teal" if color_is(color, "teal") else "group_students_gray"
    raster_icon(ax, name, x, y, w, h)


def clipboard_icon(ax, x, y, w, h, color) -> None:
    if color_is(color, "mas"):
        name = "clipboard_mas"
    elif color_is(color, "purple"):
        name = "clipboard_purple"
    elif color_is(color, "teal"):
        name = "document_teal_check"
    else:
        name = "clipboard_purple_clean"
    raster_icon(ax, name, x, y, w, h)


def funnel_icon(ax, x, y, w, h, color) -> None:
    raster_icon(ax, "funnel_teal", x, y, w, h)


def shuffle_icon(ax, x, y, w, h, color) -> None:
    name = "shuffle_teal" if color_is(color, "teal") else "shuffle_gray"
    raster_icon(ax, name, x, y, w, h)


def chart_icon(ax, x, y, w, h, color, *, kind="bar") -> None:
    if color_is(color, "teal"):
        name = {
            "bar": "bars_teal",
            "ci": "bars_teal",
            "interaction": "target_teal",
            "dots": "bars_teal",
        }.get(kind, "bars_teal")
    else:
        name = {
            "bar": "bars_purple",
            "ci": "ci_purple",
            "interaction": "interaction_purple",
            "dots": "dots_purple",
            "curve": "curve_purple",
        }.get(kind, "bars_purple")
    raster_icon(ax, name, x, y, w, h)


def clock_icon(ax, x, y, r, color) -> None:
    if color_is(color, "teal"):
        name = "clock_teal"
    elif color_is(color, "purple"):
        name = "clock_purple"
    else:
        name = "clock_gray"
    raster_icon(ax, name, x - r, y - r, 2 * r, 2 * r)


def target_icon(ax, x, y, r, color) -> None:
    name = "reconstruction_mas" if color_is(color, "mas") else "target_teal"
    raster_icon(ax, name, x - r, y - r, 2 * r, 2 * r)


def shield_icon(ax, x, y, w, h, color, *, mark="check") -> None:
    name = "shield_teal" if color_is(color, "teal") else "shield_ochre"
    raster_icon(ax, name, x, y, w, h)


def gavel_icon(ax, x, y, w, h, color) -> None:
    raster_icon(ax, "gavel_teal", x, y, w, h)


def tag_icon(ax, x, y, w, h, color) -> None:
    name = "tag_teal" if color_is(color, "teal") else "tag_gray"
    raster_icon(ax, name, x, y, w, h)


def phase_container(ax, x, y, w, h, title, color=COLOR["teal"], fill="white", *, header_size=8) -> None:
    rounded(ax, x, y, w, h, edge=color, fill=fill, lw=0.8, radius=0.8)
    header(ax, x, y + h - 3.5, w, 3.5, title, color, radius=0.7, size=header_size)


def small_label_box(
    ax,
    x,
    y,
    w,
    h,
    label,
    edge,
    fill,
    *,
    size=6.5,
    weight="normal",
    xscale=1.0,
    linespacing=1.0,
) -> None:
    rounded(ax, x, y, w, h, edge=edge, fill=fill, lw=0.7, radius=0.55)
    if label and xscale != 1.0:
        path_txt(
            ax,
            x + w / 2,
            y + h / 2,
            label,
            size=size,
            color=BASE["dark"],
            weight=weight,
            xscale=xscale,
            linespacing=linespacing,
        )
        return
    txt(
        ax,
        x + w / 2,
        y + h / 2,
        label,
        size=size,
        color=BASE["dark"],
        weight=weight,
        xscale=xscale,
        linespacing=linespacing,
    )


def figure_1a() -> None:
    fig, ax = canvas(9.0)
    panel_title(ax, "A", "Study workflow: Human versus UroEMAS examination items", 90)
    # Zone headers and separators.
    header(ax, 0.8, 38.6, 30.3, 2.7, "ITEM-BANK CONSTRUCTION", COLOR["human"])
    header(ax, 33.0, 38.6, 32.2, 2.7, "SCREENING AND EXPERT EVALUATION", COLOR["teal"])
    header(ax, 67.1, 38.6, 22.1, 2.7, "STUDENT TESTING AND ANALYSIS", COLOR["purple"])
    separator(ax, 32.0, 2.2, 32.0, 41.4)
    separator(ax, 66.2, 2.2, 66.2, 41.4)

    # Human construction lane.
    rounded(ax, 0.8, 22.8, 29.7, 14.5, edge=COLOR["human"], fill="#F7F8FD", lw=0.8, radius=0.8)
    txt(ax, 15.6, 35.9, "HUMAN (expert-authored; not AI-generated)", size=8, color=COLOR["human"], weight="bold")
    small_label_box(ax, 1.5, 25.2, 7.2, 8.6, "", COLOR["human"], FILL["human"])
    document_icon(ax, 4.1, 29.1, 2.3, 2.9, COLOR["human"])
    txt(ax, 5.1, 27.1, "Human expert\nquestion\ndocuments", size=6.5, color=BASE["dark"], linespacing=1.0)
    small_label_box(ax, 10.5, 25.2, 9.8, 8.6, "", COLOR["human"], FILL["human"])
    document_icon(ax, 11.5, 29.3, 1.7, 2.2, COLOR["human"])
    txt(ax, 15.4, 27.1, "Word → TXT →\nstructured JSON", size=6.5, color=BASE["dark"])
    txt(ax, 14.7, 30.4, "TXT", size=6.5, color=COLOR["human"], weight="bold")
    txt(ax, 17.8, 30.4, "{ }", size=8, color=COLOR["human"], weight="bold")
    small_label_box(ax, 22.1, 25.2, 7.1, 8.6, "", COLOR["human"], FILL["human"])
    database_icon(ax, 24.4, 29.0, 2.6, 3.1, COLOR["human"])
    path_txt(ax, 25.65, 26.8, "Human item bank\n$n$=775", size=6.5, color=BASE["dark"], xscale=0.86)
    arrow(ax, [(8.7, 29.5), (10.4, 29.5)], COLOR["human"], 0.9, 6)
    arrow(ax, [(20.3, 29.5), (22.0, 29.5)], COLOR["human"], 0.9, 6)

    # MAS construction lane.
    rounded(ax, 0.8, 3.7, 29.7, 17.3, edge=COLOR["mas"], fill="#FDF8F7", lw=0.8, radius=0.8)
    txt(ax, 15.6, 19.7, "UroEMAS (MAS-assisted; human-reviewed)", size=8, color=COLOR["mas"], weight="bold")
    small_label_box(ax, 1.3, 7.3, 6.3, 10.3, "", COLOR["mas"], FILL["mas"])
    database_icon(ax, 2.1, 13.2, 2.2, 2.5, COLOR["mas"])
    clipboard_icon(ax, 4.7, 12.6, 1.7, 2.9, COLOR["mas"])
    path_txt(ax, 4.45, 9.6, "Human bank +\nitem-writing\nspecifications", size=5.5, color=BASE["dark"], linespacing=1.0, xscale=0.76)
    modules = [
        (8.2, "1", "Stems and\noptions", "doc"),
        (13.2, "2", "Answer and\nexplanation", "check"),
        (18.3, "3", "Test-point\nreconstruction", "target"),
    ]
    for mx, num, label, icon in modules:
        small_label_box(ax, mx, 7.3, 4.3, 10.3, "", COLOR["mas"], FILL["mas"])
        ax.add_patch(Circle((mx + 2.15, 16.0), 0.75, facecolor=COLOR["mas"], edgecolor="none", zorder=6))
        txt(ax, mx + 2.15, 16.0, num, size=8, color="white", weight="bold")
        if icon == "doc":
            document_icon(ax, mx + 1.15, 12.0, 2.0, 2.4, COLOR["mas"], checklist=True)
        elif icon == "check":
            raster_icon(ax, "check_mas", mx + 1.0, 11.8, 2.3, 2.7)
        else:
            target_icon(ax, mx + 2.15, 13.0, 1.15, COLOR["mas"])
        path_txt(ax, mx + 2.15, 9.1, label, size=5.5, color=BASE["dark"], linespacing=1.0, xscale=0.70)
    small_label_box(ax, 23.4, 7.3, 5.9, 10.3, "", COLOR["mas"], FILL["mas"])
    database_icon(ax, 25.0, 12.4, 2.7, 3.2, COLOR["mas"])
    path_txt(ax, 26.35, 9.4, "UroEMAS item bank\n$n$=3,676", size=5.5, color=BASE["dark"], xscale=0.76)
    for x1, x2 in [(7.6, 8.1), (12.5, 13.1), (17.5, 18.2), (22.6, 23.3)]:
        arrow(ax, [(x1, 12.4), (x2, 12.4)], COLOR["mas"], 0.9, 6)

    # Entry source tabs and machine annotation.
    ax.add_patch(Rectangle((30.5, 28.5), 1.2, 1.15, facecolor=COLOR["human"], edgecolor=BASE["dark"], lw=0.6, zorder=5))
    ax.add_patch(Rectangle((30.5, 27.35), 1.2, 1.15, facecolor=COLOR["mas"], edgecolor=BASE["dark"], lw=0.6, zorder=5))
    arrow(ax, [(31.7, 28.5), (34.0, 28.5)], BASE["dark"], 0.9, 6)
    rounded(ax, 34.0, 24.0, 11.0, 11.7, edge=COLOR["teal"], fill="#F7FCFB", lw=0.8, radius=0.8)
    path_txt(ax, 39.5, 34.0, "Machine annotation", size=8, color=BASE["dark"], weight="bold", xscale=0.80)
    chips = [
        (34.6, 29.0, 4.4, 3.5, "Readability", 0.94),
        (39.4, 29.0, 4.9, 3.5, "Human–MAS\nsimilarity\n(MAS items only)", 0.38),
        (34.6, 24.7, 4.4, 3.5, "QGEval", 0.94),
        (39.4, 24.7, 4.9, 3.5, "ULM", 0.94),
    ]
    for cx, cy, cw, ch, label, xscale in chips:
        small_label_box(
            ax,
            cx,
            cy,
            cw,
            ch,
            label,
            COLOR["teal"],
            FILL["teal"],
            size=5.5,
            xscale=xscale,
            linespacing=0.90,
        )

    # Sampling funnel and expert evaluation.
    arrow(ax, [(39.5, 24.0), (39.5, 22.8), (42.8, 22.0)], BASE["dark"], 0.8, 6)
    rounded(ax, 39.6, 14.8, 6.4, 7.2, edge=COLOR["teal"], fill="#F7FCFB", lw=0.8, radius=0.8)
    funnel_icon(ax, 41.5, 19.2, 2.6, 2.2, COLOR["teal"])
    path_txt(ax, 42.8, 16.9, "First-round\nstratified sample\n$n$=70/source", size=5.5, color=BASE["dark"], linespacing=0.92, xscale=0.92)
    arrow(ax, [(46.0, 18.6), (47.0, 18.6)], BASE["dark"], 0.8, 6)
    rounded(ax, 47.0, 10.0, 12.3, 17.0, edge=COLOR["gray"], fill="#FAFAFA", lw=0.8, radius=0.8)
    path_txt(ax, 52.8, 25.2, "Blinded evaluation by\n3 human experts", size=8, color=BASE["dark"], weight="bold", linespacing=1.0, xscale=0.74)
    lock_icon(ax, 57.0, 23.0, 1.5, 2.2, COLOR["gray"])
    eval_tiles = [
        (47.7, 18.9, 5.1, 4.0, "QGEval\nquality", COLOR["purple"], FILL["purple"]),
        (53.3, 18.9, 5.2, 4.0, "ULM\nquality", COLOR["purple"], FILL["purple"]),
        (47.7, 14.3, 5.1, 4.0, "Major\ndefects", COLOR["ochre"], FILL["ochre"]),
        (53.3, 14.3, 5.2, 4.0, "Source-\nidentification\ntask", COLOR["gray"], FILL["gray"]),
    ]
    for ex, ey, ew, eh, label, edge, fill in eval_tiles:
        small_label_box(ax, ex, ey, ew, eh, label, edge, fill, size=5.5, linespacing=0.90)
    rounded(ax, 48.0, 10.6, 10.3, 2.8, edge=COLOR["gray"], fill=FILL["gray"], lw=0.7, radius=0.45, linestyle=(0, (3, 2)))
    lock_icon(ax, 48.3, 11.0, 1.2, 1.8, COLOR["gray"])
    path_txt(ax, 54.4, 12.0, "Sources are blinded\n(Human vs. UroEMAS)", size=5.5, color=BASE["dark"], weight="bold", linespacing=1.0, xscale=0.82)
    arrow(ax, [(59.3, 18.6), (60.0, 18.6)], BASE["dark"], 0.8, 6)
    rounded(ax, 60.0, 14.8, 5.2, 7.2, edge=COLOR["teal"], fill="#F7FCFB", lw=0.8, radius=0.8)
    funnel_icon(ax, 61.3, 19.2, 2.6, 2.2, COLOR["teal"])
    path_txt(ax, 62.6, 16.9, "Final examination\nblocks\n$n$=50/source", size=5.5, color=BASE["dark"], linespacing=0.92, xscale=0.62)

    # Student-testing zone.
    rounded(ax, 67.2, 2.7, 22.0, 34.4, edge="#C9C1EF", fill="#FCFBFF", lw=0.8, radius=0.8)
    small_label_box(ax, 68.2, 31.5, 8.8, 4.2, "", COLOR["human"], FILL["human"], weight="bold")
    lock_icon(ax, 68.5, 32.0, 1.6, 2.7, COLOR["human"])
    txt(ax, 73.4, 33.6, "Human block\n50 items", size=6.5, color=BASE["dark"], weight="bold", linespacing=1.0)
    small_label_box(ax, 77.8, 31.5, 9.2, 4.2, "", COLOR["mas"], FILL["mas"], weight="bold")
    lock_icon(ax, 78.1, 32.0, 1.6, 2.7, COLOR["mas"])
    txt(ax, 82.8, 33.6, "UroEMAS block\n50 items", size=6.5, color=BASE["dark"], weight="bold", linespacing=1.0)
    line(ax, [(72.6, 31.5), (72.6, 30.2), (82.4, 30.2), (82.4, 31.5)], BASE["dark"], 0.75)
    arrow(ax, [(77.5, 30.2), (77.5, 28.8)], BASE["dark"], 0.8, 6)
    rounded(ax, 68.1, 22.0, 19.0, 6.7, edge=COLOR["gray"], fill="#FAFAFA", lw=0.8, radius=0.7)
    path_txt(ax, 77.6, 27.8, "Randomized two-sequence crossover", size=6.5, color=BASE["dark"], weight="bold", xscale=0.90)
    shuffle_icon(ax, 68.9, 24.4, 2.0, 1.8, BASE["dark"])
    small_label_box(ax, 72.0, 24.9, 14.2, 2.1, "Form A: Human → UroEMAS   $n$=25", COLOR["purple"], FILL["purple"], size=5.5, weight="bold", xscale=0.64)
    small_label_box(ax, 72.0, 22.5, 14.2, 2.1, "Form B: UroEMAS → Human   $n$=25", COLOR["ochre"], FILL["ochre"], size=5.5, weight="bold", xscale=0.64)
    arrow(ax, [(77.6, 22.0), (77.6, 20.5)], BASE["dark"], 0.8, 6)
    rounded(ax, 68.2, 16.2, 18.8, 4.3, edge=COLOR["gray"], fill="#FAFAFA", lw=0.8, radius=0.7)
    group_icon(ax, 69.2, 17.0, 3.1, 2.8, COLOR["gray"])
    txt(ax, 78.2, 18.5, "Student examination\n$n$=50", size=8, color=BASE["dark"], weight="bold")
    arrow(ax, [(77.6, 16.2), (77.6, 14.9)], BASE["dark"], 0.8, 6)
    rounded(ax, 67.8, 3.3, 19.8, 11.5, edge=COLOR["purple"], fill="#FCFBFF", lw=0.8, radius=0.7)
    txt(ax, 76.2, 13.5, "Prespecified analyses", size=8, color=COLOR["purple"], weight="bold")
    chart_icon(ax, 84.0, 12.5, 2.1, 1.7, COLOR["purple"], kind="bar")
    rows = [
        "Expert quality and reliability",
        "Student score and cognitive level",
        "Classical test theory and KR-20",
        "Source detectability",
        "Time, cost, and fatigue",
    ]
    for i, label in enumerate(rows):
        yy = 11.7 - i * 1.65
        ax.add_patch(Rectangle((68.3, yy - 0.65), 18.7, 1.4, facecolor="#FAF8FF", edgecolor="#B5A8F0", lw=0.45, zorder=3))
        txt(ax, 77.65, yy, label, size=6.5, color=BASE["dark"])
    save(fig, "Figure1A_workflow_inputs.pdf")


def figure_1b() -> None:
    fig, ax = canvas(9.0)
    panel_title(ax, "B", "Major-defect safety review and rubric validation", 90)
    # Source cards.
    for y, label, key in [(31.2, "Human\nfirst-round\nitems\n$n$=70", "human"), (18.7, "UroEMAS\nfirst-round\nitems\n$n$=70", "mas")]:
        small_label_box(ax, 0.9, y, 12.0, 8.4, "", COLOR[key], FILL[key])
        document_icon(ax, 2.4, y + 3.1, 2.5, 3.7, COLOR[key])
        txt(ax, 8.8, y + 4.2, label, size=8, color=COLOR[key], weight="bold")
    # Merge to blinding.
    arrow(ax, [(12.9, 35.4), (15.0, 35.4), (15.0, 29.8), (16.5, 29.8)], BASE["dark"], 0.8, 6)
    arrow(ax, [(12.9, 22.9), (15.0, 22.9), (15.0, 29.8), (16.5, 29.8)], BASE["dark"], 0.8, 6)
    rounded(ax, 16.5, 21.0, 9.3, 14.2, edge=COLOR["teal"], fill="#F7FCFB", lw=0.8, radius=0.8)
    path_txt(ax, 21.15, 33.1, "De-identify and\nrandomize", size=8, color=COLOR["teal"], weight="bold", xscale=0.82)
    shuffle_icon(ax, 18.1, 27.3, 5.8, 2.7, COLOR["teal"])
    lock_icon(ax, 19.6, 25.0, 2.5, 3.3, COLOR["teal"])
    path_txt(ax, 21.15, 23.4, "Source labels hidden\nfrom reviewers", size=5.5, color=BASE["dark"], linespacing=1.0, xscale=0.88)
    arrow(ax, [(25.8, 28.9), (27.5, 28.9)], BASE["dark"], 0.8, 6)

    # Review container.
    rounded(ax, 27.5, 16.9, 22.6, 22.0, edge=COLOR["ochre"], fill="#FFFCF5", lw=0.9, radius=1.0)
    txt(ax, 38.8, 37.1, "Independent Major-defect review", size=8, color="#9A6B08", weight="bold")
    small_label_box(ax, 28.7, 29.3, 9.5, 6.1, "", COLOR["ochre"], "#FFFEFA")
    txt(ax, 33.45, 30.4, "Machine\nreview", size=8, color=BASE["dark"], weight="bold")
    raster_icon(ax, "machine_ochre", 31.4, 32.4, 4.0, 2.7)
    small_label_box(ax, 38.7, 29.3, 10.1, 6.1, "", COLOR["ochre"], "#FFFEFA")
    person_icon(ax, 42.4, 32.2, 2.8, 3.1, COLOR["ochre"], doctor=True)
    txt(ax, 43.75, 30.5, "Human expert\nreview", size=8, color=BASE["dark"], weight="bold")
    path_txt(ax, 38.8, 28.0, "Seven-domain major-defect checklist", size=8, color="#9A6B08", weight="bold", xscale=0.90)
    left_items = [(1, "Stem defect"), (2, "Option defect"), (3, "Format defect"), (4, "Answer-key /\nscoring defect")]
    right_items = [(5, "Fairness defect"), (6, "Outdated-guideline\ndefect"), (7, "Linked-item\nstructural defect")]
    for i, (num, label) in enumerate(left_items):
        yy = 25.2 - i * 2.15
        small_label_box(ax, 28.2, yy, 1.5, 1.8, str(num), COLOR["ochre"], "white", weight="bold")
        small_label_box(ax, 29.9, yy, 8.4, 1.8, label, COLOR["ochre"], "white", size=5.5)
    for i, (num, label) in enumerate(right_items):
        yy = 25.2 - i * 2.75
        small_label_box(ax, 38.9, yy, 1.5, 1.8, str(num), COLOR["ochre"], "white", weight="bold")
        small_label_box(
            ax,
            40.6,
            yy - (0.35 if "\n" in label else 0),
            8.6,
            2.5 if "\n" in label else 1.8,
            label,
            COLOR["ochre"],
            "white",
            size=5.5,
        )

    # Decision and branches.
    arrow(ax, [(50.1, 28.0), (52.0, 28.0)], BASE["dark"], 0.8, 6)
    diamond = Polygon([(56.7, 33.1), (61.3, 28.0), (56.7, 22.9), (52.1, 28.0)], closed=True, facecolor=FILL["ochre"], edgecolor=COLOR["ochre"], lw=0.9, zorder=2)
    ax.add_patch(diamond)
    path_txt(ax, 56.7, 28.0, "Any\neducationally\nunacceptable\ndefect?", size=8, color=BASE["dark"], weight="bold", linespacing=0.90, xscale=0.82)
    txt(ax, 62.3, 35.2, "No", size=8, color=COLOR["green"], weight="bold")
    arrow(ax, [(61.3, 30.8), (64.1, 30.8), (64.1, 34.1), (65.2, 34.1)], BASE["dark"], 0.8, 6)
    rounded(ax, 65.2, 30.7, 15.0, 5.6, edge=COLOR["teal"], fill="#F7FCFB", lw=0.8, radius=0.8)
    shield_icon(ax, 65.8, 31.6, 2.1, 3.6, COLOR["teal"], mark="check")
    path_txt(ax, 74.1, 34.2, "No → Pass safety gate", size=8, color=COLOR["teal"], weight="bold", xscale=0.82)
    txt(ax, 74.0, 32.4, "First-round result:\n0/70 in each source", size=6.5, color=BASE["dark"])
    txt(ax, 56.7, 21.7, "Yes", size=8, color="#9A6B08", weight="bold")
    arrow(ax, [(56.7, 22.9), (56.7, 20.4)], BASE["dark"], 0.8, 6)
    small_label_box(ax, 54.2, 15.8, 5.0, 4.6, "", COLOR["ochre"], FILL["ochre"])
    shield_icon(ax, 55.5, 16.7, 2.4, 3.0, COLOR["ochre"], mark="alert")
    arrow(ax, [(59.2, 18.1), (61.2, 18.1)], BASE["dark"], 0.8, 6)
    small_label_box(ax, 61.2, 15.7, 6.9, 4.8, "Assign\ndefect code\nand written\nreason", COLOR["ochre"], FILL["ochre"], weight="bold")
    arrow(ax, [(68.1, 18.1), (70.3, 18.1)], BASE["dark"], 0.8, 6)
    small_label_box(ax, 70.3, 15.7, 7.8, 4.8, "", COLOR["teal"], FILL["teal"])
    gavel_icon(ax, 71.0, 16.7, 2.5, 2.8, COLOR["teal"])
    path_txt(ax, 75.8, 18.1, "Expert\nadjudication", size=6.5, color=BASE["dark"], weight="bold", linespacing=1.0, xscale=0.65)
    # Final status and joins.
    rounded(ax, 80.0, 22.4, 8.7, 9.3, edge=COLOR["gray"], fill="#F5F5F5", lw=0.9, radius=0.8)
    document_icon(ax, 83.0, 27.1, 2.2, 2.8, COLOR["gray"])
    txt(ax, 84.35, 24.5, "Item-level\nsafety status", size=8, color=BASE["dark"], weight="bold")
    arrow(ax, [(80.2, 33.5), (84.4, 33.5), (84.4, 31.7)], BASE["dark"], 0.8, 6)
    arrow(ax, [(78.1, 18.1), (84.4, 18.1), (84.4, 22.4)], BASE["dark"], 0.8, 6)

    # Lower validation branch.
    small_label_box(ax, 1.8, 5.7, 11.9, 7.0, "", COLOR["purple"], FILL["purple"])
    clipboard_icon(ax, 3.2, 7.1, 2.6, 4.5, COLOR["purple"])
    txt(ax, 9.3, 9.2, "Rubric\nvalidation\nsamples", size=8, color="#4C27B8", weight="bold")
    arrow(ax, [(13.7, 9.2), (16.8, 9.2)], BASE["dark"], 0.8, 6)
    arrow(ax, [(16.8, 9.2), (16.8, 12.5), (20.1, 12.5)], BASE["dark"], 0.75, 6)
    arrow(ax, [(16.8, 9.2), (16.8, 6.0), (20.1, 6.0)], BASE["dark"], 0.75, 6)
    small_label_box(ax, 20.1, 10.1, 15.7, 4.9, "", COLOR["purple"], FILL["purple"], size=8, weight="bold")
    chart_icon(ax, 21.0, 11.0, 3.0, 2.6, COLOR["purple"], kind="bar")
    path_txt(ax, 29.3, 12.55, "Low-score band\n$n$=50", size=8, color=BASE["dark"], weight="bold", linespacing=1.0, xscale=0.88)
    small_label_box(ax, 20.1, 3.6, 15.7, 4.9, "", COLOR["purple"], FILL["purple"], size=8, weight="bold")
    chart_icon(ax, 21.0, 4.5, 3.0, 2.6, COLOR["purple"], kind="bar")
    path_txt(ax, 29.3, 6.05, "Middle-score band\n$n$=50", size=8, color=BASE["dark"], weight="bold", linespacing=1.0, xscale=0.82)
    line(ax, [(17.5, 2.5), (17.5, 1.9), (37.9, 1.9), (37.9, 2.5)], BASE["dark"], 0.7)
    txt(ax, 27.7, 0.9, "Proportional sampling from Human and UroEMAS banks", size=6.5, color=BASE["dark"])
    line(ax, [(35.8, 12.5), (38.9, 12.5), (38.9, 9.2)], BASE["dark"], 0.75)
    line(ax, [(35.8, 6.0), (38.9, 6.0), (38.9, 9.2)], BASE["dark"], 0.75)
    arrow(ax, [(38.9, 9.2), (42.2, 9.2)], BASE["dark"], 0.8, 6)
    small_label_box(ax, 42.2, 5.3, 16.0, 7.8, "", COLOR["teal"], FILL["teal"])
    raster_icon(ax, "machine_person_teal", 43.0, 7.5, 7.2, 4.0)
    path_txt(ax, 54.3, 9.2, "Independent\nmachine and\nhuman review", size=8, color=COLOR["teal"], weight="bold", linespacing=1.0, xscale=0.80)
    arrow(ax, [(58.2, 9.2), (61.5, 9.2)], BASE["dark"], 0.8, 6)
    rounded(ax, 61.5, 4.1, 24.0, 10.2, edge=COLOR["purple"], fill=FILL["purple"], lw=0.8, radius=0.8)
    small_label_box(ax, 62.3, 9.4, 22.4, 4.0, "", COLOR["purple"], "#F9F7FF", size=8, weight="bold")
    chart_icon(ax, 63.0, 10.2, 2.5, 2.1, COLOR["purple"], kind="bar")
    path_txt(ax, 75.0, 11.4, "Agreement and category-level\nerror analysis", size=8, color=BASE["dark"], weight="bold", linespacing=1.0, xscale=0.86)
    small_label_box(ax, 62.3, 4.9, 22.4, 3.8, "", COLOR["purple"], "#F9F7FF", size=8, weight="bold")
    person_icon(ax, 63.1, 5.4, 2.1, 2.6, COLOR["purple"])
    path_txt(ax, 75.0, 6.8, "Human adjudication pending", size=8, color=BASE["dark"], weight="bold", xscale=0.84)
    save(fig, "Figure1B_safety_gate.pdf")


def expert_icon_with_label(ax, x, y, label) -> None:
    person_icon(ax, x, y + 1.3, 3.3, 4.0, BASE["text"], doctor=True)
    txt(ax, x + 1.65, y + 0.7, label, size=6.5, color=BASE["dark"], weight="bold")


def figure_2a() -> None:
    fig, ax = canvas(13.5)
    panel_title(ax, "A", "Blinded expert evaluation of item quality", 135)
    # Three main zones.
    phase_container(ax, 1.0, 3.0, 32.0, 37.9, "L1  BLINDED ITEM SET", COLOR["teal"], "white")
    phase_container(ax, 36.5, 3.0, 44.5, 37.9, "L2  THREE HUMAN EXPERTS", COLOR["gray"], "white")
    phase_container(ax, 84.8, 3.0, 49.2, 37.9, "L3  LOCKED ANALYSIS", "#4C2EB8", "white")
    separator(ax, 34.8, 3.0, 34.8, 41.0)
    separator(ax, 82.8, 3.0, 82.8, 41.0)
    # L1 source cards.
    small_label_box(ax, 2.0, 28.6, 14.8, 6.2, "", COLOR["human"], FILL["human"])
    document_icon(ax, 3.4, 30.0, 3.2, 3.8, COLOR["human"])
    txt(ax, 11.0, 31.7, "Human\n$n$=70 items", size=8, color=COLOR["human"], weight="bold")
    small_label_box(ax, 2.0, 14.8, 14.8, 6.2, "", COLOR["mas"], FILL["mas"])
    document_icon(ax, 3.4, 16.2, 3.2, 3.8, COLOR["mas"])
    txt(ax, 11.0, 17.9, "UroEMAS\n$n$=70 items", size=8, color=COLOR["mas"], weight="bold")
    arrow(ax, [(16.8, 31.7), (23.4, 31.7), (23.4, 27.7)], COLOR["human"], 0.9, 6)
    arrow(ax, [(16.8, 17.9), (18.2, 17.9), (18.2, 25.4), (23.2, 25.4)], COLOR["mas"], 0.9, 6)
    rounded(ax, 19.0, 18.6, 12.5, 10.1, edge=COLOR["teal"], fill=FILL["teal"], lw=0.8, radius=0.8)
    shuffle_icon(ax, 23.2, 26.0, 4.0, 2.0, COLOR["teal"])
    txt(ax, 25.25, 23.7, "Replace source\nlabels with study IDs", size=6.5, color=BASE["dark"], weight="bold")
    separator(ax, 19.9, 22.0, 30.6, 22.0)
    txt(ax, 25.25, 20.4, "Randomize\nrating order", size=6.5, color=BASE["dark"], weight="bold")
    arrow(ax, [(25.25, 18.6), (25.25, 15.3)], COLOR["teal"], 0.9, 6)
    rounded(ax, 18.9, 8.0, 12.7, 7.3, edge=COLOR["gray"], fill=FILL["gray"], lw=0.8, radius=0.8)
    database_icon(ax, 20.2, 9.8, 3.2, 3.8, COLOR["gray"], lock=True)
    txt(ax, 27.7, 11.7, "140 blinded\nitems", size=8, color=BASE["dark"], weight="bold", linespacing=1.0)

    # L2 expert container and assessment modules.
    rounded(ax, 37.5, 8.6, 42.5, 28.6, edge=BASE["border"], fill="#FCFCFC", lw=0.8, radius=0.8)
    txt(ax, 58.75, 35.7, "3 independent human experts", size=8, color=BASE["dark"], weight="bold")
    expert_icon_with_label(ax, 42.0, 29.8, "Expert 1")
    expert_icon_with_label(ax, 57.0, 29.8, "Expert 3")
    expert_icon_with_label(ax, 72.0, 29.8, "Expert 4")
    separator(ax, 51.4, 29.0, 51.4, 35.0)
    separator(ax, 66.4, 29.0, 66.4, 35.0)
    modules = [
        (24.9, "QGEval: 7 dimensions, total 35", COLOR["purple"], FILL["purple"]),
        (21.1, "ULM: 16 dimensions, total 76", COLOR["purple"], FILL["purple"]),
        (17.3, "Major-defect review: 7 categories", COLOR["ochre"], FILL["ochre"]),
        (13.5, "Source guess: Human or UroEMAS", COLOR["gray"], FILL["gray"]),
    ]
    for my, label, edge, fill in modules:
        small_label_box(ax, 44.5, my, 28.5, 3.0, label, edge, fill, size=8, weight="bold")
        if my > 20:
            clipboard_icon(ax, 46.0, my + 0.25, 1.6, 2.4, edge)
        elif my > 16:
            shield_icon(ax, 45.8, my + 0.2, 2.1, 2.5, edge, mark="alert")
        else:
            raster_icon(ax, "question_gray", 45.7, my + 0.35, 2.2, 2.3)
    # Expert connectors run along outer rails.
    for cx in [43.65, 58.65, 73.65]:
        arrow(ax, [(cx, 29.8), (cx, 27.9)], BASE["dark"], 0.7, 5)
    line(ax, [(43.65, 27.9), (43.65, 15.0)], BASE["dark"], 0.65)
    line(ax, [(73.65, 27.9), (73.65, 15.0)], BASE["dark"], 0.65)
    for my, *_ in modules:
        arrow(ax, [(43.65, my + 1.5), (44.45, my + 1.5)], BASE["dark"], 0.65, 5)
        arrow(ax, [(73.65, my + 1.5), (73.05, my + 1.5)], BASE["dark"], 0.65, 5)
    # Tags.
    small_label_box(ax, 42.8, 5.1, 11.0, 3.0, "Item type", COLOR["gray"], FILL["gray"], weight="bold")
    tag_icon(ax, 44.0, 5.7, 2.0, 1.8, COLOR["gray"])
    small_label_box(ax, 58.1, 4.7, 18.0, 3.8, "Cognitive level:\nKnowledge, Comprehension,\nApplication, Analysis", COLOR["gray"], FILL["gray"], weight="bold")
    line(ax, [(58.75, 13.5), (58.75, 10.0), (48.3, 10.0), (48.3, 8.2)], BASE["spine"], 0.65, linestyle=(0, (3, 2)))
    line(ax, [(58.75, 10.0), (67.1, 10.0), (67.1, 8.2)], BASE["spine"], 0.65, linestyle=(0, (3, 2)))

    # L3 locked analysis.
    rounded(ax, 95.1, 31.5, 22.0, 5.3, edge=COLOR["teal"], fill=FILL["teal"], lw=0.8, radius=0.8)
    database_icon(ax, 97.0, 32.4, 3.2, 3.6, COLOR["teal"], lock=True)
    txt(ax, 108.8, 34.2, "Quality-control checks\nand rater–item linkage", size=8, color=BASE["dark"], weight="bold")
    arrow(ax, [(106.1, 31.5), (106.1, 28.7)], COLOR["teal"], 0.9, 6)
    rounded(ax, 95.1, 23.2, 22.0, 5.4, edge=COLOR["teal"], fill=FILL["teal"], lw=0.8, radius=0.8)
    lock_icon(ax, 97.0, 24.1, 3.0, 3.8, COLOR["teal"], open_lock=True)
    txt(ax, 108.7, 25.9, "Unlock true source\nonly after ratings\nare complete", size=8, color=BASE["dark"], weight="bold")
    line(ax, [(106.1, 23.2), (106.1, 20.7), (89.0, 20.7), (89.0, 18.5)], COLOR["teal"], 0.8)
    endpoints = [
        (85.2, "B", "Composite\nquality\ndifference", "ci"),
        (95.0, "C", "23 dimension-\nlevel comparisons", "bar"),
        (105.0, "D", "Quality gap\nby cognitive\nlevel", "bar"),
        (115.0, "E", "Source ×\ncognitive-level\nmixed model", "interaction"),
        (125.0, "F", "Inter-rater ICC\nfor QGEval\nand ULM", "dots"),
    ]
    for ex, letter, label, kind in endpoints:
        rounded(ax, ex, 4.0, 8.5, 14.5, edge=COLOR["purple"], fill="#FCFBFF", lw=0.8, radius=0.7)
        txt(ax, ex + 4.25, 17.2, letter, size=11, color="#34218F", weight="bold")
        path_txt(ax, ex + 4.25, 14.3, label, size=6.5, color=BASE["dark"], weight="bold", linespacing=1.0, xscale=0.86)
        chart_icon(ax, ex + 1.5, 6.1, 5.5, 4.8, COLOR["purple"], kind=kind)
        arrow(ax, [(106.1, 20.7), (ex + 4.25, 20.7), (ex + 4.25, 18.5)], COLOR["teal"], 0.7, 5)
    save(fig, "Figure2A_expert_quality_evaluation_workflow.pdf")


def figure_3a() -> None:
    fig, ax = canvas(9.0)
    panel_title(ax, "A", "Randomized two-sequence student examination", 90)
    # Four phase frames.
    phase_container(ax, 0.8, 2.3, 19.8, 38.5, "PHASE 1\nPARTICIPANTS AND BLOCKS", COLOR["teal"], "white", header_size=6.5)
    phase_container(ax, 23.4, 2.3, 24.2, 38.5, "PHASE 2\nBALANCED SEQUENCE ALLOCATION", COLOR["gray"], "white", header_size=6.5)
    phase_container(ax, 50.4, 2.3, 17.4, 38.5, "PHASE 3\nEXAMINATION AND DATA CAPTURE", COLOR["teal"], "white", header_size=5.5)
    phase_container(ax, 70.2, 2.3, 19.0, 38.5, "PHASE 4\nPRESPECIFIED ANALYSES", COLOR["teal"], "white", header_size=6.5)
    for sx in [22.0, 49.0, 69.0]:
        separator(ax, sx, 2.3, sx, 40.8)
    # Phase 1 participant and blocks.
    rounded(ax, 1.5, 13.0, 8.2, 20.5, edge=COLOR["teal"], fill=FILL["teal"], lw=0.8, radius=0.8)
    group_icon(ax, 2.5, 27.8, 5.8, 4.0, COLOR["teal"])
    txt(ax, 5.6, 24.5, "Urology\ntrainees\n$n$=50", size=8, color=BASE["dark"], weight="bold", linespacing=1.0)
    separator(ax, 2.1, 21.6, 9.1, 21.6)
    small_label_box(ax, 2.1, 17.8, 7.0, 2.7, "", COLOR["teal"], "white")
    txt(ax, 2.8, 19.2, "◆", size=6.5, color=COLOR["teal"])
    txt(ax, 6.1, 19.2, "Training year", size=6.5, color=BASE["dark"])
    small_label_box(ax, 2.1, 14.2, 7.0, 2.7, "", COLOR["teal"], "white")
    txt(ax, 2.8, 15.6, "▥", size=8, color=COLOR["teal"])
    txt(ax, 6.1, 15.6, "Campus", size=6.5, color=BASE["dark"])
    small_label_box(ax, 12.0, 26.8, 7.4, 9.5, "", COLOR["human"], FILL["human"])
    lock_icon(ax, 15.3, 34.1, 1.8, 2.5, COLOR["human"])
    document_icon(ax, 14.2, 30.5, 2.7, 3.4, COLOR["human"], checklist=True)
    path_txt(ax, 15.7, 28.8, "Human block\n50 items", size=8, color=BASE["dark"], weight="bold", linespacing=1.0, xscale=0.76)
    small_label_box(ax, 12.0, 14.1, 7.4, 9.5, "", COLOR["mas"], FILL["mas"])
    lock_icon(ax, 15.3, 21.4, 1.8, 2.5, COLOR["mas"])
    document_icon(ax, 14.2, 17.8, 2.7, 3.4, COLOR["mas"], checklist=True)
    path_txt(ax, 15.7, 16.1, "UroEMAS block\n50 items", size=8, color=BASE["dark"], weight="bold", linespacing=1.0, xscale=0.64)
    line(ax, [(9.7, 23.0), (11.0, 23.0), (11.0, 31.6), (12.0, 31.6)], BASE["spine"], 0.7, linestyle=(0, (3, 2)))
    line(ax, [(11.0, 23.0), (11.0, 18.8), (12.0, 18.8)], BASE["spine"], 0.7, linestyle=(0, (3, 2)))
    small_label_box(ax, 2.6, 5.1, 16.0, 4.1, "", COLOR["gray"], "#FAFAFA", size=8, weight="bold")
    group_icon(ax, 3.4, 5.8, 3.1, 2.7, COLOR["gray"])
    path_txt(ax, 12.5, 7.15, "Same two blocks\nfor every participant", size=8, color=BASE["dark"], weight="bold", linespacing=1.0, xscale=0.76)
    arrow(ax, [(19.4, 23.0), (23.3, 23.0)], BASE["dark"], 0.9, 6)
    # Phase 2 random allocation and parallel forms.
    rounded(ax, 24.0, 17.6, 4.2, 10.5, edge=COLOR["gray"], fill="#F7F7F7", lw=0.8, radius=0.7)
    shuffle_icon(ax, 25.0, 24.6, 2.2, 1.8, COLOR["gray"])
    path_txt(ax, 26.1, 21.6, "Random\nallocation\n(1:1)", size=5.5, color=BASE["dark"], weight="bold", linespacing=1.0, xscale=0.78)
    arrow(ax, [(28.2, 23.0), (29.3, 23.0), (29.3, 32.0), (31.0, 32.0)], BASE["dark"], 0.8, 6)
    arrow(ax, [(29.3, 23.0), (29.3, 12.0), (31.0, 12.0)], BASE["dark"], 0.8, 6)
    rounded(ax, 31.0, 25.8, 15.6, 10.5, edge=COLOR["purple"], fill="#FCFBFF", lw=0.8, radius=0.8)
    txt(ax, 38.8, 34.5, "Form A\n$n$=25", size=8, color="#4C27B8", weight="bold")
    small_label_box(ax, 31.8, 27.0, 6.4, 5.5, "", COLOR["human"], FILL["human"])
    document_icon(ax, 32.3, 28.8, 1.5, 2.2, COLOR["human"])
    path_txt(ax, 36.0, 29.8, "First:\nHuman", size=5.5, color=BASE["dark"], weight="bold", linespacing=1.0, xscale=0.92)
    arrow(ax, [(38.2, 29.7), (39.7, 29.7)], BASE["dark"], 0.8, 6)
    small_label_box(ax, 39.7, 27.0, 6.2, 5.5, "", COLOR["mas"], FILL["mas"])
    document_icon(ax, 40.2, 28.8, 1.5, 2.2, COLOR["mas"])
    path_txt(ax, 44.0, 29.8, "Second:\nUroEMAS", size=5.5, color=BASE["dark"], weight="bold", linespacing=1.0, xscale=0.86)
    rounded(ax, 31.0, 6.7, 15.6, 10.5, edge=COLOR["ochre"], fill="#FFFDF8", lw=0.8, radius=0.8)
    txt(ax, 38.8, 15.4, "Form B\n$n$=25", size=8, color="#9A6B08", weight="bold")
    small_label_box(ax, 31.8, 7.8, 6.4, 5.5, "", COLOR["mas"], FILL["mas"])
    document_icon(ax, 32.3, 9.6, 1.5, 2.2, COLOR["mas"])
    path_txt(ax, 36.0, 10.6, "First:\nUroEMAS", size=5.5, color=BASE["dark"], weight="bold", linespacing=1.0, xscale=0.86)
    arrow(ax, [(38.2, 10.5), (39.7, 10.5)], BASE["dark"], 0.8, 6)
    small_label_box(ax, 39.7, 7.8, 6.2, 5.5, "", COLOR["human"], FILL["human"])
    document_icon(ax, 40.2, 9.6, 1.5, 2.2, COLOR["human"])
    path_txt(ax, 44.0, 10.6, "Second:\nHuman", size=5.5, color=BASE["dark"], weight="bold", linespacing=1.0, xscale=0.90)
    clock_icon(ax, 35.4, 21.2, 1.4, COLOR["gray"])
    txt(ax, 40.5, 21.2, "Order/fatigue\nbalanced by design", size=6.5, color=BASE["dark"])
    # Route both forms to phase 3.
    line(ax, [(46.6, 31.0), (48.7, 31.0), (48.7, 23.0)], BASE["dark"], 0.75)
    line(ax, [(46.6, 12.0), (48.7, 12.0), (48.7, 23.0)], BASE["dark"], 0.75)
    arrow(ax, [(48.7, 23.0), (50.3, 23.0)], BASE["dark"], 0.9, 6)
    # Phase 3 capture.
    rounded(ax, 51.7, 4.5, 14.8, 31.5, edge=COLOR["teal"], fill="#F8FCFB", lw=0.8, radius=0.8)
    raster_icon(ax, "examinee_teal", 55.2, 29.3, 8.0, 6.1)
    capture = [
        (25.8, "Item responses", "doc"),
        (20.5, "Block scores", "bar"),
        (15.2, "Cognitive-level\naccuracy", "target"),
        (9.9, "Total examination\nduration", "clock"),
    ]
    for cy, label, kind in capture:
        small_label_box(ax, 52.7, cy, 12.8, 4.2, "", COLOR["teal"], FILL["teal"])
        if kind == "doc":
            document_icon(ax, 53.6, cy + 0.8, 1.6, 2.5, COLOR["teal"], checklist=True)
        elif kind == "bar":
            chart_icon(ax, 53.5, cy + 0.8, 2.1, 2.5, COLOR["teal"], kind="bar")
        elif kind == "target":
            target_icon(ax, 54.6, cy + 2.1, 1.25, COLOR["teal"])
        else:
            clock_icon(ax, 54.6, cy + 2.1, 1.25, COLOR["teal"])
        txt(ax, 60.7, cy + 2.1, label, size=6.5, color=BASE["dark"], weight="bold")
    separator(ax, 52.5, 8.9, 65.7, 8.9)
    txt(ax, 59.1, 6.7, "Participant-level\npaired data", size=8, color=COLOR["teal"], weight="bold")
    arrow(ax, [(67.8, 23.0), (70.1, 23.0)], BASE["dark"], 0.9, 6)
    # Phase 4 endpoints.
    outcomes = [
        (31.5, "B", "Total score\ncomparison", "ci"),
        (25.6, "C", "Accuracy by\ncognitive level", "bar"),
        (19.7, "D", "Adjusted source ×\ncognitive-level\nmodel", "interaction"),
        (10.2, "E", "Difficulty and\ndiscrimination", "curve"),
        (4.4, "F", "KR-20 /\nCronbach’s alpha", "dots"),
    ]
    for oy, letter, label, kind in outcomes:
        small_label_box(ax, 71.0, oy, 17.2, 5.0, "", COLOR["purple"], "#FCFBFF")
        rounded(ax, 71.7, oy + 1.1, 2.4, 2.8, edge=COLOR["purple"], fill=COLOR["purple"], lw=0, radius=0.35, zorder=4)
        txt(ax, 72.9, oy + 2.5, letter, size=11, color="white", weight="bold")
        chart_icon(ax, 75.2, oy + 1.0, 3.2, 3.0, COLOR["purple"], kind=kind)
        txt(ax, 83.1, oy + 2.5, label, size=6.5, color=BASE["dark"], weight="bold")
    rounded(ax, 73.9, 15.5, 13.7, 3.4, edge=COLOR["gray"], fill="#FAFAFA", lw=0.7, radius=0.55, linestyle=(0, (3, 2)))
    group_icon(ax, 74.4, 16.1, 2.2, 2.0, COLOR["gray"])
    path_txt(ax, 82.7, 17.15, "Adjust for order, campus,\ntraining year, and form", size=5.5, color=BASE["dark"], linespacing=1.0, xscale=0.90)
    line(ax, [(79.6, 19.7), (79.6, 19.0)], BASE["spine"], 0.65, linestyle=(0, (3, 2)))
    save(fig, "Figure3A_student_testing_workflow.pdf")


def probability_mini(ax, x, y, w, h) -> None:
    # 40-60% axis and nested near-chance regions, intentionally no observed estimate.
    ax.add_patch(Rectangle((x + w * 0.16, y + h * 0.36), w * 0.68, h * 0.23, facecolor=FILL["teal"], edgecolor="none", zorder=2))
    ax.add_patch(Rectangle((x + w * 0.33, y + h * 0.36), w * 0.34, h * 0.23, facecolor=FILL["bluepurple"], edgecolor="none", zorder=3))
    line(ax, [(x + w * 0.08, y + h * 0.70), (x + w * 0.92, y + h * 0.70)], BASE["dark"], 0.65, zorder=5)
    for frac, lab in [(0.12, "40%"), (0.50, "50% chance"), (0.88, "60%")]:
        xx = x + w * frac
        line(ax, [(xx, y + h * 0.63), (xx, y + h * 0.77)], BASE["dark"], 0.6, zorder=5)
        path_txt(ax, xx, y + h * 0.89, lab, size=5.5, color=BASE["dark"], weight="bold", xscale=0.90)
    line(ax, [(x + w * 0.5, y + h * 0.30), (x + w * 0.5, y + h * 0.92)], COLOR["gray"], 0.6, linestyle=(0, (2, 2)), zorder=5)
    path_txt(ax, x + w * 0.5, y + h * 0.475, "45%          55%", size=5.5, color=BASE["dark"], weight="bold", xscale=0.88)
    path_txt(ax, x + w * 0.5, y + h * 0.25, "Strict near-chance: 45–55%", size=5.5, color="#4C27B8", weight="bold", xscale=0.72)
    path_txt(ax, x + w * 0.5, y + h * 0.11, "Loose near-chance: 40–60%", size=5.5, color=COLOR["teal"], weight="bold", xscale=0.72)


def figure_4a() -> None:
    fig, ax = canvas(4.5)
    panel_title(ax, "A", "Blinded source-identification workflow", 45)
    # Zone 1.  Content is kept entirely below the green title band.
    phase_container(ax, 0.5, 30.8, 44.0, 10.3, "①  SOURCE-CONCEALED MATERIALS", COLOR["teal"], "white", header_size=6.5)
    small_label_box(ax, 1.5, 34.3, 8.4, 2.5, "", COLOR["human"], FILL["human"])
    document_icon(ax, 2.2, 34.7, 1.5, 1.8, COLOR["human"])
    path_txt(ax, 6.9, 35.55, "Human items", size=6.5, color=COLOR["human"], weight="bold", xscale=0.72)
    small_label_box(ax, 1.5, 31.4, 8.4, 2.5, "", COLOR["mas"], FILL["mas"])
    document_icon(ax, 2.2, 31.8, 1.5, 1.8, COLOR["mas"])
    path_txt(ax, 7.0, 32.65, "UroEMAS items", size=6.5, color=COLOR["mas"], weight="bold", xscale=0.60)
    arrow(ax, [(9.9, 35.55), (14.0, 35.55)], COLOR["human"], 0.8, 5)
    arrow(ax, [(9.9, 32.65), (14.0, 32.65)], COLOR["mas"], 0.8, 5)
    rounded(ax, 14.0, 31.3, 13.5, 5.6, edge=COLOR["teal"], fill=FILL["teal"], lw=0.8, radius=0.6)
    tag_icon(ax, 14.8, 35.2, 1.7, 1.1, COLOR["teal"])
    path_txt(ax, 22.2, 35.75, "Replace source labels\nwith study IDs", size=6.5, color=BASE["dark"], weight="bold", linespacing=0.9, xscale=0.76)
    separator(ax, 14.6, 34.8, 26.9, 34.8)
    shuffle_icon(ax, 14.9, 33.5, 1.8, 0.8, COLOR["teal"])
    path_txt(ax, 22.2, 33.9, "Randomize presentation order", size=6.5, color=BASE["dark"], weight="bold", xscale=0.66)
    separator(ax, 14.6, 33.0, 26.9, 33.0)
    lock_icon(ax, 15.0, 31.55, 1.6, 1.5, COLOR["teal"])
    path_txt(ax, 21.8, 32.15, "Lock the source key", size=6.5, color=BASE["dark"], weight="bold", xscale=0.80)
    arrow(ax, [(27.5, 34.1), (31.1, 34.1)], COLOR["teal"], 0.8, 5)
    rounded(ax, 31.1, 32.1, 11.7, 4.2, edge=COLOR["gray"], fill=FILL["gray"], lw=0.8, radius=0.6)
    raster_icon(ax, "stack_gray", 31.6, 32.7, 4.0, 3.0)
    path_txt(ax, 39.3, 34.2, "Blinded items\nand examination\nblocks", size=6.5, color=BASE["dark"], weight="bold", linespacing=0.9, xscale=0.80)

    # Zone 2.  Two balanced task cards with one shared baseline.
    phase_container(ax, 0.5, 15.9, 44.0, 14.3, "②  TWO IDENTIFICATION TASKS", COLOR["gray"], "white", header_size=6.5)
    rounded(ax, 1.5, 16.6, 19.5, 9.6, edge=COLOR["gray"], fill="#FCFCFC", lw=0.8, radius=0.6)
    txt(ax, 11.25, 25.2, "Expert item-level judgments", size=8, color=BASE["dark"], weight="bold", xscale=0.86)
    for x, lab in [(3.7, "Expert 1"), (9.2, "Expert 3"), (14.7, "Expert 4")]:
        person_icon(ax, x, 22.5, 2.1, 2.4, BASE["text"], doctor=True)
        txt(ax, x + 1.05, 22.0, lab, size=6.5, color=BASE["dark"], weight="bold")
    line(ax, [(3.2, 21.3), (19.2, 21.3)], BASE["dark"], 0.6)
    arrow(ax, [(3.2, 21.3), (3.2, 20.05)], BASE["dark"], 0.65, 5)
    txt(ax, 11.25, 20.45, "140 judgments per expert", size=5.5, color=BASE["dark"], weight="bold")
    rounded(ax, 2.7, 17.1, 17.0, 2.9, edge=COLOR["gray"], fill="#FAFAFA", lw=0.7, radius=0.5, linestyle=(0, (3, 2)))
    small_label_box(ax, 3.2, 17.6, 5.7, 1.9, "", COLOR["gray"], FILL["gray"], weight="bold")
    path_txt(ax, 6.05, 18.55, "Guess Human", size=6.5, color=BASE["dark"], weight="bold", xscale=0.72)
    txt(ax, 11.2, 18.55, "OR", size=8, color=BASE["dark"], weight="bold")
    small_label_box(ax, 13.2, 17.6, 5.9, 1.9, "", COLOR["gray"], FILL["gray"], weight="bold")
    path_txt(ax, 16.15, 18.55, "Guess UroEMAS", size=6.5, color=BASE["dark"], weight="bold", xscale=0.66)
    separator(ax, 22.5, 16.6, 22.5, 26.2)
    rounded(ax, 24.0, 16.6, 19.5, 9.6, edge=COLOR["gray"], fill="#FCFCFC", lw=0.8, radius=0.6)
    path_txt(ax, 33.75, 25.2, "Student block-level judgments", size=8, color=BASE["dark"], weight="bold", xscale=0.76)
    group_icon(ax, 32.0, 23.0, 3.5, 1.7, BASE["text"])
    txt(ax, 33.75, 21.7, "48 students with complete\nsource judgments", size=5.5, color=BASE["dark"], weight="bold", linespacing=1.0, xscale=0.94)
    rounded(ax, 25.2, 17.1, 17.0, 3.5, edge=COLOR["gray"], fill="#FAFAFA", lw=0.7, radius=0.5, linestyle=(0, (3, 2)))
    txt(ax, 33.7, 19.9, "Which block was UroEMAS?", size=5.5, color=BASE["dark"], weight="bold", xscale=0.92)
    small_label_box(ax, 25.8, 17.5, 5.7, 1.8, "", COLOR["gray"], FILL["gray"], weight="bold")
    path_txt(ax, 28.65, 18.4, "Guess Human", size=6.5, color=BASE["dark"], weight="bold", xscale=0.72)
    txt(ax, 33.75, 18.4, "OR", size=8, color=BASE["dark"], weight="bold")
    small_label_box(ax, 35.8, 17.5, 5.8, 1.8, "", COLOR["gray"], FILL["gray"], weight="bold")
    path_txt(ax, 38.7, 18.4, "Guess UroEMAS", size=6.5, color=BASE["dark"], weight="bold", xscale=0.66)

    # Zone 3.  The linkage gate sits below the title band; four analysis cards
    # use the full width below it.
    phase_container(ax, 0.5, 0.6, 44.0, 14.5, "③  UNBLINDING AND ANALYSIS", COLOR["teal"], "white", header_size=6.5)
    line(ax, [(11.2, 16.6), (11.2, 15.5), (20.0, 15.5), (20.0, 11.4)], COLOR["teal"], 0.75)
    line(ax, [(33.7, 16.6), (33.7, 15.5), (24.5, 15.5), (24.5, 11.4)], COLOR["teal"], 0.75)
    rounded(ax, 14.2, 9.2, 16.6, 2.2, edge=COLOR["teal"], fill=FILL["teal"], lw=0.8, radius=0.5)
    lock_icon(ax, 15.0, 9.45, 1.6, 1.65, COLOR["teal"], open_lock=True)
    path_txt(ax, 24.4, 10.3, "Link each guess to the locked true source", size=5.5, color=BASE["dark"], weight="bold", xscale=0.68)
    endpoints = [
        (1.0, "B", "Expert accuracy\nwith Wilson\n90% CI"),
        (11.7, "C", "Expert\nconfusion matrix"),
        (22.4, "D", "Mixed model for\nguessed UroEMAS"),
        (33.1, "E", "Student accuracy\nwith Wilson\n90% CI"),
    ]
    for ex, letter, label in endpoints:
        rounded(ax, ex, 0.68, 10.0, 8.12, edge=COLOR["purple"], fill="#FCFBFF", lw=0.8, radius=0.55)
        rounded(ax, ex + 0.7, 6.7, 1.6, 1.6, edge=COLOR["purple"], fill=COLOR["purple"], lw=0, radius=0.22, zorder=4)
        txt(ax, ex + 1.5, 7.5, letter, size=11, color="white", weight="bold")
        path_txt(ax, ex + 6.7, 7.45, label, size=5.5, color=BASE["dark"], weight="bold", linespacing=0.9, xscale=0.86)
        arrow(ax, [(22.5, 9.2), (ex + 5.0, 9.2), (ex + 5.0, 8.85)], COLOR["teal"], 0.6, 5)
    probability_mini(ax, 1.4, 0.82, 9.2, 4.4)
    # Confusion matrix.
    path_txt(ax, 18.6, 5.25, "True source", size=5.5, color=BASE["dark"], weight="bold", xscale=0.82)
    path_txt(ax, 17.4, 4.55, "Human", size=5.5, color=BASE["dark"], weight="bold", xscale=0.52)
    path_txt(ax, 19.8, 4.55, "UroEMAS", size=5.5, color=BASE["dark"], weight="bold", xscale=0.38)
    ax.add_patch(Rectangle((16.5, 1.10), 4.2, 3.00, facecolor="white", edgecolor=COLOR["gray"], lw=0.7, zorder=4))
    line(ax, [(18.6, 1.10), (18.6, 4.10)], COLOR["gray"], 0.6, zorder=5)
    line(ax, [(16.5, 2.60), (20.7, 2.60)], COLOR["gray"], 0.6, zorder=5)
    txt(ax, 12.55, 2.60, "Guessed", size=5.5, color=BASE["dark"], weight="bold", rotation=90)
    path_txt(ax, 16.2, 3.35, "Human", size=5.5, color=BASE["dark"], weight="bold", ha="right", xscale=0.82)
    path_txt(ax, 16.2, 1.85, "UroEMAS", size=5.5, color=BASE["dark"], weight="bold", ha="right", xscale=0.72)
    for xx, yy, lab in [(17.55, 3.35, "$a$"), (19.65, 3.35, "$b$"), (17.55, 1.85, "$c$"), (19.65, 1.85, "$d$")]:
        txt(ax, xx, yy, lab, size=8, color=BASE["dark"], style="italic")
    # Forest plot and compact mixed-model formula.
    line(ax, [(24.2, 3.25), (31.6, 3.25)], BASE["dark"], 0.55, zorder=5)
    line(ax, [(28.0, 3.25), (28.0, 6.05)], BASE["spine"], 0.55, linestyle=(0, (2, 2)), zorder=5)
    for i, (center, lo, hi) in enumerate([(28.5, 27.2, 29.6), (27.5, 26.4, 28.9), (28.1, 26.9, 29.3), (26.9, 25.7, 28.4)]):
        yy = 5.8 - i * 0.58
        line(ax, [(lo, yy), (hi, yy)], BASE["dark"], 0.55, zorder=5)
        ax.add_patch(Circle((center, yy), 0.12, facecolor=COLOR["purple"], edgecolor="none", zorder=6))
    rounded(ax, 23.1, 0.82, 8.6, 2.15, edge=COLOR["gray"], fill="#FAFAFA", lw=0.6, radius=0.3, linestyle=(0, (3, 2)))
    path_txt(ax, 27.4, 1.90, "guess ~ true source +\nitem features + crossed\nexpert/item effects", size=5.5, color=BASE["dark"], weight="bold", linespacing=0.84, xscale=0.72)
    probability_mini(ax, 33.5, 0.82, 9.2, 4.4)
    save(fig, "Figure4A_turing_test_workflow.pdf")


def main() -> None:
    setup_style()
    figure_1a()
    figure_1b()
    figure_2a()
    figure_3a()
    figure_4a()
    for name in [
        "Figure1A_workflow_inputs.pdf",
        "Figure1B_safety_gate.pdf",
        "Figure2A_expert_quality_evaluation_workflow.pdf",
        "Figure3A_student_testing_workflow.pdf",
        "Figure4A_turing_test_workflow.pdf",
    ]:
        print(f"Wrote {(OUT / name).relative_to(REPO_ROOT)}")
    # These panels are inputs to the assembled figures. Refresh their derived
    # PDFs in the same run so an updated standalone panel cannot leave a stale
    # Figure1--Figure4 behind.
    subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "plotting" / "assemble_final_figures.py"),
            "Figure1",
            "Figure2",
            "Figure3",
            "Figure4",
        ],
        cwd=REPO_ROOT,
        check=True,
    )


if __name__ == "__main__":
    main()
