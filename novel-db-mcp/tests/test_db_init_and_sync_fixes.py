"""
本次修复的单元测试

验证以下三个修复点：
  1. DB 自动初始化（db.py _init_db_schema）— 数据库不存在时自动创建表结构
  2. sync_engine _files_to_db_aggregate 参数修复 — 移除多余的 base 参数
  3. world.yaml category_file_map 目录格式 — 以 / 结尾表示目录

运行方式:
  cd novel-db-mcp
  python -m pytest tests/test_db_init_and_sync_fixes.py -v
"""

import json
import os
import sys
import sqlite3
import tempfile
import shutil

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from novel_db.sync_engine import SyncEngine, SyncTemplate


# ============================================================================
# 修复 1: DB 自动初始化
# ============================================================================

class TestDbAutoInit:
    """验证 DB 不存在时自动初始化表结构。"""

    def test_init_db_schema_creates_tables(self, tmp_path, monkeypatch):
        """_init_db_schema 应在空数据库上创建所有表。"""
        import novel_db.db as db_mod

        tmp_db = str(tmp_path / "auto_init.db")
        monkeypatch.setattr(db_mod, "LIBSQL_DB_PATH", tmp_db)
        monkeypatch.setattr(db_mod, "_db_initialized", False)

        conn = sqlite3.connect(tmp_db)
        db_mod._init_db_schema(conn)

        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = {row[0] for row in cursor.fetchall()}

        required_tables = {
            "novels", "characters", "world_settings", "volumes",
            "chapters", "foreshadows", "character_relations",
            "timeline_events", "character_state_snapshots",
        }
        for t in required_tables:
            assert t in tables, f"表 {t} 未创建"

        conn.close()

    def test_init_db_schema_idempotent(self, tmp_path, monkeypatch):
        """_init_db_schema 应幂等：多次调用不报错。"""
        import novel_db.db as db_mod

        tmp_db = str(tmp_path / "idempotent.db")
        monkeypatch.setattr(db_mod, "LIBSQL_DB_PATH", tmp_db)
        monkeypatch.setattr(db_mod, "_db_initialized", False)

        conn = sqlite3.connect(tmp_db)
        db_mod._init_db_schema(conn)
        db_mod._init_db_schema(conn)

        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        tables = {row[0] for row in cursor.fetchall()}
        assert "novels" in tables
        conn.close()

    def test_get_conn_auto_initializes(self, tmp_path, monkeypatch):
        """get_conn() 在首次调用时应自动初始化数据库。"""
        import novel_db.db as db_mod

        tmp_db = str(tmp_path / "auto_conn.db")
        monkeypatch.setattr(db_mod, "LIBSQL_DB_PATH", tmp_db)
        monkeypatch.setattr(db_mod, "_db_initialized", False)
        db_mod.close_conn()

        conn = db_mod.get_conn()
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
        tables = {row[0] for row in cursor.fetchall()}
        assert "novels" in tables, "get_conn() 未自动初始化表"

        db_mod.close_conn()

    def test_schema_file_not_found_raises(self, tmp_path, monkeypatch):
        """schema 文件不存在时应抛出 FileNotFoundError。"""
        import novel_db.db as db_mod

        monkeypatch.setattr(db_mod, "PROJECT_ROOT", str(tmp_path))
        monkeypatch.setattr(db_mod, "_db_initialized", False)
        monkeypatch.setattr(db_mod, "__file__", str(tmp_path / "fake.py"))

        conn = sqlite3.connect(":memory:")
        with pytest.raises(FileNotFoundError):
            db_mod._init_db_schema(conn)
        conn.close()


# ============================================================================
# 修复 2: sync_engine _files_to_db_aggregate 参数修复
# ============================================================================

