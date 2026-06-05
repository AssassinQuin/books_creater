"""
审计修复单元测试

验证 P0/P1/P2/P3 各项修复的正确性。

运行方式:
  cd novel-db-mcp
  python -m pytest tests/test_audit_fixes.py -v
"""

import json
import os
import sys
import sqlite3

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _make_db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    schema_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "schema", "003_libsql_schema.sql"
    )
    with open(schema_path, encoding="utf-8") as f:
        conn.executescript(f.read())
    conn.execute("INSERT INTO novels (id, name) VALUES (1, '测试小说')")
    conn.commit()
    return conn


def _mock_query_factory(conn):
    def mock_query(sql, params=(), fetch="all"):
        adapted = []
        for p in (params if isinstance(params, (list, tuple)) else ()):
            if isinstance(p, bool):
                adapted.append(int(p))
            elif isinstance(p, (list, dict)):
                adapted.append(json.dumps(p, ensure_ascii=False))
            else:
                adapted.append(p)
        params = tuple(adapted)
        cur = conn.execute(sql, params)
        if fetch == "none":
            conn.commit()
            return None
        if fetch == "insert":
            conn.commit()
            return {"id": cur.lastrowid}
        if fetch == "one":
            row = cur.fetchone()
            return dict(row) if row else None
        if fetch == "val":
            row = cur.fetchone()
            return row[0] if row else None
        return [dict(r) for r in cur.fetchall()]
    return mock_query


# ============================================================================
# P0-1: sync_lorebook 静默跳过错误 → 收集错误并在返回值中报告
# ============================================================================

