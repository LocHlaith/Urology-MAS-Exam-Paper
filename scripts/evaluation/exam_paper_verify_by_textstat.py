# exam_paper_verify_by_textstat.py
# -*- coding: utf-8 -*-
"""
exam_paper_verify_by_textstat.py

需求实现：
1) 使用 textstat 计算可读性（Flesch Reading Ease）
2) 在 outputs/report_drafts/B.json 中为第一作者组卷后的试卷题目写入可读性分数
3) 不覆盖已存在字段（默认跳过）；可用 --overwrite 强制覆盖

写入字段：
- textstat_flesch_reading_ease: float（通常范围约 0~100，textstat 可能返回负数或 >100，属正常现象）

运行：
python scripts/evaluation/exam_paper_verify_by_textstat.py

不覆盖已存在 textstat_flesch_reading_ease（默认跳过）：
python scripts/evaluation/exam_paper_verify_by_textstat.py

允许覆盖：
python scripts/evaluation/exam_paper_verify_by_textstat.py --overwrite

仅计算不写回：
python scripts/evaluation/exam_paper_verify_by_textstat.py --dry-run

依赖：
pip install textstat
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

import textstat


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from project_paths import REPORT_DRAFTS_DIR


TARGET_FILE = REPORT_DRAFTS_DIR / "B.json"
KEY_SCORE = "textstat_flesch_reading_ease"


# -------------------------
# IO
# -------------------------

def load_json_list(path: str) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError(f"JSON 顶层必须是 list：{path}")
    out: List[Dict[str, Any]] = []
    for i, item in enumerate(data):
        if not isinstance(item, dict):
            raise ValueError(f"{path} 第 {i} 个元素不是 dict")
        out.append(item)
    return out


def dump_json_list(path: str, data: List[Dict[str, Any]]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


# -------------------------
# Text builders
# -------------------------

def _get_str(q: Dict[str, Any], key: str) -> str:
    v = q.get(key)
    return v if isinstance(v, str) else ""


def _append_str(parts: List[str], s: str) -> None:
    if isinstance(s, str) and s:
        parts.append(s)


def _append_options_dict(parts: List[str], opt: Any) -> None:
    """
    opt 形如 {"A": "...", "B": "..."}；按 key 排序拼接 value
    """
    if not isinstance(opt, dict):
        return
    for k in sorted(opt.keys()):
        v = opt.get(k)
        if isinstance(v, str) and v:
            parts.append(v)


def _append_stem_series(parts: List[str], q: Dict[str, Any], keys: List[str]) -> None:
    for k in keys:
        _append_str(parts, _get_str(q, k))


def _append_options_series(parts: List[str], q: Dict[str, Any], keys: List[str]) -> None:
    for k in keys:
        _append_options_dict(parts, q.get(k))


def question_to_string_by_type(q: Dict[str, Any]) -> str:
    """
    按题型拼接用于可读性计算的字符串（不加分隔符）：

    - A1/A2/X：stem、options（也兼容 stem1/stem2..., options1/options2... 若存在）
    - A3：case、stem1、options1、stem2、options2
    - A4：case、stem1、options1、stem2、options2、stem3、options3
    - B：options、stem1、stem2、stem3
    """
    t = q.get("type")
    t = t.upper() if isinstance(t, str) else ""

    parts: List[str] = []

    if t in {"A1", "A2", "X"}:
        _append_str(parts, _get_str(q, "stem"))
        _append_options_dict(parts, q.get("options"))

        # 兼容可能存在的 stem1/stem2..., options1/options2...
        for i in range(1, 10):
            _append_str(parts, _get_str(q, f"stem{i}"))
            _append_options_dict(parts, q.get(f"options{i}"))

    elif t == "A3":
        _append_str(parts, _get_str(q, "case"))
        _append_stem_series(parts, q, ["stem1", "stem2"])
        _append_options_series(parts, q, ["options1", "options2"])

    elif t == "A4":
        _append_str(parts, _get_str(q, "case"))
        _append_stem_series(parts, q, ["stem1", "stem2", "stem3"])
        _append_options_series(parts, q, ["options1", "options2", "options3"])

    elif t == "B":
        _append_options_dict(parts, q.get("options"))
        _append_stem_series(parts, q, ["stem1", "stem2", "stem3"])

    else:
        # 未知类型：尽量把常见字段都拼上，保证不崩
        _append_str(parts, _get_str(q, "case"))
        _append_str(parts, _get_str(q, "stem"))
        for i in range(1, 10):
            _append_str(parts, _get_str(q, f"stem{i}"))
        _append_options_dict(parts, q.get("options"))
        for i in range(1, 10):
            _append_options_dict(parts, q.get(f"options{i}"))

    return "".join(parts)


# -------------------------
# Progress / ETA
# -------------------------

def fmt_mmss(seconds: float) -> str:
    seconds = max(0.0, float(seconds))
    m = int(seconds // 60)
    s = int(round(seconds - 60 * m))
    if s >= 60:
        m += 1
        s -= 60
    return f"{m:02d}:{s:02d}"


def progress_line(done: int, total: int, elapsed: float) -> str:
    if done <= 0:
        rate = 0.0
        remaining = 0.0
    else:
        rate = elapsed / done
        remaining = rate * (total - done)
    return f"{done}/{total} [{fmt_mmss(elapsed)}<{fmt_mmss(remaining)},  {rate:0.2f}s/it]"


# -------------------------
# Core
# -------------------------

def compute_flesch_reading_ease(text: str) -> float:
    """
    使用 textstat 计算 Flesch Reading Ease。
    注意：该公式主要面向英文；中文文本也能跑，但解释需谨慎。
    """
    text = text if isinstance(text, str) else ""
    text = text.strip()
    if not text:
        return 0.0

    # textstat 有时会抛异常（极端字符/编码/内部依赖问题），这里兜底
    try:
        score = textstat.flesch_reading_ease(text)
        return float(score)
    except Exception:
        return 0.0


def process_file(path: str, overwrite: bool, dry_run: bool) -> Tuple[int, int]:
    qs = load_json_list(path)
    total = len(qs)

    written = 0
    skipped = 0

    t0 = time.time()
    last_print = 0.0

    for idx, q in enumerate(qs, start=1):
        if (not overwrite) and (KEY_SCORE in q):
            skipped += 1
        else:
            text = question_to_string_by_type(q)
            score = compute_flesch_reading_ease(text)
            q[KEY_SCORE] = score
            written += 1

        elapsed = time.time() - t0
        if elapsed - last_print >= 0.2 or idx == total:
            line = progress_line(idx, total, elapsed)
            print(line, end="\r" if idx != total else "\n", flush=True)
            last_print = elapsed

    if not dry_run:
        dump_json_list(path, qs)

    return written, skipped


def main():
    parser = argparse.ArgumentParser(
        description="Compute Flesch Reading Ease for outputs/report_drafts/B.json via textstat."
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help=f"覆盖已存在的 {KEY_SCORE}（默认不覆盖）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只计算不写回文件",
    )
    args = parser.parse_args()

    overwrite = args.overwrite
    dry_run = args.dry_run

    path = str(TARGET_FILE)

    if not os.path.exists(path):
        print(f"[ERROR] 文件不存在：{path}", file=sys.stderr)
        sys.exit(1)

    print(f"处理 {path}（overwrite={overwrite}, dry_run={dry_run}）")
    written, skipped = process_file(
        path,
        overwrite=overwrite,
        dry_run=dry_run
    )
    print(f"[OK] {path}: 写入 {written} 题，跳过 {skipped} 题")


if __name__ == "__main__":
    main()
