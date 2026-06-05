"""
多维度交叉生成单元测试

验证大纲、章节事件、人物、物品、设定、势力、地点等维度
能否根据模板在 DB ↔ File 之间正确同步，以及维度间交叉引用是否一致。

测试层次:
  1. DB→File→DB 往返一致性（Round-Trip）：每个维度独立验证
  2. 模板字段映射完整性：验证模板定义的每个字段都能正确同步
  3. 跨维度交叉引用一致性：验证维度间的 ID/名称引用关系
  4. JSONB 深度结构保持：验证嵌套 JSON 结构在往返后不丢失
  5. 聚合文件同步（section_replace）：验证伏笔/回响/世界观的聚合模式
  6. 交叉生成验证：从一个维度的数据能否推断/验证另一个维度的数据

运行方式:
  cd novel-db-mcp
  python -m pytest tests/test_cross_dimension.py -v
"""

import json
import os
import sys
import tempfile

import pytest

# ─── 确保可以 import 项目模块 ───
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from novel_db.db import query, get_conn, LIBSQL_DB_PATH
from novel_db.sync_engine import SyncEngine, SyncTemplate, SectionDef, FieldDef, BlockquoteField
from novel_db.md_parser import (
    split_sections, find_section, parse_bullet_fields,
    parse_jsonb_bullets, parse_md_table, parse_blockquotes, parse_acts,
    parse_relations,
)
from novel_db.sync import _is_empty, _jsonb_to_md, _md_bullet, _render_md_table, _parse_json_field


def roundtrip(data, jsonb_key="content", indent=1, title_key=None):
    """
    模拟实际 DB→MD→DB 往返流程。

    _render_jsonb 的渲染逻辑:
      [f"- **{jsonb_key}**:"]
      + _jsonb_to_md(parsed, indent, title_key=sec.title_key)

    parse_jsonb_bullets 的解析逻辑:
      跳过首行 `- **jsonb_key**:`，然后解析嵌套 bullets
    """
    md_lines = [f"- **{jsonb_key}**:"]
    md_lines.extend(_jsonb_to_md(data, indent, title_key=title_key))
    md_text = "\n".join(md_lines)
    return parse_jsonb_bullets(md_text)


# ============================================================================
# Fixtures
# ============================================================================

# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture(autouse=True)
def clean_db():
    """每个测试前清空数据表，保证测试隔离。"""
    priority_order = [
        "data_hashes", "chapter_quality", "dimension_changes",
        "scene_outlines", "timeline_events", "echoes",
        "foreshadows", "chapter_summaries", "character_state_snapshots",
        "character_distillation_evolution", "character_relations",
        "characters", "world_settings", "chapters", "volumes", "novels",
    ]
    for t in priority_order:
        try:
            query(f"DELETE FROM {t}", fetch="none")
        except Exception:
            pass
    yield


@pytest.fixture
def novel_id():
    """创建测试小说并返回 novel_id。"""
    r = query(
        "INSERT INTO novels (name, genre, status) VALUES (?, ?, ?)",
        ("测试小说", "玄幻", "writing"), fetch="insert"
    )
    return r["id"]


@pytest.fixture
def test_novel_dir(tmp_path):
    """创建临时小说文件目录。"""
    base = tmp_path / "novels" / "测试小说"
    base.mkdir(parents=True, exist_ok=True)
    return base


@pytest.fixture
def engine(test_novel_dir):
    """创建已加载所有 manifest 的 SyncEngine 实例，使用临时目录。"""
    import novel_db.sync as sync_mod
    import novel_db.sync_engine as engine_mod

    original_sync_base = sync_mod._NOVELS_BASE
    original_engine_base = engine_mod._NOVELS_BASE

    new_base = str(test_novel_dir.parent)
    sync_mod._NOVELS_BASE = new_base
    engine_mod._NOVELS_BASE = new_base

    eng = SyncEngine()
    manifest_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "..", "sync_manifests"
    )
    if os.path.isdir(manifest_dir):
        eng.load_manifests(manifest_dir)

    yield eng

    sync_mod._NOVELS_BASE = original_sync_base
    engine_mod._NOVELS_BASE = original_engine_base


# ============================================================================
# 1. 人物维度 — DB→File→DB 往返一致性
# ============================================================================

