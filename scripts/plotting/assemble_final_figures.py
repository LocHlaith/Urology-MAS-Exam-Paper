#!/usr/bin/env python3
"""Assemble manuscript panels into rectangular, vector-preserving PDFs.

脚本用途：把正式 panel PDF 拼接为 Figure 1–6，并为 PPT 手工流程图保留固定位置。
流程阶段：论文绘图与最终拼版。
主要输入：outputs/figures/panels 下的正式 PDF panel。
主要输出：outputs/figures/assembled/Figure1.pdf 至 Figure6.pdf。
重要边界：1A、1B、2A、3A、4A 缺失时仅绘制占位框；占位框不冒充正式流程图。
"""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PANEL_DIR = REPO_ROOT / "outputs" / "figures" / "panels"
ASSEMBLED_DIR = REPO_ROOT / "outputs" / "figures" / "assembled"
UNIT_INCHES = 4.5


@dataclass(frozen=True)
class Slot:
    panel: str
    filename: str
    column: int
    row: int
    width_units: int = 1
    height_units: int = 1
    manual: bool = False


@dataclass(frozen=True)
class FigureLayout:
    columns: int
    rows: int
    slots: tuple[Slot, ...]


LAYOUTS = {
    "Figure1": FigureLayout(
        columns=2,
        rows=2,
        slots=(
            Slot("A", "Figure1A_workflow_inputs.pdf", 0, 0, 2, 1, True),
            Slot("B", "Figure1B_safety_gate.pdf", 0, 1, 2, 1, True),
        ),
    ),
    "Figure2": FigureLayout(
        columns=4,
        rows=3,
        slots=(
            Slot("A", "Figure2A_expert_quality_evaluation_workflow.pdf", 0, 0, 3, 1, True),
            Slot("B", "Figure2B_quality_difference.pdf", 3, 0, 1, 2),
            Slot("C", "Figure2C_dimension_scores.pdf", 0, 1, 1, 2),
            Slot("D", "Figure2D_quality_by_cognitive_level.pdf", 1, 1, 2, 1),
            Slot("E", "Figure2E_expert_quality_source_cognitive_interaction.pdf", 1, 2, 2, 1),
            Slot("F", "Figure2F_expert_inter_rater_reliability.pdf", 3, 2, 1, 1),
        ),
    ),
    "Figure3": FigureLayout(
        columns=4,
        rows=3,
        slots=(
            Slot("A", "Figure3A_student_testing_workflow.pdf", 0, 0, 2, 1, True),
            Slot("B", "Figure3B_student_correct_rate.pdf", 2, 0, 2, 1),
            Slot("C", "Figure3C_student_accuracy_by_cognitive_level.pdf", 0, 1, 2, 1),
            Slot("D", "Figure3D_source_cognitive_interaction.pdf", 2, 1, 2, 1),
            Slot("E", "Figure3E_ctt_by_cognitive_level.pdf", 0, 2, 2, 1),
            Slot("F", "Figure3F_reliability.pdf", 2, 2, 2, 1),
        ),
    ),
    "Figure4": FigureLayout(
        columns=4,
        rows=2,
        slots=(
            Slot("A", "Figure4A_turing_test_workflow.pdf", 0, 0, 1, 1, True),
            Slot("B", "Figure4B_expert_source_identification_accuracy.pdf", 1, 0, 2, 1),
            Slot("C", "Figure4C_expert_source_confusion_matrix.pdf", 3, 0, 1, 1),
            Slot("D", "Figure4D_expert_guessed_MAS_model_forest.pdf", 0, 1, 1, 1),
            Slot("E", "Figure4E_student_source_identification_accuracy.pdf", 1, 1, 2, 1),
            Slot("F", "Figure4F_efficiency_sensitivity.pdf", 3, 1, 1, 1),
        ),
    ),
    "Figure5": FigureLayout(
        columns=4,
        rows=2,
        slots=(
            Slot("A", "Figure5A_total_workflow_time.pdf", 0, 0, 2, 1),
            Slot("B", "Figure5B_time_per_usable_item.pdf", 2, 0, 1, 1),
            Slot("C", "Figure5C_time_sensitivity.pdf", 3, 0, 1, 1),
            Slot("D", "Figure5D_api_cost.pdf", 0, 1, 2, 1),
            Slot("E", "Figure5E_total_cost_comparison.pdf", 3, 1, 1, 1),
        ),
    ),
    "Figure6": FigureLayout(
        columns=3,
        rows=2,
        slots=(
            Slot("A", "Figure6A_order_schema.pdf", 0, 0, 1, 1),
            Slot("B", "Figure6B_scores_by_block_position.pdf", 1, 0, 1, 1),
            Slot("C", "Figure6C_position_difference_by_sequence.pdf", 2, 0, 1, 1),
            Slot("D", "Figure6D_adjusted_fatigue_effect.pdf", 0, 1, 2, 1),
            Slot("E", "Figure6E_total_duration_by_sequence.pdf", 2, 1, 1, 1),
        ),
    ),
}


