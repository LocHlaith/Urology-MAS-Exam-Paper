"""为 MAS 题库补充“答案解析”字段。

脚本用途：为 MAS 题库补充或补齐答案解析字段。
流程阶段：MAS 题库生成后的内容补全。
主要输入：`data/banks/new_bank_*.json` 与 `prompts/generation/prompts_for_new_bank_answer_explanation_*.txt`。
主要输出：原地更新的 `data/banks/new_bank_*.json`。
重要边界：字段名沿用既有 JSON 结构中的 `analysis` / `analysis1` 等；本脚本不评价题库质量。
"""

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
    answer_explanation_prompt_files,
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

PROMPT_FILES = answer_explanation_prompt_files()

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

# 生成答案解析时不上传的派生评价字段。
STRIP_FIELDS = {
    "prototype",
    "fuzzywuzzy_doubt",
    "fuzzywuzzy_ratio_max",
    "sentencebert_doubt",
    "sentencebert_cosine_max",
    "3gram_doubt",
    "3gram_jaccard_max",
    "textstat_flesch_reading_ease",
}


# ===== 日志 =====

LOG_DIR = str(runtime_log_dir())

MAIN_LOG_PATH = os.path.join(
    LOG_DIR,
    f"answer_explanation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
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
    return os.path.join(LOG_DIR, f"answer_explanation_{target_type}_batch_{batch_index:04d}_{ts}.log")


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


# ===== 模型返回解析 =====

_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```", re.IGNORECASE)

def extract_first_json_array_robust(text: str) -> List[Dict[str, Any]]:
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
    results: List[Dict[str, Any]] = []
    for cand in iter_json_object_candidates(text):
        try:
            obj = json.loads(cand)
        except Exception:
            continue
        if isinstance(obj, dict):
            results.append(obj)
    return results


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
    """
    调用模型时不上传 prototype/相似度/可读性等派生字段。
    其它字段（stem/options/answer/...）保留。
    """
    out = dict(q)
    for k in STRIP_FIELDS:
        out.pop(k, None)
    return out

def make_user_prompt_json(questions: List[Dict[str, Any]]) -> str:
    payload = [strip_for_prompt(q) for q in questions]
    return json.dumps(payload, ensure_ascii=False, indent=4)


# ===== 字段规则 =====

def analysis_keys_for_type(t: str) -> List[str]:
    # 字段名沿用既有 JSON 结构；中文含义为“答案解析”。
    if t in ("A1", "A2", "X"):
        return ["analysis"]
    if t == "A3":
        return ["analysis1", "analysis2"]
    if t in ("A4", "B"):
        return ["analysis1", "analysis2", "analysis3"]
    raise ValueError(f"未知题型: {t}")

def answer_keys_for_type(t: str) -> List[str]:
    if t in ("A1", "A2", "X"):
        return ["answer"]
    if t == "A3":
        return ["answer1", "answer2"]
    if t in ("A4", "B"):
        return ["answer1", "answer2", "answer3"]
    raise ValueError(f"未知题型: {t}")

def _nonempty_str(v: Any) -> bool:
    return isinstance(v, str) and bool(v.strip())

def needs_answer_explanation(
    q: Dict[str, Any],
    t: str,
    allow_b_two_explanations: bool = False,
) -> bool:
    """判断题目是否需要补充答案解析。

    默认按题型应有字段完整检查。为兼容补齐逻辑，可通过
    `allow_b_two_explanations` 允许 B 型题在已有 `analysis1` 和
    `analysis2` 时不因 `analysis3` 缺失而重跑。
    """
    if t == "B" and allow_b_two_explanations:
        if _nonempty_str(q.get("analysis1", "")) and _nonempty_str(q.get("analysis2", "")):
            return False

    for k in analysis_keys_for_type(t):
        if not _nonempty_str(q.get(k, "")):
            return True
    return False


# ===== 字段写回顺序 =====

def insert_answer_explanation_after_answer(q: Dict[str, Any], t: str, patch: Dict[str, Any]) -> Dict[str, Any]:
    """
    将 patch 中的 analysis* 写回 q，并确保顺序：答案解析字段紧跟对应参考答案字段。
    做法：重建 dict 的插入顺序（Python 3.7+ 保序）。
    """
    q0 = dict(q)  # 原数据
    a_keys = answer_keys_for_type(t)
    an_keys = analysis_keys_for_type(t)

    # 先把 patch 的值准备好（只取该题型需要的字段）
    patch_clean: Dict[str, str] = {}
    for k in an_keys:
        v = patch.get(k, "")
        if isinstance(v, str):
            patch_clean[k] = v.strip()
        else:
            patch_clean[k] = ""

    # 重建字段顺序：保留原字段顺序，并在各 answer* 后插入对应 analysis*。
    out: Dict[str, Any] = {}

    def analysis_key_for_answer_key(ak: str) -> Optional[str]:
        if ak == "answer":
            return "analysis"
        m = re.fullmatch(r"answer(\d+)", ak)
        if m:
            return f"analysis{m.group(1)}"
        return None

    for k, v in q0.items():
        # 原有 analysis* 由统一写回逻辑处理，避免字段顺序漂移。
        if k in an_keys:
            continue
        out[k] = v

        if k in a_keys:
            # 在参考答案后写入对应答案解析字段。
            ak = analysis_key_for_answer_key(k)
            if ak and ak in an_keys:
                out[ak] = patch_clean.get(ak, q0.get(ak, ""))

    # 如果某些题型意外没在遍历中插入（理论上不会），兜底追加到末尾
    for k in an_keys:
        if k not in out:
            out[k] = patch_clean.get(k, q0.get(k, ""))

    return out


# ===== 模型结果写回映射 =====

def normalize_response_items(
    t: str,
    parsed: List[Dict[str, Any]]
) -> Dict[str, Dict[str, Any]]:
    """
    模型返回：[{id, analysis*}, ...]
    输出：id -> {analysis*: "..."}
    """
    want = set(["id"] + analysis_keys_for_type(t))
    out: Dict[str, Dict[str, Any]] = {}

    for it in parsed:
        if not isinstance(it, dict):
            continue
        qid = it.get("id", None)
        if qid is None:
            continue
        qid = str(qid)

        patch: Dict[str, Any] = {"id": qid}
        for k in analysis_keys_for_type(t):
            patch[k] = it.get(k, "")

        # 允许多余字段，但只保留需要的
        out[qid] = {k: patch[k] for k in patch if k in want}

    return out


# ===== 主处理流程 =====

def load_existing_new_bank(path: str) -> List[Dict[str, Any]]:
    if not os.path.exists(path):
        raise FileNotFoundError(f"缺少文件: {path}")
    return read_json_list(path)

def refresh_one_type_answer_explanation(
    target_type: str,
    client: DeepSeekClient,
    start_batch: int = 1,
    write_user_prompt_to_batch_log: bool = True,
    sleep_s: float = 0.6,
    allow_b_two_explanations: bool = False,
    max_batches: Optional[int] = None,
) -> None:
    in_path = NEW_BANK_FILES[target_type]
    prompt_path = PROMPT_FILES[target_type]
    batch_size = BATCH_SIZES[target_type]

    system_prompt = read_text(prompt_path)
    bank = load_existing_new_bank(in_path)

    # 只处理缺少答案解析的题。
    pending: List[Dict[str, Any]] = [
        q for q in bank
        if needs_answer_explanation(q, target_type, allow_b_two_explanations)
    ]
    batches = build_batches(pending, batch_size=batch_size)

    log_line(
        f"\n==> 开始生成答案解析 {target_type}: batch_size={batch_size}, "
        f"总题数={len(bank)}, 待补答案解析={len(pending)}, 批次数={len(batches)}, "
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
            content=f"prompt_path={prompt_path}\nin_path={in_path}\n",
        )
        if write_user_prompt_to_batch_log:
            log_block(batch_log_path, "USER PROMPT (JSON)", user_prompt)

        log_line(f"  - {target_type} 第 {bi}/{len(batches)} 轮：题数={len(batch_questions)}")

        try:
            text = client.chat(system_prompt=system_prompt, user_prompt=user_prompt, temperature=0.2)
            log_block(batch_log_path, "DEEPSEEK RAW RESPONSE", text)

            parsed_list: List[Dict[str, Any]] = []
            array_err: Optional[str] = None
            try:
                parsed_list = extract_first_json_array_robust(text)
            except Exception as e:
                array_err = f"{type(e).__name__}: {e}"

            salvaged = harvest_json_objects(text)

            combined: List[Dict[str, Any]] = []
            if parsed_list:
                combined.extend(parsed_list)
            if salvaged:
                combined.extend(salvaged)

            if not combined:
                msg = "返回中未提取到任何可解析 JSON 对象(dict)，本 batch 写入 0"
                log_line(f"[SKIP] {target_type} 第 {bi} 轮：{msg}")
                log_block(batch_log_path, "NO USABLE OBJECTS", msg + (f"\narray_parse_error={array_err}" if array_err else ""))
                if sleep_s > 0:
                    time.sleep(min(0.2, sleep_s))
                continue

            if array_err:
                log_block(batch_log_path, "ARRAY PARSE FAILED (SALVAGE USED)", array_err)

            patch_map = normalize_response_items(target_type, combined)

            # 回写：按 batch 中的 id 逐一写入（缺失则跳过）
            batch_updated = 0
            missing_ids: List[str] = []
            for q in batch_questions:
                qid = str(q.get("id", ""))
                if not qid or qid not in id2idx:
                    continue
                patch = patch_map.get(qid)
                if not patch:
                    missing_ids.append(qid)
                    continue

                idx = id2idx[qid]
                bank[idx] = insert_answer_explanation_after_answer(bank[idx], target_type, patch)
                batch_updated += 1

            write_json_list(in_path, bank)
            updated_count += batch_updated

            log_block(
                batch_log_path,
                "BATCH OK",
                content=(
                    f"parsed_array_items={len(parsed_list)}\n"
                    f"salvaged_objects={len(salvaged)}\n"
                    f"unique_patches={len(patch_map)}\n"
                    f"batch_updated={batch_updated}\n"
                    f"missing_ids={len(missing_ids)}\n"
                    + (f"missing_id_list={missing_ids}\n" if missing_ids else "")
                    + f"total_updated_so_far={updated_count}\n"
                ),
            )
            log_line(f"[OK] {target_type} 第 {bi} 轮：更新 {batch_updated} 题答案解析，累计更新 {updated_count}")
            time.sleep(sleep_s)

        except Exception as e:
            err_text = f"{type(e).__name__}: {e}"
            log_line(f"[SKIP] {target_type} 第 {bi} 轮失败，已跳过：{err_text}")
            log_block(batch_log_path, "BATCH FAILED (SKIPPED)", err_text)
            log_block(batch_log_path, "TRACEBACK", traceback.format_exc())
            if sleep_s > 0:
                time.sleep(min(0.2, sleep_s))
            continue

    log_line(f"==> 完成 {target_type}: 本次共更新答案解析 {updated_count} 题 -> {in_path}")


# ===== 命令行入口 =====

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="为 MAS 题库补充或补齐答案解析字段。")
    p.add_argument(
        "--banks",
        type=str,
        default="",
        help="Bank types: 'A1 A3 B' or 'A1,A3,B' or 'all'. If empty, interactive selection is used."
    )
    p.add_argument(
        "--no_log_user_prompt",
        action="store_true",
        help="Do not write user prompt JSON into per-batch log files (smaller logs)."
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
        help="Sleep seconds between batches (default 0.6)."
    )
    p.add_argument(
        "--allow_b_two_explanations",
        "--allow-b-two-explanations",
        action="store_true",
        help="兼容补齐逻辑：B 型题已有 analysis1 与 analysis2 时，不因 analysis3 缺失而重跑。"
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
    log_line("请选择要生成答案解析的题库（如：A4 B X 或 A4,B,X 或 all）：")
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

    # 读取内容补全专用 API key。
    api_key = (os.getenv("DEEPSEEK_API_KEY_001") or "").strip()
    model = (os.getenv("DEEPSEEK_MODEL") or "deepseek-reasoner").strip()
    base_url = (os.getenv("DEEPSEEK_BASE_URL") or "https://api.deepseek.com").strip()

    targets = select_banks_from_args(args.banks)
    if not targets:
        targets = select_banks_interactive()

    if not targets:
        log_line("[FATAL] 未选择任何题库，程序结束。")
        return

    log_line(f"[OK] 本次选择生成答案解析：{targets}")

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

    for t in BANK_ORDER:
        if t not in targets:
            continue
        try:
            # 预检查文件存在
            if not os.path.exists(NEW_BANK_FILES[t]):
                log_line(f"[WARN] 找不到输入文件，跳过 {t}: {NEW_BANK_FILES[t]}")
                continue
            if not os.path.exists(PROMPT_FILES[t]):
                log_line(f"[WARN] 找不到 prompt 文件，跳过 {t}: {PROMPT_FILES[t]}")
                continue

            refresh_one_type_answer_explanation(
                t,
                client,
                start_batch=start_batches.get(t, 1),
                write_user_prompt_to_batch_log=write_user_prompt,
                sleep_s=max(float(args.sleep), 0.0),
                allow_b_two_explanations=bool(args.allow_b_two_explanations),
                max_batches=max_batches,
            )
        except Exception:
            log_line(f"[ERROR] 生成答案解析 {t} 发生未捕获异常，已跳过该题库，继续下一个。")
            log_block(MAIN_LOG_PATH, f"UNCAUGHT EXCEPTION in refresh_one_type_answer_explanation({t})", traceback.format_exc())
            continue

    log_line("全部流程结束（失败 batch 已跳过；new_bank 为原地更新写回）。")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        log_line("[ERROR] main() 发生未捕获异常，程序将正常结束（已记录日志）。")
        log_block(MAIN_LOG_PATH, "UNCAUGHT EXCEPTION in __main__", traceback.format_exc())
