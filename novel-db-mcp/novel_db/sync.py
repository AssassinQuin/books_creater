import hashlib
import json
import os
import re

from .db import query, PROJECT_ROOT
from .resolvers import _resolve_novel_id

_NOVELS_BASE = os.path.join(PROJECT_ROOT, "novels")


def _ensure_data_hashes_table():
    query("""
        CREATE TABLE IF NOT EXISTS data_hashes (
            id SERIAL PRIMARY KEY,
            novel_id INTEGER NOT NULL,
            data_type TEXT NOT NULL,
            data_key TEXT NOT NULL,
            db_hash TEXT NOT NULL DEFAULT '',
            file_hash TEXT NOT NULL DEFAULT '',
            db_updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
            file_updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
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
            "VALUES (%s, %s, %s, %s, NOW()) "
            "ON CONFLICT (novel_id, data_type, data_key) DO UPDATE SET db_hash = %s, db_updated_at = NOW()",
            (novel_id, data_type, data_key, db_hash, db_hash), fetch="none"
        )
    elif file_hash and not db_hash:
        query(
            "INSERT INTO data_hashes (novel_id, data_type, data_key, file_hash, file_updated_at) "
            "VALUES (%s, %s, %s, %s, NOW()) "
            "ON CONFLICT (novel_id, data_type, data_key) DO UPDATE SET file_hash = %s, file_updated_at = NOW()",
            (novel_id, data_type, data_key, file_hash, file_hash), fetch="none"
        )
    else:
        sets = []
        vals = []
        if db_hash:
            sets.append("db_hash = %s")
            sets.append("db_updated_at = NOW()")
            vals.append(db_hash)
        if file_hash:
            sets.append("file_hash = %s")
            sets.append("file_updated_at = NOW()")
            vals.append(file_hash)
        if not sets:
            return
        vals.extend([novel_id, data_type, data_key])
        query(
            f"INSERT INTO data_hashes (novel_id, data_type, data_key, {', '.join(['db_hash','file_hash'][:len(sets)])}) "
            f"VALUES (%s, %s, %s, {', '.join(['%s','%s'][:len(sets)])}) "
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


def _sync_world_to_file(novel_id: int, novel_name: str, category: str, name: str, data: dict):
    base = os.path.join(_NOVELS_BASE, novel_name, "设定", "世界观")
    os.makedirs(base, exist_ok=True)

    category_file_map = {
        "core_setting": "核心设定.md",
        "bestiary": "异灵图鉴.md",
        "ability": "能力体系.md",
        "item": "物品装备.md",
        "economy": "经济体系.md",
        "daily_life": "日常生活.md",
        "history": "历史事件.md",
        "location": "地图.md",
        "faction": "势力.md",
        "race": "种族.md",
    }
    target_file = category_file_map.get(category, f"{category}.md")
    fpath = os.path.join(base, target_file)

    meta = {k: v for k, v in data.items() if k != "content"}
    lines = [f"\n## {category}: {name}\n"]
    for key, val in meta.items():
        if isinstance(val, (list, dict)):
            val_str = json.dumps(val, ensure_ascii=False)
        else:
            val_str = str(val)
        lines.append(f"- **{key}**: {val_str}")
    if data.get("content"):
        lines.append("")
        lines.append(data["content"])
    entry_text = "\n".join(lines) + "\n"

    if os.path.exists(fpath):
        with open(fpath, "r", encoding="utf-8") as f:
            content = f.read()
        marker = f"## {category}: {name}"
        if marker in content:
            start = content.index(marker)
            next_h2 = content.find("\n## ", start + len(marker))
            if next_h2 == -1:
                next_h2 = len(content)
            content = content[:start] + entry_text + content[next_h2:]
        else:
            content += entry_text
    else:
        title = target_file.replace(".md", "")
        content = f"# {title}\n{entry_text}"

    with open(fpath, "w", encoding="utf-8") as f:
        f.write(content)
    _record_file_hash(novel_id, "world", f"{category}:{name}", content)


def _sync_character_to_file(novel_id: int, novel_name: str, char: dict):
    base = os.path.join(_NOVELS_BASE, novel_name, "设定", "人物")
    os.makedirs(base, exist_ok=True)
    fpath = os.path.join(base, f"{char['name']}.md")
    lines = [f"# {char['name']}\n"]
    for k, v in char.items():
        if k in ("id", "novel_id", "created_at", "updated_at"):
            continue
        if v and v != "{}" and v != "[]" and v != "":
            lines.append(f"- **{k}**: {v}")
    content = "\n".join(lines) + "\n"
    with open(fpath, "w", encoding="utf-8") as f:
        f.write(content)
    _record_file_hash(novel_id, "character", char["name"], content)


def _sync_foreshadow_to_file(novel_id: int, novel_name: str, fs: dict):
    base = os.path.join(_NOVELS_BASE, novel_name, "设定", "大纲")
    os.makedirs(base, exist_ok=True)
    fpath = os.path.join(base, "伏笔清单.md")
    entry = f"- [{fs['status']}] {fs['description']} (id:{fs['id']}"
    if fs.get("planned_recall_chapter"):
        entry += f", 计划回收:Ch{fs['planned_recall_chapter']}"
    entry += ")\n"
    if os.path.exists(fpath):
        with open(fpath, "r", encoding="utf-8") as f:
            content = f.read()
        marker = f"(id:{fs['id']}"
        if marker in content:
            start = content.index(marker)
            line_start = content.rfind("\n- ", 0, start) + 1
            line_end = content.find("\n", start)
            content = content[:line_start] + entry + content[line_end:]
        else:
            content += entry
    else:
        content = f"# 伏笔清单\n{entry}"
    with open(fpath, "w", encoding="utf-8") as f:
        f.write(content)
    _record_file_hash(novel_id, "foreshadow", str(fs["id"]), content)


def _sync_world_to_db(novel_id: int, category: str, name: str, file_content: str):
    data = {"content": file_content[:4000]}
    data_json = json.dumps(data, ensure_ascii=False)
    query(
        "INSERT INTO world_settings (novel_id, category, name, data) "
        "VALUES (%s, %s, %s, %s) "
        "ON CONFLICT (novel_id, category, name) DO UPDATE SET data = %s, updated_at = NOW()",
        (novel_id, category, name, data_json, data_json), fetch="none"
    )
    _record_db_hash(novel_id, "world", f"{category}:{name}", data_json)


def _sync_character_to_db(novel_id: int, char_name: str, file_content: str):
    existing = query(
        "SELECT id FROM characters WHERE novel_id = %s AND name = %s",
        (novel_id, char_name), fetch="one"
    )
    if existing:
        data = {"content": file_content[:4000]}
        data_json = json.dumps(data, ensure_ascii=False)
        query(
            "UPDATE characters SET status = %s, updated_at = NOW() WHERE id = %s",
            (data_json, existing["id"]), fetch="none"
        )
        _record_db_hash(novel_id, "character", char_name, data_json)


def _sync_foreshadow_to_db(novel_id: int, fs_id: int, status: str, file_content: str):
    if status == "recalled":
        query(
            "UPDATE foreshadows SET status = 'recalled', updated_at = NOW() WHERE id = %s",
            (fs_id,), fetch="none"
        )
    _record_db_hash(novel_id, "foreshadow", str(fs_id), file_content)
