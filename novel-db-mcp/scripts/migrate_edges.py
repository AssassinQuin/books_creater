#!/usr/bin/env python3
"""一次性迁移脚本：从现有数据生成 entity_edges 边。

数据源 → 边类型映射：
  character_relations → character_relation
  characters.faction_id → belongs_to_faction
  world_settings.related_ids → related_setting
  world_settings(category=ability) keys 含角色名 → has_ability
  foreshadows.planted_chapter_id → planted_in
  foreshadows.actual_recall_chapter_id → recalled_in
  foreshadows.related_characters → relates_character
  chapter_summaries.characters_involved → appears_in
  echoes → source_of_echo

用法：
  python scripts/migrate_edges.py [--db-path data/novel.db] [--dry-run]
"""
import json
import os
import sys
import sqlite3


def upsert_edge(conn, novel_id, from_type, from_id, to_type, to_id, edge_type,
                weight=1.0, metadata=None):
    conn.execute(
        "INSERT INTO entity_edges (novel_id, from_type, from_id, to_type, to_id, edge_type, weight, metadata) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?) "
        "ON CONFLICT (novel_id, from_type, from_id, to_type, to_id, edge_type) DO UPDATE SET "
        "weight = ?, metadata = ?",
        (novel_id, from_type, from_id, to_type, to_id, edge_type, weight, metadata,
         weight, metadata),
    )


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
    conn.execute("PRAGMA foreign_keys = ON")

    try:
        conn.execute("SELECT 1 FROM entity_edges LIMIT 1")
    except sqlite3.OperationalError:
        print("entity_edges table not found. Run schema migration first.")
        sys.exit(1)

    if not dry_run:
        conn.execute("DELETE FROM entity_edges")

    counts = {}

    # 1. character_relations → character_relation
    rows = conn.execute(
        "SELECT novel_id, from_character_id, to_character_id, relation_type, intensity "
        "FROM character_relations"
    ).fetchall()
    for r in rows:
        weight = (r[4] / 10.0) if r[4] else 0.5
        metadata = json.dumps({"relation_type": r[3]}, ensure_ascii=False)
        if not dry_run:
            upsert_edge(conn, r[0], "character", r[1], "character", r[2],
                        "character_relation", weight, metadata)
        counts["character_relation"] = counts.get("character_relation", 0) + 1

    # 2. characters.faction_id → belongs_to_faction
    rows = conn.execute(
        "SELECT id, novel_id, faction_id FROM characters WHERE faction_id IS NOT NULL"
    ).fetchall()
    for r in rows:
        if not dry_run:
            upsert_edge(conn, r[1], "character", r[0], "world_setting", r[2],
                        "belongs_to_faction")
        counts["belongs_to_faction"] = counts.get("belongs_to_faction", 0) + 1

    # 3. world_settings.related_ids → related_setting
    rows = conn.execute(
        "SELECT id, novel_id, related_ids FROM world_settings WHERE related_ids IS NOT NULL"
    ).fetchall()
    for r in rows:
        raw = r[2]
        if not raw:
            continue
        try:
            related = json.loads(raw) if isinstance(raw, str) else raw
        except (json.JSONDecodeError, TypeError):
            continue
        if not isinstance(related, list):
            continue
        for rid in related:
            if rid:
                if not dry_run:
                    upsert_edge(conn, r[1], "world_setting", r[0], "world_setting", rid,
                                "related_setting")
                counts["related_setting"] = counts.get("related_setting", 0) + 1

    # 4. world_settings(category=ability) keys 含角色名 → has_ability
    rows = conn.execute(
        "SELECT id, novel_id, keys FROM world_settings WHERE category = 'ability' AND keys IS NOT NULL"
    ).fetchall()
    for r in rows:
        raw = r[2]
        if not raw:
            continue
        try:
            keys = json.loads(raw) if isinstance(raw, str) else raw
        except (json.JSONDecodeError, TypeError):
            continue
        if not isinstance(keys, list):
            continue
        for k in keys:
            char = conn.execute(
                "SELECT id FROM characters WHERE novel_id = ? AND name = ?",
                (r[1], k)
            ).fetchone()
            if char:
                if not dry_run:
                    upsert_edge(conn, r[1], "character", char[0], "world_setting", r[0],
                                "has_ability")
                counts["has_ability"] = counts.get("has_ability", 0) + 1

    # 5. foreshadows.planted_chapter_id → planted_in
    rows = conn.execute(
        "SELECT id, novel_id, planted_chapter_id FROM foreshadows WHERE planted_chapter_id IS NOT NULL"
    ).fetchall()
    for r in rows:
        if not dry_run:
            upsert_edge(conn, r[1], "foreshadow", r[0], "chapter", r[2], "planted_in")
        counts["planted_in"] = counts.get("planted_in", 0) + 1

    # 6. foreshadows.actual_recall_chapter_id → recalled_in
    rows = conn.execute(
        "SELECT id, novel_id, actual_recall_chapter_id FROM foreshadows WHERE actual_recall_chapter_id IS NOT NULL"
    ).fetchall()
    for r in rows:
        if not dry_run:
            upsert_edge(conn, r[1], "foreshadow", r[0], "chapter", r[2], "recalled_in")
        counts["recalled_in"] = counts.get("recalled_in", 0) + 1

    # 7. foreshadows.related_characters → relates_character
    rows = conn.execute(
        "SELECT id, novel_id, related_characters FROM foreshadows WHERE related_characters IS NOT NULL"
    ).fetchall()
    for r in rows:
        raw = r[2]
        if not raw:
            continue
        try:
            chars = json.loads(raw) if isinstance(raw, str) else raw
        except (json.JSONDecodeError, TypeError):
            continue
        if not isinstance(chars, list):
            continue
        for cid in chars:
            if cid:
                if not dry_run:
                    upsert_edge(conn, r[1], "foreshadow", r[0], "character", cid,
                                "relates_character")
                counts["relates_character"] = counts.get("relates_character", 0) + 1

    # 8. chapter_summaries.characters_involved → appears_in
    rows = conn.execute(
        "SELECT chapter_id, characters_involved FROM chapter_summaries WHERE characters_involved IS NOT NULL"
    ).fetchall()
    for r in rows:
        raw = r[1]
        if not raw:
            continue
        try:
            chars = json.loads(raw) if isinstance(raw, str) else raw
        except (json.JSONDecodeError, TypeError):
            continue
        if not isinstance(chars, list):
            continue
        chapter = conn.execute("SELECT novel_id FROM chapters WHERE id = ?", (r[0],)).fetchone()
        if not chapter:
            continue
        for cid in chars:
            if cid:
                if not dry_run:
                    upsert_edge(conn, chapter[0], "character", cid, "chapter", r[0],
                                "appears_in")
                counts["appears_in"] = counts.get("appears_in", 0) + 1

    # 9. echoes → source_of_echo
    rows = conn.execute(
        "SELECT id, novel_id, source_chapter_id, echo_chapter_id FROM echoes"
    ).fetchall()
    for r in rows:
        if r[2] and r[3]:
            if not dry_run:
                upsert_edge(conn, r[1], "chapter", r[2], "chapter", r[3], "source_of_echo")
            counts["source_of_echo"] = counts.get("source_of_echo", 0) + 1

    if not dry_run:
        conn.commit()
    conn.close()

    total = sum(counts.values())
    print(f"Edge migration complete. Total edges: {total}")
    for etype, cnt in sorted(counts.items()):
        print(f"  {etype}: {cnt}")
    if dry_run:
        print("(dry-run mode, no changes written)")


if __name__ == "__main__":
    main()