class TestSyncEngineAggregateFix:
    """验证 _files_to_db_aggregate 方法签名和内部 base 变量定义。"""

    def test_files_to_db_aggregate_signature(self):
        """_files_to_db_aggregate 应只接受 4 个参数（self + 3）。"""
        import inspect
        from novel_db.sync_engine import SyncEngine

        sig = inspect.signature(SyncEngine._files_to_db_aggregate)
        params = list(sig.parameters.keys())
        assert params == ["self", "tpl", "novel_id", "novel_name"], \
            f"参数列表不正确: {params}"

    def test_files_to_db_aggregate_no_name_error(self, tmp_path, fresh_db, mock_query):
        """_files_to_db_aggregate 内部不应出现 NameError: name 'base' is not defined。"""
        import novel_db.sync_engine as engine_mod
        import novel_db.sync as sync_mod
        import novel_db.resolvers as resolvers

        original_query = resolvers.query
        original_sync_query = sync_mod.query
        original_engine_query = engine_mod.query

        resolvers.query = mock_query
        sync_mod.query = mock_query
        engine_mod.query = mock_query

        novel_base = tmp_path / "novels" / "测试小说" / "设定" / "世界观" / "核心设定"
        novel_base.mkdir(parents=True)

        md_content = """## core_setting: 测试设定

- **keys**: ["测试"]
- **tags**: ["test"]

测试内容。
"""
        (novel_base / "测试设定.md").write_text(md_content, encoding="utf-8")

        original_sync_base = sync_mod._NOVELS_BASE
        original_engine_base = engine_mod._NOVELS_BASE
        new_base = str(tmp_path / "novels")
        sync_mod._NOVELS_BASE = new_base
        engine_mod._NOVELS_BASE = new_base

        try:
            eng = SyncEngine()
            tpl = SyncTemplate(
                name="world",
                display_name="世界观",
                db_table="world_settings",
                id_field="name",
                file_dir="设定/世界观",
                merge_mode="section_replace",
                section_marker="## {category}: {name}",
                file_pattern="{category_file}/{name}.md",
                composite_id_fields=["category", "name"],
                file_to_db_enabled=True,
                category_file_map={
                    "core_setting": "核心设定/",
                },
            )
            eng.register(tpl)

            result = eng.files_to_db("测试小说", "world")

            assert "error" not in result or result.get("synced", 0) > 0, \
                f"聚合同步失败: {result}"
        finally:
            resolvers.query = original_query
            sync_mod.query = original_sync_query
            engine_mod.query = original_engine_query
            sync_mod._NOVELS_BASE = original_sync_base
            engine_mod._NOVELS_BASE = original_engine_base

    def test_files_to_db_aggregate_finds_directory_files(self, tmp_path, fresh_db, mock_query):
        """category_file_map 以 / 结尾时，应正确扫描子目录下的 .md 文件。"""
        import novel_db.sync_engine as engine_mod
        import novel_db.sync as sync_mod
        import novel_db.resolvers as resolvers

        original_query = resolvers.query
        original_sync_query = sync_mod.query
        original_engine_query = engine_mod.query

        resolvers.query = mock_query
        sync_mod.query = mock_query
        engine_mod.query = mock_query

        novel_base = tmp_path / "novels" / "测试小说" / "设定" / "世界观"
        (novel_base / "核心设定").mkdir(parents=True)
        (novel_base / "能力体系").mkdir(parents=True)

        (novel_base / "核心设定" / "灵衰.md").write_text(
            '## core_setting: 灵衰\n\n- **keys**: ["灵衰"]\n\n测试。\n',
            encoding="utf-8"
        )
        (novel_base / "能力体系" / "震刃.md").write_text(
            '## ability: 震刃\n\n- **keys**: ["震刃"]\n\n测试。\n',
            encoding="utf-8"
        )

        original_sync_base = sync_mod._NOVELS_BASE
        original_engine_base = engine_mod._NOVELS_BASE
        new_base = str(tmp_path / "novels")
        sync_mod._NOVELS_BASE = new_base
        engine_mod._NOVELS_BASE = new_base

        try:
            eng = SyncEngine()
            tpl = SyncTemplate(
                name="world",
                display_name="世界观",
                db_table="world_settings",
                id_field="name",
                file_dir="设定/世界观",
                merge_mode="section_replace",
                section_marker="## {category}: {name}",
                file_pattern="{category_file}/{name}.md",
                composite_id_fields=["category", "name"],
                file_to_db_enabled=True,
                category_file_map={
                    "core_setting": "核心设定/",
                    "ability": "能力体系/",
                },
            )
            eng.register(tpl)

            result = eng.files_to_db("测试小说", "world")

            assert result["synced"] >= 2, \
                f"应同步至少 2 条记录，实际: {result}"
            keys = [d["key"] for d in result.get("details", [])]
            assert any("灵衰" in k for k in keys), "应包含灵衰"
            assert any("震刃" in k for k in keys), "应包含震刃"
        finally:
            resolvers.query = original_query
            sync_mod.query = original_sync_query
            engine_mod.query = original_engine_query
            sync_mod._NOVELS_BASE = original_sync_base
            engine_mod._NOVELS_BASE = original_engine_base


# ============================================================================
# 修复 3: world.yaml category_file_map 目录格式
# ============================================================================