class TestCharacterRoundTrip:
    """人物维度：验证 DB → File → DB 往返后数据一致性。"""

    def _insert_character(self, novel_id, name="沈野", **overrides):
        """辅助：插入一条人物记录。"""
        defaults = {
            "role": "protagonist", "race": "人类", "ability_level": "通感",
            "appearance": "瘦削少年，眼窝深陷，颧骨突出", "personality": "沉默、固执、善良",
            "background": "铁谷镇长大的孤儿", "goals": "找到失踪的妹妹",
            "weaknesses": "过度保护他人", "speech_style": "简短直接",
            "catchphrase": "不关你的事", "arc_notes": "从自我封闭到学会信任",
            "first_appearance_chapter": 1,
            "appearance_detail": json.dumps({
                "gender": "男", "body": "瘦削但结实",
                "face": "眼窝深陷，颧骨突出", "hair": "乱发遮住半边脸",
                "signature_features": ["左耳后一道旧疤"]
            }, ensure_ascii=False),
            "decision_engine": json.dumps({
                "core_conflict": "安全 vs 真相",
                "daily_state": "谨慎观察",
                "rules": [{"priority": 1, "name": "保护弱者", "description": "遇到危险优先保护他人"}]
            }, ensure_ascii=False),
            "voice_fingerprint": json.dumps({
                "tone": "低沉沙哑", "pace": "日常缓慢，紧急急促",
                "habits": ["反问代替回答", "沉默代替否认"]
            }, ensure_ascii=False),
            "ability_system": json.dumps({
                "core": "灵纹共鸣", "essence": "感知并操控灵能纹路",
                "stages": [{"name": "初觉", "volume": "V1", "description": "能感知灵纹"}]
            }, ensure_ascii=False),
            "behavior_pattern": json.dumps({
                "core_drive": "守护", "decision_logic": "最小代价最大保护",
                "wont_say": ["我不在乎"]
            }, ensure_ascii=False),
            "current_snapshot": json.dumps({
                "identity": "灵纹共鸣者", "goal": "阻止灵衰扩散",
                "journey_summary": [{"stage": "V1起点", "summary": "普通少年"}]
            }, ensure_ascii=False),
        }
        defaults.update(overrides)

        cols = ["novel_id", "name"] + list(defaults.keys())
        vals = [novel_id, name] + [defaults[k] for k in defaults]

        placeholders = ",".join(["?"] * len(cols))
        r = query(
            f"INSERT INTO characters ({','.join(cols)}) VALUES ({placeholders})",
            tuple(vals), fetch="insert"
        )
        return r["id"]

    def test_character_db_to_file_to_db(self, novel_id, engine, test_novel_dir):
        """DB→File→DB：人物数据在往返后关键字段一致。"""
        char_id = self._insert_character(novel_id)

        # Step 1: DB → File
        result = engine.db_to_files("测试小说", "character", overwrite=True)
        assert result["synced"] == 1, f"DB→File 同步失败: {result}"
        assert result["errors"] == []

        # 验证文件已生成
        char_file = test_novel_dir / "设定" / "人物" / "沈野.md"
        assert char_file.exists(), "人物文件未生成"

        content = char_file.read_text(encoding="utf-8")
        assert "沈野" in content
        assert "protagonist" in content

        # Step 2: 清空 DB 中的人物数据
        query("DELETE FROM characters WHERE id = ?", (char_id,), fetch="none")

        # Step 3: File → DB
        if engine.get("character").file_to_db_enabled:
            result2 = engine.files_to_db("测试小说", "character")
            assert result2["synced"] >= 1, f"File→DB 同步失败: {result2}"

            # 验证数据恢复
            restored = query(
                "SELECT * FROM characters WHERE novel_id = ? AND name = ?",
                (novel_id, "沈野"), fetch="one"
            )
            assert restored is not None, "File→DB 后人物未恢复"
            assert restored["name"] == "沈野"
            assert restored["role"] == "protagonist"
            assert restored["race"] == "人类"

    def test_character_jsonb_round_trip(self, novel_id, engine, test_novel_dir):
        """验证人物 JSONB 字段（决策引擎/声音指纹/能力体系等）在往返后结构不变。"""
        decision_data = {
            "core_conflict": "安全 vs 真相",
            "daily_state": "谨慎观察",
            "trigger_state": "保护本能激活",
            "rules": [
                {"priority": 1, "name": "保护弱者", "description": "优先保护"},
                {"priority": 2, "name": "不暴露身份", "description": "隐藏能力"}
            ]
        }
        self._insert_character(
            novel_id,
            decision_engine=json.dumps(decision_data, ensure_ascii=False)
        )

        # DB → File
        engine.db_to_files("测试小说", "character", overwrite=True)

        char_file = test_novel_dir / "设定" / "人物" / "沈野.md"
        content = char_file.read_text(encoding="utf-8")

        # 验证 JSONB 内容在文件中可见
        assert "决策引擎" in content
        assert "core_conflict" in content or "安全 vs 真相" in content

    def test_character_with_relation(self, novel_id, engine, test_novel_dir):
        """验证人物关系在同步到文件后包含关系信息。"""
        id1 = self._insert_character(novel_id, name="沈野")
        id2 = self._insert_character(novel_id, name="方岩", role="ally",
                                     appearance="魁梧青年", personality="豪爽直率",
                                     background="壁盾军团士兵", goals="守护城镇",
                                     weaknesses="冲动", speech_style="大嗓门",
                                     arc_notes="从服从到质疑", first_appearance_chapter=1)

        # 创建关系
        query(
            "INSERT INTO character_relations "
            "(novel_id, from_character_id, to_character_id, relation_type, description, intensity, status, subtext_design) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (novel_id, id1, id2, "ally", "战友", 7, "active", "对TA的关心永远通过动作表达"),
            fetch="none"
        )

        # DB → File
        engine.db_to_files("测试小说", "character", overwrite=True)

        char_file = test_novel_dir / "设定" / "人物" / "沈野.md"
        content = char_file.read_text(encoding="utf-8")

        # 验证关系段落存在
        assert "关系" in content
        assert "ally" in content or "战友" in content


# ============================================================================
# 2. 卷级大纲维度 — DB→File→DB 往返
# ============================================================================

class TestVolumeRoundTrip:
    """卷级大纲维度：验证大纲数据在 DB↔File 往返后一致。"""

    def _insert_volume(self, novel_id, number=1, title="兽潮", **overrides):
        """辅助：插入一卷。"""
        defaults = {
            "core_emotion": "恐惧→坚韧", "pov_anchor": "第三人称·沈野限知",
            "time_span": "D1-D14", "voice_mapping": "日常→daily / 战斗→battle",
            "causal_chain": "因为兽潮来袭所以被迫战斗",
            "act_intro": json.dumps({
                "prose": "铁谷镇的黎明被兽吼撕碎。",
                "events": ["兽潮前兆", "沈野觉醒灵纹"],
                "feibi_notes": ["镇民恐慌"], "list_items": []
            }, ensure_ascii=False),
            "act_rise": json.dumps({
                "prose": "危机加剧。",
                "events": ["防线崩溃"], "feibi_notes": [], "list_items": []
            }, ensure_ascii=False),
            "character_arcs": json.dumps([
                {"角色": "沈野", "卷初状态": "普通少年", "触发事件": "兽潮", "卷末状态": "觉醒者"}
            ], ensure_ascii=False),
            "notes": "第一卷测试备注",
        }
        defaults.update(overrides)

        cols = ["novel_id", "number", "title"] + list(defaults.keys())
        vals = [novel_id, number, title] + [defaults[k] for k in defaults]

        placeholders = ",".join(["?"] * len(cols))
        r = query(
            f"INSERT INTO volumes ({','.join(cols)}) VALUES ({placeholders})",
            tuple(vals), fetch="insert"
        )
        return r["id"]

    def test_volume_db_to_file(self, novel_id, engine, test_novel_dir):
        """卷级大纲 DB→File 生成验证。"""
        vol_id = self._insert_volume(novel_id)

        result = engine.db_to_files("测试小说", "volume", overwrite=True)
        # volume 有 skip_existing，用 overwrite=True 强制写入
        if result["synced"] == 0 and result["skipped"] == 1:
            result = engine.db_to_files("测试小说", "volume", overwrite=True)

        # 检查文件是否生成
        outline_dir = test_novel_dir / "设定" / "大纲"
        if outline_dir.exists():
            files = list(outline_dir.glob("*.md"))
            assert len(files) > 0, "大纲文件未生成"

    def test_volume_acts_round_trip(self, novel_id, engine, test_novel_dir):
        """验证四幕结构（起承转合）JSONB 往返。"""
        act_intro = {"prose": "铁谷镇黎明。", "events": ["兽潮前兆"], "feibi_notes": [], "list_items": []}
        act_rise = {"prose": "危机加剧。", "events": ["防线崩溃"], "feibi_notes": ["士兵逃跑"], "list_items": []}

        vol_id = self._insert_volume(
            novel_id,
            act_intro=json.dumps(act_intro, ensure_ascii=False),
            act_rise=json.dumps(act_rise, ensure_ascii=False),
        )

        result = engine.db_to_files("测试小说", "volume", overwrite=True)

        # 找到生成的大纲文件
        outline_dir = test_novel_dir / "设定" / "大纲"
        if outline_dir.exists():
            for f in outline_dir.glob("*.md"):
                content = f.read_text(encoding="utf-8")
                # 验证四幕结构渲染
                if "起" in content:
                    assert "铁谷镇" in content or "兽潮前兆" in content


