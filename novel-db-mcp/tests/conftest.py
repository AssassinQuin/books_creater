"""
全局测试配置：所有测试使用临时数据库，避免污染生产 data/novel.db。

conftest 被 pytest 自动发现，作用于 tests/ 下所有测试文件。
通过 autouse session-scoped fixture 将 LIBSQL_DB_PATH 重定向到临时 DB，
任何测试（即使忘记自行隔离）也不会触及生产数据库。
"""

import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(autouse=True, scope="session")
def _test_db_redirect():
    """
    全局重定向 LIBSQL_DB_PATH 到临时数据库文件。
    所有测试共享一个临时 DB，但互不污染生产数据。
    """
    tmp_db = os.path.join(tempfile.mkdtemp(), "test_novel.db")

    import novel_db.db as db_mod

    original_path = db_mod.LIBSQL_DB_PATH
    db_mod.LIBSQL_DB_PATH = tmp_db

    # 清除连接缓存和初始化标记，让首次 get_conn() 自动初始化新 DB
    db_mod._db_initialized = False
    if hasattr(db_mod._local, "conn"):
        del db_mod._local.conn

    yield

    db_mod.LIBSQL_DB_PATH = original_path
    db_mod._db_initialized = False
    if hasattr(db_mod._local, "conn"):
        del db_mod._local.conn
