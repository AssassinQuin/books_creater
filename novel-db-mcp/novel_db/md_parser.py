"""
MD → DB 逆向解析器

将 Markdown 格式的文件内容解析为结构化数据，用于 File→DB 同步。
每种 section type 有对应的解析函数，是 sync_engine 渲染器的逆操作。

解析原则：
  1. 宽容输入：不要求文件严格匹配模板格式，尽量提取可用数据
  2. 结构保持：JSONB 字段的嵌套结构在 round-trip 后不变
  3. 空值安全：解析失败返回 None，不抛异常
"""

from __future__ import annotations

import json
import re
from typing import Any


# ============================================================================
# Section 切分器
# ============================================================================


def split_sections(md_text: str) -> list[dict]:
    """
    将 Markdown 文本按 ## 标题切分为段落数组。

    注意：仅在 H1（#）和 H2（##）级别切分。H3（###）作为段落内部子标题，
    不触发切分（用于 acts 起承转合、写作优先级 P0/P1/P2 等子结构）。

    Returns:
        [{"heading": "标题", "level": 2, "body": "段落内容", "start": 0}, ...]
    """
    sections = []
    lines = md_text.split("\n")
    current_heading = None
    current_level = 0
    current_body: list[str] = []
    current_start = 0

    for i, line in enumerate(lines):
        # 匹配 H1/H2 标题（不匹配 H3，H3 作为子标题保留在 body 中）
        m = re.match(r'^(#{1,2})\s+(.+)$', line)
        if m:
            # 保存上一段
            if current_heading is not None:
                sections.append({
                    "heading": current_heading,
                    "level": current_level,
                    "body": "\n".join(current_body).strip(),
                    "start": current_start,
                })
            current_heading = m.group(2).strip()
            current_level = len(m.group(1))
            current_body = []
            current_start = i
        elif current_heading is not None:
            current_body.append(line)

    # 保存最后一段
    if current_heading is not None:
        sections.append({
            "heading": current_heading,
            "level": current_level,
            "body": "\n".join(current_body).strip(),
            "start": current_start,
        })

    return sections


def find_section(sections: list[dict], heading_pattern: str | re.Pattern) -> dict | None:
    """
    在段落数组中查找匹配的段落。

    Args:
        sections: split_sections() 的输出
        heading_pattern: 精确标题或正则表达式

    Returns:
        匹配的 section dict，或 None
    """
    if isinstance(heading_pattern, str):
        # 支持模板变量如 "{id}"：先尝试精确匹配，再尝试正则
        for sec in sections:
            if sec["heading"] == heading_pattern:
                return sec
        # 尝试作为正则
        try:
            pat = re.compile(heading_pattern)
            for sec in sections:
                if pat.search(sec["heading"]):
                    return sec
        except re.error:
            pass
        return None
    else:
        for sec in sections:
            if heading_pattern.search(sec["heading"]):
                return sec
        return None


# ============================================================================
# Fields 解析器：- **key**: value → dict
# ============================================================================

_FIELD_LINE_RE = re.compile(r'^-\s+\*\*(.+?)\*\*:\s*(.*)$')
# 支持中文key: `首次出场`, `核心情绪` 等
_FIELD_LINE_RE2 = re.compile(r'^>\s+\*\*(.+?)\*\*[：:]\s*(.*)$')  # blockquote 格式


def parse_bullet_fields(text: str) -> dict[str, Any]:
    """
    解析 `- **key**: value` 格式的 bullet 列表为 dict。

    支持:
      - **key**: plain text
      - **key**: ["array", "of", "strings"]
      - **key**: {"json": "object"}
      - **key**: true / false (bool)
      - **key**: 42 (int)

    重复键处理：当同一 key 出现多次时，收集为 list。
    例如多个 `- **main_plotlines**: xxx` 行 → {"main_plotlines": [val1, val2, ...]}

    Returns:
        {"key": parsed_value, ...}
    """
    result = {}
    if not text:
        return result

    for line in text.split("\n"):
        line = line.rstrip()
        if not line:
            continue

        m = _FIELD_LINE_RE.match(line)
        if not m:
            # 尝试 blockquote 格式
            m2 = _FIELD_LINE_RE2.match(line)
            if m2:
                key = m2.group(1).strip()
                val = m2.group(2).strip()
                _append_or_set(result, key, _parse_value(val))
            continue

        key = m.group(1).strip()
        val = m.group(2).strip()
        _append_or_set(result, key, _parse_value(val))

    return result


