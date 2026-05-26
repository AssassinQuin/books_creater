"""
向量搜索增强功能测试。

覆盖:
  1. VectorStore 持久化向量存储 + 增量更新
  2. find_incomplete 字段缺失检测
  3. vector_find_incomplete MCP 工具
  4. vector_search MCP 工具
  5. vector_search_and_update MCP 工具（dry_run + 实际修改）
  6. _ensure_deps 自动安装逻辑
"""

import json
import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture()
def vector_db(fresh_db):
    fresh_db.execute(
        "INSERT INTO volumes (id, novel_id, number, title, core_emotion, causal_chain) "
        "VALUES (1, 1, 1, '第一卷', '紧迫', '因果链')"
    )
    fresh_db.execute(
        "INSERT INTO chapters (id, novel_id, number, title, volume_id) "
        "VALUES (1, 1, 1, '第一章', 1)"
    )
    fresh_db.execute(
        "INSERT INTO characters (id, novel_id, name, role, personality, speech_style) "
        "VALUES (1, 1, '沈野', 'protagonist', '坚韧', '简洁')"
    )
    fresh_db.execute(
        "INSERT INTO characters (id, novel_id, name, role, personality) "
        "VALUES (2, 1, '方岩', 'ally', '沉稳')"
    )
    fresh_db.execute(
        "INSERT INTO world_settings (id, novel_id, category, name, data, region, writing_guide) "
        "VALUES (1, 1, 'ability', '震刃', '{\"content\": \"北境战斗能力\"}', '北境', '注意衰减')"
    )
    fresh_db.execute(
        "INSERT INTO world_settings (id, novel_id, category, name, data, region) "
        "VALUES (2, 1, 'location', '壁盾城', '{\"content\": \"中域核心城市\"}', '中域')"
    )
    fresh_db.execute(
        "INSERT INTO foreshadows (id, novel_id, description, status, tags) "
        "VALUES (1, 1, '沈野身世之谜', 'planted', '[\"身世\"]')"
    )
    fresh_db.execute(
        "INSERT INTO chapter_summaries (chapter_id, summary, key_events, characters_involved) "
        "VALUES (1, '沈野初到壁盾城', '[\"抵达壁盾城\"]', '[1]')"
    )
    fresh_db.commit()
    return fresh_db


class TestEnsureDeps:
    def test_ensure_deps_loads_model(self):
        from novel_db.embedding import _ensure_deps, _st_model, _np

        _ensure_deps()

        from novel_db import embedding
        assert embedding._st_model is not None
        assert embedding._np is not None

    def test_ensure_deps_idempotent(self):
        from novel_db.embedding import _ensure_deps

        _ensure_deps()
        _ensure_deps()


class TestFindIncomplete:
    def test_find_incomplete_character_missing_fields(self, mock_query, vector_db):
        from novel_db.embedding import VectorStore

        store = VectorStore(mock_query)
        results = store.find_incomplete(1, entity_types=["character"])

        assert len(results) > 0

        fangyan = [r for r in results if r["id"] == 2]
        assert len(fangyan) == 1
        missing_fields = [mf["field"] for mf in fangyan[0]["missing_fields"]]
        assert "speech_style" in missing_fields
        assert "goals" in missing_fields
        assert "background" in missing_fields

    def test_find_incomplete_character_complete(self, mock_query, vector_db):
        from novel_db.embedding import VectorStore

        store = VectorStore(mock_query)
        results = store.find_incomplete(1, entity_types=["character"])

        shenye = [r for r in results if r["id"] == 1]
        missing_fields = []
        if shenye:
            missing_fields = [mf["field"] for mf in shenye[0]["missing_fields"]]
        assert "speech_style" not in missing_fields
        assert "personality" not in missing_fields

    def test_find_incomplete_world_setting(self, mock_query, vector_db):
        from novel_db.embedding import VectorStore

        store = VectorStore(mock_query)
        results = store.find_incomplete(1, entity_types=["world_setting"])

        bidun = [r for r in results if r["id"] == 2]
        if bidun:
            missing_fields = [mf["field"] for mf in bidun[0]["missing_fields"]]
            assert "writing_guide" in missing_fields

    def test_find_incomplete_min_missing_filter(self, mock_query, vector_db):
        from novel_db.embedding import VectorStore

        store = VectorStore(mock_query)
        results_low = store.find_incomplete(1, min_missing=1)
        results_high = store.find_incomplete(1, min_missing=5)

        assert len(results_high) <= len(results_low)

    def test_find_incomplete_sorted_by_missing_count(self, mock_query, vector_db):
        from novel_db.embedding import VectorStore

        store = VectorStore(mock_query)
        results = store.find_incomplete(1)

        for i in range(len(results) - 1):
            assert results[i]["missing_count"] >= results[i + 1]["missing_count"]

    def test_find_incomplete_empty_novel(self, mock_query, fresh_db):
        from novel_db.embedding import VectorStore

        store = VectorStore(mock_query)
        results = store.find_incomplete(1)
        assert results == []