class TestP01SyncLorebookErrorReporting:
    """验证 sync_lorebook 在遇到错误时不再静默跳过，而是在返回值中报告错误。"""

    def test_sync_lorebook_reports_errors_in_return(self, tmp_path):
        """正常同步应返回 ok=True。"""
        import novel_db.tools_world as tw
        import novel_db.sync as sync_mod
        import novel_db.resolvers as resolvers

        novel_dir = tmp_path / "novels" / "测试小说" / "设定" / "世界观"
        novel_dir.mkdir(parents=True)

        md_content = """## ability: 测试能力

- **keys**: ["测试"]
- **tags**: ["test"]

这是测试内容。
"""
        (novel_dir / "test.md").write_text(md_content, encoding="utf-8")

        original_base = sync_mod._NOVELS_BASE
        original_tw_base = tw._NOVELS_BASE
        new_base = str(tmp_path / "novels")
        sync_mod._NOVELS_BASE = new_base
        tw._NOVELS_BASE = new_base

        conn = _make_db()
        mock_query = _mock_query_factory(conn)

        original_tw_query = tw.query
        original_res_query = resolvers.query
        tw.query = mock_query
        resolvers.query = mock_query

        try:
            result_json = tw._sync_lorebook("测试小说")
            result = json.loads(result_json)

            assert result.get("ok") is True, f"正常同步应 ok=True: {result}"
            assert "errors" not in result or result.get("error_count", 0) == 0
        finally:
            tw.query = original_tw_query
            resolvers.query = original_res_query
            sync_mod._NOVELS_BASE = original_base
            tw._NOVELS_BASE = original_tw_base

    def test_sync_lorebook_db_failure_reported(self, tmp_path):
        """当 DB 写入抛出异常时，错误应被收集到 errors 列表中。"""
        import novel_db.tools_world as tw
        import novel_db.sync as sync_mod
        import novel_db.resolvers as resolvers

        novel_dir = tmp_path / "novels" / "测试小说" / "设定" / "世界观"
        novel_dir.mkdir(parents=True)

        md_content = """## ability: 测试能力

- **keys**: ["测试"]

这是测试内容。
"""
        (novel_dir / "test.md").write_text(md_content, encoding="utf-8")

        original_base = sync_mod._NOVELS_BASE
        original_tw_base = tw._NOVELS_BASE
        new_base = str(tmp_path / "novels")
        sync_mod._NOVELS_BASE = new_base
        tw._NOVELS_BASE = new_base

        conn = _make_db()
        base_mock = _mock_query_factory(conn)

        insert_count = [0]

        def failing_query(sql, params=(), fetch="all"):
            if "INSERT INTO world_settings" in sql:
                insert_count[0] += 1
                raise sqlite3.IntegrityError("mock constraint violation")
            return base_mock(sql, params, fetch)

        original_tw_query = tw.query
        original_res_query = resolvers.query
        tw.query = failing_query
        resolvers.query = base_mock

        try:
            result_json = tw._sync_lorebook("测试小说")
            result = json.loads(result_json)

            assert result["ok"] is False, "有错误时 ok 应为 False"
            assert "errors" in result, "应包含 errors 列表"
            assert len(result["errors"]) > 0, "errors 列表不应为空"
            assert result["error_count"] > 0, "error_count 应大于 0"
            err = result["errors"][0]
            assert "category" in err, "错误条目应包含 category"
            assert "name" in err, "错误条目应包含 name"
            assert "error" in err, "错误条目应包含 error 信息"
        finally:
            tw.query = original_tw_query
            resolvers.query = original_res_query
            sync_mod._NOVELS_BASE = original_base
            tw._NOVELS_BASE = original_tw_base

    def test_sync_lorebook_partial_failure(self, tmp_path):
        """部分条目成功、部分失败时，changes 和 errors 应分别记录。"""
        import novel_db.tools_world as tw
        import novel_db.sync as sync_mod
        import novel_db.resolvers as resolvers

        novel_dir = tmp_path / "novels" / "测试小说" / "设定" / "世界观"
        novel_dir.mkdir(parents=True)

        md_content = """## ability: 能力A

- **keys**: ["A"]

能力A内容。

## ability: 能力B

- **keys**: ["B"]

能力B内容。
"""
        (novel_dir / "test.md").write_text(md_content, encoding="utf-8")

        original_base = sync_mod._NOVELS_BASE
        original_tw_base = tw._NOVELS_BASE
        new_base = str(tmp_path / "novels")
        sync_mod._NOVELS_BASE = new_base
        tw._NOVELS_BASE = new_base

        conn = _make_db()
        base_mock = _mock_query_factory(conn)
        insert_count = [0]

        def partial_fail_query(sql, params=(), fetch="all"):
            if "INSERT INTO world_settings" in sql:
                insert_count[0] += 1
                if insert_count[0] == 2:
                    raise sqlite3.IntegrityError("mock: second insert fails")
            return base_mock(sql, params, fetch)

        original_tw_query = tw.query
        original_res_query = resolvers.query
        tw.query = partial_fail_query
        resolvers.query = base_mock

        try:
            result_json = tw._sync_lorebook("测试小说")
            result = json.loads(result_json)

            assert result["ok"] is False
            assert result.get("changes", {}).get("ability", 0) >= 1, \
                "至少一个条目应成功"
            assert len(result.get("errors", [])) >= 1, \
                "至少一个条目应失败"
        finally:
            tw.query = original_tw_query
            resolvers.query = original_res_query
            sync_mod._NOVELS_BASE = original_base
            tw._NOVELS_BASE = original_tw_base


# ============================================================================
# P0-2: validate_chapter DB规则异常时 passed 可能为 True → 修复
# ============================================================================

