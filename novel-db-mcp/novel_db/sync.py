import hashlib
import json
import os
import re
import threading

from .db import query, PROJECT_ROOT
from .resolvers import _resolve_novel_id

_NOVELS_BASE = os.path.join(PROJECT_ROOT, "novels")

# ============================================================================
# Hash infrastructure (unchanged)
# ============================================================================


_hashes_table_ensured = False
_hashes_table_lock = threading.Lock()


def _ensure_data_hashes_table():
    global _hashes_table_ensured
    with _hashes_table_lock:
        if _hashes_table_ensured:
            return
        query(
            "CREATE TABLE IF NOT EXISTS data_hashes ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "novel_id INTEGER NOT NULL, "
            "data_type TEXT NOT NULL, "
            "data_key TEXT NOT NULL, "
            "db_hash TEXT NOT NULL DEFAULT '', "
            "file_hash TEXT NOT NULL DEFAULT '', "
            "db_updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, "
            "file_updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, "
            "UNIQUE(novel_id, data_type, data_key)"
            ")",
            fetch="none",
        )
        _migrate_hashes_table()
        _hashes_table_ensured = True


def _migrate_hashes_table():
    """Add last_sync_hash and last_sync_file_hash columns if missing."""
    cols = query("PRAGMA table_info(data_hashes)", fetch="all")
    existing = {c["name"] for c in cols} if cols else set()
    if "last_sync_hash" not in existing:
        query("ALTER TABLE data_hashes ADD COLUMN last_sync_hash TEXT NOT NULL DEFAULT ''", fetch="none")
    if "last_sync_file_hash" not in existing:
        query("ALTER TABLE data_hashes ADD COLUMN last_sync_file_hash TEXT NOT NULL DEFAULT ''", fetch="none")


def _compute_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]


def _upsert_hash(novel_id: int, data_type: str, data_key: str,
                 db_hash: str = "", file_hash: str = ""):
    _ensure_data_hashes_table()
    if db_hash and not file_hash:
        query(
            "INSERT INTO data_hashes (novel_id, data_type, data_key, db_hash, db_updated_at) "
            "VALUES (?, ?, ?, ?, datetime('now')) "
            "ON CONFLICT (novel_id, data_type, data_key) DO UPDATE SET db_hash = ?, db_updated_at = datetime('now')",
            (novel_id, data_type, data_key, db_hash, db_hash), fetch="none"
        )
    elif file_hash and not db_hash:
        query(
            "INSERT INTO data_hashes (novel_id, data_type, data_key, file_hash, file_updated_at) "
            "VALUES (?, ?, ?, ?, datetime('now')) "
            "ON CONFLICT (novel_id, data_type, data_key) DO UPDATE SET file_hash = ?, file_updated_at = datetime('now')",
            (novel_id, data_type, data_key, file_hash, file_hash), fetch="none"
        )
    else:
        sets = []
        vals = []
        if db_hash:
            sets.append("db_hash = ?")
            sets.append("db_updated_at = datetime('now')")
            vals.append(db_hash)
        if file_hash:
            sets.append("file_hash = ?")
            sets.append("file_updated_at = datetime('now')")
            vals.append(file_hash)
        if not sets:
            return
        vals.extend([novel_id, data_type, data_key])
        query(
            f"INSERT INTO data_hashes (novel_id, data_type, data_key, {', '.join(['db_hash','file_hash'][:len(sets)])}) "
            f"VALUES (?, ?, ?, {', '.join(['?','?'][:len(sets)])}) "
            f"ON CONFLICT (novel_id, data_type, data_key) DO UPDATE SET {', '.join(sets)}",
            tuple(vals), fetch="none"
        )


def _record_db_hash(novel_id: int, data_type: str, data_key: str, content: str):
    h = _compute_hash(content)
    _upsert_hash(novel_id, data_type, data_key, db_hash=h)


def _record_file_hash(novel_id: int, data_type: str, data_key: str, content: str):
    h = _compute_hash(content)
    _upsert_hash(novel_id, data_type, data_key, file_hash=h)


def _get_hash_record(novel_id: int, data_type: str, data_key: str) -> dict | None:
    """Read all hash columns for an entity from data_hashes."""
    _ensure_data_hashes_table()
    rows = query(
        "SELECT db_hash, file_hash, last_sync_hash, last_sync_file_hash, "
        "db_updated_at, file_updated_at "
        "FROM data_hashes WHERE novel_id=? AND data_type=? AND data_key=?",
        (novel_id, data_type, data_key), fetch="all"
    )
    return rows[0] if rows else None