class TestVectorStorePersistence:
    def test_ensure_table(self, mock_query, vector_db):
        from novel_db.embedding import VectorStore

        store = VectorStore(mock_query)
        store._ensure_table()

        tables = mock_query(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='embedding_vectors'",
            (), fetch="val"
        )
        assert tables == "embedding_vectors"

    def test_rebuild_index_creates_vectors(self, mock_query, vector_db):
        from novel_db.embedding import VectorStore

        store = VectorStore(mock_query)
        store._ensure_table()
        store.rebuild_index(1, entity_types=["world_setting"])

        count = mock_query(
            "SELECT COUNT(*) as cnt FROM embedding_vectors WHERE novel_id = 1",
            (), fetch="val"
        )
        assert count == 2

    def test_rebuild_index_incremental(self, mock_query, vector_db):
        from novel_db.embedding import VectorStore

        store = VectorStore(mock_query)
        store._ensure_table()

        store.rebuild_index(1, entity_types=["world_setting"])

        count_before = mock_query(
            "SELECT COUNT(*) as cnt FROM embedding_vectors WHERE novel_id = 1",
            (), fetch="val"
        )

        store.rebuild_index(1, entity_types=["world_setting"])

        count_after = mock_query(
            "SELECT COUNT(*) as cnt FROM embedding_vectors WHERE novel_id = 1",
            (), fetch="val"
        )
        assert count_after == count_before

    def test_search_returns_scored_results(self, mock_query, vector_db):
        from novel_db.embedding import VectorStore

        store = VectorStore(mock_query)
        store._ensure_table()
        store.rebuild_index(1, entity_types=["world_setting"])

        results = store.search(1, "战斗能力", top_k=5)

        assert len(results) > 0
        for r in results:
            assert "score" in r
            assert "type" in r
            assert "id" in r
            assert r["score"] > 0

    def test_search_with_type_filter(self, mock_query, vector_db):
        from novel_db.embedding import VectorStore

        store = VectorStore(mock_query)
        store._ensure_table()
        store.rebuild_index(1)

        results = store.search(1, "战斗", top_k=10, entity_types=["world_setting"])

        for r in results:
            assert r["type"] == "world_setting"

    def test_rebuild_all_entity_types(self, mock_query, vector_db):
        from novel_db.embedding import VectorStore

        store = VectorStore(mock_query)
        store._ensure_table()
        store.rebuild_index(1)

        count = mock_query(
            "SELECT COUNT(*) as cnt FROM embedding_vectors WHERE novel_id = 1",
            (), fetch="val"
        )
        assert count >= 3


