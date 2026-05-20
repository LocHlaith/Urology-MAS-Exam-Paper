from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, List


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATA_DIR = PROJECT_ROOT / "data"
BANK_DIR = DATA_DIR / "banks"
RAW_DATASETS_DIR = DATA_DIR / "raw" / "datasets"

PROMPT_DIR = PROJECT_ROOT / "prompts"
GENERATION_PROMPT_DIR = PROMPT_DIR / "generation"
ANALYSIS_PROMPT_DIR = PROMPT_DIR / "analysis"
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


def old_bank_path(bank_type: str) -> Path:
    return BANK_DIR / f"bank_{BANK_FILE_STEMS[bank_type]}.json"


def new_bank_path(bank_type: str) -> Path:
    return BANK_DIR / f"new_bank_{BANK_FILE_STEMS[bank_type]}.json"


def old_bank_files() -> Dict[str, str]:
    return {bank_type: str(old_bank_path(bank_type)) for bank_type in BANK_TYPES}


def new_bank_files() -> Dict[str, str]:
    return {bank_type: str(new_bank_path(bank_type)) for bank_type in BANK_TYPES}


def generation_prompt_files() -> Dict[str, str]:
    return {
        bank_type: str(GENERATION_PROMPT_DIR / f"prompts_for_bank_to_new_bank_{BANK_FILE_STEMS[bank_type]}.txt")
        for bank_type in BANK_TYPES
    }


def analysis_prompt_files() -> Dict[str, str]:
    return {
        bank_type: str(ANALYSIS_PROMPT_DIR / f"prompts_for_new_bank_analysis_{BANK_FILE_STEMS[bank_type]}.txt")
        for bank_type in BANK_TYPES
    }


def ensure_output_dirs(extra_dirs: Iterable[Path] = ()) -> None:
    for path in [OUTPUT_DIR, LOG_DIR, FIGURE_DIR, REPORT_DRAFTS_DIR, REPORT_EXPORTS_DIR, *extra_dirs]:
        path.mkdir(parents=True, exist_ok=True)
