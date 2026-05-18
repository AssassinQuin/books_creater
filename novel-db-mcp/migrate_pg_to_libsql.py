#!/usr/bin/env python3
"""
迁移脚本：PostgreSQL -> libSQL (本地 SQLite)
用法:
    # 1. 确保 PostgreSQL 可连接（默认使用 DATABASE_URL 环境变量）
    # 2. 运行迁移
    cd novel-db-mcp && python migrate_pg_to_libsql.py

    # 或使用自定义路径
    LIBSQL_DB_PATH=../data/novel.db python migrate_pg_to_libsql.py
"""

import os
import sys
import json

# ─── Configuration ───────────────────────────────────────
PG_DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql:///fcli")
LIBSQL_PATH = os.environ.get(
    "LIBSQL_DB_PATH",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "novel.db")
)

# ─── Connect PostgreSQL ──────────────────────────────────
import psycopg2
import psycopg2.extras

pg_conn = psycopg2.connect(PG_DATABASE_URL)
pg_cur = pg_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

# ─── Connect libSQL ──────────────────────────────────────
import libsql_experimental as libsql

os.makedirs(os.path.dirname(LIBSQL_PATH), exist_ok=True)
libsql_conn = libsql.connect(LIBSQL_PATH)
libsql_cur = libsql_conn.cursor()

# ─── Initialize libSQL Schema ────────────────────────────
schema_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "003_libsql_schema.sql")
with open(schema_path, "r") as f:
    libsql_conn.executescript(f.read())
libsql_conn.commit()
print(f"[OK] Schema initialized in {LIBSQL_PATH}")

# ─── Migration Helper ────────────────────────────────────
def _adapt_value(val):
    """Convert PostgreSQL value to libSQL-compatible value."""
    if val is None:
        return None
    if isinstance(val, bool):
        return int(val)
    if isinstance(val, (list, dict)):
        return json.dumps(val, ensure_ascii=False)
    if isinstance(val, str):
        # Handle PostgreSQL array string representation '{a,b,c}'
        if val.startswith("{") and val.endswith("}"):
            try:
                items = val[1:-1].split(",")
                return json.dumps([i.strip().strip('"') for i in items if i.strip()], ensure_ascii=False)
            except:
                pass
        return val
    # Convert datetime to ISO string
    from datetime import datetime
    if isinstance(val, datetime):
        return val.isoformat()
    return val


def migrate_table(table_name, columns, pk_column="id"):
    """Migrate a single table from PostgreSQL to libSQL."""
    print(f"\n[Migrating] {table_name}...")

    # Fetch from PostgreSQL
    pg_cur.execute(f"SELECT * FROM {table_name}")
    rows = pg_cur.fetchall()

    if not rows:
        print(f"  [SKIP] No data in {table_name}")
        return 0

    # Build INSERT statement
    col_names = list(rows[0].keys())
    placeholders = ",".join(["?"] * len(col_names))
    insert_sql = f"INSERT INTO {table_name} ({','.join(col_names)}) VALUES ({placeholders})"

    # For tables with AUTOINCREMENT, we need to handle id conflicts
    # SQLite will auto-assign if we omit the id, but let's preserve IDs
    # by setting the sequence after insertion
    has_serial_pk = pk_column in col_names and pk_column == "id"

    count = 0
    max_id = 0
    for row in rows:
        values = [_adapt_value(row[col]) for col in col_names]
        if has_serial_pk and row[pk_column]:
            max_id = max(max_id, row[pk_column])
        try:
            libsql_cur.execute(insert_sql, tuple(values))
            count += 1
        except Exception as e:
            print(f"  [ERROR] Failed to insert row {row.get(pk_column, '?')}: {e}")
            print(f"          Values: {values}")

    libsql_conn.commit()
    print(f"  [OK] Migrated {count}/{len(rows)} rows")

    # Update SQLite sequence for auto-increment
    if has_serial_pk and max_id > 0:
        try:
            libsql_cur.execute(
                "INSERT OR REPLACE INTO sqlite_sequence (name, seq) VALUES (?, ?)",
                (table_name, max_id)
            )
            libsql_conn.commit()
        except:
            pass  # sqlite_sequence might not exist for this table

    return count


# ─── Run Migrations ──────────────────────────────────────
print("=" * 60)
print("PostgreSQL -> libSQL Migration")
print(f"Source: {PG_DATABASE_URL}")
print(f"Target: {LIBSQL_PATH}")
print("=" * 60)

tables = [
    ("novels", "id"),
    ("volumes", "id"),
    ("chapters", "id"),
    ("characters", "id"),
    ("character_relations", "id"),
    ("character_state_snapshots", "id"),
    ("character_distillation_evolution", "id"),
    ("world_settings", "id"),
    ("chapter_summaries", "chapter_id"),
    ("foreshadows", "id"),
    ("timeline_events", "id"),
    ("scene_outlines", "id"),
    ("dimension_changes", "id"),
    ("chapter_quality", "id"),
]

total_rows = 0
for table_name, pk in tables:
    total_rows += migrate_table(table_name, None, pk)

print("\n" + "=" * 60)
print(f"Migration complete! Total rows migrated: {total_rows}")
print(f"Target database: {LIBSQL_PATH}")
print("=" * 60)

# ─── Verify ──────────────────────────────────────────────
print("\n[Verification]")
for table_name, _ in tables:
    libsql_cur.execute(f"SELECT COUNT(*) FROM {table_name}")
    count = libsql_cur.fetchone()[0]
    print(f"  {table_name}: {count} rows")

pg_cur.close()
pg_conn.close()
libsql_conn.close()