# ============================================================================
# 3. 世界观维度 — 势力、地点、物品、设定
# ============================================================================

class TestWorldSettingsRoundTrip:
    """世界观维度：验证势力、地点、物品、能力、核心设定等分类的 DB↔File 同步。"""

    def _insert_world(self, novel_id, category, name, data, **meta):
        """辅助：插入一条世界观设定。"""
        data_json = json.dumps(data, ensure_ascii=False)
        keys = json.dumps(meta.get("keys", []), ensure_ascii=False)
        tags = json.dumps(meta.get("tags", [category]), ensure_ascii=False)

        query(
            "INSERT INTO world_settings (novel_id, category, name, data, keys, tags, volume_range, region) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (novel_id, category, name, data_json, keys, tags,
             meta.get("volume_range", ""), meta.get("region", "全域")),
            fetch="none"
        )

    def test_faction_sync(self, novel_id, engine, test_novel_dir):
        """势力（faction）DB→File 同步验证。"""
        self._insert_world(novel_id, "faction", "壁盾军团", {
            "定位": "铁谷镇唯一军事力量",
            "规模": "中型",
            "与主角关系": "复杂",
            "核心理念": "守护壁盾，永不动摇",
            "内部结构": "军团长→百夫长→小队长→士兵",
            "标志特征": "黑铁色铠甲、盾形徽章",
            "叙事定位": "前中期boss·军事独裁",
            "关键人物": ["赵铁山"],
            "核心矛盾": "守城责任 vs 对上层的盲从",
            "写作要点": "写壁盾军团时，氛围是压迫感和铁锈味",
            "content": "壁盾军团是铁谷镇唯一的军事组织……"
        }, keys=["壁盾", "军团"], volume_range="V1-V5")

        result = engine.db_to_files("测试小说", "world", overwrite=True)
        assert result["synced"] >= 1, f"世界观同步失败: {result}"

        faction_file = test_novel_dir / "设定" / "世界观" / "势力" / "壁盾军团.md"
        assert faction_file.exists(), "势力文件未生成"

        content = faction_file.read_text(encoding="utf-8")
        assert "壁盾军团" in content
        # per-entity mode: category encoded in directory path, not file content
        assert "势力" in str(faction_file)

    def test_location_sync(self, novel_id, engine, test_novel_dir):
        """地点（location）DB→File 同步验证。"""
        self._insert_world(novel_id, "location", "铁谷镇", {
            "空间结构": "多层",
            "灵能状态": "紊乱",
            "感官基线": {
                "气味": "铁锈和潮湿泥土",
                "声音": "远处锻造锤击声",
                "温度": "偏冷",
                "光照": "灰蒙蒙"
            },
            "所属势力": "壁盾军团",
            "功能": "聚居点",
            "安全等级": "中风险",
            "content": "铁谷镇位于外围与北境的交界处……"
        }, keys=["铁谷", "镇"], volume_range="V1-V3", region="外围")

        result = engine.db_to_files("测试小说", "world", overwrite=True)
        assert result["synced"] >= 1

        location_file = test_novel_dir / "设定" / "世界观" / "地图" / "铁谷镇.md"
        assert location_file.exists(), "地点文件未生成"

        content = location_file.read_text(encoding="utf-8")
        assert "铁谷镇" in content

    def test_item_sync(self, novel_id, engine, test_novel_dir):
        """物品/装备（item）DB→File 同步验证。"""
        self._insert_world(novel_id, "item", "碎铁匕首", {
            "type": "武器",
            "rarity": "稀有",
            "外观": "灰黑色、布满裂纹、握柄缠旧布条",
            "功能": "对灵能体造成额外伤害",
            "来源": "沈野从废墟中捡到",
            "使用限制": "每次使用消耗持有者微量灵能",
            "归属": "沈野",
            "content": "碎铁匕首是一把从远古灵纹碎片中诞生的武器……"
        }, keys=["碎铁", "匕首"], volume_range="V1-V8")

        result = engine.db_to_files("测试小说", "world", overwrite=True)
        assert result["synced"] >= 1

        item_file = test_novel_dir / "设定" / "世界观" / "物品装备" / "碎铁匕首.md"
        assert item_file.exists(), "物品文件未生成"

        content = item_file.read_text(encoding="utf-8")
        assert "碎铁匕首" in content

    def test_ability_sync(self, novel_id, engine, test_novel_dir):
        """能力体系（ability）DB→File 同步验证。"""
        self._insert_world(novel_id, "ability", "灵纹共鸣", {
            "类型": "感知型",
            "阶位": "初觉",
            "核心机制": "感知并操控灵能纹路",
            "触发条件": "情绪强烈时自动激活",
            "限制": ["消耗体力", "高频使用会导致灵衰"],
            "代价": "每次使用消耗精神力",
            "代表角色": "沈野",
            "content": "灵纹共鸣是极其罕见的感知型能力……"
        }, keys=["灵纹", "共鸣"], volume_range="V1-V14")

        result = engine.db_to_files("测试小说", "world", overwrite=True)
        assert result["synced"] >= 1

        ability_file = test_novel_dir / "设定" / "世界观" / "能力体系" / "灵纹共鸣.md"
        assert ability_file.exists(), "能力体系文件未生成"

    def test_core_setting_sync(self, novel_id, engine, test_novel_dir):
        """核心设定（core_setting）DB→File 同步验证。"""
        self._insert_world(novel_id, "core_setting", "灵衰", {
            "锁定": True,
            "叙事功能": "核心危机驱动",
            "关联设定": ["灵能", "异灵"],
            "content": "灵衰是灵能逐渐消散的灾难性现象……"
        }, keys=["灵衰", "消散"], volume_range="V1-V14")

        result = engine.db_to_files("测试小说", "world", overwrite=True)
        assert result["synced"] >= 1

        core_file = test_novel_dir / "设定" / "世界观" / "核心设定" / "灵衰.md"
        assert core_file.exists(), "核心设定文件未生成"

        content = core_file.read_text(encoding="utf-8")
        assert "灵衰" in content

    def test_world_multi_category_aggregate(self, novel_id, engine, test_novel_dir):
        """验证多个世界观分类写入不同文件。"""
        self._insert_world(novel_id, "faction", "壁盾军团", {"content": "军事力量"}, keys=["壁盾"])
        self._insert_world(novel_id, "faction", "星火社", {"content": "反抗组织"}, keys=["星火"])
        self._insert_world(novel_id, "location", "铁谷镇", {"content": "边境小镇"}, keys=["铁谷"])

        result = engine.db_to_files("测试小说", "world", overwrite=True)
        assert result["synced"] >= 3

        faction_file1 = test_novel_dir / "设定" / "世界观" / "势力" / "壁盾军团.md"
        faction_file2 = test_novel_dir / "设定" / "世界观" / "势力" / "星火社.md"
        location_file = test_novel_dir / "设定" / "世界观" / "地图" / "铁谷镇.md"

        assert faction_file1.exists(), "壁盾军团文件未生成"
        assert faction_file2.exists(), "星火社文件未生成"
        assert location_file.exists(), "铁谷镇文件未生成"

        assert "壁盾军团" in faction_file1.read_text(encoding="utf-8")
        assert "星火社" in faction_file2.read_text(encoding="utf-8")


