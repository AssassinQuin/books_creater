import os
import json
import re
from typing import Any

from fastmcp import FastMCP

PROJECT_ROOT = os.environ.get(
    "NOVEL_PROJECT_ROOT",
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

# ─── Database Backend Selection ──────────────────────────
# Priority: LIBSQL_URL > DATABASE_URL (postgres) > fallback to local libsql
DATABASE_URL = os.environ.get("DATABASE_URL", "")
LIBSQL_URL = os.environ.get("LIBSQL_URL", "")
LIBSQL_DB_PATH = os.environ.get(
    "LIBSQL_DB_PATH",
    os.path.join(PROJECT_ROOT, "data", "novel.db")
)

# Determine backend: "libsql" | "postgres"
DB_BACKEND = os.environ.get("DB_BACKEND", "")
if not DB_BACKEND:
    if LIBSQL_URL or (not DATABASE_URL.startswith("postgresql")):
        DB_BACKEND = "libsql"
    else:
        DB_BACKEND = "postgres"

mcp = FastMCP("novel-db", instructions="网文小说创作数据库 MCP，管理小说项目、世界观、人物、章节、伏笔、时间线等结构化数据。")

# ─── PostgreSQL Backend ──────────────────────────────────
if DB_BACKEND == "postgres":
    import psycopg2
    import psycopg2.extras

    def get_conn():
        return psycopg2.connect(DATABASE_URL or "postgresql:///fcli")

    def query(sql: str, params: tuple = (), fetch: str = "all") -> Any:
        conn = get_conn()
        try:
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute(sql, params)
            if fetch == "none":
                result = None
            elif fetch == "one":
                result = cur.fetchone()
            elif fetch == "val":
                result = cur.fetchone()
                result = list(result.values())[0] if result else None
            else:
                result = cur.fetchall()
            conn.commit()
            return result
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

# ─── libSQL Backend (Local or Remote) ─────────────────────
else:
    import libsql_experimental as libsql

    # Ensure data directory exists
    os.makedirs(os.path.dirname(LIBSQL_DB_PATH), exist_ok=True)

    def get_conn():
        if LIBSQL_URL:
            return libsql.connect(LIBSQL_DB_PATH, sync_url=LIBSQL_URL)
        return libsql.connect(LIBSQL_DB_PATH)

    def _adapt_param(p):
        """Convert Python types to libsql-compatible types."""
        if p is None:
            return None
        if isinstance(p, bool):
            return int(p)
        if isinstance(p, (list, dict)):
            return json.dumps(p, ensure_ascii=False)
        return p

    def _adapt_sql(sql: str) -> tuple[str, bool]:
        """Translate PostgreSQL SQL to SQLite/libSQL compatible SQL.
        Returns (adapted_sql, has_returning)
        """
        adapted = sql

        # Placeholders: %s -> ?
        adapted = adapted.replace("%s", "?")

        # Functions
        adapted = adapted.replace("NOW()", "datetime('now')")

        # Booleans
        adapted = adapted.replace("TRUE", "1").replace("FALSE", "0")

        # Data types
        adapted = adapted.replace("JSONB", "TEXT")
        adapted = adapted.replace("TEXT[]", "TEXT")
        adapted = adapted.replace("TIMESTAMP WITHOUT TIME ZONE", "TIMESTAMP")

        # PostgreSQL cast syntax ::jsonb -> remove cast
        adapted = re.sub(r'::\w+', '', adapted)

        # ON CONFLICT ... DO UPDATE SET ... EXCLUDED.col -> VALUES(col)
        # SQLite uses excluded.column but libsql supports it; however we need
        # to handle the case where EXCLUDED is used in the SET clause
        # libsql supports ON CONFLICT DO UPDATE with excluded.* references
        # so this should work as-is for libsql

        # RETURNING clause -> remove and track
        has_returning = False
        returning_match = re.search(r'\s+RETURNING\s+(\w+)', adapted, re.IGNORECASE)
        if returning_match:
            has_returning = True
            adapted = re.sub(r'\s+RETURNING\s+\w+', '', adapted, flags=re.IGNORECASE)

        return adapted, has_returning

    def query(sql: str, params: tuple = (), fetch: str = "all") -> Any:
        adapted_sql, has_returning = _adapt_sql(sql)
        adapted_params = tuple(_adapt_param(p) for p in params)

        conn = get_conn()
        try:
            cur = conn.cursor()
            cur.execute(adapted_sql, adapted_params)

            if fetch == "none":
                conn.commit()
                return None

            # For INSERT with RETURNING, return lastrowid
            if has_returning and adapted_sql.strip().upper().startswith("INSERT"):
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

            # fetch == "all"
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
