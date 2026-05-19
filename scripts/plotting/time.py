# time.py
# -*- coding: utf-8 -*-
"""
time.py
用于统计 bank_to_new_bank.py 的出题耗时（按题型/批次/单题耗时），并绘制论文风格图。

新增规则：
- 单个 batch 题数为 0/1/2/3 时，该 batch 不参与统计（直接跳过）。

统计逻辑（关键约束）：
1) 仅用 logs 文件名中的时间戳推断程序运行时间与 batch 开始时间：
   - 主日志：bank_to_new_bank_YYYYMMDD_HHMMSS.log  -> run_start
   - batch日志：{TYPE}_batch_{index:04d}_YYYYMMDD_HHMMSS.log -> batch_start
   - batch耗时 = batch_start(i) -> batch_start(i+1) 的时间差（同一题型、同一运行内、index 连续）
   - 每次运行每个题型的最后一个 batch 耗时不可知：忽略
   - 两次运行之间的停机时间不会被纳入（因为 batch 不会归属到任何 run 区间之外）

2) 从每个 batch 日志中读取 "DEEPSEEK RAW RESPONSE" 区块，统计其中“完整题目对象”的数量：
   - 优先解析到 JSON 数组 list[dict]，数量=数组长度
   - 若失败，则扫描所有闭合的 {...}，json.loads 成功且“像题目”的 dict 才计数
   - 为避免把嵌套 options 等 dict 误计为题目，做了启发式过滤（见 is_question_like）

3) 输出：
   - 每题型每 batch：batch 秒数、题目数、单题秒数（题数<=3的batch不输出）
   - 每题型：单题秒数均值、方差（并给出标准差）

4) 绘图：
   - 横轴：Question Type（A1/A2/...）
   - 纵轴：Seconds per Question
   - 柱形：均值，颜色 #EBE6DE
   - 圆点：均值±标准差，颜色 #D6CDBE
   - 4:3，Times New Roman，英文标题 Title Case
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from project_paths import FIGURE_DIR, LOG_DIR, STATISTICS_DIR


# ----------------------------
# 配置
# ----------------------------
BANK_ORDER = ["A1", "A2", "A3", "A4", "B", "X"]

# 新增：batch 最小题数阈值（<=3 的 batch 直接剔除）
MIN_QUESTIONS_PER_BATCH = 4

# 配色（按需求固定）
COL_BAR = "#EBE6DE"
COL_DOT = "#D6CDBE"


# ----------------------------
# 图形风格（Times New Roman + 论文风格）
# ----------------------------
def setup_style() -> None:
    mpl.rcParams.update({
        "font.family": "Times New Roman",
        "font.size": 11,
        "axes.titlesize": 14,
        "axes.labelsize": 12,
        "legend.fontsize": 10,
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
        "figure.dpi": 120,
        "savefig.dpi": 300,
        "axes.unicode_minus": False,
    })


def title_case(s: str) -> str:
    small = {"a", "an", "the", "and", "or", "but", "for", "nor", "as", "at", "by", "in", "of", "on", "per", "to", "vs"}
    parts = re.split(r"(\s+)", (s or "").strip())
    out: List[str] = []
    for i, w in enumerate(parts):
        if w.isspace():
            out.append(w)
            continue
        lw = w.lower()
        if i == 0 or i == len(parts) - 1:
            out.append(lw.capitalize())
        else:
            out.append(lw if lw in small else lw.capitalize())
    return "".join(out)


# ----------------------------
# 日志文件名解析
# ----------------------------
MAIN_LOG_RE = re.compile(r"^bank_to_new_bank_(\d{8})_(\d{6})\.log$", re.IGNORECASE)
BATCH_LOG_RE = re.compile(r"^(A1|A2|A3|A4|B|X)_batch_(\d{4})_(\d{8})_(\d{6})\.log$", re.IGNORECASE)


def parse_ts(date8: str, time6: str) -> datetime:
    return datetime.strptime(date8 + time6, "%Y%m%d%H%M%S")


@dataclass(frozen=True)
class RunInfo:
    start: datetime
    main_log_path: Path


@dataclass(frozen=True)
class BatchInfo:
    qtype: str
    index: int
    start: datetime
    path: Path


def list_runs(log_dir: Path) -> List[RunInfo]:
    runs: List[RunInfo] = []
    for p in log_dir.iterdir():
        if not p.is_file():
            continue
        m = MAIN_LOG_RE.match(p.name)
        if not m:
            continue
        dt = parse_ts(m.group(1), m.group(2))
        runs.append(RunInfo(start=dt, main_log_path=p))
    runs.sort(key=lambda x: x.start)
    return runs


def list_batches(log_dir: Path) -> List[BatchInfo]:
    batches: List[BatchInfo] = []
    for p in log_dir.iterdir():
        if not p.is_file():
            continue
        m = BATCH_LOG_RE.match(p.name)
        if not m:
            continue
        qtype = m.group(1).upper()
        idx = int(m.group(2))
        dt = parse_ts(m.group(3), m.group(4))
        batches.append(BatchInfo(qtype=qtype, index=idx, start=dt, path=p))
    batches.sort(key=lambda x: (x.start, x.qtype, x.index))
    return batches


def assign_batches_to_runs(runs: List[RunInfo], batches: List[BatchInfo]) -> Dict[datetime, List[BatchInfo]]:
    """
    将 batch 按时间归属到 run 区间 [run_start, next_run_start)。
    返回：{run_start: [batches...]}
    """
    out: Dict[datetime, List[BatchInfo]] = {r.start: [] for r in runs}
    if not runs:
        return out

    run_starts = [r.start for r in runs]

    def find_run_start(t: datetime) -> Optional[datetime]:
        lo, hi = 0, len(run_starts) - 1
        ans: Optional[datetime] = None
        while lo <= hi:
            mid = (lo + hi) // 2
            if run_starts[mid] <= t:
                ans = run_starts[mid]
                lo = mid + 1
            else:
                hi = mid - 1
        return ans

    run_end: Dict[datetime, Optional[datetime]] = {}
    for i, r in enumerate(runs):
        run_end[r.start] = runs[i + 1].start if i + 1 < len(runs) else None

    for b in batches:
        rs = find_run_start(b.start)
        if rs is None:
            continue
        re_ = run_end.get(rs)
        if re_ is not None and not (rs <= b.start < re_):
            continue
        out[rs].append(b)

    for rs in list(out.keys()):
        out[rs].sort(key=lambda x: (x.qtype, x.index, x.start))
    return out


# ----------------------------
# 从 batch 日志中提取 DeepSeek response 文本
# ----------------------------
RAW_BLOCK_TITLE = "DEEPSEEK RAW RESPONSE"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def extract_block_content(log_text: str, title: str) -> str:
    """
    解析 log_block 写入的格式：
        ================================================================================
        TITLE
        --------------------------------------------------------------------------------
        content...
        ================================================================================
    返回 title 对应的 content（找不到则返回空串）
    """
    s = log_text or ""
    pattern = re.compile(
        r"={80}\s*\n" + re.escape(title) + r"\s*\n-{80}\s*\n([\s\S]*?)\n={80}",
        re.MULTILINE
    )
    m = pattern.search(s)
    if not m:
        return ""
    return (m.group(1) or "").strip("\n")


# ----------------------------
# JSON 数组解析 + “题目对象”打捞（避免嵌套 options 误计）
# ----------------------------
_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```", re.IGNORECASE)


def extract_first_json_array_robust(text: str) -> Optional[List[Dict[str, Any]]]:
    text = (text or "").strip()
    if not text:
        return None

    m = _JSON_FENCE_RE.search(text)
    if m:
        cand = m.group(1).strip()
        try:
            obj = json.loads(cand)
        except Exception:
            return None
        if isinstance(obj, list) and all(isinstance(x, dict) for x in obj):
            return obj
        return None

    idx = text.find("[")
    if idx == -1:
        return None

    depth = 0
    in_str = False
    escape = False
    start: Optional[int] = None

    for i in range(idx, len(text)):
        ch = text[i]
        if in_str:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_str = False
            continue

        if ch == '"':
            in_str = True
            continue

        if ch == "[":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0 and start is not None:
                cand = text[start:i + 1]
                try:
                    obj = json.loads(cand)
                except Exception:
                    return None
                if isinstance(obj, list) and all(isinstance(x, dict) for x in obj):
                    return obj
                return None

    last = text.rfind("]")
    if last != -1 and start is not None and last > start:
        cand = text[start:last + 1]
        try:
            obj = json.loads(cand)
        except Exception:
            return None
        if isinstance(obj, list) and all(isinstance(x, dict) for x in obj):
            return obj

    return None


def iter_json_object_candidates(text: str) -> List[str]:
    s = text or ""
    out: List[str] = []

    depth = 0
    in_str = False
    escape = False
    start: Optional[int] = None

    for i, ch in enumerate(s):
        if in_str:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_str = False
            continue

        if ch == '"':
            in_str = True
            continue

        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            if depth > 0:
                depth -= 1
                if depth == 0 and start is not None:
                    out.append(s[start:i + 1])
                    start = None

    return out


def is_option_dict(d: Dict[str, Any]) -> bool:
    keys = set(str(k).strip() for k in d.keys())
    if not keys:
        return False
    option_like = set("ABCDE") | {"A", "B", "C", "D", "E"}
    digit_like = {"1", "2", "3", "4", "5", "6", "7", "8", "9"}
    if keys.issubset(option_like) and len(keys) >= 3:
        return True
    if keys.issubset(digit_like) and len(keys) >= 3:
        return True
    return False


def is_question_like(d: Dict[str, Any]) -> bool:
    if not isinstance(d, dict):
        return False
    if is_option_dict(d):
        return False

    keys = set(str(k) for k in d.keys())
    hint_keys = {
        "stem", "case",
        "stem1", "stem2", "stem3",
        "options", "options1", "options2", "options3",
        "answer", "analysis", "explanation",
        "question", "prompt",
    }
    if keys & hint_keys:
        return True

    if len(keys) >= 4:
        long_text_fields = 0
        for v in d.values():
            if isinstance(v, str) and len(v.strip()) >= 20:
                long_text_fields += 1
        if long_text_fields >= 1:
            return True

    return False


def stable_dumps_without_id_type(obj: Dict[str, Any]) -> str:
    tmp = dict(obj)
    tmp.pop("id", None)
    tmp.pop("type", None)
    return json.dumps(tmp, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def count_questions_in_response(raw_text: str) -> int:
    arr = extract_first_json_array_robust(raw_text)
    if arr is not None:
        return len(arr)

    objs: List[Dict[str, Any]] = []
    for cand in iter_json_object_candidates(raw_text):
        try:
            o = json.loads(cand)
        except Exception:
            continue
        if isinstance(o, dict) and is_question_like(o):
            objs.append(o)

    seen = set()
    cnt = 0
    for o in objs:
        k = stable_dumps_without_id_type(o)
        if k in seen:
            continue
        seen.add(k)
        cnt += 1
    return cnt


# ----------------------------
# 耗时计算
# ----------------------------
@dataclass
class BatchTiming:
    run_start: datetime
    qtype: str
    batch_index: int
    batch_start: datetime
    next_batch_start: datetime
    batch_seconds: float
    question_count: int
    seconds_per_question: float


def compute_timings(
    runs: List[RunInfo],
    batches_by_run: Dict[datetime, List[BatchInfo]],
) -> List[BatchTiming]:
    """
    计算每个“可确定耗时”的 batch：
      - 同一 run 内
      - 同一 qtype 内
      - batch_index 连续 (i -> i+1)
      - 耗时 = start(i+1) - start(i)
      - question_count 从 batch(i) 日志内容统计
      - 题数 <= 3 的 batch 直接剔除
    """
    results: List[BatchTiming] = []
    if not runs:
        return results

    for r in runs:
        blist = batches_by_run.get(r.start, [])
        if not blist:
            continue

        by_type: Dict[str, List[BatchInfo]] = {}
        for b in blist:
            by_type.setdefault(b.qtype, []).append(b)
        for qt in list(by_type.keys()):
            by_type[qt].sort(key=lambda x: (x.index, x.start))

        for qt, q_batches in by_type.items():
            for i in range(len(q_batches) - 1):
                cur = q_batches[i]
                nxt = q_batches[i + 1]

                # index 必须连续，否则该 batch 耗时不可知
                if nxt.index != cur.index + 1:
                    continue

                dt = (nxt.start - cur.start).total_seconds()
                if dt <= 0:
                    continue

                txt = read_text(cur.path)
                raw = extract_block_content(txt, RAW_BLOCK_TITLE)
                qn = count_questions_in_response(raw)

                # 新增规则：题数 0/1/2/3 的 batch 不参与统计
                if qn < MIN_QUESTIONS_PER_BATCH:
                    continue

                spq = dt / qn
                results.append(BatchTiming(
                    run_start=r.start,
                    qtype=qt,
                    batch_index=cur.index,
                    batch_start=cur.start,
                    next_batch_start=nxt.start,
                    batch_seconds=float(dt),
                    question_count=int(qn),
                    seconds_per_question=float(spq),
                ))

    return results


def mean_var(xs: List[float]) -> Tuple[float, float]:
    if not xs:
        return float("nan"), float("nan")
    arr = np.array(xs, dtype=float)
    mu = float(np.mean(arr))
    var = float(np.var(arr))  # 总体方差
    return mu, var


# ----------------------------
# 绘图
# ----------------------------
def plot_per_type_stats(
    per_type_values: Dict[str, List[float]],
    out_path: Path,
) -> None:
    setup_style()

    types = [t for t in BANK_ORDER if t in per_type_values and len(per_type_values[t]) > 0]
    if not types:
        raise RuntimeError("No valid timing data to plot.")

    means: List[float] = []
    stds: List[float] = []

    for t in types:
        arr = np.array(per_type_values[t], dtype=float)
        means.append(float(np.mean(arr)))
        stds.append(float(np.std(arr)))  # 总体标准差

    x = np.arange(len(types), dtype=float)

    fig, ax = plt.subplots(figsize=(8, 6))  # 4:3
    ax.bar(x, means, color=COL_BAR, edgecolor="white", linewidth=0.8)

    for xi, mu, sd in zip(x, means, stds):
        ax.scatter([xi, xi], [mu - sd, mu + sd], c=COL_DOT, s=28, zorder=3)

    ax.set_xticks(x)
    ax.set_xticklabels(types)
    ax.set_xlabel("Question Type")
    ax.set_ylabel("Seconds per Question")
    ax.set_title(title_case("Per-Question Time by Question Type"))
    ax.grid(axis="y", alpha=0.25, linestyle="--", linewidth=0.7)

    fig.tight_layout()
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)


# ----------------------------
# CLI & 主流程
# ----------------------------
def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Compute per-question generation time from logs and plot stats.")
    p.add_argument("--logs_dir", type=str, default=str(LOG_DIR), help="Directory containing log files.")
    p.add_argument("--output_png", type=str, default=str(FIGURE_DIR / "time_per_question.png"), help="Output figure path (.png).")
    p.add_argument("--output_json", type=str, default=str(STATISTICS_DIR / "time_stats.json"), help="Output stats JSON path.")
    p.add_argument("--print_batches", action="store_true", help="Print per-batch details to stdout.")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    log_dir = Path(args.logs_dir)
    if not log_dir.exists():
        raise FileNotFoundError(f"logs_dir not found: {log_dir}")

    runs = list_runs(log_dir)
    batches = list_batches(log_dir)
    batches_by_run = assign_batches_to_runs(runs, batches)

    timings = compute_timings(runs, batches_by_run)

    per_type: Dict[str, List[float]] = {t: [] for t in BANK_ORDER}
    per_type_batches: Dict[str, List[Dict[str, Any]]] = {t: [] for t in BANK_ORDER}

    for bt in timings:
        per_type.setdefault(bt.qtype, []).append(bt.seconds_per_question)
        per_type_batches.setdefault(bt.qtype, []).append({
            "run_start": bt.run_start.strftime("%Y-%m-%d %H:%M:%S"),
            "type": bt.qtype,
            "batch_index": bt.batch_index,
            "batch_start": bt.batch_start.strftime("%Y-%m-%d %H:%M:%S"),
            "next_batch_start": bt.next_batch_start.strftime("%Y-%m-%d %H:%M:%S"),
            "batch_seconds": bt.batch_seconds,
            "question_count": bt.question_count,
            "seconds_per_question": bt.seconds_per_question,
        })

    stats: Dict[str, Any] = {
        "meta": {
            "logs_dir": str(log_dir.resolve()),
            "run_count": len(runs),
            "batch_log_count": len(batches),
            "usable_batch_count": len(timings),
            "min_questions_per_batch_included": MIN_QUESTIONS_PER_BATCH,
            "note": "Batches with question_count <= 3 are excluded from statistics.",
        },
        "per_type": {},
        "per_batch": per_type_batches,
    }

    for t in BANK_ORDER:
        xs = per_type.get(t, [])
        mu, var = mean_var(xs)
        stats["per_type"][t] = {
            "n_batches_usable": len(xs),
            "mean_seconds_per_question": mu,
            "var_seconds_per_question": var,
            "std_seconds_per_question": (math.sqrt(var) if np.isfinite(var) and var >= 0 else float("nan")),
        }

    if args.print_batches:
        for t in BANK_ORDER:
            rows = per_type_batches.get(t, [])
            if not rows:
                continue
            print(f"\n== {t} ==")
            for r in rows:
                print(
                    f"batch={r['batch_index']:04d}  "
                    f"batch_s={r['batch_seconds']:.2f}  "
                    f"q={r['question_count']}  "
                    f"sec/q={r['seconds_per_question']:.4f}"
                )

        print("\n== Per-Type Summary ==")
        for t in BANK_ORDER:
            st = stats["per_type"][t]
            if st["n_batches_usable"] == 0:
                continue
            print(
                f"{t}: n={st['n_batches_usable']}  "
                f"mean={st['mean_seconds_per_question']:.4f}  "
                f"var={st['var_seconds_per_question']:.6f}  "
                f"std={st['std_seconds_per_question']:.4f}"
            )

    out_json = Path(args.output_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")

    out_png = Path(args.output_png)
    out_png.parent.mkdir(parents=True, exist_ok=True)
    plot_per_type_stats(per_type, out_png)


if __name__ == "__main__":
    main()
