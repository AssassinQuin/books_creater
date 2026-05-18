import os
from typing import Any

import psycopg2
import psycopg2.extras
from fastmcp import FastMCP

PROJECT_ROOT = os.environ.get(
    "NOVEL_PROJECT_ROOT",
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql:///fcli"
)

mcp = FastMCP("novel-db", instructions="网文小说创作数据库 MCP，管理小说项目、世界观、人物、章节、伏笔、时间线等结构化数据。")


def get_conn():
    return psycopg2.connect(DATABASE_URL)


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
