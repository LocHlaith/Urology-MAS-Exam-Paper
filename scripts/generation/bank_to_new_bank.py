# bank_to_new_bank.py
# -*- coding: utf-8 -*-

import os
import json
import time
import re
import traceback
import argparse
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from deepseek_env import load_dotenv
from project_paths import (
    ENV_PATH,
    LOG_DIR as PROJECT_LOG_DIR,
    PROJECT_ROOT,
    generation_prompt_files,
    new_bank_files,
    old_bank_files,
)


# ----------------------------
# Paths / Constants
# ----------------------------

ROOT = str(PROJECT_ROOT)

BANK_FILES = old_bank_files()

PROMPT_FILES = generation_prompt_files()

NEW_BANK_FILES = new_bank_files()

BANK_ORDER = ["A1", "A2", "A3", "A4", "B", "X"]

BATCH_SIZES = {
    "A1": 20,
    "A2": 10,
    "A3": 10,
    "A4": 10,
    "B":  10,
    "X":  20,
}


# ----------------------------
# Logging
# ----------------------------

LOG_DIR = str(PROJECT_LOG_DIR)
os.makedirs(LOG_DIR, exist_ok=True)

MAIN_LOG_PATH = os.path.join(
    LOG_DIR,
    f"bank_to_new_bank_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
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
    return os.path.join(LOG_DIR, f"{target_type}_batch_{batch_index:04d}_{ts}.log")


# ----------------------------
# Utility: IO
# ----------------------------

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


# ----------------------------
# Utility: DeepSeek API
# ----------------------------

class DeepSeekClient:
    """
    DeepSeek OpenAI-style Chat Completions:
    POST {base_url}/chat/completions
    """
    def __init__(self, api_key: str, base_url: str, model: str, timeout: int = 180):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def chat(self, system_prompt: str, user_prompt: str, temperature: float = 0.2) -> str:
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


# ----------------------------
# Utility: Response JSON extraction
# 1) 原来的“数组提取”保留（有就用）
# 2) 新增“对象打捞”：从文本中抓所有完整闭合的 {...} JSON 对象
# ----------------------------

_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```", re.IGNORECASE)

def extract_first_json_array_robust(text: str) -> List[Dict[str, Any]]:
    """
    更鲁棒地从模型返回中提取第一个 JSON 数组（list[dict]）。
    - 优先解析 ```json ...```
    - 否则提取第一个完整的 [...]（状态机）
    - 若疑似截断：尝试截到最后一个 ']' 再解析
    """
    text = (text or "").strip()
    if not text:
        raise ValueError("返回为空文本")

    m = _JSON_FENCE_RE.search(text)
    if m:
        candidate = m.group(1).strip()
        return _loads_json_array(candidate)

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
                    return _loads_json_array(candidate)

    last_close = text.rfind("]")
    if last_close != -1 and start is not None and last_close > start:
        candidate = text[start:last_close + 1]
        return _loads_json_array(candidate)

    raise ValueError("未能从返回中截取完整 JSON 数组（疑似截断/括号不匹配）")

def _loads_json_array(candidate: str) -> List[Dict[str, Any]]:
    data = json.loads(candidate)
    if not isinstance(data, list):
        raise ValueError("解析结果不是 list")
    for k, item in enumerate(data):
        if not isinstance(item, dict):
            raise ValueError(f"第 {k} 项不是对象(dict)")
    return data

def iter_json_object_candidates(text: str) -> List[str]:
    """
    从任意文本中扫描所有“完整闭合”的 JSON 对象片段 {...}
    - 处理字符串与转义，避免误把字符串里的 { } 当结构
    - 支持嵌套对象
    """
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

def harvest_json_objects(text: str) -> List[Dict[str, Any]]:
    """
    从文本中“打捞”所有能 json.loads 为 dict 的 {...}。
    注意：只针对 dict；不会把数组当题库写入。
    """
    results: List[Dict[str, Any]] = []
    for cand in iter_json_object_candidates(text):
        try:
            obj = json.loads(cand)
        except Exception:
            continue
        if isinstance(obj, dict):
            results.append(obj)
    return results


# ----------------------------
# Batching logic
# ----------------------------

def source_banks_for(target_type: str) -> List[str]:
    return [b for b in BANK_ORDER if b != target_type]

def build_batches_from_sources(
    sources_in_order: List[List[Dict[str, Any]]],
    batch_size: int
) -> List[List[Dict[str, Any]]]:
    batches: List[List[Dict[str, Any]]] = []
    cur: List[Dict[str, Any]] = []
    for src in sources_in_order:
        for q in src:
            cur.append(q)
            if len(cur) == batch_size:
                batches.append(cur)
                cur = []
    if cur:
        batches.append(cur)
    return batches

def make_user_prompt_json(questions: List[Dict[str, Any]]) -> str:
    return json.dumps(questions, ensure_ascii=False, indent=4)

def normalize_and_reid(
    generated: List[Dict[str, Any]],
    target_type: str,
    start_index: int
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for i, item in enumerate(generated):
        item = dict(item)
        item["type"] = target_type
        item["id"] = str(start_index + i)
        out.append(item)
    return out

def stable_dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

def dedupe_questions(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    轻量去重：忽略 id/type 的差异，避免同一题被重复写入。
    """
    seen = set()
    out: List[Dict[str, Any]] = []
    for it in items:
        if not isinstance(it, dict):
            continue
        tmp = dict(it)
        tmp.pop("id", None)
        tmp.pop("type", None)
        key = stable_dumps(tmp)
        if key in seen:
            continue
        seen.add(key)
        out.append(it)
    return out


# ----------------------------
# Orchestration
# ----------------------------

def load_all_banks_safely() -> Dict[str, List[Dict[str, Any]]]:
    banks: Dict[str, List[Dict[str, Any]]] = {}
    for t, path in BANK_FILES.items():
        try:
            if not os.path.exists(path):
                raise FileNotFoundError(f"缺少文件: {path}")
            banks[t] = read_json_list(path)
            log_line(f"[OK] 读取题库 {t}: {len(banks[t])} 题")
        except Exception:
            banks[t] = []
            log_line(f"[ERROR] 读取题库 {t} 失败，将按 0 题处理。路径: {path}")
            log_block(MAIN_LOG_PATH, f"EXCEPTION reading bank {t}", traceback.format_exc())
    return banks

def load_existing_new_bank(out_path: str) -> List[Dict[str, Any]]:
    if not os.path.exists(out_path):
        return []
    try:
        return read_json_list(out_path)
    except Exception:
        bad_path = out_path + ".bad_" + datetime.now().strftime("%Y%m%d_%H%M%S")
        try:
            os.replace(out_path, bad_path)
        except Exception:
            pass
        log_line(f"[WARN] 输出文件解析失败，已尝试备份并从空开始：{out_path}")
        log_block(MAIN_LOG_PATH, f"EXCEPTION reading existing out {out_path}", traceback.format_exc())
        return []

def refresh_one_bank(
    target_type: str,
    client: DeepSeekClient,
    banks: Dict[str, List[Dict[str, Any]]],
    start_batch: int = 1,
    write_user_prompt_to_batch_log: bool = True,
) -> None:
    out_path = NEW_BANK_FILES[target_type]
    batch_size = BATCH_SIZES[target_type]

    try:
        prompt_path = PROMPT_FILES[target_type]
        system_prompt = read_text(prompt_path)
    except Exception:
        log_line(f"[ERROR] 读取 system prompt 失败，跳过题库 {target_type}")
        log_block(MAIN_LOG_PATH, f"EXCEPTION reading prompt for {target_type}", traceback.format_exc())
        return

    sources = source_banks_for(target_type)
    sources_lists = [banks.get(s, []) for s in sources]
    total_source = sum(len(x) for x in sources_lists)
    batches = build_batches_from_sources(sources_lists, batch_size=batch_size)

    new_bank: List[Dict[str, Any]] = load_existing_new_bank(out_path)
    start_len = len(new_bank)

    log_line(
        f"\n==> 开始翻新 {target_type}: batch_size={batch_size}, "
        f"来源顺序={sources}, 来源总题数={total_source}, 批次数={len(batches)}, "
        f"从第 {start_batch} 轮开始, 现有输出={start_len} -> {out_path}"
    )

    for bi, batch_questions in enumerate(batches, start=1):
        if bi < start_batch:
            continue

        batch_log_path = make_batch_log_path(target_type, bi)
        user_prompt = make_user_prompt_json(batch_questions)

        log_block(
            batch_log_path,
            title=f"BATCH START | target={target_type} | batch={bi}/{len(batches)} | user_n={len(batch_questions)}",
            content=(
                f"prompt_path={PROMPT_FILES[target_type]}\n"
                f"out_path={out_path}\n"
                f"existing_out_len={len(new_bank)}\n"
            ),
        )

        if write_user_prompt_to_batch_log:
            log_block(batch_log_path, "USER PROMPT (JSON)", user_prompt)

        log_line(f"  - {target_type} 第 {bi}/{len(batches)} 轮：题数={len(batch_questions)}（截断也尽量打捞）")

        try:
            text = client.chat(system_prompt=system_prompt, user_prompt=user_prompt)

            log_block(batch_log_path, title="DEEPSEEK RAW RESPONSE", content=text)

            # 1) 先尝试解析数组（能成就用）
            parsed_list: List[Dict[str, Any]] = []
            array_err: Optional[str] = None
            try:
                parsed_list = extract_first_json_array_robust(text)
            except Exception as e:
                array_err = f"{type(e).__name__}: {e}"

            # 2) 不管数组是否成功，都“打捞”所有完整 {...} 对象（满足你的核心诉求）
            salvaged = harvest_json_objects(text)

            # 决策：优先用 parsed_list；同时把打捞到的对象合并进来（去重）
            combined: List[Dict[str, Any]] = []
            if parsed_list:
                combined.extend(parsed_list)
            if salvaged:
                combined.extend(salvaged)

            combined = dedupe_questions(combined)

            if not combined:
                # 真的一个 {} 都没有：这才算“血本无归”
                msg = "返回中未打捞到任何可解析的 JSON 对象(dict)，本 batch 写入 0"
                log_line(f"[SKIP] {target_type} 第 {bi} 轮：{msg}")
                log_block(batch_log_path, "NO USABLE OBJECTS", msg + (f"\narray_parse_error={array_err}" if array_err else ""))
                time.sleep(0.2)
                continue

            if array_err:
                log_block(batch_log_path, "ARRAY PARSE FAILED (SALVAGED OBJECTS USED)", array_err)

            if parsed_list and len(parsed_list) != len(batch_questions):
                log_line(f"[WARN] {target_type} 第 {bi} 轮：数组返回题数={len(parsed_list)}，期望={len(batch_questions)}（仍将合并打捞写入）")
                log_block(
                    batch_log_path,
                    "WARN: ARRAY COUNT MISMATCH",
                    f"array_returned={len(parsed_list)} expected={len(batch_questions)}"
                )

            # 归一化写入
            normalized = normalize_and_reid(combined, target_type, start_index=len(new_bank))
            new_bank.extend(normalized)
            write_json_list(out_path, new_bank)

            log_block(
                batch_log_path,
                title="BATCH OK",
                content=(
                    f"array_parsed={len(parsed_list)}\n"
                    f"objects_salvaged={len(salvaged)}\n"
                    f"deduped_to_write={len(normalized)}\n"
                    f"total_out={len(new_bank)}"
                )
            )
            log_line(f"[OK] {target_type} 第 {bi} 轮：写入 {len(normalized)} 题（解析+打捞），累计 {len(new_bank)}")

            time.sleep(0.6)

        except Exception as e:
            err_text = f"{type(e).__name__}: {e}"
            log_line(f"[SKIP] {target_type} 第 {bi} 轮失败，已跳过：{err_text}")
            log_block(batch_log_path, "BATCH FAILED (SKIPPED)", err_text)
            log_block(batch_log_path, "TRACEBACK", traceback.format_exc())
            time.sleep(0.2)
            continue

    log_line(f"==> 完成 {target_type}: 本次新增 {len(new_bank) - start_len} 题，当前累计 {len(new_bank)} -> {out_path}")


# ----------------------------
# CLI selection
# ----------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Refresh selected new_bank files incrementally.")
    p.add_argument(
        "--banks",
        type=str,
        default="",
        help="Bank types: supports 'A1 A3 B' or 'A1,A3,B' or 'all'. If empty, interactive selection is used."
    )
    p.add_argument(
        "--no_log_user_prompt",
        action="store_true",
        help="Do not write user prompt JSON into per-batch log files (smaller logs)."
    )
    return p.parse_args()

def _split_bank_tokens(s: str) -> List[str]:
    """
    支持：空格/逗号/中文逗号/分号/竖线等分隔
    例如：'A4 B X' / 'A4,B,X' / 'A4，B，X'
    """
    s = (s or "").strip()
    if not s:
        return []
    parts = re.split(r"[,\s，;；|/]+", s)
    return [p.strip().upper() for p in parts if p.strip()]

def select_banks_interactive() -> List[str]:
    log_line("请选择要翻新的题库（如：A4 B X 或 A4,B,X 或 all）：")
    s = input("> ").strip()
    if not s:
        return []
    if s.lower() == "all":
        return BANK_ORDER[:]
    chosen = _split_bank_tokens(s)
    return [x for x in chosen if x in BANK_ORDER]

def select_banks_from_args(arg_banks: str) -> List[str]:
    s = (arg_banks or "").strip()
    if not s:
        return []
    if s.lower() == "all":
        return BANK_ORDER[:]
    chosen = _split_bank_tokens(s)
    return [x for x in chosen if x in BANK_ORDER]

def ask_start_batches(targets: List[str]) -> Dict[str, int]:
    """
    向用户询问每一种题型从第几轮开始。
    输入示例：targets=['A4','B','X'] -> 用户输入 '45 1 1'
    """
    if not targets:
        return {}

    log_line("请依次输入每个题型从第几轮(batch)开始（空格分隔）。")
    log_line(f"题型顺序：{' '.join(targets)}")
    log_line("例如：45 1 1")

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


def main() -> None:
    log_line(f"主日志文件：{MAIN_LOG_PATH}")

    args = parse_args()

    # Load env
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

    api_key = (os.getenv("DEEPSEEK_API_KEY") or "").strip()
    model = (os.getenv("DEEPSEEK_MODEL") or "deepseek-reasoner").strip()
    base_url = (os.getenv("DEEPSEEK_BASE_URL") or "https://api.deepseek.com").strip()

    # 选择目标 banks（允许多选）
    targets = select_banks_from_args(args.banks)
    if not targets:
        targets = select_banks_interactive()

    if not targets:
        log_line("[FATAL] 未选择任何题库，程序结束。")
        return

    log_line(f"[OK] 本次选择翻新：{targets}")

    # 询问每种题型从第几轮开始
    try:
        start_batches = ask_start_batches(targets)
    except Exception:
        log_line("[FATAL] 读取开始轮次失败，程序结束。")
        log_block(MAIN_LOG_PATH, "EXCEPTION reading start batches", traceback.format_exc())
        return

    log_line(f"[OK] 开始轮次设置：{start_batches}")

    if not api_key:
        log_line("[FATAL] 未读取到 DEEPSEEK_API_KEY：将跳过所有 API 调用。请检查 .env 或系统环境变量。")
        return

    client = DeepSeekClient(api_key=api_key, base_url=base_url, model=model)

    # Load banks safely
    banks = load_all_banks_safely()

    # Refresh selected banks in stable order
    write_user_prompt = not args.no_log_user_prompt
    for target_type in BANK_ORDER:
        if target_type not in targets:
            continue
        try:
            refresh_one_bank(
                target_type,
                client,
                banks,
                start_batch=start_batches.get(target_type, 1),
                write_user_prompt_to_batch_log=write_user_prompt
            )
        except Exception:
            log_line(f"[ERROR] 翻新题库 {target_type} 发生未捕获异常，已跳过该题库，继续下一个。")
            log_block(MAIN_LOG_PATH, f"UNCAUGHT EXCEPTION in refresh_one_bank({target_type})", traceback.format_exc())
            continue

    log_line("全部流程结束（失败 batch 已跳过；输出为增量追加，不会被覆盖）。")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        log_line("[ERROR] main() 发生未捕获异常，程序将正常结束（已记录日志）。")
        log_block(MAIN_LOG_PATH, "UNCAUGHT EXCEPTION in __main__", traceback.format_exc())
