# llm.py
# -*- coding: utf-8 -*-

import os
import json
import time
import re
import traceback
import argparse
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import requests
from dotenv import load_dotenv


# ----------------------------
# Paths / Constants
# ----------------------------

ROOT = os.path.dirname(os.path.abspath(__file__))

OLD_BANK_FILES = {
    "A1": os.path.join(ROOT, "bank_a1.json"),
    "A2": os.path.join(ROOT, "bank_a2.json"),
    "A3": os.path.join(ROOT, "bank_a3.json"),
    "A4": os.path.join(ROOT, "bank_a4.json"),
    "B":  os.path.join(ROOT, "bank_b.json"),
    "X":  os.path.join(ROOT, "bank_x.json"),
}

NEW_BANK_FILES = {
    "A1": r"D:\Desktop\当务之急\EAGLE\泌尿外科\泌尿外科专科出卷\new_bank_a1.json",
    "A2": r"D:\Desktop\当务之急\EAGLE\泌尿外科\泌尿外科专科出卷\new_bank_a2.json",
    "A3": r"D:\Desktop\当务之急\EAGLE\泌尿外科\泌尿外科专科出卷\new_bank_a3.json",
    "A4": r"D:\Desktop\当务之急\EAGLE\泌尿外科\泌尿外科专科出卷\new_bank_a4.json",
    "B":  r"D:\Desktop\当务之急\EAGLE\泌尿外科\泌尿外科专科出卷\new_bank_b.json",
    "X":  r"D:\Desktop\当务之急\EAGLE\泌尿外科\泌尿外科专科出卷\new_bank_x.json",
}

BANK_ORDER = ["A1", "A2", "A3", "A4", "B", "X"]

PROMPT_LLM_PATH = os.path.join(ROOT, "prompt_for_llm.txt")

BATCH_SIZE = 100

# LLM 评分项数量（不含 id）
LLM_SCORE_COUNT = 16
LLM_TOTAL_COLS = 1 + LLM_SCORE_COUNT  # id + 16 scores

# 新题库中不要上传 deepseek 的字段
# 说明：
# - 你明确列出的 8 个新增字段：不上传
# - “可能多了 QGEval”：这里也不上传，避免把 QGEval 带给 LLM 评分造成泄漏/偏置
# - “LLM”本身也不上传（本脚本是在生成 LLM；即使重跑也不应把旧 LLM 传上去）
NEW_BANK_STRIP_KEYS = {
    "prototype",
    "fuzzywuzzy_doubt",
    "fuzzywuzzy_ratio_max",
    "sentencebert_doubt",
    "sentencebert_cosine_max",
    "3gram_doubt",
    "3gram_jaccard_max",
    "textstat_flesch_reading_ease",
    "QGEval",
    "LLM",
}


# ----------------------------
# Logging
# ----------------------------