class TestP02ValidateChapterDbError:
    """验证 validate_chapter 在 DB 规则加载失败时正确标记 passed=False。"""

    def test_validate_chapter_db_error_marks_passed_false(self):
        """当 DB 规则加载抛出异常时，passed 应为 False 且包含 db_error 信息。"""
        import novel_db.tools_writing as tw
        import novel_db.resolvers as resolvers

        original_validate = tw.validate_with_db_rules

        def failing_validate(novel_id, text):
            raise RuntimeError("DB connection failed")

        tw.validate_with_db_rules = failing_validate

        conn = _make_db()
        mock_query = _mock_query_factory(conn)
        original_res_query = resolvers.query
        resolvers.query = mock_query

        try:
            text = "这是测试文本。" * 100
            result_json = tw.validate_chapter(text, novel_name="测试小说")
            result = json.loads(result_json)

            assert "db_error" in result, f"应包含 db_error 字段, got: {list(result.keys())}"
            assert result["passed"] is False, \
                "DB 规则加载失败时 passed 应为 False"
            assert result.get("db_rules_available") is False, \
                "db_rules_available 应为 False"
        finally:
            tw.validate_with_db_rules = original_validate
            resolvers.query = original_res_query

    def test_validate_chapter_no_novel_name_no_db_error(self):
        """不传 novel_name 时，不应触发 DB 规则加载，也不应有 db_error。"""
        import novel_db.tools_writing as tw

        text = "这是测试文本。" * 100
        result_json = tw.validate_chapter(text)
        result = json.loads(result_json)

        assert "db_error" not in result, "不传 novel_name 时不应有 db_error"
        assert "db_violations" not in result, "不传 novel_name 时不应有 db_violations"


# ============================================================================
# P0-3: world_deactivate data 为字符串时丢失原始数据 → 修复
# ============================================================================

class TestP03WorldDeactivateDataString:
    """验证 world_deactivate 在 data 为字符串时正确解析并保留原始数据。"""

    def test_deactivate_with_dict_data(self):
        """data 为 dict 时，停用后应保留原始数据并添加 _deactivated 标记。"""
        import novel_db.tools_world as tw
        import novel_db.resolvers as resolvers

        conn = _make_db()
        mock_query = _mock_query_factory(conn)

        original_tw_query = tw.query
        original_res_query = resolvers.query
        tw.query = mock_query
        resolvers.query = mock_query

        try:
            original_data = {"content": "铁谷镇是边境小镇", "population": 5000}
            data_json = json.dumps(original_data, ensure_ascii=False)

            conn.execute(
                "INSERT INTO world_settings (id, novel_id, category, name, data, status) "
                "VALUES (1, 1, 'location', '铁谷镇', ?, 'active')",
                (data_json,)
            )
            conn.commit()

            result_json = tw._world_deactivate("测试小说", "location", "铁谷镇", "被兽潮摧毁")
            result = json.loads(result_json)

            assert result["ok"] is True
            assert result["status"] == "inactive"

            row = conn.execute(
                "SELECT data, status FROM world_settings WHERE id = 1"
            ).fetchone()

            stored_data = json.loads(row["data"]) if isinstance(row["data"], str) else row["data"]
            assert stored_data.get("_deactivated") is True
            assert stored_data.get("_deactivation_reason") == "被兽潮摧毁"
            assert stored_data.get("content") == "铁谷镇是边境小镇"
            assert stored_data.get("population") == 5000
        finally:
            tw.query = original_tw_query
            resolvers.query = original_res_query

    def test_deactivate_with_string_data(self):
        """data 为 JSON 字符串时，停用后应解析原始数据并保留。"""
        import novel_db.tools_world as tw
        import novel_db.resolvers as resolvers

        conn = _make_db()
        mock_query = _mock_query_factory(conn)

        original_tw_query = tw.query
        original_res_query = resolvers.query
        tw.query = mock_query
        resolvers.query = mock_query

        try:
            original_data = {"content": "灵衰是核心危机", "severity": "极高"}
            data_json = json.dumps(original_data, ensure_ascii=False)

            conn.execute(
                "INSERT INTO world_settings (id, novel_id, category, name, data, status) "
                "VALUES (1, 1, 'core_setting', '灵衰', ?, 'active')",
                (data_json,)
            )
            conn.commit()

            result_json = tw._world_deactivate("测试小说", "core_setting", "灵衰", "已被解决")
            result = json.loads(result_json)

            assert result["ok"] is True

            row = conn.execute(
                "SELECT data FROM world_settings WHERE id = 1"
            ).fetchone()

            stored_data = json.loads(row["data"]) if isinstance(row["data"], str) else row["data"]
            assert stored_data.get("_deactivated") is True
            assert stored_data.get("content") == "灵衰是核心危机"
            assert stored_data.get("severity") == "极高"
        finally:
            tw.query = original_tw_query
            resolvers.query = original_res_query

    def test_deactivate_nonexistent_element(self):
        """停用不存在的元素应返回错误。"""
        import novel_db.tools_world as tw
        import novel_db.resolvers as resolvers

        conn = _make_db()
        mock_query = _mock_query_factory(conn)

        original_tw_query = tw.query
        original_res_query = resolvers.query
        tw.query = mock_query
        resolvers.query = mock_query

        try:
            result_json = tw._world_deactivate("测试小说", "location", "不存在的地点")
            result = json.loads(result_json)

            assert "error" in result
        finally:
            tw.query = original_tw_query
            resolvers.query = original_res_query


