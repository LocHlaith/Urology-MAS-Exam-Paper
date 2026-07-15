"""构建论文绘图分析数据集。

脚本用途：把试卷解析标注、考生作答、来源辨识和题库规模整理为统一 CSV。
流程阶段：论文绘图前的数据处理。
主要输入：outputs/report_drafts、plot/data/derived/source_workbooks、data/banks。
主要输出：plot/data/derived 下的 item_master、responses、block_scores、machine_ratings 等表。
重要边界：机器评分只是现有解析标注中的可用评价数据；最终盲法专家表上传后应作为独立 phase 合并。
"""

from __future__ import annotations

import csv
import json
import math
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from project_paths import BANK_DIR, PLOT_DERIVED_DATA_DIR, REPORT_DRAFTS_DIR  # noqa: E402


# ===== 输出位置 =====

PLOT_DATA_DIR = PLOT_DERIVED_DATA_DIR


# ===== 固定口径 =====

SOURCE_BY_PAPER = {
    "M": "MAS",
    "P": "Human",
}

ITEM_ID_PREFIX = {
    "M": "M",
    "P": "H",
}

SCORE_FILES = {
    "M": {
        "A1": "exam_responses_workbook_2__06__M卷分析A1汇总.csv",
        "A2": "exam_responses_workbook_2__07__M卷分析A2汇总.csv",
        "A3/A4": "exam_responses_workbook_2__08__M卷分析A3-4汇总.csv",
        "B": "exam_responses_workbook_2__09__M卷分析B汇总.csv",
        "X": "exam_responses_workbook_2__10__M卷分析X汇总.csv",
    },
    "P": {
        "A1": "exam_responses_workbook_2__16__P卷分析_A1汇总.csv",
        "A2": "exam_responses_workbook_2__17__P卷分析_A2汇总.csv",
        "A3/A4": "exam_responses_workbook_2__18__P卷分析_A3-4汇总.csv",
        "B": "exam_responses_workbook_2__19__P卷分析_B汇总.csv",
        "X": "exam_responses_workbook_2__20__P卷分析_X汇总.csv",
    },
}

BLUEPRINT_COGNITIVE_BY_ITEM_TYPE = {
    "A1": "recall",
    "B": "comprehension",
    "A2": "application",
    "A3": "analysis",
    "A4": "analysis",
    "A3/A4": "analysis",
    "X": "analysis",
}

COGNITIVE_LEVEL_MAP = {
    "recall": "knowledge",
    "comprehension": "knowledge",
    "application": "application",
    "analysis": "reasoning",
}

COGNITIVE_ORDER = {"knowledge": 0, "application": 1, "reasoning": 2}

TOPIC_RULES = [
    ("Tumors", ["肿瘤", "癌", "PSA", "尿路上皮", "膀胱占位", "睾丸肿物"]),
    ("Stones", ["结石", "尿石", "碎石"]),
    ("Obstruction", ["梗阻", "前列腺增生", "尿潴留", "排尿困难", "肾积水"]),
    ("Infection", ["感染", "前列腺炎", "肾盂肾炎", "附睾炎", "膀胱炎", "尿路刺激"]),
    ("Trauma", ["损伤", "外伤", "断裂", "挫伤", "创伤"]),
    ("Andrology/Pelvic floor", ["男科学", "盆底", "不育", "性功能", "精索", "隐睾", "鞘膜", "阴囊"]),
    ("Tuberculosis", ["结核"]),
    ("Other", ["肾功能", "肾上腺", "解剖", "尿液检查", "影像学", "诊断", "血尿"]),
]

MACHINE_PROXY_DOMAIN_COMPONENTS = {
    "presentation_clarity": {
        "label": "Presentation clarity",
        "components": [
            ("qgeval", "流畅性", 5),
            ("qgeval", "清晰度", 5),
            ("qgeval", "简洁性", 5),
            ("llm", "流畅性", 5),
            ("llm", "排他性", 5),
            ("llm", "明确性", 4),
        ],
    },
    "blueprint_relevance": {
        "label": "Blueprint relevance",
        "components": [
            ("qgeval", "相关性", 5),
            ("llm", "目标性", 5),
            ("llm", "侧重性", 5),
            ("llm", "公平性", 3),
        ],
    },
    "answer_validity": {
        "label": "Answer validity",
        "components": [
            ("qgeval", "一致性", 5),
            ("qgeval", "可回答性", 5),
            ("qgeval", "答案一致性", 5),
            ("llm", "正确性", 5),
            ("llm", "可解性", 5),
            ("llm", "绝对性", 5),
        ],
    },
    "item_design": {
        "label": "Item-writing design",
        "components": [
            ("llm", "防猜性", 5),
            ("llm", "迷惑性", 5),
            ("llm", "完整性", 5),
        ],
    },
    "cognitive_feedback": {
        "label": "Cognitive and feedback value",
        "components": [
            ("llm", "综合性", 5),
            ("llm", "思维性", 4),
            ("llm", "反馈性", 5),
            ("llm", "答案解析专门评分", 5),
        ],
    },
}

MACHINE_PROXY_DOMAIN_FIELDS = [f"machine_proxy_{key}" for key in MACHINE_PROXY_DOMAIN_COMPONENTS]

MACHINE_SAFETY_SCREEN_COMPONENTS = {
    "guideline_consistency": {
        "label": "Guideline consistency",
        "components": [
            ("qgeval", "相关性", 5, 0.25),
            ("qgeval", "一致性", 5, 0.15),
            ("llm", "目标性", 5, 0.25),
            ("llm", "侧重性", 5, 0.15),
            ("llm", "正确性", 5, 0.20),
        ],
    },
    "single_best_answer": {
        "label": "Single best answer",
        "components": [
            ("qgeval", "可回答性", 5, 0.25),
            ("qgeval", "答案一致性", 5, 0.25),
            ("llm", "可解性", 5, 0.20),
            ("llm", "绝对性", 5, 0.20),
            ("llm", "排他性", 5, 0.10),
        ],
    },
    "answer_key_validation": {
        "label": "Answer-key validation",
        "components": [
            ("qgeval", "答案一致性", 5, 0.25),
            ("llm", "正确性", 5, 0.25),
            ("llm", "可解性", 5, 0.25),
            ("llm", "绝对性", 5, 0.15),
            ("llm", "答案解析专门评分", 5, 0.10),
        ],
    },
    "distractor_effectiveness": {
        "label": "Distractor effectiveness",
        "components": [
            ("llm", "迷惑性", 5, 0.35),
            ("llm", "防猜性", 5, 0.25),
            ("llm", "完整性", 5, 0.15),
            ("llm", "排他性", 5, 0.15),
            ("qgeval", "答案一致性", 5, 0.10),
        ],
    },
    "stem_ambiguity_control": {
        "label": "Stem ambiguity controlled",
        "components": [
            ("qgeval", "清晰度", 5, 0.30),
            ("qgeval", "流畅性", 5, 0.15),
            ("qgeval", "一致性", 5, 0.10),
            ("llm", "排他性", 5, 0.25),
            ("llm", "明确性", 4, 0.20),
        ],
    },
}

MACHINE_SAFETY_SCREEN_FIELDS = [f"{key}_score_5" for key in MACHINE_SAFETY_SCREEN_COMPONENTS]
SAFETY_PASS_THRESHOLD = 4.0
SAFETY_CRITICAL_THRESHOLD = 3.0

SAFETY_CRITICAL_COMPONENTS = [
    ("qgeval", "清晰度", 5, "stem_unclear"),
    ("qgeval", "一致性", 5, "internal_inconsistency"),
    ("qgeval", "可回答性", 5, "not_answerable"),
    ("qgeval", "答案一致性", 5, "answer_inconsistent"),
    ("llm", "排他性", 5, "nonexclusive_or_ambiguous"),
    ("llm", "目标性", 5, "off_blueprint"),
    ("llm", "侧重性", 5, "outdated_or_peripheral"),
    ("llm", "正确性", 5, "factual_error"),
    ("llm", "可解性", 5, "answer_key_error"),
    ("llm", "绝对性", 5, "multiple_plausible_answers"),
]