def _append_or_set(result: dict, key: str, val: Any):
    """向 dict 中添加键值：首次直接设值，重复键收集为 list。"""
    if key not in result:
        result[key] = val
    else:
        existing = result[key]
        if isinstance(existing, list):
            existing.append(val)
        else:
            result[key] = [existing, val]


def _parse_value(val: str) -> Any:
    """解析单个字段值。"""
    if not val:
        return None

    # Empty JSON structures
    if val == "[]":
        return []
    if val == "{}":
        return {}

    # JSON array or object
    if val.startswith(("[", "{")):
        try:
            return json.loads(val)
        except (json.JSONDecodeError, ValueError):
            pass

    # Boolean
    if val.lower() in ("true", "是"):
        return True
    if val.lower() in ("false", "否"):
        return False

    # Integer
    try:
        return int(val)
    except ValueError:
        pass

    # Float
    try:
        return float(val)
    except ValueError:
        pass

    return val


# ============================================================================
# JSONB 逆向解析器：嵌套 bullet → dict/list
# ============================================================================

def parse_jsonb_bullets(text: str) -> dict | list | None:
    """
    将 `_jsonb_to_md()` 渲染的嵌套 bullet 结构逆向解析回 Python 对象。

    这是 `_jsonb_to_md()` 的逆函数。支持完整的 round-trip：
    dict ↔ 嵌套 bullet dict，list ↔ 嵌套 bullet list，混合结构正确还原。

    输入格式:
        - **key**:
            - **sub_key**: value
            - **sub_key2**: value
        - **list_item_1**
        - **list_item_2**
            - **nested_in_item**
        - **key2**: flat_value

    Returns:
        解析后的 dict 或 list
    """
    if not text or not text.strip():
        return None

    lines = text.split("\n")
    # 跳过第一行（通常是 `- **key**:` 本身，即 jsonb_key 的标题行）
    if lines and lines[0].strip().startswith("- **") and lines[0].strip().endswith("**:"):
        lines = lines[1:]

    return _parse_nested_bullets(lines, base_indent=0)


def _get_indent(line: str) -> int:
    """计算行的缩进级别（空格数）。"""
    stripped = line.lstrip()
    if not stripped:
        return -1  # 空行
    return len(line) - len(stripped)


# 在 _parse_nested_bullets 中使用的正则：匹配去掉 "- " 前缀后的 **key**: value
_INNER_KV_RE = re.compile(r'^\*\*(.+?)\*\*:\s*(.*)$')
# 匹配 **key**: 格式（无值，子行跟随）
_INNER_KEY_ONLY_RE = re.compile(r'^\*\*(.+?)\*\*:\s*$')
# 匹配 **value**: <!-- title_key --> 格式 — list[dict] 的 HTML 注释标注
# 例如: **沈野**: <!-- name --> → title_val="沈野", title_key="name"
# 使用 HTML 注释而非行内标注，对人类读者不可见，对解析器可识别
_TITLE_HTML_COMMENT_RE = re.compile(
    r'^\*\*(.+?)\*\*:\s*<!--\s*([\w\u4e00-\u9fff]+)\s*-->\s*$'
)
# 匹配 **value**: <!-- title_key --> (旧格式兼容: **value** (title_key):)
_TITLE_PAREN_ANNOTATION_RE = re.compile(
    r'^\*\*(.+?)\*\*\s+\(([\w\u4e00-\u9fff]+)\)\s*:\s*$'
)


