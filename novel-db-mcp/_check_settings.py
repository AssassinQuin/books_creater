"""Check DB world settings for awakeners"""
import sqlite3, json

db_path = r"D:\code\books_creater\data\novel.db"
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row

# Find entries about awakeners / 参战体系
rows = conn.execute(
    "SELECT id, novel_id, category, name, data, writing_guide FROM world_settings WHERE data LIKE '%觉醒%'"
).fetchall()

print(f"Entries with '觉醒' in data: {len(rows)}")
for r in rows:
    d = dict(r)
    print(f"  ID={d['id']} novel_id={d['novel_id']} cat={d['category']} name={d['name']}")
    data = d.get('data') or ''
    if len(data) > 200:
        print(f"  data (first 200): {data[:200]}")
    else:
        print(f"  data: {data}")
    wg = d.get('writing_guide') or ''
    if wg:
        print(f"  writing_guide: {wg[:200]}")
    print()

# Also search for 参战 or 战场 specifically
rows2 = conn.execute(
    "SELECT id, novel_id, category, name, data FROM world_settings WHERE name LIKE '%参战%' OR name LIKE '%战场%' OR name LIKE '%角色%'"
).fetchall()
print(f"\nEntries about 参战/战场/角色: {len(rows2)}")
for r in rows2:
    d = dict(r)
    print(f"  ID={d['id']} novel_id={d['novel_id']} cat={d['category']} name={d['name']}")

conn.close()