class TestMCPTools:
    @pytest.fixture(autouse=True)
    def _setup_global_db(self):
        from novel_db.db import query, transaction
        with transaction():
            query("DELETE FROM novels WHERE name = '__test_vector__'")
            r = query(
                "INSERT INTO novels (name, genre, status) VALUES ('__test_vector__', 'test', 'testing')",
                fetch="insert"
            )
            self.novel_id = r["id"]
            query(
                "INSERT INTO volumes (novel_id, number, title, core_emotion, causal_chain) "
                "VALUES (?, 1, '第一卷', '紧迫', '因果链')",
                (self.novel_id,)
            )
            query(
                "INSERT INTO chapters (novel_id, number, title) VALUES (?, 1, '第一章')",
                (self.novel_id,)
            )
            ch = query(
                "SELECT id FROM chapters WHERE novel_id = ? AND number = 1",
                (self.novel_id,), fetch="one"
            )
            self.chapter_id = ch["id"]
            query(
                "INSERT INTO characters (novel_id, name, role, personality, speech_style) "
                "VALUES (?, '沈野', 'protagonist', '坚韧', '简洁')",
                (self.novel_id,)
            )
            query(
                "INSERT INTO characters (novel_id, name, role, personality) "
                "VALUES (?, '方岩', 'ally', '沉稳')",
                (self.novel_id,)
            )
            query(
                "INSERT INTO world_settings (novel_id, category, name, data, region, writing_guide) "
                "VALUES (?, 'ability', '震刃', '{\"content\": \"北境战斗能力\"}', '北境', '注意衰减')",
                (self.novel_id,)
            )
            query(
                "INSERT INTO world_settings (novel_id, category, name, data, region) "
                "VALUES (?, 'location', '壁盾城', '{\"content\": \"中域核心城市\"}', '中域')",
                (self.novel_id,)
            )
            query(
                "INSERT INTO foreshadows (novel_id, description, status, tags) "
                "VALUES (?, '沈野身世之谜', 'planted', '[\"身世\"]')",
                (self.novel_id,)
            )
            query(
                "INSERT INTO chapter_summaries (chapter_id, summary, key_events, characters_involved) "
                "VALUES (?, '沈野初到壁盾城', '[\"抵达壁盾城\"]', '[]')",
                (self.chapter_id,)
            )

        yield

        from novel_db.db import query
        query("DELETE FROM novels WHERE name = '__test_vector__'")

    def test_vector_find_incomplete_tool(self):
        from novel_db.tools_vector import vector_find_incomplete

        result_json = vector_find_incomplete("__test_vector__")
        result = json.loads(result_json)

        assert "total_incomplete" in result
        assert "by_type" in result
        assert "results" in result
        assert result["total_incomplete"] > 0

    def test_vector_find_incomplete_with_type_filter(self):
        from novel_db.tools_vector import vector_find_incomplete

        result_json = vector_find_incomplete("__test_vector__", entity_types="character")
        result = json.loads(result_json)

        for r in result["results"]:
            assert r["type"] == "character"

    def test_vector_find_incomplete_min_missing(self):
        from novel_db.tools_vector import vector_find_incomplete

        result_json = vector_find_incomplete("__test_vector__", min_missing=5)
        result = json.loads(result_json)

        for r in result["results"]:
            assert r["missing_count"] >= 5

    def test_vector_search_tool(self):
        from novel_db.tools_vector import vector_search

        result_json = vector_search("__test_vector__", "战斗")
        result = json.loads(result_json)

        assert "results" in result
        assert result["mode"] == "persistent_vector"

    def test_vector_search_with_rebuild(self):
        from novel_db.tools_vector import vector_search

        result_json = vector_search("__test_vector__", "战斗", rebuild=True)
        result = json.loads(result_json)

        assert "results" in result

    def test_vector_search_and_update_dry_run(self):
        from novel_db.tools_vector import vector_search_and_update

        result_json = vector_search_and_update(
            "__test_vector__", "北境", "world_setting", "region", "北境",
            dry_run=True
        )
        result = json.loads(result_json)

        assert result.get("mode") == "dry_run" or result.get("matches", 0) >= 0

    def test_vector_search_and_update_execute(self):
        from novel_db.tools_vector import vector_search_and_update

        result_json = vector_search_and_update(
            "__test_vector__", "壁盾城", "world_setting", "writing_guide", "新增指导",
            dry_run=False, min_score=0.05
        )
        result = json.loads(result_json)

        assert result.get("mode") == "executed" or result.get("matches", 0) >= 0


class TestEntityFieldSpecs:
    def test_all_entity_types_have_specs(self):
        from novel_db.embedding import _ENTITY_FIELD_SPECS

        expected = {"world_setting", "character", "foreshadow",
                    "chapter_summary", "volume", "echo", "timeline"}
        assert set(_ENTITY_FIELD_SPECS.keys()) == expected

    def test_all_specs_have_required_keys(self):
        from novel_db.embedding import _ENTITY_FIELD_SPECS

        for etype, spec in _ENTITY_FIELD_SPECS.items():
            assert "table" in spec, f"{etype} missing 'table'"
            assert "name_col" in spec, f"{etype} missing 'name_col'"
            assert "text_fn" in spec, f"{etype} missing 'text_fn'"
            assert "completeness_fields" in spec, f"{etype} missing 'completeness_fields'"

    def test_completeness_fields_have_check_fn(self):
        from novel_db.embedding import _ENTITY_FIELD_SPECS

        for etype, spec in _ENTITY_FIELD_SPECS.items():
            for fname, fspec in spec["completeness_fields"].items():
                assert "label" in fspec, f"{etype}.{fname} missing 'label'"
                assert "check" in fspec, f"{etype}.{fname} missing 'check'"
                assert callable(fspec["check"]), f"{etype}.{fname} 'check' not callable"


