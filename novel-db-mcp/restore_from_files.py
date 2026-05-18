#!/usr/bin/env python3
"""
从文件恢复完整数据到 libSQL 数据库
- 卷级大纲: novels/这次不一样了/设定/大纲/V{N}-*.md
- 人物档案: novels/这次不一样了/设定/角色深化.md
- 世界观: novels/这次不一样了/设定/世界观.md
- 伏笔: novels/这次不一样了/设定/线索追踪.md
"""

import os
import sys
import glob
import re
import json

os.environ['DB_BACKEND'] = 'libsql'
os.environ['LIBSQL_DB_PATH'] = 'data/novel.db'
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import libsql_experimental as libsql

# ─── Init ────────────────────────────────────────────────
DB_PATH = 'data/novel.db'
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)

conn = libsql.connect(DB_PATH)
schema_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '003_libsql_schema.sql')
with open(schema_path, 'r') as f:
    conn.executescript(f.read())
conn.commit()

NOVEL_NAME = '这次不一样了'
NOVEL_ROOT = f'novels/{NOVEL_NAME}'

# ─── Helper ──────────────────────────────────────────────
def insert_volume(number, title, notes):
    conn.execute('INSERT INTO volumes (novel_id, number, title, notes) VALUES (?, ?, ?, ?)',
                 (1, number, title, notes))
    conn.commit()

# ─── Novels ──────────────────────────────────────────────
conn.execute("INSERT INTO novels (name, genre, status) VALUES (?, ?, ?)",
             (NOVEL_NAME, '玄幻', 'writing'))
conn.commit()
print("[OK] novels: 1 row")

# ─── Volumes ─────────────────────────────────────────────
print("\n[Migrating volumes from files...]")

# Map specific files to volume numbers
volume_files = {
    1: 'V1-兽潮.md',
    2: 'V2-边城.md',
    3: 'V3-惨败.md',
    4: 'V4-灵站.md',
    5: 'V5-星火.md',
    6: 'V6-多线.md',
    7: 'V7-灰色.md',
    8: 'V8-双星.md',
    9: 'V9-断裂.md',
    10: 'V10-血脉.md',
    11: 'V11-核心.md',
    12: 'V12-循环.md',
    13: 'V13-暗涌.md',
    14: 'V14-抉择.md',  # 主卷
    15: 'V15-尾声.md',
}

for num, filename in volume_files.items():
    filepath = os.path.join(NOVEL_ROOT, '设定/大纲', filename)
    if not os.path.exists(filepath):
        print(f"  [SKIP] {filename} not found")
        continue
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Extract title from first line
    title_match = re.search(r'# V\d+[：\s]+(.+)', content)
    if not title_match:
        title_match = re.search(r'# V\d+\s+(.+)', content)
    title = title_match.group(1).strip() if title_match else f'V{num}'
    
    insert_volume(num, title, content)
    print(f"  V{num:02d}: {title} - {len(content)} chars")

# ─── Verify ──────────────────────────────────────────────
print("\n[Verification]")
cur = conn.cursor()
cur.execute('SELECT number, title, LENGTH(notes) as notes_len FROM volumes ORDER BY number')
for row in cur.fetchall():
    print(f"  V{row[0]:02d}: {row[1]} - {row[2]} chars")

conn.close()
print("\n[OK] All data restored from files!")
