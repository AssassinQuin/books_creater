"""DB 数据恢复脚本：从文件同步到 DB"""
import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "novel-db-mcp"))
os.environ["DB_BACKEND"] = "libsql"
os.environ["LIBSQL_DB_PATH"] = os.path.join(os.path.dirname(__file__), "data", "novel.db")

from novel_db.db import query
from novel_db.sync_engine import engine

NOVEL_NAME = "这次不一样了"

# 1. 检查并创建小说记录
rows = query("SELECT id, name FROM novels WHERE name = ?", (NOVEL_NAME,))
if rows:
    print(f"[OK] 小说已存在: ID={rows[0]['id']}, name={rows[0]['name']}")
else:
    query("INSERT INTO novels (name, genre, status) VALUES (?, ?, ?)",
          (NOVEL_NAME, "玄幻", "planning"))
    rows = query("SELECT id, name FROM novels WHERE name = ?", (NOVEL_NAME,))
    print(f"[创建] 小说 ID={rows[0]['id']}")

# 2. 按类型依次从文件同步到 DB
types = ["character", "relation", "world", "volume", "volume_core", "volume_analysis", "foreshadow", "echo"]
for etype in types:
    if etype not in engine.available_types:
        print(f"[跳过] {etype} (未注册)")
        continue
    print(f"[同步] {etype} ...", end=" ", flush=True)
    try:
        r = engine.files_to_db(NOVEL_NAME, etype)
        synced = len(r.get("details", []))
        errors = r.get("error_count", 0) or len(r.get("errors", []))
        print(f"✓ 同步 {synced} 条, 错误 {errors}")
        if errors:
            for err in r.get("errors", []):
                print(f"   ⚠ {err}")
    except Exception as e:
        print(f"✗ 失败: {e}")

# 3. 最终统计
print("\n=== 恢复后统计 ===")
tables = ["characters", "world_settings", "volumes", "foreshadows", "echoes", "character_relations"]
for t in tables:
    cnt = query(f"SELECT COUNT(*) as c FROM {t}")[0]["c"]
    print(f"  {t}: {cnt} 条")
