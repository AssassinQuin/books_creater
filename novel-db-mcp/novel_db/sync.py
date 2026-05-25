import hashlib
import json
import os
import re

from .db import query, PROJECT_ROOT
from .resolvers import _resolve_novel_id

_NOVELS_BASE = os.path.join(PROJECT_ROOT, "novels")

# ============================================================================
# Hash infrastructure (unchanged)
# ============================================================================


def _ensure_data_hashes_table():
    query("""
        CREATE TABLE IF NOT EXISTS data_hashes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            novel_id INTEGER NOT NULL,
            data_type TEXT NOT NULL,
            data_key TEXT NOT NULL,
            db_hash TEXT NOT NULL DEFAULT '',
            file_hash TEXT NOT NULL DEFAULT '',
            db_updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            file_updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(novel_id, data_type, data_key)
        )
    """, fetch="none")


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

