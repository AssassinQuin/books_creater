import os
import json
from typing import Any

from fastmcp import FastMCP

PROJECT_ROOT = os.path.abspath(os.environ.get(
    "NOVEL_PROJECT_ROOT",
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
))

_raw_db_path = os.environ.get(
    "LIBSQL_DB_PATH",
    os.path.join(PROJECT_ROOT, "data", "novel.db")
)
LIBSQL_DB_PATH = _raw_db_path if os.path.isabs(_raw_db_path) else os.path.abspath(os.path.join(PROJECT_ROOT, _raw_db_path))

mcp = FastMCP("novel-db", instructions="网文小说创作数据库 MCP，管理小说项目、世界观、人物、章节、伏笔、时间线等结构化数据。")

import sqlite3

os.makedirs(os.path.dirname(LIBSQL_DB_PATH), exist_ok=True)

def get_conn():
    return sqlite3.connect(LIBSQL_DB_PATH)

def _adapt_param(p):
    if p is None:
        return None
    if isinstance(p, bool):
        return int(p)
    if isinstance(p, (list, dict)):
        return json.dumps(p, ensure_ascii=False)
    return p

def query(sql: str, params: tuple = (), fetch: str = "all") -> Any:
    adapted_params = tuple(_adapt_param(p) for p in params)

    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(sql, adapted_params)

        if fetch == "none":
            conn.commit()
            return None

        if fetch == "insert":
            conn.commit()
            return {"id": cur.lastrowid}

        if fetch == "one":
            row = cur.fetchone()
            if row is None:
                return None
            columns = [desc[0] for desc in cur.description] if cur.description else []
            return {col: row[i] for i, col in enumerate(columns)}

        if fetch == "val":
            row = cur.fetchone()
            if row is None:
                return None
            return row[0]

        rows = cur.fetchall()
        if not rows:
            return []
        columns = [desc[0] for desc in cur.description] if cur.description else []
        return [{col: row[i] for i, col in enumerate(columns)} for row in rows]

    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def get_novel_config(novel_id: int, config_type: str, name: str, default=None):
    row = query(
        "SELECT data FROM novel_config WHERE novel_id = ? AND config_type = ? AND name = ?",
        (novel_id, config_type, name), fetch="one"
    )
    if not row or not row.get("data"):
        return default
    raw = row["data"]
    if isinstance(raw, (dict, list)):
        return raw
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except Exception:
            return raw
    return default
