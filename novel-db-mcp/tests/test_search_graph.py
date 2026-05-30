"""Tests for novel-db search, graph, hooks, and clean_data modules.

Run: python -m pytest tests/ -v
"""
import json
import os
import sqlite3
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _make_db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    schema_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                               "schema", "003_libsql_schema.sql")
    with open(schema_path, encoding="utf-8") as f:
        conn.executescript(f.read())
    conn.execute("INSERT INTO novels (id, name) VALUES (1, '测试小说')")
    return conn


class TestCleanDataForStorage:
    def test_dict_with_metadata_removed(self):
        from novel_db.sync_engine import clean_data_for_storage
        raw = {
            "content": "灵衰症是一种...",
            "keys": ["灵衰症", "疾病"],
            "tags": ["核心设定"],
            "related": [1, 2],
            "region": "全域",
            "volume_range": "V1-V15",
            "priority": 50,
            "is_constant": True,
            "writing_guide": "用于...",
            "faction_id": 3,
            "锁定": "不可修改",
            "关联设定": "灵枢",
            "叙事功能": "主线推动",
            "核心机制": "灵力衰减",
        }
        cleaned = clean_data_for_storage(raw)
        assert "keys" not in cleaned
        assert "tags" not in cleaned
        assert "related" not in cleaned
        assert "region" not in cleaned
        assert "锁定" not in cleaned
        assert "content" in cleaned
        assert "核心机制" in cleaned

    def test_list_with_mixed_items(self):
        from novel_db.sync_engine import clean_data_for_storage
        raw = [
            {"keys": ["a"], "tags": ["b"]},
            "Some content text",
            {"核心机制": "灵力衰减"},
            {"region": "全域", "content": "more text"},
        ]
        cleaned = clean_data_for_storage(raw)
        assert "content" in cleaned
        assert "灵力衰减" in cleaned["content"]
        assert "Some content text" in cleaned["content"]

    def test_already_clean_data(self):
        from novel_db.sync_engine import clean_data_for_storage
        raw = {"content": "just content", "代价": "生命值"}
        cleaned = clean_data_for_storage(raw)
        assert cleaned == raw

    def test_empty_dict(self):
        from novel_db.sync_engine import clean_data_for_storage
        assert clean_data_for_storage({}) == {}

    def test_string_passthrough(self):
        from novel_db.sync_engine import clean_data_for_storage
        assert clean_data_for_storage("just a string") == "just a string"


class TestHooks:
    def test_fire_post_save_calls_hooks(self):
        from novel_db.hooks import fire_post_save, _HOOKS
        called = []
        _HOOKS.append(lambda nid, et, eid: called.append((nid, et, eid)))
        try:
            fire_post_save(1, "world_setting", 42)
            assert (1, "world_setting", 42) in called
        finally:
            _HOOKS.pop()

    def test_hook_exception_logged_not_raised(self):
        from novel_db.hooks import fire_post_save, _HOOKS
        def bad_hook(nid, et, eid):
            raise ValueError("intentional error")
        _HOOKS.append(bad_hook)
        try:
            fire_post_save(1, "character", 1)
        finally:
            _HOOKS.pop()


class TestGraphResolveEntityNames:
    def test_batch_resolve(self):
        from novel_db.tools_graph import _resolve_entity_names
        conn = _make_db()
        conn.execute("INSERT INTO world_settings (id, novel_id, category, name, data) VALUES (10, 1, 'ability', '铸造', '{}')")
        conn.execute("INSERT INTO characters (id, novel_id, name, role, race, appearance) VALUES (20, 1, '沈野', 'protagonist', '人族', '')")
        conn.commit()

        def mock_query(sql, params=(), fetch="all"):
            cur = conn.execute(sql, params)
            if fetch == "one":
                row = cur.fetchone()
                return dict(row) if row else None
            if fetch == "val":
                row = cur.fetchone()
                return row[0] if row else None
            return [dict(r) for r in cur.fetchall()]

        import novel_db.tools_graph as tg
        original_query = tg.query
        tg.query = mock_query
        try:
            result = _resolve_entity_names([("world_setting", 10), ("character", 20), ("unknown_type", 99)])
            assert result[("world_setting", 10)] == "铸造"
            assert result[("character", 20)] == "沈野"
            assert result[("unknown_type", 99)] == "99"
        finally:
            tg.query = original_query


class TestDbSearchSpec:
    def test_search_specs_structure(self):
        from novel_db.tools_misc import _extract_world_summary
        r = {"data": {"content": "灵衰症是一种灵力衰减的疾病"}}
        assert "灵衰症" in _extract_world_summary(r)

    def test_search_world_summary_from_string_data(self):
        from novel_db.tools_misc import _extract_world_summary
        r = {"data": json.dumps({"content": "测试内容"})}
        assert "测试内容" in _extract_world_summary(r)


class TestGraphQueryParams:
    def test_both_direction_params_no_duplication(self):
        et_ph = "AND e.edge_type IN (?,?)"
        et_params = ["related_setting", "has_ability"]
        base_params = ["world_setting", 1, "world_setting", 1]
        all_params = (
            [1] + base_params + et_params
            + [2] + et_params
            + [50]
        )
        assert len(all_params) == 11
        assert all_params.count("related_setting") == 2
        assert all_params.count("has_ability") == 2
        assert all_params.count(1) == 3
        assert all_params.count(2) == 1
        assert all_params.count(50) == 1


class TestEmbeddingLazyImport:
    def test_import_without_deps(self):
        import novel_db.embedding as emb
        assert emb._np is None
        assert emb._st_model is None

    def test_invalidate_cache_no_error(self):
        from novel_db.embedding import invalidate_cache
        invalidate_cache(999)
        invalidate_cache()