def _parse_nested_bullets(lines: list[str], base_indent: int) -> dict | list:
    """
    递归解析嵌套 bullet 结构。

    核心修复：去掉 "- " 前缀后的 content 使用 _INNER_KV_RE 正则匹配
    `**key**: value` 格式，而非 _FIELD_LINE_RE（后者要求行首有 `- `），
    从而正确提取键名和值。

    策略（优先级从高到低）：
      0. 如果任一顶层 bullet 匹配 `**value**: <!-- title_key -->` 标注格式
         → list_of_dicts 模式，还原 list[dict] 结构
      1. 如果所有顶层 bullet 都是 `**key**: value` 或 `**key**:` 格式 → dict
      2. 如果所有顶层 bullet 都是纯文本或 `- **title**:` (list-of-dict 模式) → list
      3. 混合情况 → dict
    """
    # 过滤有效行，计算相对缩进
    items = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue

        indent = _get_indent(line)
        if indent < base_indent:
            break  # 回到更上层

        stripped = line.strip()
        if not stripped.startswith("- ") and stripped != "-":
            i += 1
            continue

        # content = 去掉 "- " 前缀后的内容（"- " 或 "-" 后面的部分）
        if stripped == "-":
            content = ""  # 空字符串项
        else:
            content = stripped[2:]  # 去掉 "- "

        # 收集子行（缩进更深的行）
        child_lines = []
        j = i + 1
        while j < len(lines):
            next_indent = _get_indent(lines[j])
            if next_indent <= indent:
                break
            child_lines.append(lines[j])
            j += 1

        items.append({
            "content": content,
            "indent": indent,
            "children": child_lines,
        })
        i = j

    if not items:
        return {}

    # ── 检测 list_of_dicts 标注模式 ──
    # 任一项匹配 `**value**: <!-- title_key -->` 即视为 list[dict]
    # 同时兼容旧格式 `**value** (title_key):`
    has_annotation = any(
        _TITLE_HTML_COMMENT_RE.match(item["content"]) or
        _TITLE_PAREN_ANNOTATION_RE.match(item["content"])
        for item in items
    )

    if has_annotation:
        # ── List-of-dicts 标注模式 ──
        # 还原 list[dict]：从 HTML 注释或旧格式中提取 title_key
        result: list = []
        for item in items:
            m_html = _TITLE_HTML_COMMENT_RE.match(item["content"])
            m_paren = _TITLE_PAREN_ANNOTATION_RE.match(item["content"])

            if m_html:
                title_val = m_html.group(1).strip()
                title_key = m_html.group(2).strip()
            elif m_paren:
                title_val = m_paren.group(1).strip()
                title_key = m_paren.group(2).strip()
            else:
                # 未匹配标注的项：降级为普通 KV 或纯文本
                # 尝试作为 KV 解析，如果失败则作为纯字符串
                m_kv = _INNER_KV_RE.match(item["content"])
                if m_kv:
                    sub_dict = {m_kv.group(1).strip(): _parse_value(m_kv.group(2).strip())}
                else:
                    sub_dict = {"_text": item["content"].strip().strip("*")}
                if item["children"]:
                    child_indent = _get_indent(item["children"][0]) if item["children"] else item["indent"] + 4
                    child_val = _parse_nested_bullets(item["children"], child_indent)
                    if isinstance(child_val, dict):
                        sub_dict.update(child_val)
                result.append(sub_dict)
                continue

            # 构建子 dict：title_key 回注为 dict 的键
            sub_dict = {title_key: title_val}

            if item["children"]:
                child_indent = _get_indent(item["children"][0]) if item["children"] else item["indent"] + 4
                child_val = _parse_nested_bullets(item["children"], child_indent)
                if isinstance(child_val, dict):
                    sub_dict.update(child_val)
                elif child_val is not None:
                    # child_val 是纯列表（如 list[str]），用 "items" 作为键名
                    sub_dict["items"] = child_val

            result.append(sub_dict)
        return result

    # ── 判断是 dict 还是 list ──
    # 使用 _INNER_KV_RE 匹配去掉 "- " 前缀后的 **key**: value 格式
    all_kv = all(
        _INNER_KV_RE.match(item["content"]) or
        _INNER_KEY_ONLY_RE.match(item["content"])
        for item in items
    )

    if all_kv:
        # ── Dict 模式 ──
        result = {}
        for item in items:
            m = _INNER_KV_RE.match(item["content"])
            m_key_only = _INNER_KEY_ONLY_RE.match(item["content"])
            if m:
                key = m.group(1).strip()
                val_str = m.group(2).strip()
            elif m_key_only:
                key = m_key_only.group(1).strip()
                val_str = ""
            else:
                # 降级：strip ** 和 :
                key = item["content"].strip("*: ")
                val_str = ""

            if item["children"]:
                child_indent = _get_indent(item["children"][0]) if item["children"] else item["indent"] + 4
                result[key] = _parse_nested_bullets(item["children"], child_indent)
            elif val_str:
                result[key] = _parse_value(val_str)
            else:
                result[key] = None
        return result
    else:
        # ── List 模式 ──
        result: list = []
        for item in items:
            m = _INNER_KV_RE.match(item["content"])
            m_key_only = _INNER_KEY_ONLY_RE.match(item["content"])

            if m:
                # `**key**: value` — list 中的 dict 元素（title_key 模式）
                key = m.group(1).strip()
                val_str = m.group(2).strip()
                if item["children"]:
                    child_indent = _get_indent(item["children"][0]) if item["children"] else item["indent"] + 4
                    child_val = _parse_nested_bullets(item["children"], child_indent)
                    # 合并：key 的值 + 子行解析结果
                    if isinstance(child_val, dict):
                        if val_str:
                            child_val[key] = _parse_value(val_str)
                        result.append(child_val)
                    else:
                        result.append({key: _parse_value(val_str) if val_str else child_val})
                else:
                    # 简单 KV 在 list 中 → 作为 dict 元素
                    result.append({key: _parse_value(val_str)})
            elif m_key_only:
                # `**key**:` — list 中的子结构标题
                key = m_key_only.group(1).strip()
                if item["children"]:
                    child_indent = _get_indent(item["children"][0]) if item["children"] else item["indent"] + 4
                    child_val = _parse_nested_bullets(item["children"], child_indent)
                    if isinstance(child_val, dict):
                        result.append({key: child_val})
                    else:
                        result.append({key: child_val})
                else:
                    result.append({key: None})
            else:
                # 纯文本条目
                text = item["content"].strip().strip("*")  # 去掉可能的 ** 包裹
                if item["children"]:
                    child_indent = _get_indent(item["children"][0]) if item["children"] else item["indent"] + 4
                    child_val = _parse_nested_bullets(item["children"], child_indent)
                    if isinstance(child_val, dict):
                        result.append({text: child_val})
                    else:
                        result.append(text)
                else:
                    # 空字符串项：content 为空或只有空格
                    if not text:
                        result.append("")
                    else:
                        result.append(text)
        return result