LOG_DIR = os.path.join(ROOT, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

MAIN_LOG_PATH = os.path.join(
    LOG_DIR,
    f"llm_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
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

def make_batch_log_path(bank_set: str, bank_type: str, batch_index: int) -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return os.path.join(LOG_DIR, f"llm_{bank_set}_{bank_type}_batch_{batch_index:04d}_{ts}.log")


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
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def backup_file(path: str) -> Optional[str]:
    if not os.path.exists(path):
        return None
    bak = path + ".bak_" + datetime.now().strftime("%Y%m%d_%H%M%S")
    os.replace(path, bak)
    return bak


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
# Utility: Response extraction (array-of-arrays)
# ----------------------------

_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```", re.IGNORECASE)

def extract_first_json_array_robust(text: str) -> Any:
    text = (text or "").strip()
    if not text:
        raise ValueError("返回为空文本")

    m = _JSON_FENCE_RE.search(text)
    if m:
        candidate = m.group(1).strip()
        return json.loads(candidate)

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
                    return json.loads(candidate)

    last_close = text.rfind("]")
    if last_close != -1 and start is not None and last_close > start:
        candidate = text[start:last_close + 1]
        return json.loads(candidate)

    raise ValueError("未能从返回中截取完整 JSON 数组（疑似截断/括号不匹配）")

def parse_llm_rows(obj: Any) -> List[Tuple[int, List[int]]]:
    """
    期望输入形如：
    [
      [1052, 5,3,4,5,5,5,4, 5,3,4,4,4,4,3,1,4],
      ...
    ]
    每行 17 列（id + 16评分）。
    """
    if not isinstance(obj, list):
        raise ValueError("LLM 返回不是 list")

    rows: List[Tuple[int, List[int]]] = []
    for i, row in enumerate(obj):
        if not isinstance(row, list):
            raise ValueError(f"第 {i} 行不是 list：{row!r}")
        if len(row) != LLM_TOTAL_COLS:
            raise ValueError(
                f"第 {i} 行长度不是 {LLM_TOTAL_COLS}（id+{LLM_SCORE_COUNT}项）："
                f"len={len(row)} row={row!r}"
            )

        qid = row[0]
        scores = row[1:]

        if not isinstance(qid, int):
            try:
                qid = int(str(qid).strip())
            except Exception:
                raise ValueError(f"第 {i} 行 id 无法转为 int：{row!r}")

        out_scores: List[int] = []
        for s in scores:
            if isinstance(s, bool):
                raise ValueError(f"第 {i} 行分数出现 bool：{row!r}")
            if isinstance(s, int):
                out_scores.append(s)
            else:
                try:
                    out_scores.append(int(str(s).strip()))
                except Exception:
                    raise ValueError(f"第 {i} 行分数无法转 int：{row!r}")

        rows.append((qid, out_scores))

    return rows


# ----------------------------
# Batching / Prompt
# ----------------------------

def split_batches(items: List[Dict[str, Any]], batch_size: int) -> List[List[Dict[str, Any]]]:
    out: List[List[Dict[str, Any]]] = []
    cur: List[Dict[str, Any]] = []
    for it in items:
        cur.append(it)
        if len(cur) == batch_size:
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    return out

def sanitize_questions_for_deepseek(
    questions: List[Dict[str, Any]],
    strip_keys: Optional[set] = None
) -> List[Dict[str, Any]]:
    if not strip_keys:
        return [dict(q) for q in questions]
    out: List[Dict[str, Any]] = []
    for q in questions:
        if not isinstance(q, dict):
            continue
        qq = {k: v for k, v in q.items() if k not in strip_keys}
        out.append(qq)
    return out

def make_user_prompt_json(questions: List[Dict[str, Any]]) -> str:
    return json.dumps(questions, ensure_ascii=False, indent=4)

def format_llm(scores: List[int]) -> str:
    total = sum(scores)
    return f"{total}: {','.join(str(x) for x in scores)}"


# ----------------------------
# Core: LLM insertion ordering
# ----------------------------

def set_llm_with_order(item: Dict[str, Any], llm_text: str) -> Dict[str, Any]:
    """
    写入 LLM，并满足顺序要求：
    - 默认：LLM 在最后
    - 若存在 QGEval：LLM 插在 QGEval 后面（紧跟 QGEval）
    - 不覆盖：若已存在 LLM，则直接返回原 item
    注意：可能返回新 dict；调用者需要写回 list 的对应位置。
    """
    if "LLM" in item:
        return item

    if "QGEval" not in item:
        item["LLM"] = llm_text
        return item

    # 存在 QGEval：重建 dict，把 LLM 插到 QGEval 后
    new_item: Dict[str, Any] = {}
    inserted = False
    for k, v in item.items():
        new_item[k] = v
        if k == "QGEval" and not inserted:
            new_item["LLM"] = llm_text
            inserted = True

    if not inserted:
        # 极端兜底：追加到末尾
        new_item["LLM"] = llm_text

    return new_item


# ----------------------------
# Core: Evaluate one bank file
# ----------------------------

def eval_one_bank(
    bank_set: str,  # "old" or "new"
    bank_type: str,
    bank_files: Dict[str, str],
    client: DeepSeekClient,
    system_prompt: str,
    start_batch: int = 1,
    write_user_prompt_to_batch_log: bool = True,
    sleep_seconds: float = 0.6,
) -> None:
    path = bank_files[bank_type]
    if not os.path.exists(path):
        log_line(f"[ERROR] bank 文件不存在：{path}（跳过 {bank_set}:{bank_type}）")
        return

    data = read_json_list(path)

    # 只处理未写入 LLM 的题（不影响已有 QGEval）
    pending: List[Dict[str, Any]] = [q for q in data if isinstance(q, dict) and ("LLM" not in q)]
    log_line(f"==> {bank_set}:{bank_type}: 总题数={len(data)}, 待评分={len(pending)}, batch_size={BATCH_SIZE}, start_batch={start_batch}")

    if not pending:
        log_line(f"[OK] {bank_set}:{bank_type}: 无待评分题目，跳过。")
        return

    # 建索引：id -> list_index
    id_to_pos: Dict[int, int] = {}
    for idx, q in enumerate(data):
        if not isinstance(q, dict):
            continue
        qid_raw = q.get("id")
        try:
            qid = int(str(qid_raw).strip())
        except Exception:
            raise ValueError(f"{bank_set}:{bank_type} 出现无法解析为 int 的 id：{qid_raw!r}")
        id_to_pos[qid] = idx

    batches = split_batches(pending, BATCH_SIZE)

    bak = backup_file(path)
    log_line(f"[OK] {bank_set}:{bank_type}: 已备份原文件 -> {bak}")

    # 原文件已被 os.replace 挪走，先写回占位
    write_json_list(path, data)

    strip_keys = NEW_BANK_STRIP_KEYS if bank_set == "new" else None

    for bi, batch_questions in enumerate(batches, start=1):
        if bi < start_batch:
            continue

        batch_log_path = make_batch_log_path(bank_set, bank_type, bi)

        batch_to_send = sanitize_questions_for_deepseek(batch_questions, strip_keys=strip_keys)
        user_prompt = make_user_prompt_json(batch_to_send)

        log_block(
            batch_log_path,
            title=f"BATCH START | set={bank_set} | bank={bank_type} | batch={bi}/{len(batches)} | n={len(batch_questions)}",
            content=f"path={path}\nbackup={bak}\nstrip_keys={sorted(list(strip_keys)) if strip_keys else 'None'}\n"
        )
        if write_user_prompt_to_batch_log:
            log_block(batch_log_path, "USER PROMPT (JSON, SANITIZED)", user_prompt)

        log_line(f"  - {bank_set}:{bank_type} 第 {bi}/{len(batches)} 批：n={len(batch_questions)}")

        try:
            text = client.chat(system_prompt=system_prompt, user_prompt=user_prompt, temperature=0.2)
            log_block(batch_log_path, "DEEPSEEK RAW RESPONSE", text)

            obj = extract_first_json_array_robust(text)
            rows = parse_llm_rows(obj)

            updated = 0
            missed = 0

            for qid, scores in rows:
                pos = id_to_pos.get(qid)
                if pos is None:
                    missed += 1
                    continue

                item = data[pos]
                if not isinstance(item, dict):
                    missed += 1
                    continue
                if "LLM" in item:
                    continue  # 不覆盖

                llm_text = format_llm(scores)
                new_item = set_llm_with_order(item, llm_text)

                if new_item is not item:
                    data[pos] = new_item

                updated += 1

            write_json_list(path, data)

            log_block(
                batch_log_path,
                "BATCH OK",
                content=(
                    f"rows_returned={len(rows)}\n"
                    f"updated={updated}\n"
                    f"missed_id_not_found={missed}\n"
                    f"bank_total={len(data)}\n"
                )
            )
            log_line(f"[OK] {bank_set}:{bank_type} 第 {bi} 批：写入 LLM={updated}，返回行={len(rows)}，未命中id={missed}")

            time.sleep(sleep_seconds)

        except Exception as e:
            err_text = f"{type(e).__name__}: {e}"
            log_line(f"[SKIP] {bank_set}:{bank_type} 第 {bi} 批失败，已跳过：{err_text}")
            log_block(batch_log_path, "BATCH FAILED (SKIPPED)", err_text)
            log_block(batch_log_path, "TRACEBACK", traceback.format_exc())
            time.sleep(0.2)
            continue

    final_data = read_json_list(path)
    done = sum(1 for q in final_data if isinstance(q, dict) and ("LLM" in q))
    log_line(f"==> {bank_set}:{bank_type}: 完成。已评分={done}/{len(final_data)}，输出文件={path}")


# ----------------------------
# CLI
# ----------------------------

def _split_bank_tokens(s: str) -> List[str]:
    s = (s or "").strip()
    if not s:
        return []
    parts = re.split(r"[,\s，;；|/]+", s)
    return [p.strip().upper() for p in parts if p.strip()]

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Add LLM scores into existing bank_*.json using DeepSeek.")
    p.add_argument(
        "--bank_set",
        type=str,
        default="",
        choices=["old", "new", ""],
        help="Choose bank set: old or new. If empty, interactive selection is used."
    )
    p.add_argument(
        "--banks",
        type=str,
        default="",
        help="Bank types: 'A1 A3 B' or 'A1,A3,B' or 'all'. If empty, interactive selection is used."
    )
    p.add_argument(
        "--start_batch",
        type=int,
        default=1,
        help="Start from which batch (1-based). Applied to all selected banks."
    )
    p.add_argument(
        "--no_log_user_prompt",
        action="store_true",
        help="Do not write user prompt JSON into per-batch log files (smaller logs)."
    )
    p.add_argument(
        "--sleep",
        type=float,
        default=0.6,
        help="Sleep seconds between batches."
    )
    return p.parse_args()

def select_bank_set_interactive() -> str:
    log_line("请选择题库类型：old（老题库 bank_*.json）或 new（新题库 new_bank_*.json）：")
    s = input("> ").strip().lower()
    if s in ("old", "new"):
        return s
    return ""

def select_banks_interactive() -> List[str]:
    log_line("请选择要评分的题库（如：A4 B X 或 A4,B,X 或 all）：")
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


# ----------------------------
# Main
# ----------------------------

def main() -> None:
    log_line(f"主日志文件：{MAIN_LOG_PATH}")

    args = parse_args()

    bank_set = (args.bank_set or "").strip().lower()
    if not bank_set:
        bank_set = select_bank_set_interactive()
    if bank_set not in ("old", "new"):
        log_line("[FATAL] 未选择题库类型（old/new），程序结束。")
        return

    bank_files = OLD_BANK_FILES if bank_set == "old" else NEW_BANK_FILES

    # Load env
    env_path = os.path.join(ROOT, ".env")
    try:
        if os.path.exists(env_path):
            load_dotenv(env_path)
            log_line(f"[OK] 已加载 .env: {env_path}")
        else:
            log_line(f"[WARN] 未找到 .env：{env_path}（将尝试读取系统环境变量）")
    except Exception:
        log_line("[ERROR] 加载 .env 失败（将继续尝试系统环境变量）")
        log_block(MAIN_LOG_PATH, "EXCEPTION loading .env", traceback.format_exc())

    # 必须用 _003
    api_key = (os.getenv("DEEPSEEK_API_KEY_003") or "").strip()
    model = (os.getenv("DEEPSEEK_MODEL") or "deepseek-reasoner").strip()
    base_url = (os.getenv("DEEPSEEK_BASE_URL") or "https://api.deepseek.com").strip()

    if not api_key:
        log_line("[FATAL] 未读取到 DEEPSEEK_API_KEY_003。请检查 .env 或系统环境变量。")
        return

    # Load system prompt
    try:
        system_prompt = read_text(PROMPT_LLM_PATH)
        log_line(f"[OK] 已读取 prompt：{PROMPT_LLM_PATH}")
    except Exception:
        log_line(f"[FATAL] 读取 prompt_for_llm.txt 失败：{PROMPT_LLM_PATH}")
        log_block(MAIN_LOG_PATH, "EXCEPTION reading prompt_for_llm.txt", traceback.format_exc())
        return

    # Select banks
    targets = select_banks_from_args(args.banks)
    if not targets:
        targets = select_banks_interactive()
    if not targets:
        log_line("[FATAL] 未选择任何题库，程序结束。")
        return

    if args.start_batch < 1:
        log_line(f"[FATAL] --start_batch 必须 >= 1，收到：{args.start_batch}")
        return

    log_line(f"[OK] 本次选择评分：set={bank_set} | banks={targets} | start_batch={args.start_batch} | batch_size={BATCH_SIZE}")

    # 预检查文件是否存在
    for bt in targets:
        p = bank_files.get(bt)
        if p and (not os.path.exists(p)):
            log_line(f"[WARN] 目标题库文件不存在：set={bank_set} bank={bt} path={p}")

    client = DeepSeekClient(api_key=api_key, base_url=base_url, model=model, timeout=180)
    write_user_prompt = not args.no_log_user_prompt

    for bank_type in BANK_ORDER:
        if bank_type not in targets:
            continue
        try:
            eval_one_bank(
                bank_set=bank_set,
                bank_type=bank_type,
                bank_files=bank_files,
                client=client,
                system_prompt=system_prompt,
                start_batch=args.start_batch,
                write_user_prompt_to_batch_log=write_user_prompt,
                sleep_seconds=args.sleep,
            )
        except Exception:
            log_line(f"[ERROR] {bank_set}:{bank_type} 评分发生未捕获异常，已跳过该题库，继续下一个。")
            log_block(MAIN_LOG_PATH, f"UNCAUGHT EXCEPTION in eval_one_bank({bank_set}:{bank_type})", traceback.format_exc())
            continue

    log_line("全部流程结束（失败 batch 已跳过；已评分题会自动跳过；每个 bank 文件已在开始时备份）。")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        log_line("[ERROR] main() 发生未捕获异常，程序将正常结束（已记录日志）。")
        log_block(MAIN_LOG_PATH, "UNCAUGHT EXCEPTION in __main__", traceback.format_exc())