# ============================================================================
# P1-1: 统一错误处理策略（自定义异常 + 装饰器）
# ============================================================================

class TestP11UnifiedErrorHandling:
    """验证自定义异常类和 MCP 工具错误处理装饰器。"""

    def test_custom_exceptions_exist(self):
        """自定义异常类应可导入且继承自 Exception。"""
        from novel_db.errors import NovelDBError, NotFoundError, ValidationError

        assert issubclass(NotFoundError, NovelDBError)
        assert issubclass(ValidationError, NovelDBError)
        assert issubclass(NovelDBError, Exception)

    def test_not_found_error_raised_by_resolver(self):
        """_resolve_novel_id 找不到小说时应抛出 NotFoundError。"""
        from novel_db.errors import NotFoundError
        import novel_db.resolvers as resolvers

        conn = _make_db()
        mock_query = _mock_query_factory(conn)

        original_query = resolvers.query
        resolvers.query = mock_query

        try:
            with pytest.raises(NotFoundError):
                resolvers._resolve_novel_id("不存在的小说")
        finally:
            resolvers.query = original_query

    def test_mcp_tool_decorator_catches_exceptions(self):
        """mcp_tool 装饰器应捕获异常并返回 JSON 错误响应。"""
        from novel_db.errors import mcp_tool, ValidationError

        @mcp_tool
        def test_tool(value: int) -> str:
            if value < 0:
                raise ValidationError("值不能为负数")
            return json.dumps({"ok": True, "value": value})

        result_json = test_tool(-1)
        result = json.loads(result_json)
        assert "error" in result
        assert "负数" in result["error"]

        result_json = test_tool(5)
        result = json.loads(result_json)
        assert result["ok"] is True


# ============================================================================
# P1-2: get_chapter_context 吞掉 plot_threads 异常 → 记录并标记
# ============================================================================

class TestP12ChapterContextPlotThreadsError:
    """验证 get_chapter_context 在 plot_threads 查询失败时标记错误。"""

    def test_plot_threads_error_marked(self):
        """plot_threads 查询失败时，active_threads 应为空列表且有 _errors 标记。"""
        import novel_db.tools_chapter as tc
        import novel_db.resolvers as resolvers

        conn = _make_db()
        mock_query = _mock_query_factory(conn)

        conn.execute(
            "INSERT INTO volumes (novel_id, number, title) VALUES (1, 1, '测试卷')"
        )
        conn.execute(
            "INSERT INTO chapters (novel_id, number, title, status, volume_id) "
            "VALUES (1, 1, '第一章', 'planned', 1)"
        )
        conn.commit()

        original_tc_query = tc.query
        original_res_query = resolvers.query

        def mock_with_plot_threads_error(sql, params=(), fetch="all"):
            if "plot_threads" in sql:
                raise sqlite3.OperationalError("no such table: plot_threads")
            return mock_query(sql, params, fetch)

        tc.query = mock_with_plot_threads_error
        resolvers.query = mock_query

        try:
            result_json = tc.get_chapter_context("测试小说", 1)
            result = json.loads(result_json)

            assert "error" not in result or "chapter" in result, \
                "应有章节基本信息"
            assert result.get("active_threads") == [], \
                "plot_threads 失败时 active_threads 应为空列表"
            assert "_errors" in result, \
                "应有 _errors 标记说明 plot_threads 查询失败"
            has_threads_error = any(
                "plot_threads" in str(e) for e in result.get("_errors", [])
            )
            assert has_threads_error, "_errors 中应包含 plot_threads 相关错误"
        finally:
            tc.query = original_tc_query
            resolvers.query = original_res_query