# ============================================================================
# Markdown Table 解析器
# ============================================================================

_TABLE_SEP_RE = re.compile(r'^[\s|:-]+$')


def parse_md_table(text: str) -> list[dict] | None:
    """
    解析 Markdown 表格为 list[dict]。

    输入格式:
        | 列1 | 列2 | 列3 |
        |-----|-----|-----|
        | 值1 | 值2 | 值3 |

    Returns:
        [{"列1": "值1", "列2": "值2", ...}, ...]
    """
    if not text:
        return None

    lines = [l.strip() for l in text.strip().split("\n") if l.strip()]
    if len(lines) < 2:
        return None

    # 解析表头
    header_line = lines[0].strip()
    if not header_line.startswith("|"):
        return None

    headers = [h.strip() for h in header_line.strip("|").split("|")]

    # 跳过分隔行
    data_start = 1
    if data_start < len(lines) and _TABLE_SEP_RE.match(lines[data_start]):
        data_start += 1

    rows = []
    for line in lines[data_start:]:
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        row = {}
        for i, header in enumerate(headers):
            if i < len(cells):
                row[header] = _parse_value(cells[i])
        rows.append(row)

    return rows if rows else None


# ============================================================================
# Blockquote 解析器
# ============================================================================

_BLOCKQUOTE_RE = re.compile(r'^>\s+\*\*(.+?)\*\*[：:]\s*(.*)$')


def parse_blockquotes(text: str) -> dict[str, str]:
    """
    解析 `> **label**：value` 格式的 blockquote 为 dict。

    Returns:
        {"label": "value", ...}
    """
    result = {}
    if not text:
        return result

    for line in text.split("\n"):
        m = _BLOCKQUOTE_RE.match(line.strip())
        if m:
            key = m.group(1).strip()
            val = m.group(2).strip()
            result[key] = val

    return result


# ============================================================================
# Acts（四幕结构）解析器
# ============================================================================

_ACT_HEADING_RE = re.compile(r'^###\s+(.+)$')
_EVENT_RE = re.compile(r'^-\s+E\d+[：:]\s*(.+)$')
_FEIBI_RE = re.compile(r'^-\s+费笔\d+[：:]\s*(.+)$')
_LIST_ITEM_RE = re.compile(r'^-\s+(.+)$')


