"""集中定义项目路径。

脚本用途：为仓库内脚本提供路径的单一事实来源。
流程阶段：公共配置。
主要输入：当前脚本所在位置。
主要输出：data、prompts、outputs 等目录常量，以及人类题库/MAS 题库路径函数。
重要边界：不要在业务脚本中硬编码仓库绝对路径；历史函数名仅作兼容层。
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Iterable, List, Optional


# ===== 路径常量 =====

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATA_DIR = PROJECT_ROOT / "data"
BANK_DIR = DATA_DIR / "banks"
RAW_DATA_DIR = DATA_DIR / "raw"
RAW_HUMAN_QUESTION_DIR = RAW_DATA_DIR / "human_question_documents"
INTERMEDIATE_DATA_DIR = DATA_DIR / "intermediate"
HUMAN_QUESTION_TEXT_DIR = INTERMEDIATE_DATA_DIR / "human_question_text"
STRUCTURED_QUESTION_BANK_DIR = INTERMEDIATE_DATA_DIR / "structured_question_bank"

PLOT_DIR = PROJECT_ROOT / "plot"
PLOT_DATA_DIR = PLOT_DIR / "data"
PLOT_RAW_DATA_DIR = PLOT_DATA_DIR / "raw"
PLOT_EXAM_WORKBOOK_DIR = PLOT_RAW_DATA_DIR / "exam_response_workbooks"
PLOT_EXPERT_WORKBOOK_DIR = PLOT_RAW_DATA_DIR / "expert_rating_workbooks"
PLOT_DERIVED_DATA_DIR = PLOT_DATA_DIR / "derived"

PROMPT_DIR = PROJECT_ROOT / "prompts"
GENERATION_PROMPT_DIR = PROMPT_DIR / "generation"
EVALUATION_PROMPT_DIR = PROMPT_DIR / "evaluation"

OUTPUT_DIR = PROJECT_ROOT / "outputs"
LOG_DIR = OUTPUT_DIR / "logs"
FIGURE_DIR = OUTPUT_DIR / "figures"
PANEL_FIGURE_DIR = FIGURE_DIR / "panels"
FIGURE_SOURCE_DATA_DIR = OUTPUT_DIR / "figure_source_data"
REPORT_DRAFTS_DIR = OUTPUT_DIR / "report_drafts"
REPORT_EXPORTS_DIR = OUTPUT_DIR / "report_exports"

ENV_PATH = PROJECT_ROOT / ".env"

BANK_TYPES: List[str] = ["A1", "A2", "A3", "A4", "B", "X"]
BANK_FILE_STEMS: Dict[str, str] = {
    "A1": "a1",
    "A2": "a2",
    "A3": "a3",
    "A4": "a4",
    "B": "b",
    "X": "x",
}


# ===== 题库路径 =====

def human_bank_path(bank_type: str) -> Path:
    return BANK_DIR / f"bank_{BANK_FILE_STEMS[bank_type]}.json"


def mas_bank_path(bank_type: str) -> Path:
    return BANK_DIR / f"new_bank_{BANK_FILE_STEMS[bank_type]}.json"


def human_bank_files() -> Dict[str, str]:
    return {bank_type: str(human_bank_path(bank_type)) for bank_type in BANK_TYPES}


def mas_bank_files() -> Dict[str, str]:
    return {bank_type: str(mas_bank_path(bank_type)) for bank_type in BANK_TYPES}


def mas_bank_files_in_dir(bank_dir: Path) -> Dict[str, str]:
    bank_dir = Path(bank_dir)
    return {
        bank_type: str(bank_dir / f"new_bank_{BANK_FILE_STEMS[bank_type]}.json")
        for bank_type in BANK_TYPES
    }


# ===== 兼容路径函数 =====

def old_bank_path(bank_type: str) -> Path:
    """兼容历史函数命名；语义等同于 `human_bank_path`。"""
    return human_bank_path(bank_type)


def new_bank_path(bank_type: str) -> Path:
    """兼容历史函数命名；语义等同于 `mas_bank_path`。"""
    return mas_bank_path(bank_type)


def old_bank_files() -> Dict[str, str]:
    """兼容历史函数命名；语义等同于 `human_bank_files`。"""
    return human_bank_files()


def new_bank_files() -> Dict[str, str]:
    """兼容历史函数命名；语义等同于 `mas_bank_files`。"""
    return mas_bank_files()


# ===== 提示词路径 =====

def generation_prompt_files() -> Dict[str, str]:
    return {
        bank_type: str(GENERATION_PROMPT_DIR / f"prompts_for_bank_to_new_bank_{BANK_FILE_STEMS[bank_type]}.txt")
        for bank_type in BANK_TYPES
    }


def answer_explanation_prompt_files() -> Dict[str, str]:
    return {
        bank_type: str(GENERATION_PROMPT_DIR / f"prompts_for_new_bank_answer_explanation_{BANK_FILE_STEMS[bank_type]}.txt")
        for bank_type in BANK_TYPES
    }


# ===== 输出目录 =====

def ensure_output_dirs(extra_dirs: Iterable[Path] = ()) -> None:
    for path in [OUTPUT_DIR, LOG_DIR, FIGURE_DIR, PANEL_FIGURE_DIR, FIGURE_SOURCE_DATA_DIR, REPORT_DRAFTS_DIR, REPORT_EXPORTS_DIR, *extra_dirs]:
        path.mkdir(parents=True, exist_ok=True)


def runtime_log_dir(env_var: str = "UROLOGY_MAS_LOG_DIR") -> Path:
    """返回可写日志目录；统计脚本可用环境变量把日志导向临时目录。"""
    candidates: List[Path] = []
    if os.getenv(env_var):
        candidates.append(Path(os.environ[env_var]))
    candidates.extend([LOG_DIR, PROJECT_ROOT / "logs"])

    last_error: Optional[OSError] = None
    for path in candidates:
        try:
            path.mkdir(parents=True, exist_ok=True)
            return path
        except OSError as e:
            last_error = e
            continue

    if last_error is not None:
        raise last_error
    raise RuntimeError("未能解析日志目录")