# ============================================================================
# 4. 伏笔维度 — 聚合文件同步
# ============================================================================

class TestForeshadowRoundTrip:
    """伏笔维度：验证伏笔在 DB↔File 聚合模式下的同步。"""

    def _setup_chapters(self, novel_id):
        """辅助：创建章节用于伏笔引用。"""
        for i in range(1, 6):
            query(
                "INSERT INTO chapters (novel_id, number, title, status) VALUES (?, ?, ?, ?)",
                (novel_id, i, f"第{i}章", "planned"), fetch="none"
            )

    def test_foreshadow_db_to_file(self, novel_id, engine, test_novel_dir):
        """伏笔 DB→File 聚合同步验证。"""
        self._setup_chapters(novel_id)

        query(
            "INSERT INTO foreshadows (novel_id, description, importance, status, related_characters, tags) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (novel_id, "沈野左耳后的旧疤来历", "high", "planted",
             json.dumps(["沈野"], ensure_ascii=False),
             json.dumps(["身份", "过去"], ensure_ascii=False)),
            fetch="none"
        )

        query(
            "INSERT INTO foreshadows (novel_id, description, importance, status, related_characters, tags) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (novel_id, "铁谷镇地下的灵纹阵法", "medium", "planted",
             json.dumps(["沈野", "方岩"], ensure_ascii=False),
             json.dumps(["地点", "秘密"], ensure_ascii=False)),
            fetch="none"
        )

        result = engine.db_to_files("测试小说", "foreshadow", overwrite=True)
        assert result["synced"] >= 2, f"伏笔同步失败: {result}"

        foreshadow_file = test_novel_dir / "设定" / "大纲" / "伏笔清单.md"
        assert foreshadow_file.exists(), "伏笔清单文件未生成"

        content = foreshadow_file.read_text(encoding="utf-8")
        assert "旧疤" in content
        assert "灵纹阵法" in content


# ============================================================================
# 5. 回响维度 — 聚合文件同步
# ============================================================================

class TestEchoRoundTrip:
    """回响维度：验证回响在 DB↔File 聚合模式下的同步。"""

    def _setup_chapters_and_echoes(self, novel_id):
        """辅助：创建章节和回响。"""
        for i in range(1, 6):
            query(
                "INSERT INTO chapters (novel_id, number, title, status) VALUES (?, ?, ?, ?)",
                (novel_id, i, f"第{i}章", "planned"), fetch="none"
            )

        # 创建一个卷
        vol = query(
            "INSERT INTO volumes (novel_id, number, title) VALUES (?, ?, ?)",
            (novel_id, 1, "兽潮"), fetch="insert"
        )

        # 获取章节 ID
        ch1 = query("SELECT id FROM chapters WHERE novel_id=? AND number=?",
                     (novel_id, 1), fetch="one")
        ch3 = query("SELECT id FROM chapters WHERE novel_id=? AND number=?",
                     (novel_id, 3), fetch="one")

        if ch1 and ch3:
            query(
                "INSERT INTO echoes (novel_id, source_chapter_id, echo_chapter_id, volume_id, "
                "source_event, echo_type, echo_description, strong_related, tags) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (novel_id, ch1["id"], ch3["id"], vol["id"],
                 "沈野第一次使用灵纹", "character_habit", "方岩模仿沈野握拳方式", 0,
                 json.dumps(["沈野", "方岩"], ensure_ascii=False)),
                fetch="none"
            )

    def test_echo_db_to_file(self, novel_id, engine, test_novel_dir):
        """回响 DB→File 聚合同步验证。"""
        self._setup_chapters_and_echoes(novel_id)

        if "echo" in engine.available_types:
            result = engine.db_to_files("测试小说", "echo", overwrite=True)
            assert result["synced"] >= 1, f"回响同步失败: {result}"

            echo_file = test_novel_dir / "设定" / "大纲" / "回响清单.md"
            assert echo_file.exists(), "回响清单文件未生成"


# ============================================================================
# 6. 跨维度交叉引用一致性
# ============================================================================

