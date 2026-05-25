#!/usr/bin/env python3
"""一次性迁移脚本：清洗 world_settings.data 字段中的 metadata 冗余。

问题：sync_lorebook 和 SyncEngine 两条路径把 metadata（keys/tags/related 等）
混存在 data JSON 字段里，且每轮同步追加不覆盖，导致 keys/tags 重复 2-3 次。
metadata 还同时存在于独立列（keys, tags, related_ids），形成双重冗余。

修复：从 data 中移除 META_BLACKLIST 中的字段，只保留内容字段。

用法：
  python scripts/migrate_clean_data.py [--db-path data/novel.db] [--dry-run]
"""
import json
import os
import sys
import sqlite3

META_BLACKLIST = {
    "keys", "secondary_keys", "tags", "related", "region",
    "volume_range", "priority", "is_constant", "writing_guide",
    "lorebook_id", "faction_id", "锁定", "关联设定", "叙事功能",
}


def clean_data(raw_data):
    if isinstance(raw_data, list):
        content_items = []
        content_fields = {}
        for item in raw_data:
            if isinstance(item, dict):
                if set(item.keys()) & META_BLACKLIST:
                    continue
                content_fields.update(item)
            elif isinstance(item, str) and item.strip():
                content_items.append(item.strip())
        result = {}
        if content_fields:
            result.update(content_fields)
        if content_items:
            result["content"] = "\n".join(content_items)
        return result if result else raw_data
    elif isinstance(raw_data, dict):
        return {k: v for k, v in raw_data.items() if k not in META_BLACKLIST}
    return raw_data


def main():
    db_path = os.environ.get("LIBSQL_DB_PATH", "data/novel.db")
    if not os.path.isabs(db_path):
        db_path = os.path.abspath(db_path)

    dry_run = "--dry-run" in sys.argv
    if "--db-path" in sys.argv:
        idx = sys.argv.index("--db-path")
        if idx + 1 < len(sys.argv):
            db_path = sys.argv[idx + 1]

    if not os.path.exists(db_path):
        print(f"DB not found: {db_path}")
        sys.exit(1)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    rows = conn.execute("SELECT id, data FROM world_settings").fetchall()
    total = len(rows)
    cleaned = 0
    total_before = 0
    total_after = 0

    for row in rows:
        raw = row["data"]
        if not raw:
            continue
        try:
            parsed = json.loads(raw) if isinstance(raw, str) else raw
        except (json.JSONDecodeError, TypeError):
            continue

        if not isinstance(parsed, (dict, list)):
            continue

        before_len = len(json.dumps(parsed, ensure_ascii=False))
        total_before += before_len

        cleaned_data = clean_data(parsed)

        if cleaned_data == parsed:
            total_after += before_len
            continue

        after_len = len(json.dumps(cleaned_data, ensure_ascii=False))
        total_after += after_len
        cleaned += 1

        if not dry_run:
            conn.execute(
                "UPDATE world_settings SET data = ? WHERE id = ?",
                (json.dumps(cleaned_data, ensure_ascii=False), row["id"]),
            )

    if not dry_run and cleaned > 0:
        conn.commit()
    conn.close()

    reduction = total_before - total_after
    pct = (reduction / total_before * 100) if total_before > 0 else 0

    print(f"Total records: {total}")
    print(f"Cleaned: {cleaned}")
    print(f"Size before: {total_before:,} chars")
    print(f"Size after:  {total_after:,} chars")
    print(f"Reduction:   {reduction:,} chars ({pct:.1f}%)")
    if dry_run:
        print("(dry-run mode, no changes written)")


if __name__ == "__main__":
    main()