class TestWorldYamlCategoryFileMap:
    """验证 world.yaml 中 category_file_map 的值以 / 结尾表示目录。"""

    def test_category_file_map_trailing_slash(self):
        """category_file_map 中所有值应以 / 结尾（表示目录）。"""
        import yaml

        manifest_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "..", "sync_manifests", "world.yaml"
        )
        manifest_path = os.path.abspath(manifest_path)
        assert os.path.exists(manifest_path), f"manifest 文件不存在: {manifest_path}"

        with open(manifest_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        category_file_map = data.get("category_file_map", {})
        assert category_file_map, "category_file_map 不应为空"

        for cat, path in category_file_map.items():
            assert path.endswith("/"), \
                f"category_file_map['{cat}'] = '{path}' 应以 '/' 结尾表示目录"

    def test_category_file_map_directory_recognition(self, tmp_path, fresh_db, mock_query):
        """以 / 结尾的路径应被识别为目录并递归扫描。"""
        import novel_db.sync_engine as engine_mod
        import novel_db.sync as sync_mod
        import novel_db.resolvers as resolvers

        original_query = resolvers.query
        original_sync_query = sync_mod.query
        original_engine_query = engine_mod.query

        resolvers.query = mock_query
        sync_mod.query = mock_query
        engine_mod.query = mock_query

        novel_base = tmp_path / "novels" / "测试小说" / "设定" / "世界观"
        (novel_base / "势力").mkdir(parents=True)
        (novel_base / "地图").mkdir(parents=True)

        (novel_base / "势力" / "壁盾军团.md").write_text(
            '## faction: 壁盾军团\n\n- **keys**: ["壁盾"]\n\n测试。\n',
            encoding="utf-8"
        )
        (novel_base / "地图" / "铁谷镇.md").write_text(
            '## location: 铁谷镇\n\n- **keys**: ["铁谷"]\n\n测试。\n',
            encoding="utf-8"
        )

        original_sync_base = sync_mod._NOVELS_BASE
        original_engine_base = engine_mod._NOVELS_BASE
        new_base = str(tmp_path / "novels")
        sync_mod._NOVELS_BASE = new_base
        engine_mod._NOVELS_BASE = new_base

        try:
            eng = SyncEngine()
            tpl = SyncTemplate(
                name="world",
                display_name="世界观",
                db_table="world_settings",
                id_field="name",
                file_dir="设定/世界观",
                merge_mode="section_replace",
                section_marker="## {category}: {name}",
                file_pattern="{category_file}/{name}.md",
                composite_id_fields=["category", "name"],
                file_to_db_enabled=True,
                category_file_map={
                    "faction": "势力/",
                    "location": "地图/",
                },
            )
            eng.register(tpl)

            result = eng.files_to_db("测试小说", "world")

            assert result["synced"] >= 2, f"应同步至少 2 条: {result}"
        finally:
            resolvers.query = original_query
            sync_mod.query = original_sync_query
            engine_mod.query = original_engine_query
            sync_mod._NOVELS_BASE = original_sync_base
            engine_mod._NOVELS_BASE = original_engine_base

    def test_category_file_map_without_slash_treated_as_file(self, tmp_path, fresh_db, mock_query):
        """不以 / 结尾的路径应被当作文件而非目录。"""
        import novel_db.sync_engine as engine_mod
        import novel_db.sync as sync_mod
        import novel_db.resolvers as resolvers

        original_query = resolvers.query
        original_sync_query = sync_mod.query
        original_engine_query = engine_mod.query

        resolvers.query = mock_query
        sync_mod.query = mock_query
        engine_mod.query = mock_query

        novel_base = tmp_path / "novels" / "测试小说" / "设定" / "世界观"
        novel_base.mkdir(parents=True)

        (novel_base / "核心设定.md").write_text(
            '## core_setting: 灵衰\n\n- **keys**: ["灵衰"]\n\n测试。\n',
            encoding="utf-8"
        )

        original_sync_base = sync_mod._NOVELS_BASE
        original_engine_base = engine_mod._NOVELS_BASE
        new_base = str(tmp_path / "novels")
        sync_mod._NOVELS_BASE = new_base
        engine_mod._NOVELS_BASE = new_base

        try:
            eng = SyncEngine()
            tpl = SyncTemplate(
                name="world",
                display_name="世界观",
                db_table="world_settings",
                id_field="name",
                file_dir="设定/世界观",
                merge_mode="section_replace",
                section_marker="## {category}: {name}",
                file_pattern="{category_file}/{name}.md",
                composite_id_fields=["category", "name"],
                file_to_db_enabled=True,
                category_file_map={
                    "core_setting": "核心设定",
                },
            )
            eng.register(tpl)

            result = eng.files_to_db("测试小说", "world")

            assert result["synced"] >= 1, f"文件模式应能同步: {result}"
        finally:
            resolvers.query = original_query
            sync_mod.query = original_sync_query
            engine_mod.query = original_engine_query
            sync_mod._NOVELS_BASE = original_sync_base
            engine_mod._NOVELS_BASE = original_engine_base


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