# ============================================================================
# P1-3: N+1 查询（health_check 等）→ 批量查询
# ============================================================================

class TestP13HealthCheckBatchQuery:
    """验证 health_check 使用批量查询替代 N+1 查询。"""

    def test_health_check_no_n_plus_1_for_foreshadows(self):
        """health_check 不应为每个伏笔单独查询章节号。"""
        import novel_db.tools_misc as tm
        import novel_db.resolvers as resolvers

        conn = _make_db()
        mock_query = _mock_query_factory(conn)

        conn.execute(
            "INSERT INTO volumes (novel_id, number, title) VALUES (1, 1, '测试卷')"
        )
        conn.execute(
            "INSERT INTO chapters (novel_id, number, title, status, volume_id) "
            "VALUES (1, 1, '第一章', 'written', 1)"
        )
        conn.execute(
            "INSERT INTO chapters (novel_id, number, title, status, volume_id) "
            "VALUES (1, 2, '第二章', 'written', 1)"
        )
        conn.execute(
            "INSERT INTO foreshadows (novel_id, description, importance, status, planted_chapter_id) "
            "VALUES (1, '伏笔1', 'high', 'planted', 1)"
        )
        conn.execute(
            "INSERT INTO foreshadows (novel_id, description, importance, status, planted_chapter_id) "
            "VALUES (1, '伏笔2', 'medium', 'planted', 2)"
        )
        conn.commit()

        original_tm_query = tm.query
        original_res_query = resolvers.query
        query_log = []

        def logging_mock_query(sql, params=(), fetch="all"):
            query_log.append(sql[:80])
            return mock_query(sql, params, fetch)

        tm.query = logging_mock_query
        resolvers.query = mock_query

        try:
            result_json = tm.health_check("测试小说")
            result = json.loads(result_json)

            single_chapter_queries = [
                q for q in query_log
                if "SELECT number FROM chapters WHERE id" in q
            ]

            assert len(single_chapter_queries) == 0, \
                f"应为批量查询而非逐条查询，发现 {len(single_chapter_queries)} 条单条查询"

            assert "foreshadow" in result
            assert result["foreshadow"]["planted"] == 2
        finally:
            tm.query = original_tm_query
            resolvers.query = original_res_query


# ============================================================================
# P1-4: 连接复用（单连接持久化）
# ============================================================================

class TestP14ConnectionReuse:
    """验证 db.py 使用连接复用而非每次查询新建连接。"""

    def test_get_conn_returns_persistent_connection(self):
        """get_conn 应返回持久化连接（同一线程内多次调用返回同一对象）。"""
        import novel_db.db as db_mod

        conn1 = db_mod.get_conn()
        conn2 = db_mod.get_conn()
        assert conn1 is conn2, "同一线程内 get_conn 应返回同一连接"

        db_mod.close_conn()

    def test_close_conn_resets_connection(self):
        """close_conn 后应创建新连接。"""
        import novel_db.db as db_mod

        conn1 = db_mod.get_conn()
        db_mod.close_conn()
        conn2 = db_mod.get_conn()
        assert conn1 is not conn2, "close_conn 后应创建新连接"

        db_mod.close_conn()


# ============================================================================
# P2-1: 抽取通用 SQL builder
# ============================================================================

