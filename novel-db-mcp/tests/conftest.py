"""
全局测试配置：所有测试使用 data/novel_test.db，避免污染生产 data/novel.db。

conftest 被 pytest 自动发现，作用于 tests/ 下所有测试文件。
测试数据库固定使用 _test 后缀：data/novel_test.db。
任何测试都不会触及 data/novel.db（生产库）。

三层防护：
  1. 环境变量 LIBSQL_DB_PATH 在 import db.py 之前设置
  2. session fixture 重定向 + 连接缓存清除
  3. autouse per-test 安全守卫：检测到生产路径则 skip
"""

import os
import sys

import pytest

_TEST_DB_PATH = os.path.abspath(os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data", "novel_test.db"
))

os.environ["LIBSQL_DB_PATH"] = _TEST_DB_PATH

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import novel_db.db as db_mod

_PRODUCTION_DB_PATHS = set()
_prod_path = os.path.abspath(os.path.join(db_mod.PROJECT_ROOT, "data", "novel.db"))
_PRODUCTION_DB_PATHS.add(_prod_path)


def _is_production_db(path):
    return os.path.abspath(path) in _PRODUCTION_DB_PATHS


@pytest.fixture(autouse=True, scope="session")
def _test_db_redirect():
    if _is_production_db(db_mod.LIBSQL_DB_PATH):
        raise RuntimeError(
            f"测试检测到生产 DB 路径: {db_mod.LIBSQL_DB_PATH}，拒绝执行！"
        )

    # 清理旧测试数据库，确保干净启动
    if os.path.exists(_TEST_DB_PATH):
        os.remove(_TEST_DB_PATH)
    wal_path = _TEST_DB_PATH + "-wal"
    if os.path.exists(wal_path):
        os.remove(wal_path)
    shm_path = _TEST_DB_PATH + "-shm"
    if os.path.exists(shm_path):
        os.remove(shm_path)

    db_mod.LIBSQL_DB_PATH = _TEST_DB_PATH
    db_mod._db_initialized = False
    if hasattr(db_mod._local, "conn"):
        del db_mod._local.conn

    yield

    db_mod._db_initialized = False
    if hasattr(db_mod._local, "conn"):
        del db_mod._local.conn


@pytest.fixture(autouse=True)
def _guard_production_db():
    if _is_production_db(db_mod.LIBSQL_DB_PATH):
        pytest.skip("检测到生产 DB 路径，跳过测试以保护数据")


@pytest.fixture()
def fresh_db():
    """提供干净的临时 DB 连接，适用于需要独立 DB 的测试。

    使用方式：
        def test_something(fresh_db):
            conn = fresh_db
            conn.execute("INSERT INTO novels ...")
            ...
    """
    import sqlite3

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")

    schema_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "003_libsql_schema.sql",
    )
    with open(schema_path, "r", encoding="utf-8") as f:
        conn.executescript(f.read())
    conn.execute("INSERT INTO novels (id, name) VALUES (1, '测试小说')")
    conn.commit()

    yield conn

    conn.close()


@pytest.fixture()
def mock_query(fresh_db):
    """基于 fresh_db 的 mock query 函数，替代手动 _mock_query_factory。"""
    import json

    def _mock_query(sql, params=(), fetch="all"):
        adapted = []
        for p in (params if isinstance(params, (list, tuple)) else ()):
            if isinstance(p, bool):
                adapted.append(int(p))
            elif isinstance(p, (list, dict)):
                adapted.append(json.dumps(p, ensure_ascii=False))
            else:
                adapted.append(p)
        params = tuple(adapted)
        cur = fresh_db.execute(sql, params)
        if fetch == "none":
            fresh_db.commit()
            return None
        if fetch == "insert":
            fresh_db.commit()
            return {"id": cur.lastrowid}
        if fetch == "one":
            row = cur.fetchone()
            return dict(row) if row else None
        if fetch == "val":
            row = cur.fetchone()
            return row[0] if row else None
        return [dict(r) for r in cur.fetchall()]

    return _mock_query
