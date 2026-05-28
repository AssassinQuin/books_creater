import atexit
import os
import json
import threading
from contextlib import contextmanager
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

_local = threading.local()
_db_initialized = False
_db_init_lock = threading.Lock()


def _init_db_schema(conn: sqlite3.Connection):
    """自动初始化数据库表结构（如果表不存在）。"""
    global _db_initialized
    with _db_init_lock:
        if _db_initialized:
            return

        schema_path = os.path.join(PROJECT_ROOT, "novel-db-mcp", "003_libsql_schema.sql")
        if not os.path.exists(schema_path):
            schema_path = os.path.join(os.path.dirname(__file__), "..", "003_libsql_schema.sql")

        if os.path.exists(schema_path):
            with open(schema_path, "r", encoding="utf-8") as f:
                schema = f.read()
            conn.executescript(schema)
            conn.commit()
            _db_initialized = True
        else:
            raise FileNotFoundError(f"DB schema file not found: {schema_path}")


def get_conn():
    if not hasattr(_local, 'conn') or _local.conn is None:
        os.makedirs(os.path.dirname(LIBSQL_DB_PATH), exist_ok=True)
        _local.conn = sqlite3.connect(LIBSQL_DB_PATH)
        _local.conn.execute("PRAGMA journal_mode=WAL")
        _local.conn.execute("PRAGMA busy_timeout=5000")
        _local.conn.execute("PRAGMA foreign_keys = ON")
        _local.in_transaction = 0
        _init_db_schema(_local.conn)
    return _local.conn


def close_conn():
    if hasattr(_local, 'conn') and _local.conn is not None:
        try:
            _local.conn.close()
        except Exception:
            pass
        _local.conn = None


def _cleanup_conns():
    conn = getattr(_local, 'conn', None)
    if conn:
        try:
            conn.close()
        except Exception:
            pass

atexit.register(_cleanup_conns)


@contextmanager
def transaction():
    conn = get_conn()
    if not hasattr(_local, 'in_transaction'):
        _local.in_transaction = 0
    _local.in_transaction += 1
    try:
        yield
        if _local.in_transaction == 1:
            conn.commit()
    except Exception:
        if _local.in_transaction == 1:
            conn.rollback()
        raise
    finally:
        _local.in_transaction -= 1

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
    in_txn = getattr(_local, 'in_transaction', 0) > 0
    try:
        cur = conn.cursor()
        cur.execute(sql, adapted_params)

        if fetch == "none":
            if not in_txn:
                conn.commit()
            return None

        if fetch == "insert":
            result = {"id": cur.lastrowid}
            if not in_txn:
                conn.commit()
            return result

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
        if not in_txn:
            conn.rollback()
        raise e


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
