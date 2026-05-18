#!/usr/bin/env python3
"""
DB → 文件 同步脚本
将数据库中的世界观数据同步到 Markdown 文件
"""

import json
import os
import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "novel.db"
NOVEL_DIR = PROJECT_ROOT / "novels/这次不一样了"
WORLD_DIR = NOVEL_DIR / "设定" / "世界观"

# Category → file mapping
CATEGORY_FILES = {
    "core_setting": "核心设定.md",
    "bestiary": "异灵图鉴.md",
    "ability": "物品装备.md",  # abilities are items too
    "item": "物品装备.md",
    "building": "building.md",
    "culture": "culture.md",
    "plant": "plant.md",
    "economy": "经济体系.md",
    "daily_life": "日常生活.md",
    "history": "历史事件.md",
    "location": "地图.md",
    "faction": "势力.md",
    "race": "种族.md",
    "location_detail": "地点细节.md",
    "character": "人物状态.md",
}


def is_empty(v) -> bool:
    if v is None:
        return True
    if isinstance(v, str):
        return v.strip() == "" or v in ("{}", "[]")
    if isinstance(v, (dict, list)):
        return len(v) == 0
    return False


def md_bullet(key: str, value) -> str:
    if isinstance(value, bool):
        return f"- **{key}**: {'是' if value else '否'}"
    if isinstance(value, list):
        return f"- **{key}**: {json.dumps(value, ensure_ascii=False)}"
    return f"- **{key}**: {value}"


def jsonb_to_md(data, indent=0) -> list:
    prefix = "    " * indent
    lines = []
    if isinstance(data, dict):
        for k, v in data.items():
            if is_empty(v):
                continue
            if k == "content":
                continue
            if isinstance(v, dict):
                lines.append(f"{prefix}- **{k}**:")
                lines.extend(jsonb_to_md(v, indent + 1))
            elif isinstance(v, list):
                lines.append(f"{prefix}- **{k}**:")
                lines.extend(jsonb_to_md(v, indent + 1))
            else:
                lines.append(f"{prefix}- **{k}**: {v}")
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                for k, v in item.items():
                    if is_empty(v):
                        continue
                    if isinstance(v, (dict, list)):
                        lines.append(f"{prefix}- **{k}**:")
                        lines.extend(jsonb_to_md(v, indent + 1))
                    else:
                        lines.append(f"{prefix}- **{k}**: {v}")
            elif isinstance(item, str):
                lines.append(f"{prefix}- {item}")
            elif item is not None:
                lines.append(f"{prefix}- {item}")
    return lines


def build_entry(category: str, name: str, row: dict) -> str:
    """Build a markdown section for a single world_settings entry."""
    lines = [f"\n## {category}: {name}\n"]
    
    # Metadata fields
    meta_items = [
        ("keys", row.get("keys")),
        ("secondary_keys", row.get("secondary_keys")),
        ("tags", row.get("tags")),
        ("related", row.get("related_ids")),
        ("volume_range", row.get("volume_range")),
        ("writing_guide", row.get("writing_guide")),
    ]
    for key, val in meta_items:
        if is_empty(val):
            continue
        lines.append(md_bullet(key, val))
    
    priority = row.get("priority")
    if priority is not None and priority != 30:
        lines.append(f"- **priority**: {priority}")
    if row.get("is_constant"):
        lines.append("- **is_constant**: 是")
    
    # Data JSONB fields
    data = row.get("data") or {}
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except (json.JSONDecodeError, TypeError):
            data = {"content": data}
    
    if data:
        for k, v in data.items():
            if k == "content":
                continue
            if is_empty(v):
                continue
            if isinstance(v, (dict, list)):
                lines.append(f"- **{k}**:")
                lines.extend(jsonb_to_md(v, 1))
            elif isinstance(v, bool):
                lines.append(f"- **{k}**: {'是' if v else '否'}")
            else:
                lines.append(f"- **{k}**: {v}")
    
    # Narrative content
    content_text = data.get("content", "") if isinstance(data, dict) else ""
    if content_text:
        lines.append("")
        lines.append(content_text)
    
    return "\n".join(lines) + "\n"


def sync_category(conn, category: str, target_file: str):
    """Sync all entries of a category to its file."""
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM world_settings WHERE novel_id=1 AND category=? ORDER BY name', (category,))
    rows = cursor.fetchall()
    
    if not rows:
        return 0
    
    fpath = WORLD_DIR / target_file
    
    # Build full file content
    title = target_file.replace(".md", "")
    sections = [f"# {title}\n"]
    
    for row in rows:
        row_dict = dict(row)
        entry = build_entry(category, row_dict["name"], row_dict)
        sections.append(entry)
    
    content = "\n".join(sections) + "\n"
    
    # Write file
    os.makedirs(WORLD_DIR, exist_ok=True)
    with open(fpath, "w", encoding="utf-8") as f:
        f.write(content)
    
    return len(rows)


def main():
    print("=" * 60)
    print("DB → 文件 同步")
    print("=" * 60)
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    total = 0
    for category, target_file in CATEGORY_FILES.items():
        count = sync_category(conn, category, target_file)
        if count > 0:
            print(f"  {category} → {target_file} ({count} 条)")
            total += count
    
    conn.close()
    
    print(f"\n同步完成！共 {total} 条设定写入文件")
    print(f"文件目录: {WORLD_DIR}")


if __name__ == "__main__":
    main()