def _detect_conflict(stored: dict | None, current_file_hash: str) -> str:
    """Determine sync conflict state.

    Returns one of:
      'safe'       — file unchanged since last sync, DB changed → safe to overwrite
      'db_newer'   — same as safe (DB changed, file didn't)
      'file_newer' — file was modified by user, DB didn't change → needs user decision
      'conflict'   — both file and DB changed since last sync → needs user decision
      'no_record'  — no previous sync record → first sync is safe
      'skip'       — neither changed → nothing to do
    """
    if stored is None:
        return "no_record"

    last_file = stored.get("last_sync_file_hash", "")
    last_db = stored.get("last_sync_hash", "")
    stored_db = stored.get("db_hash", "")

    # No previous sync — safe
    if not last_file and not last_db:
        return "no_record"

    file_changed = current_file_hash != last_file if last_file else bool(current_file_hash)
    db_changed = stored_db != last_db if last_db else bool(stored_db)

    if file_changed and db_changed:
        return "conflict"
    if file_changed:
        return "file_newer"
    if db_changed:
        return "db_newer"
    return "skip"


def _snapshot_sync_hashes(novel_id: int, data_type: str, data_key: str,
                           db_hash: str, file_hash: str):
    """After successful sync, record last_sync_hash and last_sync_file_hash."""
    _ensure_data_hashes_table()
    query(
        "UPDATE data_hashes SET last_sync_hash=?, last_sync_file_hash=? "
        "WHERE novel_id=? AND data_type=? AND data_key=?",
        (db_hash, file_hash, novel_id, data_type, data_key), fetch="none"
    )


def _auto_sync_to_files(novel_name: str, data_type: str,
                         data_key: str | None = None,
                         novel_id: int | None = None) -> str | None:
    """DB 修改后自动同步到文件。有冲突时返回冲突报告 JSON，否则返回 None。

    供各 MCP 工具在 DB 写入后调用。优先使用 novel_id 避免反向查询。
    """
    from .sync_engine import engine as _sync_engine
    try:
        # 如果有 novel_id 但没有 novel_name，先解析
        if novel_id and not novel_name:
            row = query("SELECT name FROM novels WHERE id = ?", (novel_id,), fetch="one")
            if not row:
                return None
            novel_name = row["name"]
        result = _sync_engine.db_to_files(novel_name, data_type,
                                          entity_key=data_key, overwrite=False)
        conflicts = result.get("conflicts", [])
        if conflicts:
            return json.dumps({
                "auto_sync_conflicts": conflicts,
                "message": "文件被修改过，请选择处理方式: sync(action='resolve', resolutions=[...])"
            }, ensure_ascii=False)
        return None
    except Exception as e:
        return json.dumps({"auto_sync_warning": str(e)}, ensure_ascii=False)

def _db_row_to_hashable(row: dict) -> str:
    parts = []
    for k in sorted(row.keys()):
        if k in ("id", "created_at", "updated_at"):
            continue
        v = row[k]
        if isinstance(v, (dict, list)):
            v = json.dumps(v, ensure_ascii=False, sort_keys=True)
        parts.append(f"{k}={v}")
    return "|".join(parts)


# ============================================================================
# Formatting helpers
# ============================================================================


def _is_empty(v) -> bool:
    if v is None:
        return True
    if isinstance(v, str):
        return v.strip() == "" or v in ("{}", "[]")
    if isinstance(v, (dict, list)):
        return len(v) == 0
    return False


_TITLE_KEYS = ['name', 'stage', 'volume', 'target', 'scene', 'context', 'type',
               '角色', '互动对', '章', '#', 'question']


def _find_title_key(obj: dict) -> tuple:
    for key in _TITLE_KEYS:
        if key in obj and isinstance(obj[key], str) and obj[key].strip():
            return key, obj[key].strip()
    for k, v in obj.items():
        if isinstance(v, str) and v.strip():
            return k, v.strip()
    return None, None