def latex_graphic(slot: Slot, layout: FigureLayout) -> str:
    x = slot.column * UNIT_INCHES
    y = (layout.rows - slot.row - slot.height_units) * UNIT_INCHES
    width = slot.width_units * UNIT_INCHES
    height = slot.height_units * UNIT_INCHES
    path = PANEL_DIR / slot.filename
    if path.exists():
        relative = path.relative_to(REPO_ROOT).as_posix()
        content = (
            rf"\includegraphics[width={width:.3f}in,height={height:.3f}in]"
            rf"{{\detokenize{{{relative}}}}}"
        )
    elif slot.manual:
        content = (
            rf"\color{{placeholderborder}}\framebox({width:.3f},{height:.3f}){{"
            rf"\color{{placeholdertext}}\shortstack{{"
            rf"\fontsize{{11}}{{13}}\selectfont\bfseries ({slot.panel})\\[0.12in]"
            rf"\fontsize{{8}}{{10}}\selectfont Figure workflow panel\\[0.08in]"
            rf"\fontsize{{6.5}}{{8}}\selectfont Reserved for GPT concept and PowerPoint tracing"
            rf"}}}}"
        )
    else:
        raise FileNotFoundError(f"Missing code-rendered panel: {path}")
    return rf"\put({x:.3f},{y:.3f}){{{content}}}"


def latex_document(name: str, layout: FigureLayout) -> str:
    page_width = layout.columns * UNIT_INCHES
    page_height = layout.rows * UNIT_INCHES
    graphics = "\n".join(latex_graphic(slot, layout) for slot in layout.slots)
    return rf"""\documentclass{{article}}
\usepackage[paperwidth={page_width:.3f}in,paperheight={page_height:.3f}in,margin=0in]{{geometry}}
\usepackage{{graphicx}}
\usepackage{{xcolor}}
\usepackage{{eso-pic}}
\definecolor{{placeholderborder}}{{HTML}}{{C8C2B8}}
\definecolor{{placeholdertext}}{{HTML}}{{4F4F4F}}
\setlength{{\unitlength}}{{1in}}
\setlength{{\fboxsep}}{{0pt}}
\setlength{{\fboxrule}}{{0.6pt}}
\pagestyle{{empty}}
\begin{{document}}
\thispagestyle{{empty}}
\AddToShipoutPictureFG*{{
  \AtPageLowerLeft{{
    \setlength{{\unitlength}}{{1in}}
    \begin{{picture}}(0,0)
{graphics}
    \end{{picture}}
  }}
}}
\null
\end{{document}}
"""


def compile_layout(name: str, layout: FigureLayout, pdflatex: str) -> Path:
    ASSEMBLED_DIR.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="uromas_figure_assembly_") as temp_name:
        temp_dir = Path(temp_name)
        tex_path = temp_dir / f"{name}.tex"
        tex_path.write_text(latex_document(name, layout), encoding="utf-8")
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
            raise RuntimeError(f"pdflatex failed for {name}:\n{tail}")
        output = ASSEMBLED_DIR / f"{name}.pdf"
        shutil.copy2(temp_dir / f"{name}.pdf", output)
        return output


def main() -> None:
    pdflatex = shutil.which("pdflatex")
    if pdflatex is None:
        raise RuntimeError("pdflatex is required to preserve vector panels during assembly.")
    outputs = [compile_layout(name, layout, pdflatex) for name, layout in LAYOUTS.items()]
    for output in outputs:
        print(f"Wrote {output.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
