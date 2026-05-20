"""集中定义项目路径。

脚本用途：为仓库内脚本提供路径的单一事实来源。
流程阶段：公共配置。
主要输入：当前脚本所在位置。
主要输出：data、prompts、outputs 等目录常量，以及人类题库/MAS 题库路径函数。
重要边界：不要在业务脚本中硬编码仓库绝对路径；历史函数名仅作兼容层。
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, List


# ===== 路径常量 =====

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATA_DIR = PROJECT_ROOT / "data"
BANK_DIR = DATA_DIR / "banks"
RAW_DATASETS_DIR = DATA_DIR / "raw" / "datasets"

PROMPT_DIR = PROJECT_ROOT / "prompts"
GENERATION_PROMPT_DIR = PROMPT_DIR / "generation"
EVALUATION_PROMPT_DIR = PROMPT_DIR / "evaluation"

OUTPUT_DIR = PROJECT_ROOT / "outputs"
LOG_DIR = OUTPUT_DIR / "logs"
FIGURE_DIR = OUTPUT_DIR / "figures"
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
    for path in [OUTPUT_DIR, LOG_DIR, FIGURE_DIR, REPORT_DRAFTS_DIR, REPORT_EXPORTS_DIR, *extra_dirs]:
        path.mkdir(parents=True, exist_ok=True)
