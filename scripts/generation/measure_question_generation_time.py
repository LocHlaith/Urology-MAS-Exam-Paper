"""统计 MAS 出题耗时。

脚本用途：按题型重复生成若干 batch 新题，并统计单题出题耗时。
流程阶段：MAS 出题效率统计。
主要输入：`scripts/generation/bank_to_new_bank.py`、`add_answer_explanation.py`、`add_test_point.py`。
主要输出：`plot/agent_readable/derived_data/mas_question_generation_time.csv` 与运行明细 CSV。
重要边界：只计入出题、答案解析、考点还原三个脚本；临时题库写入 timing_runs，不覆盖正式 new_bank。
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from project_paths import BANK_FILE_STEMS, PROJECT_ROOT


# ===== 路径与常量 =====

GENERATION_SCRIPT_DIR = PROJECT_ROOT / "scripts" / "generation"
BANK_TO_NEW_BANK_SCRIPT = GENERATION_SCRIPT_DIR / "bank_to_new_bank.py"
ADD_ANSWER_EXPLANATION_SCRIPT = GENERATION_SCRIPT_DIR / "add_answer_explanation.py"
ADD_TEST_POINT_SCRIPT = GENERATION_SCRIPT_DIR / "add_test_point.py"

PLOT_DERIVED_DATA_DIR = PROJECT_ROOT / "plot" / "agent_readable" / "derived_data"
DEFAULT_SUMMARY_CSV = PLOT_DERIVED_DATA_DIR / "mas_question_generation_time.csv"
DEFAULT_WORK_ROOT = PROJECT_ROOT / "timing_runs"

BANK_ORDER = ["A1", "A2", "A3", "A4", "B", "X"]

# 与 bank_to_new_bank.py 保持一致，用于记录期望输入规模。
GENERATION_BATCH_SIZES = {
    "A1": 20,
    "A2": 10,
    "A3": 10,
    "A4": 10,
    "B": 10,
    "X": 20,
}

SUMMARY_FIELDS = [
    "run_id",
    "bank_type",
    "batches_requested",
    "bank_to_new_bank_invocations",
    "bank_to_new_bank_batches_with_items",
    "expected_source_items",
    "generated_items",
    "bank_to_new_bank_seconds",
    "add_answer_explanation_seconds",
    "add_test_point_seconds",
    "total_generation_seconds",
    "seconds_per_item",
    "minutes_per_item",
    "temp_new_bank_path",
    "time_source",
    "time_granularity",
    "status",
    "completed_at",
]

DETAIL_FIELDS = [
    "run_id",
    "bank_type",
    "phase",
    "source_batch",
    "started_at",
    "finished_at",
    "elapsed_seconds",
    "returncode",
    "items_before",
    "items_after",
    "items_delta",
    "log_path",
    "command",
]


# ===== 通用工具 =====

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="统计各题型 MAS 出题单题耗时。")
    p.add_argument(
        "--banks",
        type=str,
        default="all",
        help="题型，可写为 'A1 A3 B'、'A1,A3,B' 或 'all'。默认 all。",
    )
    p.add_argument(
        "--batches_per_type",
        "--batches-per-type",
        type=int,
        default=5,
        help="每个题型调用 bank_to_new_bank.py 的次数，也就是生成 batch 数。默认 5。",
    )
    p.add_argument(
        "--work_dir",
        "--work-dir",
        type=str,
        default="",
        help="临时运行目录；留空时使用 timing_runs/<timestamp>。",
    )
    p.add_argument(
        "--summary_csv",
        "--summary-csv",
        type=str,
        default=str(DEFAULT_SUMMARY_CSV),
        help="绘图用汇总 CSV 输出路径。",
    )
    p.add_argument(
        "--detail_csv",
        "--detail-csv",
        type=str,
        default="",
        help="子进程调用明细 CSV；留空时写入 work_dir。",
    )
    p.add_argument(
        "--sleep",
        type=float,
        default=0.0,
        help="传给三个生成脚本的 batch 间等待秒数。默认 0，避免人为等待影响耗时。",
    )
    p.add_argument(
        "--timeout",
        type=int,
        default=0,
        help="单次脚本调用超时秒数；0 表示不设超时。",
    )
    p.add_argument(
        "--keep_user_prompt_logs",
        "--keep-user-prompt-logs",
        action="store_true",
        help="保留每个 batch 的 user prompt 日志；默认关闭以减少日志体积。",
    )
    p.add_argument(
        "--allow_b_two_explanations",
        "--allow-b-two-explanations",
        action="store_true",
        help="传给 add_answer_explanation.py：允许 B 型题已有 analysis1/analysis2 时不补 analysis3。",
    )
    p.add_argument(
        "--continue_on_error",
        "--continue-on-error",
        action="store_true",
        help="某题型调用失败时继续统计后续题型。",
    )
    return p.parse_args()


def split_bank_tokens(s: str) -> List[str]:
    s = (s or "").strip()
    if not s or s.lower() == "all":
        return BANK_ORDER[:]
    parts = re.split(r"[,\s，;；|/]+", s)
    selected = [p.strip().upper() for p in parts if p.strip()]
    return [t for t in BANK_ORDER if t in selected]


def bank_file_path(bank_dir: Path, bank_type: str) -> Path:
    return bank_dir / f"new_bank_{BANK_FILE_STEMS[bank_type]}.json"


def count_bank_items(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError(f"临时题库 JSON 顶层不是 list: {path}")
    return len(data)


def format_seconds(value: float) -> str:
    return f"{value:.6f}"


def write_csv(path: Path, rows: List[Dict[str, object]], fieldnames: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})


def command_to_text(command: Sequence[str]) -> str:
    if os.name == "nt":
        return subprocess.list2cmdline(list(command))
    return " ".join(command)


def build_env() -> Dict[str, str]:
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    return env


def as_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def run_command(
    command: Sequence[str],
    log_path: Path,
    timeout_s: Optional[int],
) -> Tuple[int, float, str, str, str, str]:
    started_at = datetime.now().isoformat(timespec="seconds")
    t0 = time.perf_counter()
    timed_out = False
    try:
        proc = subprocess.run(
            list(command),
            cwd=str(PROJECT_ROOT),
            env=build_env(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_s,
        )
        returncode = proc.returncode
        stdout = proc.stdout
        stderr = proc.stderr
    except subprocess.TimeoutExpired as e:
        timed_out = True
        returncode = -1
        stdout = as_text(e.stdout)
        stderr = as_text(e.stderr)

    elapsed = time.perf_counter() - t0
    finished_at = datetime.now().isoformat(timespec="seconds")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8") as f:
        f.write(f"COMMAND: {command_to_text(command)}\n")
        f.write(f"STARTED_AT: {started_at}\n")
        f.write(f"FINISHED_AT: {finished_at}\n")
        f.write(f"ELAPSED_SECONDS: {format_seconds(elapsed)}\n")
        f.write(f"RETURNCODE: {returncode}\n")
        f.write(f"TIMED_OUT: {int(timed_out)}\n\n")
        f.write("STDOUT\n")
        f.write(stdout)
        f.write("\n\nSTDERR\n")
        f.write(stderr)

    return returncode, elapsed, started_at, finished_at, str(log_path), command_to_text(command)


def append_detail_row(
    detail_rows: List[Dict[str, object]],
    run_id: str,
    bank_type: str,
    phase: str,
    source_batch: object,
    timing: Tuple[int, float, str, str, str, str],
    items_before: int,
    items_after: int,
) -> None:
    returncode, elapsed, started_at, finished_at, log_path, command_text = timing
    detail_rows.append(
        {
            "run_id": run_id,
            "bank_type": bank_type,
            "phase": phase,
            "source_batch": source_batch,
            "started_at": started_at,
            "finished_at": finished_at,
            "elapsed_seconds": format_seconds(elapsed),
            "returncode": returncode,
            "items_before": items_before,
            "items_after": items_after,
            "items_delta": items_after - items_before,
            "log_path": log_path,
            "command": command_text,
        }
    )


# ===== 命令构造 =====

def common_generation_args(bank_type: str, bank_dir: Path, args: argparse.Namespace) -> List[str]:
    common = [
        "--banks",
        bank_type,
        "--new-bank-dir",
        str(bank_dir),
        "--sleep",
        str(max(float(args.sleep), 0.0)),
    ]
    if not args.keep_user_prompt_logs:
        common.append("--no_log_user_prompt")
    return common


def bank_to_new_bank_command(bank_type: str, bank_dir: Path, source_batch: int, args: argparse.Namespace) -> List[str]:
    return [
        sys.executable,
        str(BANK_TO_NEW_BANK_SCRIPT),
        *common_generation_args(bank_type, bank_dir, args),
        "--start-batches",
        str(source_batch),
        "--max-batches",
        "1",
    ]


def add_answer_explanation_command(bank_type: str, bank_dir: Path, args: argparse.Namespace) -> List[str]:
    command = [
        sys.executable,
        str(ADD_ANSWER_EXPLANATION_SCRIPT),
        *common_generation_args(bank_type, bank_dir, args),
        "--start-batches",
        "1",
    ]
    if args.allow_b_two_explanations:
        command.append("--allow-b-two-explanations")
    return command


def add_test_point_command(bank_type: str, bank_dir: Path, args: argparse.Namespace) -> List[str]:
    return [
        sys.executable,
        str(ADD_TEST_POINT_SCRIPT),
        *common_generation_args(bank_type, bank_dir, args),
        "--start-batches",
        "1",
    ]


# ===== 统计流程 =====

def ensure_clean_temp_banks(bank_dir: Path, targets: List[str]) -> None:
    existing = [bank_file_path(bank_dir, t) for t in targets if bank_file_path(bank_dir, t).exists()]
    if existing:
        lines = "\n".join(str(p) for p in existing)
        raise FileExistsError(
            "临时题库文件已存在。为避免混入旧统计结果，请换一个 --work-dir 后再运行：\n" + lines
        )


def run_one_bank_type(
    bank_type: str,
    run_id: str,
    bank_dir: Path,
    log_dir: Path,
    args: argparse.Namespace,
    detail_rows: List[Dict[str, object]],
) -> Dict[str, object]:
    temp_bank_path = bank_file_path(bank_dir, bank_type)
    timeout_s = int(args.timeout) if int(args.timeout) > 0 else None
    batches_requested = int(args.batches_per_type)

    print(f"[INFO] {bank_type}: 调用 bank_to_new_bank.py {batches_requested} 次")

    bank_generation_seconds = 0.0
    bank_invocations = 0
    bank_batches_with_items = 0
    phase_returncodes: List[int] = []

    for source_batch in range(1, batches_requested + 1):
        before = count_bank_items(temp_bank_path)
        command = bank_to_new_bank_command(bank_type, bank_dir, source_batch, args)
        log_path = log_dir / f"{bank_type}_bank_to_new_bank_batch_{source_batch:02d}.log"
        timing = run_command(command, log_path, timeout_s)
        after = count_bank_items(temp_bank_path)

        bank_invocations += 1
        bank_generation_seconds += timing[1]
        phase_returncodes.append(timing[0])
        if after > before:
            bank_batches_with_items += 1

        append_detail_row(
            detail_rows,
            run_id,
            bank_type,
            "bank_to_new_bank",
            source_batch,
            timing,
            before,
            after,
        )

        if timing[0] != 0 and not args.continue_on_error:
            raise RuntimeError(f"{bank_type} 第 {source_batch} 次 bank_to_new_bank.py 调用失败，详见 {log_path}")

    generated_items = count_bank_items(temp_bank_path)
    add_answer_seconds = 0.0
    add_test_point_seconds = 0.0

    if generated_items > 0:
        print(f"[INFO] {bank_type}: 生成 {generated_items} 题，开始补答案解析")
        before = count_bank_items(temp_bank_path)
        timing = run_command(
            add_answer_explanation_command(bank_type, bank_dir, args),
            log_dir / f"{bank_type}_add_answer_explanation.log",
            timeout_s,
        )
        after = count_bank_items(temp_bank_path)
        add_answer_seconds = timing[1]
        phase_returncodes.append(timing[0])
        append_detail_row(
            detail_rows,
            run_id,
            bank_type,
            "add_answer_explanation",
            "",
            timing,
            before,
            after,
        )
        if timing[0] != 0 and not args.continue_on_error:
            raise RuntimeError(f"{bank_type} add_answer_explanation.py 调用失败，详见 {timing[4]}")

        print(f"[INFO] {bank_type}: 开始补考点还原")
        before = count_bank_items(temp_bank_path)
        timing = run_command(
            add_test_point_command(bank_type, bank_dir, args),
            log_dir / f"{bank_type}_add_test_point.log",
            timeout_s,
        )
        after = count_bank_items(temp_bank_path)
        add_test_point_seconds = timing[1]
        phase_returncodes.append(timing[0])
        append_detail_row(
            detail_rows,
            run_id,
            bank_type,
            "add_test_point",
            "",
            timing,
            before,
            after,
        )
        if timing[0] != 0 and not args.continue_on_error:
            raise RuntimeError(f"{bank_type} add_test_point.py 调用失败，详见 {timing[4]}")
    else:
        print(f"[WARN] {bank_type}: 未生成题目，跳过答案解析和考点还原")

    total_seconds = bank_generation_seconds + add_answer_seconds + add_test_point_seconds
    seconds_per_item = total_seconds / generated_items if generated_items else None

    if generated_items == 0:
        status = "no_items_generated"
    elif any(code != 0 for code in phase_returncodes):
        status = "completed_with_subprocess_errors"
    else:
        status = "completed"

    return {
        "run_id": run_id,
        "bank_type": bank_type,
        "batches_requested": batches_requested,
        "bank_to_new_bank_invocations": bank_invocations,
        "bank_to_new_bank_batches_with_items": bank_batches_with_items,
        "expected_source_items": GENERATION_BATCH_SIZES[bank_type] * batches_requested,
        "generated_items": generated_items,
        "bank_to_new_bank_seconds": format_seconds(bank_generation_seconds),
        "add_answer_explanation_seconds": format_seconds(add_answer_seconds),
        "add_test_point_seconds": format_seconds(add_test_point_seconds),
        "total_generation_seconds": format_seconds(total_seconds),
        "seconds_per_item": format_seconds(seconds_per_item) if seconds_per_item is not None else "",
        "minutes_per_item": format_seconds(seconds_per_item / 60.0) if seconds_per_item is not None else "",
        "temp_new_bank_path": str(temp_bank_path),
        "time_source": "script_wall_clock",
        "time_granularity": "question_type",
        "status": status,
        "completed_at": datetime.now().isoformat(timespec="seconds"),
    }


def main() -> None:
    args = parse_args()
    targets = split_bank_tokens(args.banks)
    if not targets:
        raise ValueError("未选择任何有效题型。")
    if int(args.batches_per_type) < 1:
        raise ValueError("--batches-per-type 必须 >= 1。")

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    work_dir = Path(args.work_dir) if args.work_dir else DEFAULT_WORK_ROOT / run_id
    work_dir = work_dir.resolve()
    bank_dir = work_dir / "banks"
    log_dir = work_dir / "subprocess_logs"
    summary_csv = Path(args.summary_csv).resolve()
    detail_csv = Path(args.detail_csv).resolve() if args.detail_csv else work_dir / "mas_question_generation_time_invocations.csv"

    bank_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)
    os.environ["UROLOGY_MAS_LOG_DIR"] = str(work_dir / "generation_script_logs")
    ensure_clean_temp_banks(bank_dir, targets)

    print(f"[INFO] run_id={run_id}")
    print(f"[INFO] 临时题库目录：{bank_dir}")
    print(f"[INFO] 汇总 CSV：{summary_csv}")
    print(f"[INFO] 明细 CSV：{detail_csv}")
    print(f"[INFO] 生成脚本内部日志目录：{os.environ['UROLOGY_MAS_LOG_DIR']}")

    summary_rows: List[Dict[str, object]] = []
    detail_rows: List[Dict[str, object]] = []

    for bank_type in targets:
        try:
            row = run_one_bank_type(bank_type, run_id, bank_dir, log_dir, args, detail_rows)
            summary_rows.append(row)
        except Exception as e:
            summary_rows.append(
                {
                    "run_id": run_id,
                    "bank_type": bank_type,
                    "batches_requested": int(args.batches_per_type),
                    "status": f"failed: {type(e).__name__}: {e}",
                    "completed_at": datetime.now().isoformat(timespec="seconds"),
                }
            )
            write_csv(summary_csv, summary_rows, SUMMARY_FIELDS)
            write_csv(detail_csv, detail_rows, DETAIL_FIELDS)
            if not args.continue_on_error:
                raise
        write_csv(summary_csv, summary_rows, SUMMARY_FIELDS)
        write_csv(detail_csv, detail_rows, DETAIL_FIELDS)

    print(f"[OK] 已写入汇总 CSV：{summary_csv}")
    print(f"[OK] 已写入明细 CSV：{detail_csv}")


if __name__ == "__main__":
    main()
