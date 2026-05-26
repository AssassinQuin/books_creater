"""Check EXPLAIN QUERY PLAN for common patterns to find missing indexes."""
import sqlite3

DB = r"D:\code\books_creater\novel-db-mcp\data\novel.db"
conn = sqlite3.connect(DB)

queries = [
    # character_batch_detail: relations by novel_id + character_ids
    ("character_batch_detail relations",
     "SELECT cr.relation_type, cr.description, cr.intensity "
     "FROM character_relations cr "
     "WHERE cr.novel_id = ? AND (cr.from_character_id = ? OR cr.to_character_id = ?) "
     "AND cr.status = 'active'"),
    # world_query: search by category
    ("world_query by category",
     "SELECT * FROM world_settings WHERE novel_id = ? AND category = ?"),
    # foreshadow_list: all for novel
    ("foreshadow_list",
     "SELECT * FROM foreshadows WHERE novel_id = ?"),
    # timeline_query
    ("timeline_query",
     "SELECT * FROM timeline_events WHERE novel_id = ?"),
    # scene_list
    ("scene_list",
     "SELECT * FROM scene_outlines WHERE novel_id = ?"),
    # health_check: aggregate foreshadows
    ("health_check foreshadow count",
     "SELECT status, COUNT(*) FROM foreshadows WHERE novel_id = ? GROUP BY status"),
]

for label, sql in queries:
    print(f"\n=== {label} ===")
    print(f"SQL: {sql[:100]}...")
    try:
        plan = conn.execute(f"EXPLAIN QUERY PLAN {sql}", (1,)).fetchall()
        for row in plan:
            print(f"  {row}")
    except Exception as e:
        print(f"  Error: {e}")

# Check existing indexes
print("\n\n=== EXISTING INDEXES ===")
indexes = conn.execute(
    "SELECT name, sql FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%' "
    "ORDER BY name"
).fetchall()
for name, sql in indexes:
    print(f"  {name}")

conn.close()
print("\nDone.")
