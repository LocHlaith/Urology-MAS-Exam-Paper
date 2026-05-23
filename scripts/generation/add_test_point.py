"""为 MAS 题库补充“考点还原”字段。

脚本用途：把 MAS 题库题目映射到预设考点编号。
流程阶段：MAS 题库生成后的内容补全。
主要输入：`data/banks/new_bank_*.json` 与 `prompts/generation/prompt_for_test_point.txt`。
主要输出：原地更新的 `data/banks/new_bank_*.json`，写入 `test_point` 字段。
重要边界：`test_point` 的中文含义统一为“考点还原”；本脚本不评价题库质量。
"""

import os
import json
import time
import re
import traceback
import argparse
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import requests
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from deepseek_env import load_dotenv
from project_paths import (
    ENV_PATH,
    GENERATION_PROMPT_DIR,
    LOG_DIR as PROJECT_LOG_DIR,
    PROJECT_ROOT,
    mas_bank_files,
    mas_bank_files_in_dir,
    runtime_log_dir,
)


# ===== 路径与常量 =====

ROOT = str(PROJECT_ROOT)

NEW_BANK_FILES = mas_bank_files()


def set_new_bank_dir(new_bank_dir: str) -> None:
    """临时改写 MAS 题库读写目录，用于统计或试跑时保护正式 new_bank。"""
    global NEW_BANK_FILES
    if not new_bank_dir:
        return
    bank_dir = Path(new_bank_dir)
    bank_dir.mkdir(parents=True, exist_ok=True)
    NEW_BANK_FILES = mas_bank_files_in_dir(bank_dir)

# 考点还原 prompt 统一使用一个文件。
PROMPT_FILE = str(GENERATION_PROMPT_DIR / "prompt_for_test_point.txt")

BANK_ORDER = ["A1", "A2", "A3", "A4", "B", "X"]

# 各题型每个 batch 的题目数量。
BATCH_SIZES = {
    "A1": 100,
    "A2": 100,
    "A3": 50,
    "A4": 30,
    "B":  30,
    "X":  100,
}

# 生成考点还原时不上传的派生评价字段；答案解析字段也不上传。
STRIP_FIELDS = {
    "prototype",
    "fuzzywuzzy_doubt",
    "fuzzywuzzy_ratio_max",
    "sentencebert_doubt",
    "sentencebert_cosine_max",
    "3gram_doubt",
    "3gram_jaccard_max",
    "textstat_flesch_reading_ease",
    "analysis", "analysis1", "analysis2", "analysis3"
}


# ===== 日志 =====

LOG_DIR = str(runtime_log_dir())

MAIN_LOG_PATH = os.path.join(
    LOG_DIR,
    f"test_point_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
)

def _write_line(path: str, msg: str) -> None:
    with open(path, "a", encoding="utf-8") as f:
        f.write(msg + "\n")

def log_line(msg: str) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    _write_line(MAIN_LOG_PATH, line)

def log_block(path: str, title: str, content: str) -> None:
    _write_line(path, "")
    _write_line(path, "=" * 80)
    _write_line(path, title.strip())
    _write_line(path, "-" * 80)
    _write_line(path, (content or "").rstrip())
    _write_line(path, "=" * 80)
    _write_line(path, "")

def make_batch_log_path(target_type: str, batch_index: int) -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return os.path.join(LOG_DIR, f"test_point_{target_type}_batch_{batch_index:04d}_{ts}.log")


# ===== 文件读写 =====

def read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def read_json_list(path: str) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError(f"JSON 顶层必须是 list: {path}")
    for i, item in enumerate(data):
        if not isinstance(item, dict):
            raise ValueError(f"{path} 第 {i} 项不是 dict")
    return data

def write_json_list(path: str, data: List[Dict[str, Any]]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


# ===== DeepSeek API 客户端 =====

class DeepSeekClient:
    """DeepSeek API 的 OpenAI-style Chat Completions 客户端。"""

    def __init__(self, api_key: str, base_url: str, model: str, timeout: int = 180):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def chat(self, system_prompt: str, user_prompt: str, temperature: float = 0.1) -> str:
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
        }
        resp = requests.post(url, headers=headers, json=payload, timeout=self.timeout)
        if resp.status_code >= 400:
            raise RuntimeError(f"DeepSeek API HTTP {resp.status_code}: {resp.text[:2000]}")
        obj = resp.json()
        try:
            return obj["choices"][0]["message"]["content"]
        except Exception:
            raise RuntimeError(f"无法从返回中提取 message.content: {json.dumps(obj, ensure_ascii=False)[:2000]}")


