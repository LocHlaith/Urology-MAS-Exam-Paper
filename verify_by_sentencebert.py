# verify_by_sentencebert.py
# -*- coding: utf-8 -*-
"""
verify_by_sentencebert.py

需求实现：
1) 调用 Sentence-BERT 生成向量，计算 cosine_similarity
2) 与 verify_by_fuzzywuzzy.py 相互独立：本脚本不出现 fuzzywuzzy / Levenshtein 相关内容
3) 在 new_bank_*.json 中记录旧 bank 中最像它的一题：
   例如："sentencebert_doubt": "A3_20"
4) 匹配范围：每个 new_bank_*.json 里的每道题，都与“所有旧 bank_*.json（a1/a2/a3/a4/b/x）”全库匹配

额外写入字段：
- sentencebert_doubt: 最像的旧题 ID（如 A3_20）
- sentencebert_cosine_max: cosine 相似度（float，-1~1）

运行：
python verify_by_sentencebert.py --dir "D:\\Desktop\\当务之急\\EAGLE\\泌尿外科\\泌尿外科专科出卷"

不覆盖已存在 sentencebert_doubt / sentencebert_cosine_max（默认跳过）：
python verify_by_sentencebert.py --dir "..."

允许覆盖：
python verify_by_sentencebert.py --dir "..." --overwrite

可选参数：
--model "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
--device "cpu" / "cuda"
--batch-size 64
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from typing import Any, Dict, List, Tuple

import numpy as np
from sentence_transformers import SentenceTransformer


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

KEY_DOUBT = "sentencebert_doubt"
KEY_SCORE = "sentencebert_cosine_max"


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
# Text builders（与 verify_by_fuzzywuzzy.py 保持一致）
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


# -------------------------
# Progress / ETA（与原脚本一致风格）
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
# Old corpus build
# -------------------------

def make_old_key(q: Dict[str, Any], fallback_index: int) -> str:
    """
    生成 "A3_20" 这种 key；若缺字段则用 fallback 保底。
    """
    t = q.get("type")
    i = q.get("id")
    if isinstance(t, str) and t and (isinstance(i, str) or isinstance(i, int)):
        return f"{t}_{i}"
    return f"UNK_{fallback_index}"


def build_old_corpus(base_dir: str) -> Tuple[List[str], List[str]]:
    """
    返回 (keys, texts)
    keys 形如 ["A3_20", ...]
    texts 为拼接后的题干选项字符串
    """
    keys: List[str] = []
    texts: List[str] = []
    key_set = set()
    fallback = 0

    for fn in OLD_FILES:
        path = os.path.join(base_dir, fn)
        if not os.path.exists(path):
            print(f"[WARN] 缺少旧题库：{path}", file=sys.stderr)
            continue

        qs = load_json_list(path)
        for q in qs:
            key = make_old_key(q, fallback)
            fallback += 1

            # key 冲突极少见；如发生则追加后缀保证唯一
            if key in key_set:
                suffix = 2
                new_key = f"{key}__{suffix}"
                while new_key in key_set:
                    suffix += 1
                    new_key = f"{key}__{suffix}"
                key = new_key

            s = question_to_string_by_type(q)
            keys.append(key)
            texts.append(s)
            key_set.add(key)

    return keys, texts


# -------------------------
# Sentence-BERT / cosine similarity
# -------------------------

def l2_normalize(x: np.ndarray, eps: float = 1e-12) -> np.ndarray:
    """
    对最后一维做 L2 归一化。
    x: (n, d) 或 (d,)
    """
    if x.ndim == 1:
        denom = np.linalg.norm(x) + eps
        return x / denom
    denom = np.linalg.norm(x, axis=1, keepdims=True) + eps
    return x / denom


def embed_texts(
    model: SentenceTransformer,
    texts: List[str],
    batch_size: int
) -> np.ndarray:
    """
    返回 embeddings: (n, d) float32 numpy
    """
    if not texts:
        return np.zeros((0, 0), dtype=np.float32)

    emb = model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=False,
        convert_to_numpy=True,
        normalize_embeddings=False,  # 我们自己做归一化，便于控制/兼容
    )
    if not isinstance(emb, np.ndarray):
        emb = np.array(emb)
    return emb.astype(np.float32, copy=False)


def best_matches_cosine(
    query_emb_norm: np.ndarray,   # (m, d) 已归一化
    old_emb_norm: np.ndarray      # (n, d) 已归一化
) -> Tuple[np.ndarray, np.ndarray]:
    """
    计算 cosine similarity：sim = Q @ O.T
    返回：
    - best_idx: (m,) 每个 query 最优 old 的索引
    - best_sim: (m,) 每个 query 的最高相似度
    """
    if query_emb_norm.size == 0 or old_emb_norm.size == 0:
        return np.zeros((query_emb_norm.shape[0],), dtype=np.int64), np.zeros((query_emb_norm.shape[0],), dtype=np.float32)

    sims = query_emb_norm @ old_emb_norm.T  # (m, n)
    best_idx = np.argmax(sims, axis=1).astype(np.int64)
    best_sim = sims[np.arange(sims.shape[0]), best_idx].astype(np.float32)
    return best_idx, best_sim


# -------------------------
# Core
# -------------------------

def process_new_file(
    path_new: str,
    model: SentenceTransformer,
    old_keys: List[str],
    old_emb_norm: np.ndarray,
    overwrite: bool,
    dry_run: bool,
    batch_size: int
) -> Tuple[int, int]:
    new_qs = load_json_list(path_new)
    total = len(new_qs)

    # 找出需要计算的题目索引
    todo_indices: List[int] = []
    todo_texts: List[str] = []

    skipped = 0
    for i, q in enumerate(new_qs):
        if (not overwrite) and (KEY_DOUBT in q or KEY_SCORE in q):
            skipped += 1
            continue
        todo_indices.append(i)
        todo_texts.append(question_to_string_by_type(q))

    written = 0
    if not todo_indices:
        if not dry_run:
            dump_json_list(path_new, new_qs)
        return written, skipped

    # 批量编码 + 批量相似度（比逐题快很多）
    t0 = time.time()
    last_print = 0.0

    # 为了保留“逐步进度条”的手感：分 batch 做并打印
    m = len(todo_texts)
    for start in range(0, m, batch_size):
        end = min(m, start + batch_size)
        batch_texts = todo_texts[start:end]

        q_emb = embed_texts(model, batch_texts, batch_size=batch_size)
        q_emb_norm = l2_normalize(q_emb)

        best_idx, best_sim = best_matches_cosine(q_emb_norm, old_emb_norm)

        # 写回 JSON
        for j in range(end - start):
            q_i = todo_indices[start + j]
            best_old_key = old_keys[int(best_idx[j])] if old_keys else ""
            new_qs[q_i][KEY_DOUBT] = str(best_old_key)
            new_qs[q_i][KEY_SCORE] = float(best_sim[j])
            written += 1

        elapsed = time.time() - t0
        done = min(end, m)
        if elapsed - last_print >= 0.2 or done == m:
            line = progress_line(done, m, elapsed)
            print(line, end="\r" if done != m else "\n", flush=True)
            last_print = elapsed

    if not dry_run:
        dump_json_list(path_new, new_qs)

    return written, skipped


def main():
    parser = argparse.ArgumentParser(
        description="Verify new banks by Sentence-BERT (cosine similarity) against ALL old banks."
    )
    parser.add_argument(
        "--dir",
        default=r"D:\Desktop\当务之急\EAGLE\泌尿外科\泌尿外科专科出卷",
        help="题库目录（包含 bank_*.json 与 new_bank_*.json）",
    )
    parser.add_argument(
        "--model",
        default="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        help="SentenceTransformer 模型名或本地路径",
    )
    parser.add_argument(
        "--device",
        default=None,
        help='推理设备，如 "cpu" / "cuda"（默认交给 sentence-transformers 自动选择）',
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=64,
        help="编码 batch 大小（越大越快但更占显存/内存）",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help=f"覆盖已存在的 {KEY_DOUBT}/{KEY_SCORE}（默认不覆盖）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只计算不写回文件",
    )
    args = parser.parse_args()

    base_dir = args.dir
    overwrite = args.overwrite
    dry_run = args.dry_run
    batch_size = max(1, int(args.batch_size))

    print("加载旧题库（合并所有 bank_*.json）...")
    old_keys, old_texts = build_old_corpus(base_dir)
    print(f"旧题库合计题数：{len(old_keys)}")

    if not old_keys:
        print("[ERROR] 未加载到任何旧题库题目，无法匹配。", file=sys.stderr)
        sys.exit(2)

    print(f"加载 Sentence-BERT 模型：{args.model}")
    if args.device:
        model = SentenceTransformer(args.model, device=args.device)
    else:
        model = SentenceTransformer(args.model)

    print("编码旧题库向量（一次性）...")
    t0 = time.time()
    old_emb = embed_texts(model, old_texts, batch_size=batch_size)
    old_emb_norm = l2_normalize(old_emb)
    print(f"[OK] 旧题库向量维度：{old_emb_norm.shape}，耗时 {fmt_mmss(time.time() - t0)}")

    total_written = 0
    total_skipped = 0
    processed = 0

    for fn in NEW_FILES:
        path_new = os.path.join(base_dir, fn)
        if not os.path.exists(path_new):
            print(f"[WARN] 缺少新题库，跳过：{path_new}", file=sys.stderr)
            continue

        print(f"\n处理 {fn}（overwrite={overwrite}, dry_run={dry_run}, batch_size={batch_size}）")
        written, skipped = process_new_file(
            path_new,
            model=model,
            old_keys=old_keys,
            old_emb_norm=old_emb_norm,
            overwrite=overwrite,
            dry_run=dry_run,
            batch_size=batch_size,
        )
        processed += 1
        total_written += written
        total_skipped += skipped
        print(f"[OK] {fn}: 写入 {written} 题，跳过 {skipped} 题")

    print(f"\n[DONE] 文件数：{processed}；总写入：{total_written}；总跳过：{total_skipped}；dry_run={dry_run}")


if __name__ == "__main__":
    main()