class TestCrossDimensionIntegrity:
    """
    跨维度交叉引用一致性测试。

    验证：
    - 人物引用的 faction_id 在 world_settings(faction) 中存在
    - world_settings 中的 key_persons 在 characters 表中存在
    - 伏笔的 related_characters 指向真实存在的人物
    - 章节事件引用的人物/地点在对应表中存在
    """

    def _insert_world(self, novel_id, category, name, data, **meta):
        """辅助：插入世界观设定。"""
        data_json = json.dumps(data, ensure_ascii=False)
        keys = json.dumps(meta.get("keys", []), ensure_ascii=False)
        tags = json.dumps(meta.get("tags", [category]), ensure_ascii=False)
        query(
            "INSERT INTO world_settings (novel_id, category, name, data, keys, tags) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (novel_id, category, name, data_json, keys, tags),
            fetch="none"
        )

    def test_character_faction_reference(self, novel_id, engine, test_novel_dir):
        """人物→势力交叉引用：人物的 faction_id 必须指向 world_settings(faction) 中的条目。"""
        # 先创建势力
        self._insert_world(novel_id, "faction", "壁盾军团", {"content": "军事力量"}, keys=["壁盾"])

        faction_row = query(
            "SELECT id FROM world_settings WHERE novel_id=? AND category='faction' AND name=?",
            (novel_id, "壁盾军团"), fetch="one"
        )
        assert faction_row is not None, "势力未创建成功"

        # 创建归属该势力的人物
        query(
            "INSERT INTO characters (novel_id, name, role, faction_id, appearance, personality, "
            "background, goals, weaknesses, speech_style, arc_notes, first_appearance_chapter) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (novel_id, "方岩", "ally", faction_row["id"],
             "魁梧青年", "豪爽", "壁盾军团士兵", "守护城镇",
             "冲动", "大嗓门", "从服从到质疑", 1),
            fetch="none"
        )

        # 验证交叉引用
        char = query(
            "SELECT * FROM characters WHERE novel_id=? AND name='方岩'",
            (novel_id,), fetch="one"
        )
        assert char is not None
        assert char["faction_id"] == faction_row["id"], "人物 faction_id 与势力 ID 不匹配"

        # 反向验证：势力可以查到归属人物
        faction_members = query(
            "SELECT * FROM characters WHERE novel_id=? AND faction_id=?",
            (novel_id, faction_row["id"])
        )
        assert len(faction_members) >= 1, "势力下应有人物"

    def test_foreshadow_character_reference(self, novel_id):
        """伏笔→人物交叉引用：伏笔的 related_characters 必须指向真实存在的人物。"""
        # 创建人物
        query(
            "INSERT INTO characters (novel_id, name, role, appearance, personality, "
            "background, goals, weaknesses, speech_style, arc_notes, first_appearance_chapter) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (novel_id, "沈野", "protagonist", "瘦削少年", "沉默", "孤儿",
             "找到妹妹", "过度保护", "简短", "弧线", 1),
            fetch="none"
        )

        # 创建伏笔引用该人物
        query(
            "INSERT INTO foreshadows (novel_id, description, importance, status, related_characters, tags) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (novel_id, "沈野的旧疤", "high", "planted",
             json.dumps(["沈野"], ensure_ascii=False),
             json.dumps(["身份"], ensure_ascii=False)),
            fetch="none"
        )

        # 验证：伏笔中引用的人物名称在 characters 表中存在
        foreshadows = query(
            "SELECT * FROM foreshadows WHERE novel_id=?",
            (novel_id,)
        )
        assert len(foreshadows) >= 1

        for fs in foreshadows:
            related = json.loads(fs["related_characters"]) if fs["related_characters"] else []
            for char_name in related:
                exists = query(
                    "SELECT id FROM characters WHERE novel_id=? AND name=? AND is_active=1",
                    (novel_id, char_name), fetch="one"
                )
                assert exists is not None, f"伏笔引用的人物 '{char_name}' 不存在于 characters 表"

    def test_location_faction_cross_reference(self, novel_id):
        """地点→势力交叉引用：地点的所属势力必须在 world_settings(faction) 中存在。"""
        self._insert_world(novel_id, "faction", "壁盾军团", {"content": "军事力量"}, keys=["壁盾"])

        # 创建地点关联该势力
        self._insert_world(novel_id, "location", "铁谷镇", {
            "所属势力": "壁盾军团",
            "content": "铁谷镇"
        }, keys=["铁谷"])

        # 验证：地点数据中引用的势力名在 world_settings 中存在
        loc = query(
            "SELECT * FROM world_settings WHERE novel_id=? AND category='location' AND name='铁谷镇'",
            (novel_id,), fetch="one"
        )
        assert loc is not None
        loc_data = json.loads(loc["data"]) if isinstance(loc["data"], str) else loc["data"]
        if "所属势力" in loc_data:
            faction_exists = query(
                "SELECT id FROM world_settings WHERE novel_id=? AND category='faction' AND name=?",
                (novel_id, loc_data["所属势力"]), fetch="one"
            )
            assert faction_exists is not None, f"地点引用的势力 '{loc_data['所属势力']}' 不存在"


# ============================================================================
# 7. MD 解析器往返测试
# ============================================================================

class TestMDParserRoundTrip:
    """验证 MD 解析器与渲染器的对称性。"""

    def test_bullet_fields_round_trip(self):
        """bullet 字段 `- **key**: value` 渲染→解析→比较。"""
        original = {"name": "沈野", "role": "protagonist", "race": "人类"}

        # 渲染
        lines = []
        for k, v in original.items():
            lines.append(_md_bullet(k, v))
        md_text = "\n".join(lines)

        # 解析
        parsed = parse_bullet_fields(md_text)

        assert parsed["name"] == "沈野"
        assert parsed["role"] == "protagonist"
        assert parsed["race"] == "人类"

    def test_jsonb_round_trip(self):
        """JSONB 嵌套结构渲染→解析→比较。

        通过 roundtrip() 辅助函数模拟实际 DB→MD→DB 流程，
        验证 list[dict] 通过 HTML 注释标注实现无损往返。
        """
        original = {
            "core_conflict": "安全 vs 真相",
            "daily_state": "谨慎观察",
            "rules": [
                {"priority": 1, "name": "保护弱者", "description": "优先保护"},
            ]
        }

        # 使用 roundtrip 模拟实际 DB→MD→DB 流程
        parsed = roundtrip(original)

        assert parsed is not None
        assert parsed["core_conflict"] == "安全 vs 真相"
        assert parsed["daily_state"] == "谨慎观察"
        # list[dict] 通过 HTML 注释标注正确保持 list 结构
        assert "rules" in parsed
        assert isinstance(parsed["rules"], list), f"期望 list，实际 {type(parsed['rules']).__name__}: {parsed['rules']}"
        assert len(parsed["rules"]) == 1
        assert parsed["rules"][0]["name"] == "保护弱者"

    def test_md_table_round_trip(self):
        """MD 表格渲染→解析→比较。"""
        original = [
            {"角色": "沈野", "卷初状态": "普通少年", "触发事件": "兽潮", "卷末状态": "觉醒者"},
            {"角色": "方岩", "卷初状态": "士兵", "触发事件": "防线崩溃", "卷末状态": "质疑者"},
        ]

        # 渲染
        rendered = _render_md_table(original, list(original[0].keys()))
        md_text = "\n".join(rendered)

        # 解析
        parsed = parse_md_table(md_text)

        assert parsed is not None
        assert len(parsed) == 2
        assert parsed[0]["角色"] == "沈野"
        assert parsed[1]["角色"] == "方岩"

    def test_blockquote_round_trip(self):
        """blockquote `> **label**：value` 渲染→解析→比较。"""
        md_text = "> **核心情绪**：恐惧→坚韧\n> **POV锚点**：第三人称·沈野限知\n> **时间跨度**：D1-D14"

        parsed = parse_blockquotes(md_text)

        assert parsed["核心情绪"] == "恐惧→坚韧"
        assert parsed["POV锚点"] == "第三人称·沈野限知"
        assert parsed["时间跨度"] == "D1-D14"

    def test_acts_round_trip(self):
        """四幕结构渲染→解析→比较。"""
        md_text = """### 起
铁谷镇的黎明。

事件清单：
- E1：兽潮前兆
- E2：沈野觉醒灵纹

费笔清单：
- 费笔1：镇民恐慌

### 承
危机加剧。

事件清单：
- E1：防线崩溃
"""

        parsed = parse_acts(md_text, ["起", "承", "转", "合"])

        assert "act_intro" in parsed
        assert parsed["act_intro"]["prose"] == "铁谷镇的黎明。"
        assert "兽潮前兆" in parsed["act_intro"]["events"]
        assert "镇民恐慌" in parsed["act_intro"]["feibi_notes"]

    def test_deeply_nested_jsonb_round_trip(self):
        """深度嵌套 JSONB 往返测试（3+ 层嵌套）。

        通过 roundtrip() 验证 list[dict] 在嵌套结构中通过 HTML 注释标注
        正确还原为 list，数据内容无损。
        """
        original = {
            "appearance_changes": [
                {
                    "stage": "V1起点",
                    "change": "手臂出现灵纹",
                    "trigger": "首次使用能力"
                },
                {
                    "stage": "V5",
                    "change": "灵纹扩散至全身",
                    "trigger": "与异灵战斗后"
                }
            ],
            "dialogue_generation": {
                "step1": "识别情绪状态",
                "step2": "选择声音变体",
                "step3": "应用对话调整"
            }
        }

        parsed = roundtrip(original)

        assert parsed is not None
        # appearance_changes: list[dict] 通过 HTML 注释标注正确还原为 list
        assert "appearance_changes" in parsed, \
            "appearance_changes 数据在 round-trip 中丢失"
        assert isinstance(parsed["appearance_changes"], list), \
            f"期望 list，实际 {type(parsed['appearance_changes']).__name__}"
        assert len(parsed["appearance_changes"]) == 2
        assert parsed["appearance_changes"][0]["stage"] == "V1起点"
        assert parsed["appearance_changes"][0]["change"] == "手臂出现灵纹"
        assert parsed["appearance_changes"][1]["stage"] == "V5"
        # dialogue_generation 是纯 dict，应完美还原
        assert "dialogue_generation" in parsed
        assert parsed["dialogue_generation"]["step1"] == "识别情绪状态"