class TestP21SqlBuilder:
    """验证通用 SQL builder 函数。"""

    def test_build_update_sql_basic(self):
        """build_update_sql 应生成正确的 UPDATE 语句。"""
        from novel_db.sql_utils import build_update_sql

        sql, params = build_update_sql(
            "world_settings",
            {"region": "北境", "priority": 50},
            "novel_id = ? AND category = ? AND name = ?",
            (1, "ability", "震刃")
        )

        assert "UPDATE world_settings SET" in sql
        assert "region = ?" in sql
        assert "priority = ?" in sql
        assert "WHERE novel_id = ? AND category = ? AND name = ?" in sql
        assert "updated_at" in sql
        assert params == ("北境", 50, 1, "ability", "震刃")

    def test_build_update_sql_empty_fields_raises(self):
        """空字段列表应抛出 ValueError。"""
        from novel_db.sql_utils import build_update_sql

        with pytest.raises(ValueError):
            build_update_sql("table", {}, "id = ?", (1,))

    def test_build_upsert_sql(self):
        """build_upsert_sql 应生成正确的 INSERT ON CONFLICT 语句。"""
        from novel_db.sql_utils import build_upsert_sql

        sql, params = build_upsert_sql(
            "world_settings",
            ["novel_id", "category", "name", "data"],
            ["data"],
            (1, "ability", "震刃", '{"content":"test"}'),
            ('{"content":"test"}',)
        )

        assert "INSERT INTO world_settings" in sql
        assert "ON CONFLICT" in sql
        assert "DO UPDATE SET" in sql



# ============================================================================
# P3-1: 缓存失效机制（constraints）
# ============================================================================

class TestP31ConstraintsCacheInvalidation:
    """验证 constraints 缓存有失效机制。"""

    def test_invalidate_constraints_cache(self):
        """应提供缓存失效函数。"""
        from novel_db.constraints import _get_constraints, invalidate_constraints_cache

        c1 = _get_constraints()
        assert c1 is not None

        invalidate_constraints_cache()

        from novel_db.constraints import _CONSTRAINTS_CACHE
        assert _CONSTRAINTS_CACHE is None, "失效后缓存应为 None"

    def test_cache_rebuilt_after_invalidation(self):
        """缓存失效后再次获取应重新构建。"""
        from novel_db.constraints import _get_constraints, invalidate_constraints_cache

        invalidate_constraints_cache()
        c2 = _get_constraints()
        assert c2 is not None
        assert "hard_pct" in c2


# ============================================================================
# P3-3: _is_error 魔法标记 → 正规返回类型
# ============================================================================

class TestP33IsErrorMagicMarker:
    """验证 _is_error 魔法标记已被正规返回类型替代。"""

    def test_wf_validate_raises_on_self_check_not_passed(self):
        """自检未完成时应抛出 ValidationError。"""
        import novel_db.tools_writing as tw
        from novel_db.errors import ValidationError
        from novel_db.constraints import invalidate_constraints_cache

        invalidate_constraints_cache()

        long_text = "这是一段足够长的测试文本。" * 200
        with pytest.raises(ValidationError):
            tw._wf_validate(long_text, "not_passed", novel_id=0)

    def test_wf_validate_no_is_error_in_return(self):
        """_wf_validate 成功返回时不应包含 _is_error 字段。"""
        import novel_db.tools_writing as tw
        from novel_db.constraints import invalidate_constraints_cache

        invalidate_constraints_cache()

        long_text = "这是一段足够长的测试文本。" * 200
        result = tw._wf_validate(long_text, "passed", novel_id=0)
        assert "_is_error" not in result
        assert result["passed"] is True


# ============================================================================
# Hooks: fire_post_save 返回失败列表
# ============================================================================

class TestHooksReturnFailures:
    """验证 fire_post_save 返回失败列表而非静默吞掉。"""

    def test_fire_post_save_returns_failed_hooks(self):
        """hook 失败时，fire_post_save 应返回失败列表。"""
        from novel_db.hooks import fire_post_save, _HOOKS

        saved_hooks = _HOOKS[:]

        def bad_hook(nid, et, eid):
            raise ValueError("intentional error")

        _HOOKS.clear()
        _HOOKS.append(bad_hook)

        try:
            failed = fire_post_save(1, "character", 1)
            assert len(failed) > 0, "应返回失败列表"
            assert "bad_hook" in failed[0]
            assert "intentional error" in failed[0]
        finally:
            _HOOKS.clear()
            _HOOKS.extend(saved_hooks)

    def test_fire_post_save_no_failures_returns_empty(self):
        """所有 hook 成功时，fire_post_save 应返回空列表。"""
        from novel_db.hooks import fire_post_save, _HOOKS

        saved_hooks = _HOOKS[:]

        called = []
        _HOOKS.clear()
        _HOOKS.append(lambda nid, et, eid: called.append(True))

        try:
            failed = fire_post_save(1, "world_setting", 42)
            assert failed == []
            assert len(called) > 0
        finally:
            _HOOKS.clear()
            _HOOKS.extend(saved_hooks)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])


