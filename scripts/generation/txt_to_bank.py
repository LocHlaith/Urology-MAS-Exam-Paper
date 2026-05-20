"""将人类题库 TXT 中间文件解析为题库 JSON。

脚本用途：从 Word 导出的 TXT 中提取题干、选项、参考答案、答案解析和病例题结构。
流程阶段：人类题库结构化。
主要输入：`data/raw/datasets/执业医师题库.txt`。
主要输出：`data/banks/bank_*.json`，即人类题库。
重要边界：本脚本不调用模型，不生成 MAS 题库；当前 TXT 中没有的题型不会被凭空生成。
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from project_paths import BANK_DIR, RAW_DATASETS_DIR


# ===== 路径与常量 =====
INPUT_PATH = RAW_DATASETS_DIR / "执业医师题库.txt"


# ===== 正则规则 =====
RE_HEADER = re.compile(r"单选题-(A1|A2|B|A3/A4)型题")
RE_OPTION = re.compile(r"^\s*([A-E])\s*[\.．、]\s*(.*)\s*$")
RE_ANSWER = re.compile(r"答案\s*[:：]\s*([A-E])\b")
RE_STOP_META = re.compile(
    r"^\s*(难度|统计|大纲|泌尿系统|考点还原|答案解析|知识点|（一）|"
    r"\(\d+版|\d+版|📷|🖼)\b"
)
RE_YEARLINE = re.compile(r"^\s*(19|20)\d{2}\b")

# stem里常见的“8/51”“15 /51”“2 / 255”等
RE_PAGINATION = re.compile(r"^\s*\d+\s*/\s*\d+\s*$")


# ===== 数据结构 =====
@dataclass
class Block:
    """原始分块：从一个“单选题-xxx型题”标题到下一个标题之前"""
    qtype: str  # A1 / A2 / B / A3/A4
    lines: List[str]
    index: int  # 在全文中的顺序，用于调试


@dataclass
class SingleQ:
    """解析后的单题：适用于A1/A2/B单题、以及A3/A4拆成的单题"""
    stem: str
    options: Dict[str, str]
    answer: str
    case: Optional[str] = None  # 仅A3/A4单题会带
    analysis: str = ""          # 答案解析


# ===== 文本清洗工具 =====
def _clean_line(s: str) -> str:
    s = s.replace("\ufeff", "")
    s = s.rstrip("\n").strip()
    # 统一空白（保留中文内容）
    s = re.sub(r"[ \t\u3000]+", " ", s)
    return s


def _normalize_text(s: str) -> str:
    """用于“病例相同/选项相同”的比较：压缩空白，去掉首尾"""
    s = s.replace("\r", "\n")
    s = re.sub(r"[ \t\u3000]+", " ", s)
    s = re.sub(r"\n{2,}", "\n", s)
    return s.strip()


def _strip_exam_code_prefix_from_line(line: str) -> str:
    """
    删除行首考试场次编码（只处理“行首”）：
    - 2018U1-6 xxx
    - 2017U1-104 xxx
    - 2022. 2-U2-35 xxx
    - 2022. 2-U2-57 xxx
    - 2022.2-U2-57 xxx（偶发无空格）
    目标：去掉“编码token + 其后的空白”，保留真正题干。
    """
    s = line.strip()
    if not s:
        return s

    # 1) 明确形态：2022. 2-U2-35 / 2022.2-U2-35 / 2022 -U2-35（松一点）
    p1 = re.compile(r"^\s*(?:19|20)\d{2}(?:\.\s*\d+)?\s*-\s*U\d+\s*-\s*\d+\s*")
    # 2) 形态：2018U1-6 / 2017U1-104
    p2 = re.compile(r"^\s*(?:19|20)\d{2}\s*U\d+\s*-\s*\d+\s*")
    # 3) 更宽松兜底：年份开头 + 一段非中文(最多60) + 至少一个空格
    p3 = re.compile(r"^\s*((?:19|20)\d{2}[^\u4e00-\u9fff]{0,60})\s+(.*)$")

    if p1.match(s):
        return p1.sub("", s).strip()
    if p2.match(s):
        return p2.sub("", s).strip()

    m = p3.match(s)
    if m:
        return m.group(2).strip()

    return s


def _clean_stem_text(stem: str) -> str:
    """
    统一清洗stem：
    - 删除开头若干行的“分页行”（如 8/51, 15 /51）
    - 对第一条有效行删除考试编码
    - 重新拼接为规范文本
    """
    s = _normalize_text(stem)
    if not s:
        return s

    lines = [ln.strip() for ln in s.split("\n") if ln.strip()]

    # 去掉开头连续分页行
    while lines and RE_PAGINATION.match(lines[0]):
        lines.pop(0)

    if not lines:
        return ""

    # 仅对第一条有效行剥离编码
    lines[0] = _strip_exam_code_prefix_from_line(lines[0])

    # 如果剥离后第一行空了，再往下找第一行
    while lines and not lines[0]:
        lines.pop(0)

    return _normalize_text("\n".join(lines))


def _extract_analysis(lines: List[str]) -> str:
    """
    提取答案解析部分。
    遇到“答案解析”或“答案解析：”开始收集，直到该块结束。
    """
    analysis_lines = []
    in_analysis = False
    for ln in lines:
        if not in_analysis:
            # 匹配“答案解析”或“答案解析：”，支持同行直接跟解析内容
            m = re.match(r"^\s*答案解析[:：]?\s*(.*)", ln)
            if m:
                in_analysis = True
                content = m.group(1).strip()
                if content:
                    analysis_lines.append(content)
        else:
            analysis_lines.append(ln)
    return _normalize_text("\n".join(analysis_lines))


def _cut_before_meta(lines: List[str]) -> List[str]:
    """
    只保留“题干/选项/答案”相关的上半部分。
    一般在出现“难度/统计/大纲/考点还原/答案解析...”后都可以截断。
    """
    out = []
    for ln in lines:
        if RE_STOP_META.match(ln):
            break
        out.append(ln)
    return out


def _parse_options_and_answer(lines: List[str]) -> Tuple[Dict[str, str], str]:
    """
    从若干行中解析A-E选项与答案。
    支持选项跨行（续行会拼到上一选项）。
    """
    options: Dict[str, str] = {}
    current_key: Optional[str] = None
    answer: str = ""

    for ln in lines:
        # 答案
        am = RE_ANSWER.search(ln)
        if am:
            answer = am.group(1).strip()

        # 选项
        om = RE_OPTION.match(ln)
        if om:
            current_key = om.group(1)
            options[current_key] = om.group(2).strip()
            continue

        # 选项续行（避免把“答案：”之类拼进去）
        if current_key and ln and (not RE_ANSWER.search(ln)) and (not RE_STOP_META.match(ln)):
            # 续行不能是新的题型header
            if not RE_HEADER.search(ln):
                options[current_key] = (options[current_key] + " " + ln.strip()).strip()

    # 补齐缺失key（保持A-E键存在但值为空，便于下游统一处理）
    for k in ["A", "B", "C", "D", "E"]:
        options.setdefault(k, "")

    return options, answer


def _find_first_option_index(lines: List[str]) -> Optional[int]:
    for i, ln in enumerate(lines):
        if RE_OPTION.match(ln):
            return i
    return None


# ===== 原文分块 =====
def split_blocks(all_lines: List[str]) -> List[Block]:
    """
    按“单选题-xxx型题”标题分块。标题行本身不放入Block.lines。
    """
    blocks: List[Block] = []
    cur_type: Optional[str] = None
    cur_lines: List[str] = []
    block_index = 0

    for raw in all_lines:
        ln = _clean_line(raw)
        if not ln:
            continue

        hm = RE_HEADER.search(ln)
        if hm:
            # 收尾上一个block
            if cur_type is not None:
                blocks.append(Block(qtype=cur_type, lines=cur_lines, index=block_index))
                block_index += 1
            cur_type = hm.group(1)  # A1/A2/B/A3/A4
            cur_lines = []
            continue

        # 非header行，进入当前block
        if cur_type is not None:
            cur_lines.append(ln)

    if cur_type is not None and cur_lines:
        blocks.append(Block(qtype=cur_type, lines=cur_lines, index=block_index))

    return blocks


# ===== 单题解析 =====
def parse_single_from_block(block: Block) -> Optional[SingleQ]:
    """
    解析A1/A2/B单题：
    - stem：header之后到第一个选项之前的内容（拼成一段文本），并清洗分页/考试编码
    - options：A-E
    - answer：答案字母
    - analysis：答案解析
    """
    analysis = _extract_analysis(block.lines)
    lines = _cut_before_meta(block.lines)
    if not lines:
        return None

    opt_i = _find_first_option_index(lines)
    if opt_i is None:
        return None

    stem_lines = [x for x in lines[:opt_i] if x.strip()]
    stem = _normalize_text("\n".join(stem_lines))
    stem = _clean_stem_text(stem)

    options, answer = _parse_options_and_answer(lines[opt_i:])
    if not stem or not answer:
        return None

    return SingleQ(stem=stem, options=options, answer=answer, analysis=analysis)


# ===== 病例题解析 =====
def parse_a3a4_single_from_block(block: Block) -> Optional[SingleQ]:
    """
    对“A3/A4型题”块：将其解析为一个“带case的单题”：
    - case：到“最后一个以年份开头的行”之前的全部（常见为病例段落）
    - stem：从“最后一个以年份开头的行”到选项之前（清洗分页/考试编码）
    - analysis：答案解析
    """
    analysis = _extract_analysis(block.lines)
    lines = _cut_before_meta(block.lines)
    if not lines:
        return None

    opt_i = _find_first_option_index(lines)
    if opt_i is None:
        return None

    pre = [x for x in lines[:opt_i] if x.strip()]
    if not pre:
        return None

    # 找到最后一个以年份开头的行（通常是“考试编码+题干”那行）
    year_idxs = [i for i, ln in enumerate(pre) if RE_YEARLINE.match(ln)]
    if year_idxs:
        stem_start = year_idxs[-1]
        case_lines = pre[:stem_start]
        stem_lines = pre[stem_start:]
    else:
        # 兜底：认为最后一行是题干，前面是case
        case_lines = pre[:-1]
        stem_lines = pre[-1:]

    case = _normalize_text("\n".join(case_lines)) if case_lines else ""
    stem = _normalize_text("\n".join(stem_lines))
    stem = _clean_stem_text(stem)

    options, answer = _parse_options_and_answer(lines[opt_i:])
    if not stem or not answer:
        return None

    return SingleQ(stem=stem, options=options, answer=answer, case=case, analysis=analysis)


# ===== 分组与落库 =====
def emit_a1(a1_items: List[SingleQ]) -> List[dict]:
    out = []
    for i, q in enumerate(a1_items):
        out.append(
            {
                "type": "A1",
                "id": str(i),
                "stem": q.stem,
                "options": {k: q.options.get(k, "") for k in ["A", "B", "C", "D", "E"]},
                "answer": q.answer,
                "analysis": q.analysis,
            }
        )
    return out


def emit_a2(a2_items: List[SingleQ]) -> List[dict]:
    out = []
    for i, q in enumerate(a2_items):
        out.append(
            {
                "type": "A2",
                "id": str(i),
                "stem": q.stem,
                "options": {k: q.options.get(k, "") for k in ["A", "B", "C", "D", "E"]},
                "answer": q.answer,
                "analysis": q.analysis,
            }
        )
    return out


def emit_a3(groups: List[List[SingleQ]]) -> List[dict]:
    out = []
    idx = 0
    for g in groups:
        if len(g) != 2:
            continue
        case = (g[0].case or "").strip()
        out.append(
            {
                "type": "A3",
                "id": str(idx),
                "case": case,
                "stem1": g[0].stem,
                "options1": {k: g[0].options.get(k, "") for k in ["A", "B", "C", "D", "E"]},
                "answer1": g[0].answer,
                "analysis1": g[0].analysis,
                "stem2": g[1].stem,
                "options2": {k: g[1].options.get(k, "") for k in ["A", "B", "C", "D", "E"]},
                "answer2": g[1].answer,
                "analysis2": g[1].analysis,
            }
        )
        idx += 1
    return out


def emit_a4(groups: List[List[SingleQ]]) -> List[dict]:
    out = []
    idx = 0
    for g in groups:
        if len(g) != 3:
            continue
        case = (g[0].case or "").strip()
        out.append(
            {
                "type": "A4",
                "id": str(idx),
                "case": case,
                "stem1": g[0].stem,
                "options1": {k: g[0].options.get(k, "") for k in ["A", "B", "C", "D", "E"]},
                "answer1": g[0].answer,
                "analysis1": g[0].analysis,
                "stem2": g[1].stem,
                "options2": {k: g[1].options.get(k, "") for k in ["A", "B", "C", "D", "E"]},
                "answer2": g[1].answer,
                "analysis2": g[1].analysis,
                "stem3": g[2].stem,
                "options3": {k: g[2].options.get(k, "") for k in ["A", "B", "C", "D", "E"]},
                "answer3": g[2].answer,
                "analysis3": g[2].analysis,
            }
        )
        idx += 1
    return out


def emit_b(groups: List[List[SingleQ]]) -> List[dict]:
    out = []
    idx = 0
    for g in groups:
        if len(g) not in (2, 3):
            continue
        base_opts = {k: g[0].options.get(k, "") for k in ["A", "B", "C", "D", "E"]}
        item = {
            "type": "B",
            "id": str(idx),
            "options": base_opts,
            "stem1": g[0].stem,
            "answer1": g[0].answer,
            "analysis1": g[0].analysis,
            "stem2": g[1].stem,
            "answer2": g[1].answer,
            "analysis2": g[1].analysis,
        }
        if len(g) == 3:
            item["stem3"] = g[2].stem
            item["answer3"] = g[2].answer
            item["analysis3"] = g[2].analysis
        out.append(item)
        idx += 1
    return out


def split_into_groups_by_key(
    items: List[SingleQ], key_fn, allowed_group_sizes=(2, 3)
) -> Tuple[List[List[SingleQ]], List[SingleQ]]:
    """
    将“相邻且key相同”的items分组。
    对于每个连续段：
      - 优先切3，再切2（更符合三连问常态）
      - 余下1个的，丢到singles返回（用于强制转A2）
    """
    groups: List[List[SingleQ]] = []
    singles: List[SingleQ] = []

    i = 0
    n = len(items)
    while i < n:
        j = i + 1
        ki = key_fn(items[i])
        while j < n and key_fn(items[j]) == ki:
            j += 1

        run = items[i:j]
        L = len(run)

        p = 0
        while L - p >= 3 and 3 in allowed_group_sizes:
            groups.append(run[p : p + 3])
            p += 3
        while L - p >= 2 and 2 in allowed_group_sizes:
            groups.append(run[p : p + 2])
            p += 2
        if L - p == 1:
            singles.append(run[p])

        i = j

    return groups, singles


def make_a2_from_a3a4_single(q: SingleQ) -> SingleQ:
    """孤立A3/A4单题 => A2，stem=case + 换行 + stem（并再清洗一次）"""
    case = (q.case or "").strip()
    if case:
        stem = _normalize_text(case + "\n" + q.stem)
    else:
        stem = q.stem
    stem = _clean_stem_text(stem)  # 多一道保险
    return SingleQ(stem=stem, options=q.options, answer=q.answer, case=None, analysis=q.analysis)


# ===== 程序入口 =====
def main() -> None:
    in_path = Path(INPUT_PATH)
    if not in_path.exists():
        raise FileNotFoundError(f"输入文件不存在：{in_path}")

    out_dir = BANK_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    text = in_path.read_text(encoding="utf-8", errors="ignore")
    all_lines = text.splitlines()

    blocks = split_blocks(all_lines)

    a1_items: List[SingleQ] = []
    a2_items: List[SingleQ] = []
    a3a4_singles: List[SingleQ] = []
    b_singles: List[SingleQ] = []

    # 先把各类block解析成“单题”或“带case单题”
    for b in blocks:
        if b.qtype in ("A1", "A2", "B"):
            q = parse_single_from_block(b)
            if not q:
                continue
            if b.qtype == "A1":
                a1_items.append(q)
            elif b.qtype == "A2":
                a2_items.append(q)
            else:
                b_singles.append(q)

        elif b.qtype == "A3/A4":
            q = parse_a3a4_single_from_block(b)
            if q:
                a3a4_singles.append(q)

    # A3/A4：按“相邻病例相同”分组
    def case_key(q: SingleQ) -> str:
        return _normalize_text(q.case or "")

    a3a4_groups, a3a4_lonely = split_into_groups_by_key(
        a3a4_singles,
        key_fn=case_key,
        allowed_group_sizes=(2, 3),
    )

    a3_groups = [g for g in a3a4_groups if len(g) == 2]
    a4_groups = [g for g in a3a4_groups if len(g) == 3]

    # 孤立A3/A4 => A2
    for q in a3a4_lonely:
        a2_items.append(make_a2_from_a3a4_single(q))

    # B：按“相邻选项相同”分组
    def options_key(q: SingleQ) -> str:
        opts = {k: (q.options.get(k, "") or "").strip() for k in ["A", "B", "C", "D", "E"]}
        return json.dumps(opts, ensure_ascii=False, sort_keys=True)

    b_groups, b_lonely = split_into_groups_by_key(
        b_singles,
        key_fn=options_key,
        allowed_group_sizes=(2, 3),
    )

    # 孤立B => A2
    for q in b_lonely:
        stem = _clean_stem_text(q.stem)
        a2_items.append(SingleQ(stem=stem, options=q.options, answer=q.answer, analysis=q.analysis))

    # 输出JSON（按要求id从0开始）
    bank_a1 = emit_a1(a1_items)
    bank_a2 = emit_a2(a2_items)
    bank_a3 = emit_a3(a3_groups)
    bank_a4 = emit_a4(a4_groups)
    bank_b = emit_b(b_groups)

    (out_dir / "bank_a1.json").write_text(json.dumps(bank_a1, ensure_ascii=False, indent=4), encoding="utf-8")
    (out_dir / "bank_a2.json").write_text(json.dumps(bank_a2, ensure_ascii=False, indent=4), encoding="utf-8")
    (out_dir / "bank_a3.json").write_text(json.dumps(bank_a3, ensure_ascii=False, indent=4), encoding="utf-8")
    (out_dir / "bank_a4.json").write_text(json.dumps(bank_a4, ensure_ascii=False, indent=4), encoding="utf-8")
    (out_dir / "bank_b.json").write_text(json.dumps(bank_b, ensure_ascii=False, indent=4), encoding="utf-8")


if __name__ == "__main__":
    main()