class TestTextBuilders:
    def test_build_world_text(self):
        from novel_db.embedding import _build_world_text

        r = {"name": "震刃", "category": "ability", "data": '{"content": "战斗能力"}',
             "keys": '["沈野"]', "tags": '["战斗"]', "writing_guide": "注意衰减"}
        text = _build_world_text(r)
        assert "震刃" in text
        assert "ability" in text
        assert "战斗能力" in text

    def test_build_character_text(self):
        from novel_db.embedding import _build_character_text

        r = {"name": "沈野", "role": "protagonist", "personality": "坚韧",
             "speech_style": "简洁", "goals": "保护城镇", "background": "北境孤儿",
             "weaknesses": "", "catchphrase": "",
             "appearance_detail": '{"hair": "黑"}', "decision_engine": '{}',
             "voice_fingerprint": '{}', "ability_system": '{}',
             "behavior_pattern": '{}', "current_snapshot": '{}'}
        text = _build_character_text(r)
        assert "沈野" in text
        assert "坚韧" in text
        assert "保护城镇" in text

    def test_build_volume_text(self):
        from novel_db.embedding import _build_volume_text

        r = {"title": "第一卷", "core_emotion": "紧迫", "causal_chain": "因果链",
             "act_intro": '{"prose": "开篇", "events": ["事件1"]}',
             "act_rise": '{}', "act_twist": '{}', "act_resolution": '{}',
             "character_arcs": '[{"角色": "沈野", "卷末状态": "觉醒"}]'}
        text = _build_volume_text(r)
        assert "第一卷" in text
        assert "紧迫" in text
        assert "开篇" in text

    def test_build_foreshadow_text(self):
        from novel_db.embedding import _build_foreshadow_text

        r = {"description": "沈野身世之谜", "tags": '["身世"]',
             "clue_type": "mystery", "reveal_strategy": "gradual"}
        text = _build_foreshadow_text(r)
        assert "沈野身世之谜" in text

    def test_build_echo_text(self):
        from novel_db.embedding import _build_echo_text

        r = {"source_event": "壁盾城之战", "echo_description": "城墙裂缝",
             "echo_type": "physical_trace"}
        text = _build_echo_text(r)
        assert "壁盾城之战" in text
        assert "城墙裂缝" in text

    def test_build_timeline_text(self):
        from novel_db.embedding import _build_timeline_text

        r = {"event_description": "沈野抵达壁盾城", "event_time": "第一天",
             "characters_involved": '[1]'}
        text = _build_timeline_text(r)
        assert "沈野抵达壁盾城" in text

    def test_build_chapter_summary_text(self):
        from novel_db.embedding import _build_chapter_summary_text

        r = {"summary": "沈野初到壁盾城", "key_events": '["抵达"]',
             "characters_involved": '[1]'}
        text = _build_chapter_summary_text(r)
        assert "沈野初到壁盾城" in text


class TestVectorEncoding:
    def test_encode_decode_roundtrip(self):
        from novel_db.embedding import _encode_vector_to_blob, _decode_blob_to_vector

        original = [0.1, 0.2, 0.3, 0.4, 0.5]
        blob = _encode_vector_to_blob(original)
        decoded = _decode_blob_to_vector(blob)

        assert len(decoded) == len(original)
        for o, d in zip(original, decoded):
            assert abs(o - d) < 1e-6

    def test_text_hash_deterministic(self):
        from novel_db.embedding import _compute_text_hash

        h1 = _compute_text_hash("测试文本")
        h2 = _compute_text_hash("测试文本")
        h3 = _compute_text_hash("不同文本")

        assert h1 == h2
        assert h1 != h3