def _jsonb_to_md_narrative(data: dict, level: int = 3) -> list:
    """将 dict 渲染为人可读的叙事格式：顶层 key → ### 标题，字符串→段落，列表→bullet，嵌套 dict→子标题。"""

    # key → 中文标题映射
    _KEY_LABELS = {
        "description": "概述",
        "origin": "起源",
        "name_meaning": "名字含义",
        "scale": "规模",
        "structure": "组织结构",
        "what_they_did": "四百年历程",
        "the_cost": "代价",
        "recent_tension": "当前危机",
        "created_or_guided": "暗中布局",
        "meeting_place": "据点",
        "core_asset": "核心资产",
        "internal_tension": "内部暗流",
        "economy": "经济",
        "blind_spot": "认知盲区",
        "conflict_with_ming_tang": "与明堂的冲突",
        "character": "群体气质",
        "three_missions": "三大使命",
        "belief": "信仰",
        "practices": "行事方式",
        "threat": "威胁等级",
        "power_structure": "权力结构",
        "military": "军事",
        "stance": "立场",
        "conflict_with_ming_tang": "与明堂的冲突",
        "awakener_tradition": "觉醒者传统",
        "composition": "人员构成",
        "methods": "手段",
        "relation_to_others": "与其他势力的关系",
        "form": "形态",
        "natural_behavior": "自然行为",
        "crystallization": "灵晶凝结",
        "effects_on_life": "对生命的影响",
        "灵潮": "灵潮",
        "awakening": "觉醒机制",
        "mechanism": "运作机制",
        "灵晶用途": "灵晶用途",
        "side_effect": "副作用",
        "economic_chain": "经济链",
        "geography": "地理分布",
        "moral_dilemma": "道德困境",
        "tiers": "境界划分",
        "灵晶与修炼": "灵晶与修炼",
        "beast_tide_connection": "与兽潮的关系",
        "manifestations": "表现形式",
        "rules": "规则",
        "phase_1": "第一阶段",
        "phase_2": "第二阶段",
        "phase_3": "第三阶段",
        "phase_4": "当前阶段",
        "high_concentration": "高浓度",
        "moderate_concentration": "中等浓度",
        "low_concentration": "低浓度",
        "灵衰_explanation": "灵衰的本质",
        # 核心设定 — 基调锚
        "moral_baseline": "道德底色",
        "violence_density": "暴力密度",
        "safety": "安全感",
        "cost_scale": "代价尺度",
        "redemption": "救赎弧线",
        "era_anchor": "时代锚点",
        "story_structure": "故事结构",
        # 核心设定 — 氛围DNA
        "keywords": "关键词",
        "sensory_tags": "感官标签",
        "contrast_principle": "反差原则",
        "anchors": "感官锚点",
        "references": "参考作品",
        # 核心设定 — 禁忌与词汇
        "taboos": "禁忌",
        "vocabulary": "词汇色彩",
        "prefer": "推荐",
        "avoid": "避免",
        "reason": "原因",
        "alternative": "替代方案",
        # 通用 — 行为映射
        "condition": "条件",
        "forbidden": "禁止",
        "example": "示例",
        "violation": "违反示例",
        # 势力 — 补充
        "internal_conflict": "内部冲突",
        "factions": "派系",
        "tension": "紧张关系",
        "writing_guide": "写作指导",
        "type": "类型",
    }

    # 内部字段，渲染时跳过
    _SKIP_KEYS = {"id"}

    def _label(key: str) -> str:
        return _KEY_LABELS.get(key, key)

    lines = []
    heading = "#" * level

    for k, v in data.items():
        if k in _SKIP_KEYS:
            continue
        if _is_empty(v):
            continue

        label = _label(k)

        if isinstance(v, str):
            lines.append(f"{heading} {label}")
            lines.append("")
            lines.append(v)
            lines.append("")

        elif isinstance(v, list):
            lines.append(f"{heading} {label}")
            lines.append("")
            for item in v:
                if isinstance(item, str):
                    lines.append(f"- {item}")
                elif isinstance(item, dict):
                    title_key = None
                    for candidate in ("name", "level", "phase", "tier", "title"):
                        if candidate in item:
                            title_key = candidate
                            break
                    if title_key and title_key in item:
                        lines.append(f"- **{item[title_key]}**")
                        for sk, sv in item.items():
                            if sk == title_key or sk in _SKIP_KEYS:
                                continue
                            if _is_empty(sv):
                                continue
                            if isinstance(sv, str):
                                lines.append(f"  - **{_label(sk)}**: {sv}")
                            elif isinstance(sv, list):
                                sv_strs = [str(x) for x in sv if x]
                                if sv_strs:
                                    lines.append(f"  - **{_label(sk)}**: {', '.join(sv_strs)}")
                            else:
                                lines.append(f"  - **{_label(sk)}**: {sv}")
                    else:
                        lines.extend(_jsonb_to_md(item, 1))
                elif item is not None:
                    lines.append(f"- {item}")
            lines.append("")

        elif isinstance(v, dict):
            lines.append(f"{heading} {label}")
            lines.append("")
            lines.extend(_jsonb_to_md_narrative(v, level + 1))
            lines.append("")

        else:
            lines.append(f"{heading} {label}")
            lines.append("")
            lines.append(str(v))
            lines.append("")

    return lines