def parse_acts(text: str, act_labels: list[str] | None = None) -> dict[str, dict]:
    """
    解析四幕结构（起/承/转/合）为 dict。

    输入格式:
        ### 起
        叙事散文...

        事件清单：
        - E1：事件1
        - E2：事件2

        费笔清单：
        - 费笔1：...

    Returns:
        {"act_intro": {"prose": "...", "events": [...], "feibi_notes": [...], "list_items": [...]}, ...}
    """
    if act_labels is None:
        act_labels = ["起", "承", "转", "合"]

    act_col_map = {"起": "act_intro", "承": "act_rise", "转": "act_twist", "合": "act_resolution"}

    # 按段落切分
    paragraphs = re.split(r'\n\n+', text.strip())
    result = {}
    current_act = None
    current_act_key = None
    current_section = "prose"  # prose / events / feibi / list

    for para in paragraphs:
        lines = para.strip().split("\n")
        if not lines:
            continue

        first_line = lines[0].strip()

        # 检测 act 标题
        m = _ACT_HEADING_RE.match(first_line)
        if m:
            label = m.group(1).strip()
            if label in act_labels or label in act_col_map:
                current_act = label
                current_act_key = act_col_map.get(label, label)
                current_section = "prose"
                if current_act_key not in result:
                    result[current_act_key] = {
                        "prose": "", "events": [], "feibi_notes": [], "list_items": []
                    }
                # 标题后可能紧接内容
                rest = "\n".join(lines[1:]).strip()
                if rest:
                    result[current_act_key]["prose"] = rest
                continue

        if not current_act_key:
            continue

        # 检测子段落标题（设置 current_section 但不 continue，让后续行被处理）
        if "事件清单" in first_line or "事件" in first_line:
            current_section = "events"
        if "费笔清单" in first_line:
            current_section = "feibi"

        # 解析内容行
        for line in lines:
            line = line.strip()
            if not line:
                continue

            evt_m = _EVENT_RE.match(line)
            if evt_m:
                current_section = "events"
                result[current_act_key]["events"].append(evt_m.group(1).strip())
                continue

            feibi_m = _FEIBI_RE.match(line)
            if feibi_m:
                current_section = "feibi"
                result[current_act_key]["feibi_notes"].append(feibi_m.group(1).strip())
                continue

            list_m = _LIST_ITEM_RE.match(line)
            if list_m:
                if current_section == "events":
                    result[current_act_key]["events"].append(list_m.group(1).strip())
                elif current_section == "feibi":
                    result[current_act_key]["feibi_notes"].append(list_m.group(1).strip())
                else:
                    result[current_act_key]["list_items"].append(list_m.group(1).strip())
                continue

            # 纯文本 → prose
            if current_section == "prose":
                if result[current_act_key]["prose"]:
                    result[current_act_key]["prose"] += "\n" + line
                else:
                    result[current_act_key]["prose"] = line

    return result


# ============================================================================
# 关系解析器（人物关系专用）
# ============================================================================

_RELATION_RE = re.compile(
    r'^-\s+\*\*(.+?)\*\*\s+\((.+?)\s*→\s*(.+?),\s*强度(\d+)(?:→\d+)?\)'
    r'(?:\s*[:：]\s*(.*))?$'
)


def parse_relations(text: str) -> list[dict]:
    """
    解析人物关系段落为结构化列表。

    输入格式:
        - **ally** (沈野 → 林若烟, 强度8): 描述文本
            - **弦外之音**: xxx
            - **对话调整**: ...

    Returns:
        [{"relation_type": "ally", "from_name": "沈野", "to_name": "林若烟",
          "intensity": 8, "description": "...", "subtext_design": "...",
          "dialogue_adjustment": {...}}, ...]
    """
    if not text:
        return []

    relations = []
    lines = text.split("\n")

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue

        m = _RELATION_RE.match(line)
        if m:
            rel = {
                "relation_type": m.group(1).strip(),
                "from_name": m.group(2).strip(),
                "to_name": m.group(3).strip(),
                "intensity": int(m.group(4)),
                "description": (m.group(5) or "").strip(),
            }

            # 收集子行（弦外之音、对话调整）
            j = i + 1
            while j < len(lines) and lines[j].strip().startswith("    - "):
                sub_line = lines[j].strip().strip("- ").strip()
                sub_m = re.match(r'\*\*(.+?)\*\*[：:]\s*(.*)', sub_line)
                if sub_m:
                    sub_key = sub_m.group(1).strip()
                    sub_val = sub_m.group(2).strip()
                    if sub_key == "弦外之音":
                        rel["subtext_design"] = sub_val
                    elif sub_key == "对话调整":
                        rel["dialogue_adjustment"] = sub_val
                j += 1

            relations.append(rel)
            i = j
        else:
            i += 1

    return relations