# ===== 通用工具 =====

def clean_cell(value: Any) -> str:
    return str(value).replace("\ufeff", "").strip()


def read_csv_rows(path: Path) -> List[List[str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return [[clean_cell(cell) for cell in row] for row in csv.reader(f)]


def write_csv(path: Path, rows: Sequence[Dict[str, Any]], fieldnames: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: "" if row.get(k) is None else row.get(k) for k in fieldnames})


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def maybe_float(value: Any) -> Optional[float]:
    value = clean_cell(value)
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def maybe_int(value: Any) -> Optional[int]:
    value = clean_cell(value)
    if not value:
        return None
    try:
        return int(float(value))
    except ValueError:
        return None


def normalize_rubric_score(value: Any, max_score: float, min_score: float = 1.0) -> Optional[float]:
    """Map heterogeneous rubric ranges to a common 1-5 scale."""
    score = maybe_float(value)
    if score is None or max_score <= min_score:
        return None
    score = max(min_score, min(max_score, score))
    return 1.0 + 4.0 * (score - min_score) / (max_score - min_score)


def machine_proxy_scores(row: Dict[str, Any]) -> Dict[str, Optional[float]]:
    """Derive the manuscript-facing machine proxy domains from QGEval and LLM sub-scores."""
    output: Dict[str, Optional[float]] = {}
    domain_values: List[float] = []
    for domain, spec in MACHINE_PROXY_DOMAIN_COMPONENTS.items():
        values: List[float] = []
        for prefix, name, max_score in spec["components"]:
            value = normalize_rubric_score(row.get(f"{prefix}_{name}"), max_score)
            if value is not None:
                values.append(value)
        domain_key = f"machine_proxy_{domain}"
        output[domain_key] = statistics.fmean(values) if values else None
        if output[domain_key] is not None:
            domain_values.append(output[domain_key])
    output["machine_proxy_quality_score"] = statistics.fmean(domain_values) if domain_values else None
    return output


def weighted_normalized_score(row: Dict[str, Any], components: Sequence[Tuple[str, str, float, float]]) -> Optional[float]:
    weighted_sum = 0.0
    weight_sum = 0.0
    for prefix, name, max_score, weight in components:
        value = normalize_rubric_score(row.get(f"{prefix}_{name}"), max_score)
        if value is None:
            continue
        weighted_sum += value * weight
        weight_sum += weight
    return weighted_sum / weight_sum if weight_sum else None


def answer_key_format_ok(answer_key: Any, item_type: Any) -> int:
    value = clean_cell(answer_key).upper()
    letters = re.findall(r"[A-E]", value)
    if not letters:
        return 0
    compact = "".join(letters)
    if len(set(compact)) != len(compact):
        return 0
    if clean_cell(item_type).upper() != "X" and len(compact) != 1:
        return 0
    return 1


def safety_component_failure_reasons(row: Dict[str, Any]) -> List[str]:
    reasons = []
    for prefix, name, max_score, reason in SAFETY_CRITICAL_COMPONENTS:
        value = normalize_rubric_score(row.get(f"{prefix}_{name}"), max_score)
        if value is not None and value <= 2.0:
            reasons.append(reason)
    return reasons


def machine_safety_screen_scores(row: Dict[str, Any], item_row: Dict[str, Any]) -> Dict[str, Any]:
    output: Dict[str, Any] = {}
    for domain, spec in MACHINE_SAFETY_SCREEN_COMPONENTS.items():
        output[f"{domain}_score_5"] = weighted_normalized_score(row, spec["components"])

    format_ok = answer_key_format_ok(item_row.get("answer_key", ""), item_row.get("item_type", ""))
    output["answer_key_format_ok"] = format_ok
    if not format_ok and output.get("answer_key_validation_score_5") is not None:
        output["answer_key_validation_score_5"] = min(float(output["answer_key_validation_score_5"]), 1.0)

    for domain in MACHINE_SAFETY_SCREEN_COMPONENTS:
        score = output.get(f"{domain}_score_5")
        output[f"{domain}_pass"] = 1 if score is not None and score >= SAFETY_PASS_THRESHOLD else 0

    score_values = [float(output[field]) for field in MACHINE_SAFETY_SCREEN_FIELDS if output.get(field) is not None]
    domain_failures = [
        domain
        for domain in MACHINE_SAFETY_SCREEN_COMPONENTS
        if output.get(f"{domain}_score_5") is not None and float(output[f"{domain}_score_5"]) < SAFETY_CRITICAL_THRESHOLD
    ]
    component_reasons = safety_component_failure_reasons(row)
    if not format_ok:
        component_reasons.append("invalid_answer_key_format")

    output["safety_screen_mean_score_5"] = statistics.fmean(score_values) if score_values else None
    output["safety_screen_min_score_5"] = min(score_values) if score_values else None
    output["major_defect_flag"] = 1 if any(output.get(f"{domain}_pass") == 0 for domain in MACHINE_SAFETY_SCREEN_COMPONENTS) else 0
    output["critical_defect_flag"] = 1 if domain_failures or component_reasons else 0
    output["critical_defect_reasons"] = ";".join(sorted(set(domain_failures + component_reasons)))
    output["all_safety_domains_pass"] = 1 if output["major_defect_flag"] == 0 and output["critical_defect_flag"] == 0 else 0
    return output


def item_id(paper: str, item_no: int) -> str:
    return f"{ITEM_ID_PREFIX[paper]}{item_no:03d}"


def source_true(paper: str) -> str:
    return SOURCE_BY_PAPER[paper]


def infer_training_setting(code: str) -> str:
    code = clean_cell(code).upper()
    if code == "A":
        return "main"
    if code == "B":
        return "non_main"
    return "unknown"


def block_position(form: str, paper: str) -> Optional[int]:
    form = clean_cell(form).upper()
    if form == "A":
        return 1 if paper == "P" else 2
    if form == "B":
        return 1 if paper == "M" else 2
    return None


def pearson(x: Sequence[float], y: Sequence[float]) -> Optional[float]:
    if len(x) < 3 or len(x) != len(y):
        return None
    mx = statistics.fmean(x)
    my = statistics.fmean(y)
    sx = math.sqrt(sum((v - mx) ** 2 for v in x))
    sy = math.sqrt(sum((v - my) ** 2 for v in y))
    if sx == 0 or sy == 0:
        return None
    return sum((a - mx) * (b - my) for a, b in zip(x, y)) / (sx * sy)


# ===== 考生作答 =====

def find_standard_answer_row(rows: Sequence[Sequence[str]]) -> Tuple[int, int]:
    for row_idx, row in enumerate(rows):
        for col_idx, cell in enumerate(row):
            if clean_cell(cell) == "标准答案":
                return row_idx, col_idx
    raise ValueError("未找到标准答案行")


def locate_meta_columns(rows: Sequence[Sequence[str]], std_row_idx: int, std_col_idx: int) -> Dict[str, int]:
    header_row = rows[std_row_idx - 1] if std_row_idx > 0 else []
    std_row = rows[std_row_idx]
    meta: Dict[str, int] = {}
    for label in ["AB卷", "年级", "院区", "姓名"]:
        for row in [header_row, std_row]:
            for col_idx, cell in enumerate(row[: std_col_idx + 1]):
                if clean_cell(cell) == label:
                    meta[label] = col_idx
                    break
            if label in meta:
                break
    meta.setdefault("姓名", std_col_idx)
    return meta


def parse_score_file(path: Path, paper: str, item_type_group: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    rows = read_csv_rows(path)
    std_row_idx, std_col_idx = find_standard_answer_row(rows)
    header_row = rows[std_row_idx - 1]
    std_row = rows[std_row_idx]
    meta_cols = locate_meta_columns(rows, std_row_idx, std_col_idx)

    question_cols: List[Tuple[int, int]] = []
    for col_idx in range(std_col_idx + 1, len(header_row)):
        q_no = maybe_int(header_row[col_idx])
        if q_no is not None and col_idx < len(std_row) and clean_cell(std_row[col_idx]):
            question_cols.append((q_no, col_idx))

    answer_rows = []
    for q_no, col_idx in question_cols:
        answer_rows.append(
            {
                "item_id": item_id(paper, q_no),
                "paper": paper,
                "paper_item_no": q_no,
                "source_true": source_true(paper),
                "item_type": item_type_group,
                "answer_key": clean_cell(std_row[col_idx]),
            }
        )

    response_rows: List[Dict[str, Any]] = []
    name_col = meta_cols["姓名"]
    form_col = meta_cols.get("AB卷")
    year_col = meta_cols.get("年级")
    setting_col = meta_cols.get("院区")

    for row in rows[std_row_idx + 1 :]:
        if len(row) <= name_col:
            continue
        student_no = maybe_int(row[name_col])
        if student_no is None:
            continue
        form = clean_cell(row[form_col]) if form_col is not None and form_col < len(row) else ""
        if form not in {"A", "B"}:
            continue
        training_year = clean_cell(row[year_col]) if year_col is not None and year_col < len(row) else ""
        setting_code = clean_cell(row[setting_col]) if setting_col is not None and setting_col < len(row) else ""
        for q_no, col_idx in question_cols:
            score = maybe_float(row[col_idx]) if col_idx < len(row) else None
            response_missing = 1 if score is None else 0
            if score is None:
                score = 0.0
            response_rows.append(
                {
                    "student_id": f"S{student_no:03d}",
                    "student_no": student_no,
                    "item_id": item_id(paper, q_no),
                    "paper": paper,
                    "paper_item_no": q_no,
                    "source_true": source_true(paper),
                    "item_type": item_type_group,
                    "score": score,
                    "correct": 1 if score > 0 else 0,
                    "response_missing": response_missing,
                    "form": form,
                    "order_group": form,
                    "block_position": block_position(form, paper),
                    "training_year": training_year,
                    "training_setting_code": setting_code,
                    "training_setting": infer_training_setting(setting_code),
                }
            )
    return response_rows, answer_rows


def parse_exam_time_file(path: Path) -> Dict[str, Dict[str, Any]]:
    rows = read_csv_rows(path)
    time_by_student: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        if len(row) < 8:
            continue
        form = clean_cell(row[0])
        student_no = maybe_int(row[3])
        if form not in {"A", "B"} or student_no is None:
            continue
        time_by_student[f"S{student_no:03d}"] = {
            "form": form,
            "training_year": clean_cell(row[1]),
            "training_setting_code": clean_cell(row[2]),
            "training_setting": infer_training_setting(row[2]),
            "student_no": student_no,
            "m_score_reported": maybe_float(row[4]),
            "p_score_reported": maybe_float(row[5]),
            "m_minus_p_reported": maybe_float(row[6]),
            "total_time_seconds": maybe_float(row[7]),
        }
    return time_by_student


def build_response_tables() -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    data_dir = PLOT_DATA_DIR / "source_workbooks"
    all_responses: List[Dict[str, Any]] = []
    answer_rows: Dict[str, Dict[str, Any]] = {}

    for paper, files in SCORE_FILES.items():
        for item_type_group, filename in files.items():
            responses, answers = parse_score_file(data_dir / filename, paper, item_type_group)
            all_responses.extend(responses)
            for answer in answers:
                answer_rows[answer["item_id"]] = answer

    time_by_student = parse_exam_time_file(
        data_dir / "exam_responses_workbook_2__22__疲劳性探索与总时长.csv"
    )

    assignment_by_student: Dict[str, Dict[str, Any]] = {}
    for row in all_responses:
        sid = row["student_id"]
        base = assignment_by_student.setdefault(
            sid,
            {
                "student_id": sid,
                "student_no": row["student_no"],
                "form": row["form"],
                "order_group": row["order_group"],
                "training_year": row["training_year"],
                "training_setting_code": row["training_setting_code"],
                "training_setting": row["training_setting"],
            },
        )
        if sid in time_by_student:
            base.update(time_by_student[sid])

    for row in all_responses:
        sid = row["student_id"]
        if sid in time_by_student:
            row["total_time_seconds"] = time_by_student[sid].get("total_time_seconds")

    block_scores: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for row in all_responses:
        key = (row["student_id"], row["source_true"])
        block = block_scores.setdefault(
            key,
            {
                "student_id": row["student_id"],
                "source_true": row["source_true"],
                "paper": row["paper"],
                "form": row["form"],
                "order_group": row["order_group"],
                "block_position": row["block_position"],
                "training_year": row["training_year"],
                "training_setting": row["training_setting"],
                "n_items": 0,
                "raw_score": 0.0,
                "n_correct": 0,
            },
        )
        block["n_items"] += 1
        block["raw_score"] += float(row["score"])
        block["n_correct"] += int(row["correct"])

    for block in block_scores.values():
        block["score_percent"] = block["raw_score"] / (2 * block["n_items"]) * 100 if block["n_items"] else None
        block["correct_rate"] = block["n_correct"] / block["n_items"] if block["n_items"] else None

    paired_rows = []
    for sid in sorted(assignment_by_student):
        human = block_scores.get((sid, "Human"))
        mas = block_scores.get((sid, "MAS"))
        if not human or not mas:
            continue
        assignment = assignment_by_student[sid]
        paired_rows.append(
            {
                "student_id": sid,
                "student_no": assignment["student_no"],
                "form": assignment["form"],
                "order_group": assignment["order_group"],
                "training_year": assignment["training_year"],
                "training_setting": assignment["training_setting"],
                "human_score": human["raw_score"],
                "mas_score": mas["raw_score"],
                "mas_minus_human_score": mas["raw_score"] - human["raw_score"],
                "human_correct_rate": human["correct_rate"],
                "mas_correct_rate": mas["correct_rate"],
                "mas_minus_human_correct_rate": mas["correct_rate"] - human["correct_rate"],
                "total_time_seconds": assignment.get("total_time_seconds"),
            }
        )

    item_type_map = list(answer_rows.values())
    return all_responses, list(assignment_by_student.values()), list(block_scores.values()), paired_rows, item_type_map


# ===== 解析试卷标注版 =====

HEADER_RE = re.compile(r"^(?:(?P<seq>\d+)\.)?-{5,}(?P<item_type>A1|A2|A3|A4|B|X)型题第(?P<source_item_id>\d+)题-{5,}\s*$", re.M)


def parse_score_dimensions(line: str) -> Tuple[Optional[float], Dict[str, float]]:
    total_match = re.search(r"总分\s*([-+]?\d+(?:\.\d+)?)\s*分", line)
    total = float(total_match.group(1)) if total_match else None
    dims: Dict[str, float] = {}
    after_total = line[total_match.end() :] if total_match else line
    for name, value in re.findall(r"([^，、。:：]+?)\s*([-+]?\d+(?:\.\d+)?)\s*分", after_total):
        name = clean_cell(name).strip("，、。:：")
        if name:
            dims[name] = float(value)
    return total, dims


def extract_between(text: str, start_pattern: str, end_pattern: str) -> str:
    start = re.search(start_pattern, text)
    end = re.search(end_pattern, text)
    if not start or not end or end.start() <= start.end():
        return ""
    return text[start.end() : end.start()].strip()


def content_after_llm(block: str) -> str:
    match = re.search(r"LLM：[^\n]*\n", block)
    if match:
        return block[match.end() :].strip()
    match = re.search(r"QGEval：[^\n]*\n", block)
    if match:
        return block[match.end() :].strip()
    return block.strip()


def split_question_subblocks(block: str) -> List[str]:
    content = content_after_llm(block)
    markers = list(re.finditer(r"(?m)^\((\d+)\)\s*", content))
    if not markers:
        return [content]
    subblocks = []
    for idx, marker in enumerate(markers):
        start = marker.start()
        end = markers[idx + 1].start() if idx + 1 < len(markers) else len(content)
        subblocks.append(content[start:end].strip())
    return subblocks


def extract_item_text_fields(subblock: str) -> Tuple[str, str, str]:
    test_point = ""
    test_point_match = re.search(r"考点还原：\s*(.+)", subblock)
    if test_point_match:
        test_point = clean_cell(test_point_match.group(1)).rstrip("。")

    reference_answer = ""
    answer_match = re.search(r"参考答案：\s*([^。\n]+)", subblock)
    if answer_match:
        reference_answer = clean_cell(answer_match.group(1))

    end_match = re.search(r"考点还原：", subblock)
    question_text = subblock[: end_match.start()].strip() if end_match else subblock.strip()
    return question_text, test_point, reference_answer


def parse_report_draft(path: Path, paper: str, run_id: int, answer_map: Dict[str, Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    text = path.read_text(encoding="utf-8")
    matches = list(HEADER_RE.finditer(text))
    rating_rows: List[Dict[str, Any]] = []
    item_rows: List[Dict[str, Any]] = []
    next_item_no = 1

    for match_idx, match in enumerate(matches):
        block_start = match.end()
        block_end = matches[match_idx + 1].start() if match_idx + 1 < len(matches) else len(text)
        block = text[block_start:block_end]
        header_type = match.group("item_type")
        subblocks = split_question_subblocks(block)
        seq_no = maybe_int(match.group("seq"))
        if seq_no is not None:
            item_numbers = [seq_no]
            next_item_no = max(next_item_no, seq_no + 1)
        else:
            item_count = max(1, len(subblocks))
            if match_idx + 1 < len(matches):
                next_seq = maybe_int(matches[match_idx + 1].group("seq"))
                if next_seq is not None and next_seq > next_item_no:
                    item_count = next_seq - next_item_no
            item_numbers = list(range(next_item_no, next_item_no + item_count))
            next_item_no += item_count

        qgeval_line = re.search(r"QGEval：([^\n]+)", block)
        llm_line = re.search(r"LLM：([^\n]+)", block)
        qgeval_total, qgeval_dims = parse_score_dimensions(qgeval_line.group(1)) if qgeval_line else (None, {})
        llm_total, llm_dims = parse_score_dimensions(llm_line.group(1)) if llm_line else (None, {})

        flesch = None
        flesch_match = re.search(r"Flesch Reading Ease：\s*([-+]?\d+(?:\.\d+)?)", block)
        if flesch_match:
            flesch = float(flesch_match.group(1))

        similarity = {
            "fuzzywuzzy_ratio_max": None,
            "sentencebert_cosine_max": None,
            "ngram_jaccard_max": None,
        }
        fuzzy_match = re.search(r"FuzzyWuzzy Levenshtein：.*?值为\s*([-+]?\d+(?:\.\d+)?)", block)
        sentence_match = re.search(r"Sentence-BERT Cosine：.*?值为\s*([-+]?\d+(?:\.\d+)?)", block)
        ngram_match = re.search(r"3-gram Jaccard Index：.*?值为\s*([-+]?\d+(?:\.\d+)?)", block)
        if fuzzy_match:
            similarity["fuzzywuzzy_ratio_max"] = float(fuzzy_match.group(1))
        if sentence_match:
            similarity["sentencebert_cosine_max"] = float(sentence_match.group(1))
        if ngram_match:
            similarity["ngram_jaccard_max"] = float(ngram_match.group(1))

        if len(subblocks) < len(item_numbers):
            subblocks = subblocks + [subblocks[-1]] * (len(item_numbers) - len(subblocks))

        for sub_idx, item_no in enumerate(item_numbers):
            iid = item_id(paper, item_no)
            subblock = subblocks[sub_idx] if sub_idx < len(subblocks) else block
            question_text, test_point, reference_answer = extract_item_text_fields(subblock)

            rating_row: Dict[str, Any] = {
                "rater_id": f"machine_run_{run_id}",
                "item_id": iid,
                "paper": paper,
                "paper_item_no": item_no,
                "source_true": source_true(paper),
                "rater_phase": "machine_annotation",
                "qgeval_total": qgeval_total,
                "qgeval_score_5": qgeval_total / 7 if qgeval_total is not None else None,
                "llm_total": llm_total,
                "llm_score_5": llm_total / 16 if llm_total is not None else None,
            }
            for name, value in qgeval_dims.items():
                rating_row[f"qgeval_{name}"] = value
            for name, value in llm_dims.items():
                rating_row[f"llm_{name}"] = value
            rating_row.update(machine_proxy_scores(rating_row))
            rating_rows.append(rating_row)

            if run_id == 1:
                response_answer = answer_map.get(iid, {}).get("answer_key", "")
                item_type_group = answer_map.get(iid, {}).get("item_type") or ("A3/A4" if header_type in {"A3", "A4"} else header_type)
                raw_cognitive = BLUEPRINT_COGNITIVE_BY_ITEM_TYPE.get(item_type_group, BLUEPRINT_COGNITIVE_BY_ITEM_TYPE.get(header_type, "unknown"))
                item_rows.append(
                    {
                        "item_id": iid,
                        "paper": paper,
                        "paper_item_no": item_no,
                        "source_true": source_true(paper),
                        "item_type": item_type_group,
                        "header_item_type": header_type,
                        "source_item_id": match.group("source_item_id"),
                        "answer_key": response_answer or reference_answer,
                        "answer_key_from_report": reference_answer,
                        "test_point": test_point,
                        "topic": infer_topic(test_point + " " + question_text),
                        "blueprint_cognitive_level": raw_cognitive,
                        "cognitive_level": COGNITIVE_LEVEL_MAP.get(raw_cognitive, "unknown"),
                        "has_vignette": 1 if re.search(r"(患者|男性|女性|男，|女，|患儿|查体|入院|就诊)", question_text) else 0,
                        "question_text": question_text,
                        "char_count": len(re.sub(r"\s+", "", question_text)),
                        "flesch_reading_ease": flesch,
                        **similarity,
                    }
                )
    return rating_rows, item_rows


def infer_topic(text: str) -> str:
    for topic, keywords in TOPIC_RULES:
        if any(keyword in text for keyword in keywords):
            return topic
    return "Other"


def build_report_tables(answer_rows: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    answer_map = {row["item_id"]: row for row in answer_rows}
    all_ratings: List[Dict[str, Any]] = []
    item_master: Dict[str, Dict[str, Any]] = {}

    for paper, paper_name in [("M", "M卷"), ("P", "P卷")]:
        for run_id in range(1, 5):
            path = REPORT_DRAFTS_DIR / f"{paper_name}解析标注版-第{run_id}次.txt"
            ratings, items = parse_report_draft(path, paper, run_id, answer_map)
            all_ratings.extend(ratings)
            for row in items:
                item_master[row["item_id"]] = row

    return list(item_master.values()), all_ratings


# ===== 派生统计 =====

def aggregate_machine_ratings(machine_ratings: Sequence[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in machine_ratings:
        grouped[row["item_id"]].append(row)

    summary_rows: List[Dict[str, Any]] = []
    defect_rows: List[Dict[str, Any]] = []
    raw_dimension_names = sorted(
        {
            key
            for row in machine_ratings
            for key in row
            if (
                (key.startswith("llm_") and key not in {"llm_total", "llm_score_5"})
                or (key.startswith("qgeval_") and key not in {"qgeval_total", "qgeval_score_5"})
            )
        }
    )

    for iid, rows in grouped.items():
        source = rows[0]["source_true"]
        llm_values = [float(r["llm_score_5"]) for r in rows if r.get("llm_score_5") not in {"", None}]
        qgeval_values = [float(r["qgeval_score_5"]) for r in rows if r.get("qgeval_score_5") not in {"", None}]
        proxy_values = [float(r["machine_proxy_quality_score"]) for r in rows if r.get("machine_proxy_quality_score") not in {"", None}]
        row: Dict[str, Any] = {
            "item_id": iid,
            "source_true": source,
            "n_machine_runs": len(rows),
            "llm_score_5_mean": statistics.fmean(llm_values) if llm_values else None,
            "llm_score_5_sd": statistics.stdev(llm_values) if len(llm_values) > 1 else 0,
            "qgeval_score_5_mean": statistics.fmean(qgeval_values) if qgeval_values else None,
            "qgeval_score_5_sd": statistics.stdev(qgeval_values) if len(qgeval_values) > 1 else 0,
            "machine_proxy_quality_score_mean": statistics.fmean(proxy_values) if proxy_values else None,
            "machine_proxy_quality_score_sd": statistics.stdev(proxy_values) if len(proxy_values) > 1 else 0,
        }
        major_flags = []
        critical_flags = []
        for run in rows:
            critical_components = [
                normalize_rubric_score(run.get("qgeval_可回答性"), 5),
                normalize_rubric_score(run.get("qgeval_答案一致性"), 5),
                normalize_rubric_score(run.get("llm_正确性"), 5),
                normalize_rubric_score(run.get("llm_可解性"), 5),
                normalize_rubric_score(run.get("llm_绝对性"), 5),
            ]
            critical = any(v is not None and v <= 2 for v in critical_components)
            major_domains = [
                maybe_float(run.get("machine_proxy_answer_validity")),
                maybe_float(run.get("machine_proxy_presentation_clarity")),
                maybe_float(run.get("machine_proxy_item_design")),
            ]
            major = critical or any(v is not None and v <= 3 for v in major_domains)
            major_flags.append(1 if major else 0)
            critical_flags.append(1 if critical else 0)
        row["screen_major_defect_proxy"] = 1 if sum(major_flags) >= 2 else 0
        row["screen_critical_defect_proxy"] = 1 if any(critical_flags) else 0
        for dim in raw_dimension_names + ["machine_proxy_quality_score"] + MACHINE_PROXY_DOMAIN_FIELDS:
            values = [maybe_float(r.get(dim)) for r in rows]
            values = [v for v in values if v is not None]
            row[f"{dim}_mean"] = statistics.fmean(values) if values else None
        summary_rows.append(row)
        defect_rows.append(
            {
                "item_id": iid,
                "source_true": source,
                "final_major_defect": row["screen_major_defect_proxy"],
                "final_critical_defect": row["screen_critical_defect_proxy"],
                "adjudication_reason": "machine_screen_proxy",
            }
        )
    return summary_rows, defect_rows


def build_machine_safety_screening(
    machine_ratings: Sequence[Dict[str, Any]],
    item_master: Sequence[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    item_by_id = {row["item_id"]: row for row in item_master}
    output = []
    for row in machine_ratings:
        item_row = item_by_id.get(row["item_id"], {})
        run_id_match = re.search(r"(\d+)$", clean_cell(row.get("rater_id", "")))
        run_id = maybe_int(run_id_match.group(1)) if run_id_match else None
        screen_row = {
            "item_id": row.get("item_id"),
            "paper": row.get("paper"),
            "paper_item_no": row.get("paper_item_no"),
            "source_true": row.get("source_true"),
            "item_type": item_row.get("item_type"),
            "rater_id": row.get("rater_id"),
            "run_id": run_id,
            "rater_phase": row.get("rater_phase"),
            "answer_key": item_row.get("answer_key"),
        }
        screen_row.update(machine_safety_screen_scores(dict(row), item_row))
        output.append(screen_row)
    return output


def aggregate_machine_safety_screening(screen_rows: Sequence[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in screen_rows:
        grouped[row["item_id"]].append(row)

    item_rows = []
    for iid, rows in grouped.items():
        base = rows[0]
        output: Dict[str, Any] = {
            "item_id": iid,
            "paper": base.get("paper"),
            "paper_item_no": base.get("paper_item_no"),
            "source_true": base.get("source_true"),
            "item_type": base.get("item_type"),
            "n_machine_runs": len(rows),
            "answer_key": base.get("answer_key"),
            "answer_key_format_ok": base.get("answer_key_format_ok"),
        }
        for domain in MACHINE_SAFETY_SCREEN_COMPONENTS:
            scores = [maybe_float(row.get(f"{domain}_score_5")) for row in rows]
            scores = [score for score in scores if score is not None]
            passes = [maybe_float(row.get(f"{domain}_pass")) for row in rows]
            passes = [score for score in passes if score is not None]
            output[f"{domain}_score_5_mean"] = statistics.fmean(scores) if scores else None
            output[f"{domain}_score_5_sd"] = statistics.stdev(scores) if len(scores) > 1 else 0 if scores else None
            output[f"{domain}_pass_rate"] = statistics.fmean(passes) if passes else None
        critical_values = [int(row.get("critical_defect_flag") or 0) for row in rows]
        major_values = [int(row.get("major_defect_flag") or 0) for row in rows]
        all_pass_values = [int(row.get("all_safety_domains_pass") or 0) for row in rows]
        output["critical_defect_runs"] = sum(critical_values)
        output["critical_defect_rate"] = statistics.fmean(critical_values) if critical_values else None
        output["critical_defect_any_run"] = 1 if any(critical_values) else 0
        output["major_defect_runs"] = sum(major_values)
        output["major_defect_rate"] = statistics.fmean(major_values) if major_values else None
        output["major_defect_consensus"] = 1 if sum(major_values) >= 2 else 0
        output["all_safety_domains_pass_rate"] = statistics.fmean(all_pass_values) if all_pass_values else None
        reasons = sorted({reason for row in rows for reason in clean_cell(row.get("critical_defect_reasons", "")).split(";") if reason})
        output["critical_defect_reasons"] = ";".join(reasons)
        item_rows.append(output)

    source_rows = []
    for source in ["Human", "MAS"]:
        rows = [row for row in item_rows if row.get("source_true") == source]
        if not rows:
            continue
        for domain, spec in MACHINE_SAFETY_SCREEN_COMPONENTS.items():
            pass_rates = [maybe_float(row.get(f"{domain}_pass_rate")) for row in rows]
            pass_rates = [value for value in pass_rates if value is not None]
            scores = [maybe_float(row.get(f"{domain}_score_5_mean")) for row in rows]
            scores = [value for value in scores if value is not None]
            source_rows.append(
                {
                    "source_true": source,
                    "screening_domain": domain,
                    "screening_domain_label": spec["label"],
                    "n_items": len(rows),
                    "mean_score_5": statistics.fmean(scores) if scores else None,
                    "item_level_pass_fraction": statistics.fmean(pass_rates) if pass_rates else None,
                    "display_direction": "higher_is_better",
                }
            )
        no_critical = [1.0 - float(row.get("critical_defect_rate") or 0) for row in rows]
        source_rows.append(
            {
                "source_true": source,
                "screening_domain": "no_critical_defect_flag",
                "screening_domain_label": "No critical defect flag",
                "n_items": len(rows),
                "mean_score_5": "",
                "item_level_pass_fraction": statistics.fmean(no_critical) if no_critical else None,
                "display_direction": "higher_is_better",
            }
        )
    return sorted(item_rows, key=lambda r: (r.get("source_true", ""), int(r.get("paper_item_no") or 0))), source_rows


def add_item_level_summaries(
    item_master: List[Dict[str, Any]],
    machine_summary: List[Dict[str, Any]],
    ctt_rows: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    by_item = {row["item_id"]: dict(row) for row in item_master}
    for row in machine_summary:
        by_item.setdefault(row["item_id"], {}).update(row)
    for row in ctt_rows:
        by_item.setdefault(row["item_id"], {}).update(row)
    return sorted(by_item.values(), key=lambda r: (r.get("source_true", ""), int(r.get("paper_item_no") or 0)))


def build_ctt_rows(responses: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    by_item: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    by_student_source: Dict[Tuple[str, str], int] = defaultdict(int)
    for row in responses:
        by_item[row["item_id"]].append(row)
        by_student_source[(row["student_id"], row["source_true"])] += int(row["correct"])

    ctt_rows = []
    for iid, rows in sorted(by_item.items()):
        correct = [int(r["correct"]) for r in rows]
        rests = [by_student_source[(r["student_id"], r["source_true"])] - int(r["correct"]) for r in rows]
        ctt_rows.append(
            {
                "item_id": iid,
                "source_true": rows[0]["source_true"],
                "n_responses": len(rows),
                "difficulty": statistics.fmean(correct) if correct else None,
                "discrimination": pearson(correct, rests),
            }
        )
    return ctt_rows


def parse_source_detection(path: Path) -> List[Dict[str, Any]]:
    rows = read_csv_rows(path)
    if not rows:
        return []
    header = rows[0]
    output = []
    for idx, row in enumerate(rows[1:], start=1):
        if len(row) < 12:
            continue
        item_pair = maybe_int(row[0])
        success = clean_cell(row[1]).upper()
        if item_pair is None or success not in {"T", "F"}:
            continue
        output.append(
            {
                "detection_id": idx,
                "item_pair_label": item_pair,
                "source_guess_success": 1 if success == "T" else 0,
                "human_difficulty": maybe_float(row[2]),
                "human_difficulty_distance": maybe_float(row[3]),
                "human_urology_relevance": maybe_float(row[4]),
                "human_clinical_relevance": maybe_float(row[5]),
                "human_rating": maybe_float(row[6]),
                "mas_difficulty": maybe_float(row[7]),
                "mas_difficulty_distance": maybe_float(row[8]),
                "mas_urology_relevance": maybe_float(row[9]),
                "mas_clinical_relevance": maybe_float(row[10]),
                "mas_rating": maybe_float(row[11]),
                "raw_header": "|".join(header),
            }
        )
    return output


def expand_source_detection_pairs(pair_rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Infer item-level source guesses from forced-pair success flags.

    The raw file records whether a pair-level source judgment was successful,
    not explicit source_true/source_guess rows. Under the forced-pair design,
    a successful pair judgment implies Human->Human and MAS->MAS; a failed
    judgment implies the two labels were swapped.
    """
    output: List[Dict[str, Any]] = []
    for row in pair_rows:
        success = int(row["source_guess_success"])
        for source_true in ["Human", "MAS"]:
            source_guess = source_true if success else ("MAS" if source_true == "Human" else "Human")
            output.append(
                {
                    "detection_id": row["detection_id"],
                    "item_pair_label": row["item_pair_label"],
                    "source_true": source_true,
                    "source_guess": source_guess,
                    "correct_source_guess": 1 if source_guess == source_true else 0,
                }
            )
    return output


def source_detection_confusion_rows(item_rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    counts: Counter = Counter((row["source_true"], row["source_guess"]) for row in item_rows)
    totals: Counter = Counter(row["source_true"] for row in item_rows)
    output = []
    for source_true in ["Human", "MAS"]:
        for source_guess in ["Human", "MAS"]:
            n = counts.get((source_true, source_guess), 0)
            total = totals.get(source_true, 0)
            output.append(
                {
                    "source_true": source_true,
                    "source_guess": source_guess,
                    "n": n,
                    "row_percent": n / total * 100 if total else None,
                    "inference_note": "inferred_from_forced_pair_success",
                }
            )
    return output


def source_detection_metric_rows(item_rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not item_rows:
        return []
    total = len(item_rows)
    correct = sum(int(row["correct_source_guess"]) for row in item_rows)
    mas_rows = [row for row in item_rows if row["source_true"] == "MAS"]
    human_rows = [row for row in item_rows if row["source_true"] == "Human"]
    sensitivity_n = sum(1 for row in mas_rows if row["source_guess"] == "MAS")
    specificity_n = sum(1 for row in human_rows if row["source_guess"] == "Human")
    sensitivity = sensitivity_n / len(mas_rows) if mas_rows else None
    specificity = specificity_n / len(human_rows) if human_rows else None
    balanced = (sensitivity + specificity) / 2 if sensitivity is not None and specificity is not None else None
    return [
        {"metric": "accuracy", "estimate": correct / total, "numerator": correct, "denominator": total, "inference_note": "pair_success"},
        {"metric": "balanced_accuracy", "estimate": balanced, "numerator": "", "denominator": "", "inference_note": "inferred_from_forced_pair_success"},
        {"metric": "sensitivity_mas", "estimate": sensitivity, "numerator": sensitivity_n, "denominator": len(mas_rows), "inference_note": "inferred_from_forced_pair_success"},
        {"metric": "specificity_human", "estimate": specificity, "numerator": specificity_n, "denominator": len(human_rows), "inference_note": "inferred_from_forced_pair_success"},
    ]


def bank_record_counts() -> Dict[str, Any]:
    counts: Dict[str, Any] = {}
    human_total = 0
    mas_total = 0
    for path in sorted(BANK_DIR.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        n = len(data) if isinstance(data, list) else None
        counts[path.stem] = n
        if path.stem.startswith("new_bank_") and n is not None:
            mas_total += n
        elif path.stem.startswith("bank_") and n is not None:
            human_total += n
    counts["human_bank_records_total"] = human_total
    counts["mas_bank_records_total"] = mas_total
    return counts


def summarize_main_tables(
    item_level: Sequence[Dict[str, Any]],
    assignments: Sequence[Dict[str, Any]],
    paired_scores: Sequence[Dict[str, Any]],
    source_detection: Sequence[Dict[str, Any]],
    source_detection_metrics: Sequence[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    table1 = []
    for source in ["Human", "MAS"]:
        rows = [r for r in item_level if r.get("source_true") == source]
        table1.append(
            {
                "source_true": source,
                "n_items": len(rows),
                "mean_char_count": round(statistics.fmean([float(r["char_count"]) for r in rows if r.get("char_count") not in {"", None}]), 2),
                "mean_machine_proxy_quality_score": round(statistics.fmean([float(r["machine_proxy_quality_score_mean"]) for r in rows if r.get("machine_proxy_quality_score_mean") not in {"", None}]), 3),
                "mean_raw_llm_score_5": round(statistics.fmean([float(r["llm_score_5_mean"]) for r in rows if r.get("llm_score_5_mean") not in {"", None}]), 3),
                "mean_raw_qgeval_score_5": round(statistics.fmean([float(r["qgeval_score_5_mean"]) for r in rows if r.get("qgeval_score_5_mean") not in {"", None}]), 3),
                "topic_counts": json.dumps(Counter(r.get("topic") for r in rows), ensure_ascii=False),
                "cognitive_level_counts": json.dumps(Counter(r.get("cognitive_level") for r in rows), ensure_ascii=False),
                "item_type_counts": json.dumps(Counter(r.get("item_type") for r in rows), ensure_ascii=False),
            }
        )

    table2 = []
    for form in ["A", "B"]:
        rows = [r for r in assignments if r.get("form") == form]
        table2.append(
            {
                "form": form,
                "order": "Human->MAS" if form == "A" else "MAS->Human",
                "n_students": len(rows),
                "training_setting_counts": json.dumps(Counter(r.get("training_setting") for r in rows), ensure_ascii=False),
                "training_year_counts": json.dumps(Counter(r.get("training_year") for r in rows), ensure_ascii=False),
                "mean_total_time_seconds": round(statistics.fmean([float(r["total_time_seconds"]) for r in rows if r.get("total_time_seconds") not in {"", None}]), 2) if any(r.get("total_time_seconds") not in {"", None} for r in rows) else "",
            }
        )

    endpoint_rows = []
    human_quality = [float(r["machine_proxy_quality_score_mean"]) for r in item_level if r.get("source_true") == "Human" and r.get("machine_proxy_quality_score_mean") not in {"", None}]
    mas_quality = [float(r["machine_proxy_quality_score_mean"]) for r in item_level if r.get("source_true") == "MAS" and r.get("machine_proxy_quality_score_mean") not in {"", None}]
    if human_quality and mas_quality:
        endpoint_rows.append(
            {
                "endpoint": "machine_proxy_quality_score_5_qc_only",
                "estimate": round(statistics.fmean(mas_quality) - statistics.fmean(human_quality), 3),
                "contrast": "MAS-Human",
                "interpretation_level": "machine_annotation_qc_only",
            }
        )
    paired_diffs = [float(r["mas_minus_human_score"]) for r in paired_scores if r.get("mas_minus_human_score") not in {"", None}]
    if paired_diffs:
        endpoint_rows.append(
            {
                "endpoint": "examinee_block_score_difference",
                "estimate": round(statistics.fmean(paired_diffs), 3),
                "contrast": "MAS-Human paired score",
                "interpretation_level": "student_block",
            }
        )
    detection_values = [int(r["source_guess_success"]) for r in source_detection]
    if detection_values:
        endpoint_rows.append(
            {
                "endpoint": "source_detection_accuracy",
                "estimate": round(statistics.fmean(detection_values), 3),
                "contrast": "correct source decision",
                "interpretation_level": "source_detection",
            }
        )
    for metric in source_detection_metrics:
        if metric.get("metric") == "balanced_accuracy" and metric.get("estimate") not in {"", None}:
            endpoint_rows.append(
                {
                    "endpoint": "source_detection_balanced_accuracy_inferred",
                    "estimate": round(float(metric["estimate"]), 3),
                    "contrast": "correct source decision",
                    "interpretation_level": "source_detection_inferred_from_pair_success",
                }
            )
    return table1, table2, endpoint_rows


def main() -> None:
    PLOT_DATA_DIR.mkdir(parents=True, exist_ok=True)

    responses, assignments, block_scores, paired_scores, answer_rows = build_response_tables()
    item_master, machine_ratings = build_report_tables(answer_rows)
    machine_summary, defect_rows = aggregate_machine_ratings(machine_ratings)
    safety_screen_rows = build_machine_safety_screening(machine_ratings, item_master)
    safety_item_summary, safety_source_summary = aggregate_machine_safety_screening(safety_screen_rows)
    ctt_rows = build_ctt_rows(responses)
    item_level = add_item_level_summaries(item_master, machine_summary, ctt_rows)
    source_detection = parse_source_detection(
        PLOT_DATA_DIR
        / "source_workbooks"
        / "exam_responses_workbook_1__17__评价系统与图灵测试.csv"
    )
    source_detection_item_level = expand_source_detection_pairs(source_detection)
    source_detection_confusion = source_detection_confusion_rows(source_detection_item_level)
    source_detection_metrics = source_detection_metric_rows(source_detection_item_level)

    table1, table2, table3 = summarize_main_tables(item_level, assignments, paired_scores, source_detection, source_detection_metrics)

    write_csv(
        PLOT_DATA_DIR / "responses.csv",
        responses,
        [
            "student_id",
            "student_no",
            "item_id",
            "paper",
            "paper_item_no",
            "source_true",
            "item_type",
            "score",
            "correct",
            "response_missing",
            "form",
            "order_group",
            "block_position",
            "training_year",
            "training_setting_code",
            "training_setting",
            "total_time_seconds",
        ],
    )
    write_csv(
        PLOT_DATA_DIR / "exam_form_assignment.csv",
        assignments,
        [
            "student_id",
            "student_no",
            "form",
            "order_group",
            "training_setting",
            "training_setting_code",
            "training_year",
            "total_time_seconds",
            "m_score_reported",
            "p_score_reported",
            "m_minus_p_reported",
        ],
    )
    write_csv(
        PLOT_DATA_DIR / "block_scores.csv",
        block_scores,
        [
            "student_id",
            "source_true",
            "paper",
            "form",
            "order_group",
            "block_position",
            "training_year",
            "training_setting",
            "n_items",
            "raw_score",
            "n_correct",
            "score_percent",
            "correct_rate",
        ],
    )
    write_csv(
        PLOT_DATA_DIR / "paired_block_scores.csv",
        paired_scores,
        [
            "student_id",
            "student_no",
            "form",
            "order_group",
            "training_year",
            "training_setting",
            "human_score",
            "mas_score",
            "mas_minus_human_score",
            "human_correct_rate",
            "mas_correct_rate",
            "mas_minus_human_correct_rate",
            "total_time_seconds",
        ],
    )
    write_csv(
        PLOT_DATA_DIR / "item_master.csv",
        item_master,
        [
            "item_id",
            "paper",
            "paper_item_no",
            "source_true",
            "item_type",
            "header_item_type",
            "source_item_id",
            "answer_key",
            "answer_key_from_report",
            "test_point",
            "topic",
            "blueprint_cognitive_level",
            "cognitive_level",
            "has_vignette",
            "char_count",
            "flesch_reading_ease",
            "fuzzywuzzy_ratio_max",
            "sentencebert_cosine_max",
            "ngram_jaccard_max",
            "question_text",
        ],
    )
    machine_rating_fields = sorted({key for row in machine_ratings for key in row})
    write_csv(PLOT_DATA_DIR / "machine_ratings.csv", machine_ratings, machine_rating_fields)
    machine_summary_fields = sorted({key for row in machine_summary for key in row})
    write_csv(PLOT_DATA_DIR / "machine_rating_summary.csv", machine_summary, machine_summary_fields)
    write_csv(
        PLOT_DATA_DIR / "machine_safety_screening_by_run.csv",
        safety_screen_rows,
        [
            "item_id",
            "paper",
            "paper_item_no",
            "source_true",
            "item_type",
            "rater_id",
            "run_id",
            "rater_phase",
            "answer_key",
            "answer_key_format_ok",
            *MACHINE_SAFETY_SCREEN_FIELDS,
            *[f"{domain}_pass" for domain in MACHINE_SAFETY_SCREEN_COMPONENTS],
            "safety_screen_mean_score_5",
            "safety_screen_min_score_5",
            "major_defect_flag",
            "critical_defect_flag",
            "critical_defect_reasons",
            "all_safety_domains_pass",
        ],
    )
    write_csv(
        PLOT_DATA_DIR / "machine_safety_screening_summary.csv",
        safety_item_summary,
        [
            "item_id",
            "paper",
            "paper_item_no",
            "source_true",
            "item_type",
            "n_machine_runs",
            "answer_key",
            "answer_key_format_ok",
            *[field for domain in MACHINE_SAFETY_SCREEN_COMPONENTS for field in (f"{domain}_score_5_mean", f"{domain}_score_5_sd", f"{domain}_pass_rate")],
            "major_defect_runs",
            "major_defect_rate",
            "major_defect_consensus",
            "critical_defect_runs",
            "critical_defect_rate",
            "critical_defect_any_run",
            "critical_defect_reasons",
            "all_safety_domains_pass_rate",
        ],
    )
    write_csv(
        PLOT_DATA_DIR / "machine_safety_screening_source_summary.csv",
        safety_source_summary,
        [
            "source_true",
            "screening_domain",
            "screening_domain_label",
            "n_items",
            "mean_score_5",
            "item_level_pass_fraction",
            "display_direction",
        ],
    )
    write_csv(
        PLOT_DATA_DIR / "defect_adjudication_proxy.csv",
        defect_rows,
        ["item_id", "source_true", "final_major_defect", "final_critical_defect", "adjudication_reason"],
    )
    write_csv(PLOT_DATA_DIR / "ctt_item_analysis.csv", ctt_rows, ["item_id", "source_true", "n_responses", "difficulty", "discrimination"])
    write_csv(
        PLOT_DATA_DIR / "item_level_analysis.csv",
        item_level,
        sorted({key for row in item_level for key in row if key != "question_text"}) + ["question_text"],
    )
    write_csv(
        PLOT_DATA_DIR / "source_detection.csv",
        source_detection,
        [
            "detection_id",
            "item_pair_label",
            "source_guess_success",
            "human_difficulty",
            "human_difficulty_distance",
            "human_urology_relevance",
            "human_clinical_relevance",
            "human_rating",
            "mas_difficulty",
            "mas_difficulty_distance",
            "mas_urology_relevance",
            "mas_clinical_relevance",
            "mas_rating",
            "raw_header",
        ],
    )
    write_csv(
        PLOT_DATA_DIR / "source_detection_item_level.csv",
        source_detection_item_level,
        ["detection_id", "item_pair_label", "source_true", "source_guess", "correct_source_guess"],
    )
    write_csv(
        PLOT_DATA_DIR / "source_detection_confusion_matrix.csv",
        source_detection_confusion,
        ["source_true", "source_guess", "n", "row_percent", "inference_note"],
    )
    write_csv(
        PLOT_DATA_DIR / "source_detection_metrics.csv",
        source_detection_metrics,
        ["metric", "estimate", "numerator", "denominator", "inference_note"],
    )
    write_csv(
        PLOT_DATA_DIR / "machine_rating_domain_crosswalk.csv",
        [
            {
                "proxy_domain": domain,
                "proxy_domain_label": spec["label"],
                "component_source": component[0],
                "component_name": component[1],
                "component_max_score": component[2],
                "normalization": "1 + 4 * (raw - 1) / (max_score - 1)",
            }
            for domain, spec in MACHINE_PROXY_DOMAIN_COMPONENTS.items()
            for component in spec["components"]
        ],
        ["proxy_domain", "proxy_domain_label", "component_source", "component_name", "component_max_score", "normalization"],
    )
    write_csv(
        PLOT_DATA_DIR / "machine_safety_screening_crosswalk.csv",
        [
            {
                "screening_domain": domain,
                "screening_domain_label": spec["label"],
                "component_source": component[0],
                "component_name": component[1],
                "component_max_score": component[2],
                "component_weight": component[3],
                "normalization": "1 + 4 * (raw - 1) / (max_score - 1)",
                "domain_score": "weighted mean of normalized components",
                "pass_rule": f"domain_score >= {SAFETY_PASS_THRESHOLD}",
                "critical_rule": f"domain_score < {SAFETY_CRITICAL_THRESHOLD}, any critical component <= 2, or invalid answer-key format",
            }
            for domain, spec in MACHINE_SAFETY_SCREEN_COMPONENTS.items()
            for component in spec["components"]
        ]
        + [
            {
                "screening_domain": "critical_defect_flag",
                "screening_domain_label": "Critical defect flag",
                "component_source": component[0],
                "component_name": component[1],
                "component_max_score": component[2],
                "component_weight": "",
                "normalization": "1 + 4 * (raw - 1) / (max_score - 1)",
                "domain_score": "binary flag",
                "pass_rule": "critical_defect_flag == 0",
                "critical_rule": "normalized component <= 2",
            }
            for component in SAFETY_CRITICAL_COMPONENTS
        ]
        + [
            {
                "screening_domain": "critical_defect_flag",
                "screening_domain_label": "Critical defect flag",
                "component_source": "derived",
                "component_name": "answer_key_format_ok",
                "component_max_score": "",
                "component_weight": "",
                "normalization": "legal A-E key; non-X items require one key, X items allow one or more unique keys",
                "domain_score": "binary flag",
                "pass_rule": "critical_defect_flag == 0",
                "critical_rule": "answer_key_format_ok == 0",
            }
        ],
        [
            "screening_domain",
            "screening_domain_label",
            "component_source",
            "component_name",
            "component_max_score",
            "component_weight",
            "normalization",
            "domain_score",
            "pass_rule",
            "critical_rule",
        ],
    )
    write_csv(PLOT_DATA_DIR / "table1_item_blueprint_textual_characteristics.csv", table1, list(table1[0]) if table1 else [])
    write_csv(PLOT_DATA_DIR / "table2_examinee_baseline_randomization_balance.csv", table2, list(table2[0]) if table2 else [])
    write_csv(PLOT_DATA_DIR / "table3_primary_key_secondary_endpoints.csv", table3, list(table3[0]) if table3 else [])
    write_csv(
        PLOT_DATA_DIR / "workflow_total_time_cost_TEMPLATE.csv",
        [],
        [
            "workflow",
            "total_minutes",
            "total_expert_minutes",
            "total_nonexpert_minutes",
            "api_cost",
            "number_final_items",
            "number_nondefective_items",
            "time_source",
            "time_granularity",
        ],
    )

    inventory = bank_record_counts()
    inventory.update(
        {
            "n_final_items": len(item_master),
            "n_final_human_items": sum(1 for r in item_master if r["source_true"] == "Human"),
            "n_final_mas_items": sum(1 for r in item_master if r["source_true"] == "MAS"),
            "n_students": len(assignments),
            "form_counts": dict(Counter(r["form"] for r in assignments)),
            "training_setting_counts": dict(Counter(r["training_setting"] for r in assignments)),
            "n_responses": len(responses),
            "n_missing_responses_scored_incorrect": sum(int(r.get("response_missing", 0)) for r in responses),
            "n_machine_rating_rows": len(machine_ratings),
            "n_machine_safety_screening_rows": len(safety_screen_rows),
            "n_machine_safety_screening_item_rows": len(safety_item_summary),
        }
    )
    write_json(PLOT_DATA_DIR / "data_inventory.json", inventory)

    consistency_notes = {
        "form_order": "Form A = Human -> MAS; Form B = MAS -> Human.",
        "paper_source": "P卷 is encoded as Human; M卷 is encoded as MAS.",
        "training_setting": "原始院区 A/B 保留为 training_setting_code；绘图口径映射为 A=main, B=non_main。",
        "cognitive_level": "A1=recall, B=comprehension, A2=application, A3/A4/X=analysis; 论文三层映射为 recall/comprehension->knowledge, application->application, analysis->reasoning。",
        "score_phase": "解析标注版中的四轮 QGEval/LLM 写入 rater_phase=machine_annotation；原始细则经 machine_rating_domain_crosswalk.csv 归一化并映射为 machine_proxy_* 字段，仅作QC/探索性代理。",
        "ai_safety_screening": "machine_safety_screening_by_run.csv 将23项 QGEval/LLM 评分归一化到1-5分，并加权转换为指南一致性、单一最佳答案、答案键校验、干扰项有效性、题干歧义控制和 critical defect flag；machine_safety_screening_crosswalk.csv 记录函数关系。",
        "source_detection": "原始工作簿的‘评价系统与图灵测试’工作表只记录成对来源判断是否成功；source_detection_confusion_matrix.csv 按 forced-pair 成功/失败反推，不能替代逐题 source_guess 原始表。",
        "workflow_efficiency": "Figure 5 的人工时间和成本直接来自 plot/data/raw/效率分析.xlsx，并与 plot/data/raw/人工卷用时及成本.docx 交叉核对。考生考试时长仅用于 Figure 6，不作为工作流人力时间。",
        "expert_scores": "Figure 2B–2F 与 Figure 4B–4D 的盲法专家评分直接来自 plot/data/raw/expert_rating_workbooks；expert_ratings_updated.csv 仅作历史复核。machine_proxy_quality_score 仅作 QC/探索性代理，不进入专家评分主终点。",
        "missing_responses": "考生作答空值按预设规则记为 incorrect，并用 response_missing=1 标记。",
    }
    write_json(PLOT_DATA_DIR / "consistency_resolutions.json", consistency_notes)

    print(f"[OK] Wrote plot datasets to {PLOT_DATA_DIR}")
    print(f"[OK] responses={len(responses)}, students={len(assignments)}, items={len(item_master)}, machine_ratings={len(machine_ratings)}")


if __name__ == "__main__":
    main()