# ============================================================================
# P2-3: _status_json 补丁清理
# ============================================================================

class TestP23StatusJsonPatchCleanup:
    """验证 _status_json 补丁参数已被正式的 status_json 替代。"""

    def test_character_update_uses_status_json_not_underscore(self):
        """character_update 应使用 status_json 而非 _status_json。"""
        import novel_db.tools_character as tc
        import inspect

        sig = inspect.signature(tc.character_update)
        param_names = list(sig.parameters.keys())
        assert "status_json" in param_names, "应使用 status_json 参数"
        assert "_status_json" not in param_names, "不应使用 _status_json 隐藏参数"

    def test_status_json_takes_priority_over_status(self):
        """status_json 应优先于 status 参数。"""
        import novel_db.tools_character as tc
        import novel_db.resolvers as resolvers

        conn = _make_db()
        mock_query = _mock_query_factory(conn)

        original_tc_query = tc.query
        original_res_query = resolvers.query
        tc.query = mock_query
        resolvers.query = mock_query

        try:
            conn.execute(
                "INSERT INTO characters (novel_id, name, role, status) "
                "VALUES (1, '测试角色', 'protagonist', 'active')"
            )
            conn.commit()

            result_json = tc._character_update_by_id(
                1, status="active", status_json='{"hp": 80, "mp": 50}'
            )
            result = json.loads(result_json)
            assert result.get("ok") is True

            row = conn.execute("SELECT status FROM characters WHERE id = 1").fetchone()
            stored = row["status"]
            if isinstance(stored, str):
                parsed = json.loads(stored)
                assert parsed.get("hp") == 80, "status_json 应覆盖 status"
        finally:
            tc.query = original_tc_query
            resolvers.query = original_res_query


# ============================================================================
# P3-2: timeline_add 改用 chapter_number
# ============================================================================

class TestP32TimelineAddChapterNumber:
    """验证 _timeline_add 接受 chapter_number 参数。"""

    def test_timeline_add_accepts_chapter_number(self):
        """_timeline_add 应接受 chapter_number 参数。"""
        import novel_db.tools_chapter as tc
        import novel_db.resolvers as resolvers
        import inspect

        sig = inspect.signature(tc._timeline_add)
        param_names = list(sig.parameters.keys())
        assert "chapter_number" in param_names, "应接受 chapter_number 参数"

    def test_timeline_add_resolves_chapter_number_to_id(self):
        """_timeline_add 应将 chapter_number 解析为 chapter_id。"""
        import novel_db.tools_chapter as tc
        import novel_db.resolvers as resolvers

        conn = _make_db()
        mock_query = _mock_query_factory(conn)

        conn.execute(
            "INSERT INTO volumes (novel_id, number, title) VALUES (1, 1, '测试卷')"
        )
        conn.execute(
            "INSERT INTO chapters (novel_id, number, title, status, volume_id) "
            "VALUES (1, 1, '第一章', 'written', 1)"
        )
        conn.commit()

        original_tc_query = tc.query
        original_res_query = resolvers.query
        tc.query = mock_query
        resolvers.query = mock_query

        try:
            result_json = tc._timeline_add(
                "测试小说", chapter_number=1,
                event_time="第一日清晨", event_order=1,
                event_description="沈野到达铁谷镇"
            )
            result = json.loads(result_json)
            assert result.get("ok") is True
            assert "id" in result

            row = conn.execute(
                "SELECT chapter_id FROM timeline_events WHERE id = ?", (result["id"],)
            ).fetchone()
            assert row is not None
            assert row["chapter_id"] == 1, "chapter_number=1 应解析为 chapter_id=1"
        finally:
            tc.query = original_tc_query
            resolvers.query = original_res_query