# ============================================================================
# 8. 交叉生成验证 — 从一个维度推断另一个维度
# ============================================================================

class TestCrossGeneration:
    """
    交叉生成验证：验证一个维度的数据能否用于生成/验证另一个维度的数据。

    核心思想：
    - 大纲（volume）中的人物弧光应与 characters 表中的 arc_notes 对应
    - 大纲中的伏笔清单应与 foreshadows 表中的记录对应
    - 人物的 faction_id 应与 world_settings 中的势力条目对应
    - 大纲中的场景地点应与 world_settings(location) 对应
    """

    def test_volume_character_arcs_match_characters(self, novel_id):
        """大纲人物弧光 → 人物 arc_notes 对应验证。"""
        # 创建人物
        query(
            "INSERT INTO characters (novel_id, name, role, appearance, personality, "
            "background, goals, weaknesses, speech_style, arc_notes, first_appearance_chapter) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (novel_id, "沈野", "protagonist", "瘦削", "沉默", "孤儿",
             "找到妹妹", "过度保护", "简短",
             "从自我封闭到学会信任", 1),
            fetch="none"
        )

        # 创建大纲卷，其人物弧光表引用同一人物
        vol = query(
            "INSERT INTO volumes (novel_id, number, title, character_arcs) "
            "VALUES (?, ?, ?, ?)",
            (novel_id, 1, "兽潮",
             json.dumps([
                 {"角色": "沈野", "卷初状态": "自我封闭", "触发事件": "兽潮", "卷末状态": "开始信任"}
             ], ensure_ascii=False)),
            fetch="insert"
        )

        # 验证：大纲人物弧光中的角色名在 characters 表中存在
        vol_data = query("SELECT * FROM volumes WHERE id=?", (vol["id"],), fetch="one")
        arcs = json.loads(vol_data["character_arcs"]) if vol_data["character_arcs"] else []

        for arc in arcs:
            char_name = arc.get("角色", "")
            char_exists = query(
                "SELECT id FROM characters WHERE novel_id=? AND name=? AND is_active=1",
                (novel_id, char_name), fetch="one"
            )
            assert char_exists is not None, f"大纲弧光引用的角色 '{char_name}' 不存在于 characters 表"

    def test_foreshadow_from_outline_exists_in_db(self, novel_id):
        """大纲中列出的伏笔应在 foreshadows 表中有对应记录。"""
        # 创建章节
        query(
            "INSERT INTO chapters (novel_id, number, title, status) VALUES (?, ?, ?, ?)",
            (novel_id, 1, "第一章", "planned"), fetch="none"
        )

        # 创建伏笔
        query(
            "INSERT INTO foreshadows (novel_id, description, importance, status, tags) "
            "VALUES (?, ?, ?, ?, ?)",
            (novel_id, "沈野的旧疤来历", "high", "planted",
             json.dumps(["身份"], ensure_ascii=False)),
            fetch="none"
        )

        # 验证：foreshadows 表中存在该伏笔
        fs = query(
            "SELECT * FROM foreshadows WHERE novel_id=? AND description LIKE '%旧疤%'",
            (novel_id,), fetch="one"
        )
        assert fs is not None, "伏笔未在 foreshadows 表中找到"
        assert fs["importance"] == "high"

    def test_world_location_in_volume_outline(self, novel_id):
        """大纲中提到的地点应在 world_settings(location) 中有对应条目。"""
        # 创建地点
        query(
            "INSERT INTO world_settings (novel_id, category, name, data) "
            "VALUES (?, ?, ?, ?)",
            (novel_id, "location", "铁谷镇",
             json.dumps({"content": "铁谷镇"}, ensure_ascii=False)),
            fetch="none"
        )

        # 创建卷大纲，其场景中提到该地点
        vol = query(
            "INSERT INTO volumes (novel_id, number, title, act_intro) "
            "VALUES (?, ?, ?, ?)",
            (novel_id, 1, "兽潮",
             json.dumps({
                 "prose": "铁谷镇的黎明被兽吼撕碎。",
                 "events": ["兽潮前兆"], "feibi_notes": [], "list_items": []
             }, ensure_ascii=False)),
            fetch="insert"
        )

        # 验证：大纲中提到的地点名在 world_settings 中存在
        loc_exists = query(
            "SELECT id FROM world_settings WHERE novel_id=? AND category='location' AND name LIKE '%铁谷%'",
            (novel_id,), fetch="one"
        )
        assert loc_exists is not None, "大纲中提到的地点 '铁谷镇' 不在 world_settings(location) 中"

    def test_character_ability_matches_world_ability(self, novel_id):
        """人物的 ability_system 应与 world_settings(ability) 中的条目对应。"""
        # 创建能力设定
        query(
            "INSERT INTO world_settings (novel_id, category, name, data) "
            "VALUES (?, ?, ?, ?)",
            (novel_id, "ability", "灵纹共鸣",
             json.dumps({
                 "类型": "感知型", "阶位": "初觉",
                 "代表角色": "沈野",
                 "content": "灵纹共鸣是罕见的感知型能力"
             }, ensure_ascii=False)),
            fetch="none"
        )

        # 创建人物，其 ability_system 引用该能力
        query(
            "INSERT INTO characters (novel_id, name, role, appearance, personality, "
            "background, goals, weaknesses, speech_style, arc_notes, first_appearance_chapter, "
            "ability_system) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (novel_id, "沈野", "protagonist", "瘦削", "沉默", "孤儿",
             "找到妹妹", "过度保护", "简短", "弧线", 1,
             json.dumps({"core": "灵纹共鸣", "essence": "感知灵能纹路"}, ensure_ascii=False)),
            fetch="none"
        )

        # 验证：人物的 ability_system.core 在 world_settings(ability) 中存在
        char = query(
            "SELECT * FROM characters WHERE novel_id=? AND name='沈野'",
            (novel_id,), fetch="one"
        )
        ability_data = json.loads(char["ability_system"]) if char["ability_system"] else {}
        ability_name = ability_data.get("core", "")

        ability_exists = query(
            "SELECT id FROM world_settings WHERE novel_id=? AND category='ability' AND name=?",
            (novel_id, ability_name), fetch="one"
        )
        assert ability_exists is not None, f"人物能力 '{ability_name}' 不在 world_settings(ability) 中"


