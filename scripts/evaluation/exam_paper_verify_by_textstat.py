"""为指定试卷 JSON 写入可读性字段。

脚本用途：使用 textstat 计算第一作者组卷后试卷题目的 Flesch Reading Ease。
流程阶段：试卷机器评价。
主要输入：用户通过 `--target-file` 明确指定的试卷 JSON。
主要输出：原地更新的试卷 JSON，写入 `textstat_flesch_reading_ease`。
重要边界：不得从历史路径或文件名推断试卷文件；该指标不代表专家评分。
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

KEY_SCORE = "textstat_flesch_reading_ease"


# ===== 文件读写 =====

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


# ===== 题面文本构造 =====

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


# ===== 进度显示 =====

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


# ===== 主处理流程 =====

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
        description="Compute Flesch Reading Ease for an exam paper JSON via textstat."
    )
    parser.add_argument(
        "--target-file",
        "--target_file",
        dest="target_file",
        required=True,
        help="待处理的试卷 JSON 文件路径。",
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

    path = args.target_file

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