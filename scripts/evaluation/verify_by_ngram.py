"""为 MAS 题库写入字符 n-gram Jaccard 文本重叠字段。

脚本用途：比较 MAS 题库与人类题库，记录每道 MAS 题最相似的人类题库题目。
流程阶段：题库机器评价。
主要输入：`data/banks/new_bank_*.json` 与全部 `data/banks/bank_*.json`。
主要输出：原地更新的 `data/banks/new_bank_*.json`，写入 `{n}gram_doubt` 与 `{n}gram_jaccard_max`。
重要边界：该指标只描述字符重叠，不判断最终题目质量，也不替代专家评审。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, FrozenSet, List, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from project_paths import BANK_DIR


NEW_FILES = [
    "new_bank_a1.json",
    "new_bank_a2.json",
    "new_bank_a3.json",
    "new_bank_a4.json",
    "new_bank_b.json",
    "new_bank_x.json",
]

OLD_FILES = [
    "bank_a1.json",
    "bank_a2.json",
    "bank_a3.json",
    "bank_a4.json",
    "bank_b.json",
    "bank_x.json",
]


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
    按题型拼接用于匹配的字符串（不加分隔符）：

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


# ===== 人类题库索引 =====

def make_old_key(q: Dict[str, Any], fallback_index: int) -> str:
    """
    生成 "A3_20" 这种 key；若缺字段则用 fallback 保底。
    """
    t = q.get("type")
    i = q.get("id")
    if isinstance(t, str) and t and (isinstance(i, str) or isinstance(i, int)):
        return f"{t}_{i}"
    return f"UNK_{fallback_index}"


def build_old_text_map(base_dir: str) -> Dict[str, str]:
    """
    返回 dict: { "A3_20": "拼接后的题干选项字符串", ... }
    """
    text_map: Dict[str, str] = {}
    fallback = 0

    for fn in OLD_FILES:
        path = os.path.join(base_dir, fn)
        if not os.path.exists(path):
            print(f"[WARN] 缺少人类题库：{path}", file=sys.stderr)
            continue

        qs = load_json_list(path)
        for q in qs:
            key = make_old_key(q, fallback)
            fallback += 1

            s = question_to_string_by_type(q)

            # key 冲突极少见；如发生则追加后缀保证唯一
            if key in text_map:
                suffix = 2
                new_key = f"{key}__{suffix}"
                while new_key in text_map:
                    suffix += 1
                    new_key = f"{key}__{suffix}"
                key = new_key

            text_map[key] = s

    return text_map


# ===== 相似度计算 =====

def make_char_ngrams(s: str, n: int) -> FrozenSet[str]:
    """
    字符级 n-gram（不做分词/不去标点，最大限度贴近原始题面）。
    - 若 len(s) < n：返回单元素集合 {s}（s 非空），否则空集合
    """
    if not isinstance(s, str):
        s = ""
    s = s.strip()
    if n <= 0:
        raise ValueError("n 必须为正整数")

    if not s:
        return frozenset()

    if len(s) < n:
        return frozenset([s])

    return frozenset(s[i:i + n] for i in range(0, len(s) - n + 1))


def jaccard_index(a: FrozenSet[str], b: FrozenSet[str]) -> float:
    """
    Jaccard(A, B) = |A∩B| / |A∪B|
    约定：若 A、B 都为空，返回 1.0；若仅一方为空，返回 0.0
    """
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    inter = len(a.intersection(b))
    union = len(a.union(b))
    return (inter / union) if union else 0.0


def build_old_ngram_map(old_text_map: Dict[str, str], n: int) -> Dict[str, FrozenSet[str]]:
    """
    返回 dict: { old_key: frozenset(ngrams), ... }
    """
    out: Dict[str, FrozenSet[str]] = {}
    for k, s in old_text_map.items():
        out[k] = make_char_ngrams(s, n)
    return out


def best_match_jaccard(query: str, old_ngrams: Dict[str, FrozenSet[str]], n: int) -> Tuple[str, int]:
    """
    返回 (best_old_key, best_score_0_100_int)
    """
    if not old_ngrams:
        return "", 0

    qset = make_char_ngrams(query, n)

    best_key = ""
    best_score = -1.0

    for k, sset in old_ngrams.items():
        score = jaccard_index(qset, sset)
        if score > best_score:
            best_score = score
            best_key = k

    score_int = int(round(best_score * 100))
    if score_int < 0:
        score_int = 0
    if score_int > 100:
        score_int = 100
    return best_key, score_int


# ===== 主处理流程 =====

def process_new_file(
    path_new: str,
    old_ngrams: Dict[str, FrozenSet[str]],
    n: int,
    overwrite: bool,
    dry_run: bool,
    key_doubt: str,
    key_score: str,
) -> Tuple[int, int]:
    new_qs = load_json_list(path_new)
    total = len(new_qs)

    written = 0
    skipped = 0

    t0 = time.time()
    last_print = 0.0

    for idx, q in enumerate(new_qs, start=1):
        # 默认不覆盖：若已有 key_doubt 或 key_score，就跳过计算
        if (not overwrite) and (key_doubt in q or key_score in q):
            skipped += 1
        else:
            query = question_to_string_by_type(q)
            key, score = best_match_jaccard(query, old_ngrams, n)
            q[key_doubt] = key
            q[key_score] = score
            written += 1

        elapsed = time.time() - t0
        if elapsed - last_print >= 0.2 or idx == total:
            line = progress_line(idx, total, elapsed)
            print(line, end="\r" if idx != total else "\n", flush=True)
            last_print = elapsed

    if not dry_run:
        dump_json_list(path_new, new_qs)

    return written, skipped


def main():
    parser = argparse.ArgumentParser(
        description="Verify MAS banks by character n-gram Jaccard against all human banks."
    )
    parser.add_argument(
        "--dir",
        default=str(BANK_DIR),
        help="题库目录（包含 bank_*.json 与 new_bank_*.json）",
    )
    parser.add_argument(
        "--n",
        type=int,
        default=3,
        help="n-gram 的 n（默认 3）",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="覆盖已存在的 {n}gram_doubt/{n}gram_jaccard_max（默认不覆盖）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只计算不写回文件",
    )
    args = parser.parse_args()

    base_dir = args.dir
    n = args.n
    overwrite = args.overwrite
    dry_run = args.dry_run

    if n <= 0:
        raise ValueError("--n 必须为正整数")

    key_prefix = f"{n}gram"
    key_doubt = f"{key_prefix}_doubt"
    key_score = f"{key_prefix}_jaccard_max"

    print("加载人类题库（合并所有 bank_*.json）...")
    old_text_map = build_old_text_map(base_dir)
    print(f"人类题库合计题数：{len(old_text_map)}")

    print(f"预计算人类题库 {n}-gram 集合...")
    old_ngrams = build_old_ngram_map(old_text_map, n)

    total_written = 0
    total_skipped = 0
    processed = 0

    for fn in NEW_FILES:
        path_new = os.path.join(base_dir, fn)
        if not os.path.exists(path_new):
            print(f"[WARN] 缺少 MAS 题库，跳过：{path_new}", file=sys.stderr)
            continue

        print(f"\n处理 {fn}（n={n}, overwrite={overwrite}, dry_run={dry_run}）")
        written, skipped = process_new_file(
            path_new,
            old_ngrams,
            n=n,
            overwrite=overwrite,
            dry_run=dry_run,
            key_doubt=key_doubt,
            key_score=key_score,
        )
        processed += 1
        total_written += written
        total_skipped += skipped
        print(f"[OK] {fn}: 写入 {written} 题，跳过 {skipped} 题")

    print(
        f"\n[DONE] 文件数：{processed}；总写入：{total_written}；总跳过：{total_skipped}；"
        f"dry_run={dry_run}；字段：{key_doubt}/{key_score}"
    )


if __name__ == "__main__":
    main()