def _jsonb_to_md(data, indent=0, title_key: str | None = None) -> list:
    prefix = "    " * indent
    lines = []

    if isinstance(data, dict):
        for k, v in data.items():
            if _is_empty(v):
                # 保留空 list/dict 的键（如 scenes: []），但跳过 None 和空字符串
                if isinstance(v, list) and len(v) == 0:
                    lines.append(f"{prefix}- **{k}**: []")
                elif isinstance(v, dict) and len(v) == 0:
                    lines.append(f"{prefix}- **{k}**: {{}}")
                continue
            if isinstance(v, dict):
                lines.append(f"{prefix}- **{k}**:")
                lines.extend(_jsonb_to_md(v, indent + 1))
            elif isinstance(v, list):
                lines.append(f"{prefix}- **{k}**:")
                lines.extend(_jsonb_to_md(v, indent + 1))
            else:
                lines.append(f"{prefix}- **{k}**: {v}")
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                found_key, title_val = _find_title_key(item)
                # 优先使用调用方指定的 title_key，其次用自动检测的
                effective_key = title_key or found_key
                if effective_key and effective_key in item:
                    title_val = str(item[effective_key])
                    # 使用 HTML 注释标注 title_key，对人类不可见，对解析器可识别
                    # 例如: - **沈野**: <!-- name -->
                    lines.append(f"{prefix}- **{title_val}**: <!-- {effective_key} -->")
                    sub_indent = indent + 1
                    sub_prefix = "    " * sub_indent
                    for k, v in item.items():
                        if k == effective_key:
                            continue
                        if _is_empty(v):
                            if isinstance(v, list) and len(v) == 0:
                                lines.append(f"{sub_prefix}- **{k}**: []")
                            elif isinstance(v, dict) and len(v) == 0:
                                lines.append(f"{sub_prefix}- **{k}**: {{}}")
                            continue
                        if isinstance(v, (dict, list)):
                            lines.append(f"{sub_prefix}- **{k}**:")
                            lines.extend(_jsonb_to_md(v, sub_indent + 1))
                        else:
                            lines.append(f"{sub_prefix}- **{k}**: {v}")
                else:
                    lines.extend(_jsonb_to_md(item, indent))
            elif isinstance(item, str):
                # 保留空字符串，使用占位标记以便逆向解析
                if item == "":
                    lines.append(f"{prefix}- ")  # 空字符串用 "- " 表示
                else:
                    lines.append(f"{prefix}- {item}")
            elif item is not None:
                lines.append(f"{prefix}- {item}")

    return lines


def _md_bullet(key: str, value) -> str | list[str]:
    """将 key-value 渲染为 markdown bullet。list 类型渲染为多行。"""
    if isinstance(value, bool):
        return f"- **{key}**: {'是' if value else '否'}"
    if isinstance(value, (list,)):
        # list 类型渲染为多行 bullet（每个元素一行），而非 JSON 数组
        # 这样 File→DB 解析时重复键可被 _append_or_set 正确收集为 list
        if not value:
            return f"- **{key}**: []"
        lines = []
        for item in value:
            lines.append(f"- **{key}**: {item}")
        return lines
    return f"- **{key}**: {value}"


def _render_md_table(rows: list[dict], columns: list[str] | None = None) -> list[str]:
    """Render a list of dicts as a markdown table."""
    if not rows:
        return []
    if columns is None:
        columns = list(rows[0].keys())
    lines = ['| ' + ' | '.join(columns) + ' |']
    lines.append('|' + '|'.join(['------' for _ in columns]) + '|')
    for row in rows:
        cells = [str(row.get(c, '')).replace('|', '\\|') for c in columns]
        lines.append('| ' + ' | '.join(cells) + ' |')
    return lines


def _parse_json_field(val) -> any:
    """Parse a JSON text field, returning the parsed object or None."""
    if val is None:
        return None
    if isinstance(val, (dict, list)):
        return val
    if isinstance(val, str):
        val = val.strip()
        if not val or val in ('{}', '[]', ''):
            return None
        try:
            return json.loads(val)
        except (json.JSONDecodeError, TypeError):
            return None
    return None