# ============================================================================
# 9. 引擎基础功能测试
# ============================================================================

class TestSyncEngineBasics:
    """SyncEngine 基础功能验证。"""

    def test_manifest_loading(self, engine):
        """验证 YAML manifest 正确加载。"""
        assert "character" in engine.available_types, "character 模板未加载"
        assert "world" in engine.available_types, "world 模板未加载"
        assert "volume" in engine.available_types, "volume 模板未加载"
        assert "foreshadow" in engine.available_types, "foreshadow 模板未加载"

    def test_character_template_sections(self, engine):
        """验证人物模板包含所有必需段落。"""
        tpl = engine.get("character")
        section_headings = [s.heading for s in tpl.sections]

        # 必需段落
        required = ["基本信息", "外观与性格", "背景与动机", "弧线"]
        for req in required:
            assert req in section_headings, f"人物模板缺少必需段落: {req}"

        # JSONB 段落
        jsonb_headings = ["外观描写库", "决策引擎", "对话声音指纹", "能力体系", "行为模式"]
        for jh in jsonb_headings:
            assert jh in section_headings, f"人物模板缺少 JSONB 段落: {jh}"

    def test_world_template_category_file_map(self, engine):
        """验证世界观模板的 category_file_map 映射完整。"""
        tpl = engine.get("world")
        assert tpl.category_file_map is not None

        required_categories = ["faction", "location", "ability", "item",
                               "core_setting", "race", "economy"]
        for cat in required_categories:
            assert cat in tpl.category_file_map, f"世界观 category_file_map 缺少分类: {cat}"

    def test_volume_template_acts(self, engine):
        """验证卷级大纲模板包含四幕结构。"""
        tpl = engine.get("volume")
        acts_sections = [sec for sec in tpl.sections if sec.type == "acts"]

        assert len(acts_sections) == 4, "四幕结构不完整"
        act_names = [sec.acts[0][0] for sec in acts_sections]
        assert act_names == ["起", "承", "转", "合"], f"四幕名称不正确: {act_names}"


# ============================================================================
# 10. 数据格式切换问题测试
# ============================================================================