# ===== 模型返回解析 =====

_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```", re.IGNORECASE)

def extract_2d_json_array_robust(text: str) -> List[List[Any]]:
    """
    专门用于提取类似 [[1052, 31, 33], [1053, 25]] 的二维数组
    """
    text = (text or "").strip()
    if not text:
        raise ValueError("返回为空文本")

    # 1. 尝试从 Markdown 代码块中提取
    m = _JSON_FENCE_RE.search(text)
    if m:
        candidate = m.group(1).strip()
        try:
            return _loads_2d_array(candidate)
        except Exception:
            pass # 失败则继续尝试正则或暴力截取

    # 2. 暴力寻找最外层的 [...]
    idx = text.find("[")
    if idx == -1:
        raise ValueError("返回中未找到 JSON 数组起始符号 '['")

    depth = 0
    in_str = False
    escape = False
    start = None

    for i in range(idx, len(text)):
        ch = text[i]
        if in_str:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_str = False
        else:
            if ch == '"':
                in_str = True
            elif ch == "[":
                if depth == 0:
                    start = i
                depth += 1
            elif ch == "]":
                depth -= 1
                if depth == 0 and start is not None:
                    candidate = text[start:i + 1]
                    try:
                        return _loads_2d_array(candidate)
                    except Exception:
                        pass # 失败继续找下一个闭合

    last_close = text.rfind("]")
    if last_close != -1 and start is not None and last_close > start:
        candidate = text[start:last_close + 1]
        return _loads_2d_array(candidate)

    raise ValueError("未能从返回中截取完整二维 JSON 数组")

def _loads_2d_array(candidate: str) -> List[List[Any]]:
    data = json.loads(candidate)
    if not isinstance(data, list):
        raise ValueError("解析结果不是 list")
    for k, item in enumerate(data):
        if not isinstance(item, list):
            raise ValueError(f"第 {k} 项不是数组(list)，无法构成二维数组")
    return data


# ===== 批处理与提示词 =====

def build_batches(items: List[Dict[str, Any]], batch_size: int) -> List[List[Dict[str, Any]]]:
    batches: List[List[Dict[str, Any]]] = []
    cur: List[Dict[str, Any]] = []
    for it in items:
        cur.append(it)
        if len(cur) == batch_size:
            batches.append(cur)
            cur = []
    if cur:
        batches.append(cur)
    return batches

def strip_for_prompt(q: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(q)
    for k in STRIP_FIELDS:
        out.pop(k, None)
    return out

def make_user_prompt_json(questions: List[Dict[str, Any]]) -> str:
    payload = [strip_for_prompt(q) for q in questions]
    return json.dumps(payload, ensure_ascii=False, indent=4)


# ===== 字段规则 =====

def needs_test_point(q: Dict[str, Any]) -> bool:
    v = q.get("test_point", None)
    if v is None or v == "" or v == []:
        return True
    return False


# ===== 字段写回顺序 =====

def insert_test_point_after_type(q: Dict[str, Any], points: List[int]) -> Dict[str, Any]:
    """
    将 test_point 写入 q，并确保顺序：紧跟在 type 字段后面。
    """
    q0 = dict(q)
    out: Dict[str, Any] = {}

    for k, v in q0.items():
        # 原有 test_point 由统一写回逻辑处理，避免字段顺序漂移。
        if k == "test_point":
            continue
        
        out[k] = v
        
        # 遇到 type，立刻插入 test_point
        if k == "type":
            out["test_point"] = points

    # 兜底：如果原数据里没有 type 字段，追加到末尾。
    if "test_point" not in out:
        out["test_point"] = points

    return out


# ===== 模型结果写回映射 =====

def normalize_response_items(parsed: List[List[Any]]) -> Dict[str, List[int]]:
    """
    模型返回：[[1052, 31, 33], [1053, 25], ...]
    输出：id -> [test_point1, test_point2, ...]
    """
    out: Dict[str, List[int]] = {}

    for row in parsed:
        if len(row) >= 2:
            qid = str(row[0])
            points = []
            # 从索引 1 开始遍历所有后续元素作为考点
            for val in row[1:]:
                try:
                    points.append(int(val))
                except (ValueError, TypeError):
                    continue
            
            # 只有当成功提取到至少一个考点时，才记录
            if points:
                out[qid] = points

    return out


# ===== 主处理流程 =====

def load_existing_new_bank(path: str) -> List[Dict[str, Any]]:
    if not os.path.exists(path):
        raise FileNotFoundError(f"缺少文件: {path}")
    return read_json_list(path)

def refresh_one_type_test_point(
    target_type: str,
    client: DeepSeekClient,
    start_batch: int = 1,
    write_user_prompt_to_batch_log: bool = True,
    sleep_s: float = 0.6,
    max_batches: Optional[int] = None,
) -> None:
    in_path = NEW_BANK_FILES[target_type]
    batch_size = BATCH_SIZES[target_type]

    system_prompt = read_text(PROMPT_FILE)
    bank = load_existing_new_bank(in_path)

    # 只处理缺少考点还原的题。
    pending: List[Dict[str, Any]] = [q for q in bank if needs_test_point(q)]
    batches = build_batches(pending, batch_size=batch_size)

    log_line(
        f"\n==> 开始生成考点还原 {target_type}: batch_size={batch_size}, "
        f"总题数={len(bank)}, 待补考点还原={len(pending)}, 批次数={len(batches)}, "
        f"从第 {start_batch} 轮开始, 最多处理={max_batches or '不限'} 轮 -> {in_path}"
    )

    # 建立 id -> index（用于回写）
    id2idx: Dict[str, int] = {}
    for i, q in enumerate(bank):
        if "id" in q:
            id2idx[str(q["id"])] = i

    updated_count = 0

    attempted_batches = 0
    for bi, batch_questions in enumerate(batches, start=1):
        if bi < start_batch:
            continue
        if max_batches is not None and attempted_batches >= max_batches:
            break
        attempted_batches += 1

        batch_log_path = make_batch_log_path(target_type, bi)
        user_prompt = make_user_prompt_json(batch_questions)

        log_block(
            batch_log_path,
            title=f"BATCH START | type={target_type} | batch={bi}/{len(batches)} | user_n={len(batch_questions)}",
            content=f"prompt_path={PROMPT_FILE}\nin_path={in_path}\n",
        )
        if write_user_prompt_to_batch_log:
            log_block(batch_log_path, "USER PROMPT (JSON)", user_prompt)

        log_line(f"  - {target_type} 第 {bi}/{len(batches)} 轮：题数={len(batch_questions)}")

        try:
            # 考点还原属于结构化分类任务，temperature 设低一些。
            text = client.chat(system_prompt=system_prompt, user_prompt=user_prompt, temperature=0.1)
            log_block(batch_log_path, "DEEPSEEK RAW RESPONSE", text)

            parsed_list: List[List[Any]] = []
            array_err: Optional[str] = None
            try:
                parsed_list = extract_2d_json_array_robust(text)
            except Exception as e:
                array_err = f"{type(e).__name__}: {e}"

            if not parsed_list:
                msg = "返回中未提取到任何可解析二维数组，本 batch 写入 0"
                log_line(f"[SKIP] {target_type} 第 {bi} 轮：{msg}")
                log_block(batch_log_path, "NO USABLE ARRAY", msg + (f"\narray_parse_error={array_err}" if array_err else ""))
                if sleep_s > 0:
                    time.sleep(min(0.2, sleep_s))
                continue

            patch_map = normalize_response_items(parsed_list)

            # 回写：按 batch 中的 id 逐一写入（缺失则跳过）
            batch_updated = 0
            missing_ids: List[str] = []
            for q in batch_questions:
                qid = str(q.get("id", ""))
                if not qid or qid not in id2idx:
                    continue
                points = patch_map.get(qid)
                if points is None:
                    missing_ids.append(qid)
                    continue

                idx = id2idx[qid]
                bank[idx] = insert_test_point_after_type(bank[idx], points)
                batch_updated += 1

            write_json_list(in_path, bank)
            updated_count += batch_updated

            log_block(
                batch_log_path,
                "BATCH OK",
                content=(
                    f"parsed_array_rows={len(parsed_list)}\n"
                    f"unique_patches={len(patch_map)}\n"
                    f"batch_updated={batch_updated}\n"
                    f"missing_ids={len(missing_ids)}\n"
                    + (f"missing_id_list={missing_ids}\n" if missing_ids else "")
                    + f"total_updated_so_far={updated_count}\n"
                ),
            )
            log_line(f"[OK] {target_type} 第 {bi} 轮：更新 {batch_updated} 题考点还原，累计更新 {updated_count}")
            time.sleep(sleep_s)

        except Exception as e:
            err_text = f"{type(e).__name__}: {e}"
            log_line(f"[SKIP] {target_type} 第 {bi} 轮失败，已跳过：{err_text}")
            log_block(batch_log_path, "BATCH FAILED (SKIPPED)", err_text)
            log_block(batch_log_path, "TRACEBACK", traceback.format_exc())
            if sleep_s > 0:
                time.sleep(min(0.2, sleep_s))
            continue

    log_line(f"==> 完成 {target_type}: 本次共更新考点还原 {updated_count} 题 -> {in_path}")


# ===== 命令行入口 =====

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="为 MAS 题库补充考点还原字段。")
    p.add_argument(
        "--banks",
        type=str,
        default="",
        help="Bank types: 'A1 A3 B' or 'A1,A3,B' or 'all'."
    )
    p.add_argument(
        "--no_log_user_prompt",
        action="store_true",
        help="Do not write user prompt JSON into per-batch log files."
    )
    p.add_argument(
        "--start_batches",
        "--start-batches",
        type=str,
        default="",
        help="非交互指定每个题型从第几轮 batch 开始，如 '1' 或 '1 3 5'；留空时仍交互询问。"
    )
    p.add_argument(
        "--max_batches",
        "--max-batches",
        type=int,
        default=0,
        help="每个题型最多处理多少个 batch；0 表示不限制。"
    )
    p.add_argument(
        "--new_bank_dir",
        "--new-bank-dir",
        type=str,
        default="",
        help="临时 MAS 题库读写目录；留空时读写正式 data/banks/new_bank_*.json。"
    )
    p.add_argument(
        "--sleep",
        type=float,
        default=0.6,
        help="Sleep seconds between batches."
    )
    return p.parse_args()

def _split_bank_tokens(s: str) -> List[str]:
    s = (s or "").strip()
    if not s:
        return []
    parts = re.split(r"[,\s，;；|/]+", s)
    return [p.strip().upper() for p in parts if p.strip()]

def select_banks_from_args(arg_banks: str) -> List[str]:
    s = (arg_banks or "").strip()
    if not s:
        return []
    if s.lower() == "all":
        return BANK_ORDER[:]
    chosen = _split_bank_tokens(s)
    return [x for x in chosen if x in BANK_ORDER]

def select_banks_interactive() -> List[str]:
    log_line("请选择要生成考点还原的题库（如：A4 B X 或 A4,B,X 或 all）：")
    s = input("> ").strip()
    if not s:
        return []
    if s.lower() == "all":
        return BANK_ORDER[:]
    chosen = _split_bank_tokens(s)
    return [x for x in chosen if x in BANK_ORDER]

def ask_start_batches(targets: List[str]) -> Dict[str, int]:
    if not targets:
        return {}
    log_line("请依次输入每个题型从第几轮(batch)开始（空格分隔）。")
    log_line(f"题型顺序：{' '.join(targets)}")
    log_line("例如：1 1 3")
    raw = input("> ").strip()
    nums = re.split(r"[\s,，;；|/]+", raw) if raw else []
    nums = [x for x in nums if x]

    if len(nums) != len(targets):
        raise ValueError(f"输入数量不匹配：期望 {len(targets)} 个数字，对应 {targets}，实际 {len(nums)} 个：{nums}")

    out: Dict[str, int] = {}
    for t, n in zip(targets, nums):
        v = int(n)
        if v < 1:
            raise ValueError(f"{t} 的开始轮次必须 >= 1，收到：{v}")
        out[t] = v
    return out


def parse_start_batches_arg(targets: List[str], raw: str) -> Dict[str, int]:
    nums = re.split(r"[\s,，;；|/]+", (raw or "").strip()) if raw else []
    nums = [x for x in nums if x]
    if not nums:
        return {}
    if len(nums) == 1 and len(targets) > 1:
        nums = nums * len(targets)
    if len(nums) != len(targets):
        raise ValueError(f"开始轮次数量不匹配：期望 {len(targets)} 个，实际 {len(nums)} 个：{nums}")

    out: Dict[str, int] = {}
    for t, n in zip(targets, nums):
        v = int(n)
        if v < 1:
            raise ValueError(f"{t} 的开始轮次必须 >= 1，收到：{v}")
        out[t] = v
    return out


def main() -> None:
    log_line(f"主日志文件：{MAIN_LOG_PATH}")
    args = parse_args()
    if args.new_bank_dir:
        set_new_bank_dir(args.new_bank_dir)
        log_line(f"[OK] 临时 MAS 题库读写目录：{Path(args.new_bank_dir).resolve()}")

    # 加载环境变量。
    env_path = str(ENV_PATH)
    try:
        if os.path.exists(env_path):
            load_dotenv(env_path)
            log_line(f"[OK] 已加载 .env: {env_path}")
        else:
            log_line(f"[WARN] 未找到 .env：{env_path}（将尝试读取系统环境变量）")
    except Exception:
        log_line("[ERROR] 加载 .env 失败（将继续尝试系统环境变量）")
        log_block(MAIN_LOG_PATH, "EXCEPTION loading .env", traceback.format_exc())

    api_key = (os.getenv("DEEPSEEK_API_KEY_001") or "").strip()
    model = (os.getenv("DEEPSEEK_MODEL") or "deepseek-reasoner").strip()
    base_url = (os.getenv("DEEPSEEK_BASE_URL") or "https://api.deepseek.com").strip()

    targets = select_banks_from_args(args.banks)
    if not targets:
        targets = select_banks_interactive()

    if not targets:
        log_line("[FATAL] 未选择任何题库，程序结束。")
        return

    log_line(f"[OK] 本次选择生成考点还原：{targets}")

    try:
        if args.start_batches:
            start_batches = parse_start_batches_arg(targets, args.start_batches)
        else:
            start_batches = ask_start_batches(targets)
    except Exception:
        log_line("[FATAL] 读取开始轮次失败，程序结束。")
        log_block(MAIN_LOG_PATH, "EXCEPTION reading start batches", traceback.format_exc())
        return

    log_line(f"[OK] 开始轮次设置：{start_batches}")
    max_batches = int(args.max_batches) if int(args.max_batches) > 0 else None

    if not api_key:
        log_line("[FATAL] 未读取到 DEEPSEEK_API_KEY_001：请检查 .env 或系统环境变量。")
        return

    client = DeepSeekClient(api_key=api_key, base_url=base_url, model=model)

    write_user_prompt = not args.no_log_user_prompt

    # 检查 prompt 文件是否存在。
    if not os.path.exists(PROMPT_FILE):
        log_line(f"[FATAL] 找不到 Prompt 文件: {PROMPT_FILE}")
        return

    for t in BANK_ORDER:
        if t not in targets:
            continue
        try:
            if not os.path.exists(NEW_BANK_FILES[t]):
                log_line(f"[WARN] 找不到输入文件，跳过 {t}: {NEW_BANK_FILES[t]}")
                continue

            refresh_one_type_test_point(
                t,
                client,
                start_batch=start_batches.get(t, 1),
                write_user_prompt_to_batch_log=write_user_prompt,
                sleep_s=max(float(args.sleep), 0.0),
                max_batches=max_batches,
            )
        except Exception:
            log_line(f"[ERROR] 生成考点还原 {t} 发生未捕获异常，已跳过该题库，继续下一个。")
            log_block(MAIN_LOG_PATH, f"UNCAUGHT EXCEPTION in refresh_one_type_test_point({t})", traceback.format_exc())
            continue

    log_line("全部流程结束（失败 batch 已跳过；new_bank 为原地更新写回）。")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        log_line("[ERROR] main() 发生未捕获异常，程序将正常结束（已记录日志）。")
        log_block(MAIN_LOG_PATH, "UNCAUGHT EXCEPTION in __main__", traceback.format_exc())