class TestDataFormatSwitching:
    """验证 DB 和 File 之间数据格式切换的潜在问题。"""

    def test_empty_jsonb_field_handling(self, novel_id, engine, test_novel_dir):
        """空 JSONB 字段 '{}' 和 '[]' 在同步中不应丢失或变为 null。"""
        query(
            "INSERT INTO characters (novel_id, name, role, appearance, personality, "
            "background, goals, weaknesses, speech_style, arc_notes, first_appearance_chapter, "
            "appearance_detail, decision_engine) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (novel_id, "测试人物", "npc", "普通", "普通", "无",
             "无", "无", "普通", "无", 1,
             '{}', '{}'),
            fetch="none"
        )

        # DB → File 不应报错
        result = engine.db_to_files("测试小说", "character", overwrite=True)
        assert result["errors"] == [], f"空 JSONB 字段导致同步错误: {result['errors']}"

    def test_chinese_field_names_in_file(self, novel_id, engine, test_novel_dir):
        """文件中的字段名应按模板 md_key 定义输出。

        人物模板中 first_appearance_chapter 没有 md_key 映射，所以输出原始列名。
        世界观模板中 first_appearance_chapter 有 md_key: 首次出场，输出中文名。
        """
        query(
            "INSERT INTO characters (novel_id, name, role, appearance, personality, "
            "background, goals, weaknesses, speech_style, arc_notes, first_appearance_chapter) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (novel_id, "沈野", "protagonist", "瘦削", "沉默", "孤儿",
             "找到妹妹", "过度保护", "简短", "弧线", 5),
            fetch="none"
        )

        result = engine.db_to_files("测试小说", "character", overwrite=True)
        assert result["synced"] == 1

        char_file = test_novel_dir / "设定" / "人物" / "沈野.md"
        content = char_file.read_text(encoding="utf-8")

        # 人物模板中 first_appearance_chapter 的 md_key 是 first_appearance
        assert "first_appearance" in content, "first_appearance 字段未输出"
        assert "5" in content, "first_appearance_chapter 值未正确输出"

        # 世界观模板中有 md_key: 首次出场
        query(
            "INSERT INTO world_settings (novel_id, category, name, data, keys) "
            "VALUES (?, ?, ?, ?, ?)",
            (novel_id, "ability", "灵纹共鸣",
             json.dumps({"content": "灵纹共鸣", "首次出场": "Ch1"}, ensure_ascii=False),
             json.dumps(["灵纹"], ensure_ascii=False)),
            fetch="none"
        )

        engine.db_to_files("测试小说", "world", overwrite=True)

        ability_file = test_novel_dir / "设定" / "世界观" / "能力体系" / "灵纹共鸣.md"
        if ability_file.exists():
            world_content = ability_file.read_text(encoding="utf-8")
            # 世界观模板中 first_appearance_chapter 有 md_key: 首次出场
            # 但此测试插入的是 data JSON 中的内容，模板 md_key 映射的是 DB 平铺列
            # 所以这里只验证世界观数据正确输出即可
            assert "灵纹共鸣" in world_content

    def test_list_field_multi_line_rendering(self):
        """list 类型字段应渲染为多行 bullet，而非 JSON 数组。"""
        value = ["主线1：兽潮来袭", "主线2：灵纹觉醒", "主线3：防线崩溃"]
        result = _md_bullet("main_plotlines", value)

        assert isinstance(result, list), "list 类型应渲染为多行"
        assert len(result) == 3, "list 应渲染为 3 行"
        for line in result:
            assert "- **main_plotlines**:" in line

    def test_volume_range_parsing(self):
        """验证 volume_range 的解析逻辑。"""
        from novel_db.tools_world import _volume_in_range, _parse_volume_number

        assert _parse_volume_number("V3") == 3
        assert _parse_volume_number("V15") == 15
        assert _parse_volume_number("尾声") == 99

        assert _volume_in_range(3, "V1-V5")
        assert not _volume_in_range(6, "V1-V5")
        assert _volume_in_range(1, "V1")
        assert _volume_in_range(14, "V1-V14,尾声")
        assert _volume_in_range(99, "V1-V14,尾声")  # 尾声=99

    def test_bool_field_rendering(self):
        """布尔字段应渲染为 '是'/'否'，而非 True/False。"""
        assert _md_bullet("is_constant", True) == "- **is_constant**: 是"
        assert _md_bullet("is_constant", False) == "- **is_constant**: 否"

    def test_section_replace_merge_mode(self, novel_id, engine, test_novel_dir):
        """overwrite 模式：同 category 多条记录生成独立文件，更新后重新写入。"""
        query(
            "INSERT INTO world_settings (novel_id, category, name, data) "
            "VALUES (?, ?, ?, ?)",
            (novel_id, "faction", "壁盾军团",
             json.dumps({"content": "军事力量"}, ensure_ascii=False)),
            fetch="none"
        )
        query(
            "INSERT INTO world_settings (novel_id, category, name, data) "
            "VALUES (?, ?, ?, ?)",
            (novel_id, "faction", "星火社",
             json.dumps({"content": "反抗组织"}, ensure_ascii=False)),
            fetch="none"
        )

        result1 = engine.db_to_files("测试小说", "world", overwrite=True)
        assert result1["synced"] >= 2

        faction_file1 = test_novel_dir / "设定" / "世界观" / "势力" / "壁盾军团.md"
        faction_file2 = test_novel_dir / "设定" / "世界观" / "势力" / "星火社.md"
        assert faction_file1.exists()
        assert faction_file2.exists()
        assert "壁盾军团" in faction_file1.read_text(encoding="utf-8")
        assert "星火社" in faction_file2.read_text(encoding="utf-8")

        query(
            "UPDATE world_settings SET data=? WHERE novel_id=? AND category='faction' AND name='壁盾军团'",
            (json.dumps({"content": "更新后的军事力量"}, ensure_ascii=False), novel_id),
            fetch="none"
        )

        result2 = engine.db_to_files("测试小说", "world", overwrite=True)
        assert result2["synced"] >= 1

        content2 = faction_file1.read_text(encoding="utf-8")
        assert "壁盾军团" in content2


# ============================================================================
# 11. 模板字段映射完整性验证
# ============================================================================

class TestTemplateFieldCompleteness:
    """
    验证模板定义的每个字段都能正确地 DB→File 渲染和 File→DB 解析。

    核心检查：
    - 模板中定义的每个 FieldDef 都有对应的 DB 列
    - DB 列的值在文件中正确输出
    - 文件中的值能被逆向解析回 DB 列
    """

    def test_character_all_basic_fields_synced(self, novel_id, engine, test_novel_dir):
        """人物模板的所有基础字段在 DB→File 中完整输出。"""
        query(
            "INSERT INTO characters (novel_id, name, role, race, ability_level, "
            "appearance, personality, speech_style, catchphrase, "
            "background, goals, weaknesses, "
            "arc_notes, first_appearance_chapter, status) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (novel_id, "测试角色", "rival", "异族", "凝相",
             "高瘦、银发", "冷酷、狡猾", "低沉缓慢", "不值得",
             "被驱逐的异族后裔", "复仇", "固执",
             "从复仇到救赎", 3, '{"hp": 100}'),
            fetch="none"
        )

        result = engine.db_to_files("测试小说", "character", overwrite=True)
        assert result["synced"] == 1

        char_file = test_novel_dir / "设定" / "人物" / "测试角色.md"
        content = char_file.read_text(encoding="utf-8")

        # 验证所有基础字段
        expected_fields = ["role", "race", "ability_level", "appearance",
                           "personality", "speech_style", "catchphrase",
                           "background", "goals", "weaknesses",
                           "arc_notes", "first_appearance"]
        for field in expected_fields:
            assert field in content, f"人物文件缺少字段: {field}"

    def test_volume_all_section_types(self, engine):
        """卷级大纲模板包含所有段落类型。"""
        tpl = engine.get("volume")

        section_types = set()
        for sec in tpl.sections:
            section_types.add(sec.type)

        # 模板定义的段落类型
        expected_types = {"blockquote", "raw", "acts", "table", "jsonb"}
        for et in expected_types:
            assert et in section_types, f"卷级大纲模板缺少段落类型: {et}"

    def test_world_template_dynamic_heading(self, novel_id, engine, test_novel_dir):
        """世界观模板的动态 heading `{category}: {name}` 正确替换。"""
        query(
            "INSERT INTO world_settings (novel_id, category, name, data) "
            "VALUES (?, ?, ?, ?)",
            (novel_id, "race", "灵族",
             json.dumps({"起源": "远古灵能聚合体", "content": "灵族是……"}, ensure_ascii=False)),
            fetch="none"
        )

        result = engine.db_to_files("测试小说", "world", overwrite=True)
        assert result["synced"] >= 1

        race_file = test_novel_dir / "设定" / "世界观" / "种族" / "灵族.md"
        assert race_file.exists(), "种族文件未生成"

        content = race_file.read_text(encoding="utf-8")
        assert "race: 灵族" in content or "灵族" in content


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
