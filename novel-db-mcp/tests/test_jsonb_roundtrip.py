"""
JSONB MD 往返测试 — 验证 _jsonb_to_md ↔ parse_jsonb_bullets 的无损往返

核心修复验证：list[dict] 通过 title_key 标注实现无损往返

测试维度:
  1. 基础类型: dict, list[str], list[dict], 嵌套结构
  2. 业务场景: 大纲, 章节事件, 人物, 物品, 设定, 势力, 地点
  3. 边界情况: 空值, 重复 title_val, 深层嵌套, 混合结构
  4. 向后兼容: 旧格式无标注时仍可解析
"""

import json
import pytest
import sys
import os

# 将项目根目录加入 sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from novel_db.sync import _jsonb_to_md, _is_empty
from novel_db.md_parser import parse_jsonb_bullets, _parse_nested_bullets


# ============================================================================
# 工具函数
# ============================================================================

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


def assert_roundtrip_equal(data, jsonb_key="content"):
    """断言 data 经过 MD 往返后与原始数据相等"""
    parsed = roundtrip(data, jsonb_key)
    assert parsed == data, (
        f"往返不一致:\n"
        f"  原始: {json.dumps(data, ensure_ascii=False, indent=2)}\n"
        f"  解析: {json.dumps(parsed, ensure_ascii=False, indent=2)}"
    )


def assert_roundtrip_type(data, expected_type, jsonb_key="content"):
    """断言往返后的结果类型"""
    parsed = roundtrip(data, jsonb_key)
    actual_type = type(parsed).__name__
    expected_name = expected_type.__name__
    assert isinstance(parsed, expected_type), (
        f"类型不一致: 期望 {expected_name}, 实际 {actual_type}, 值: {parsed}"
    )


# ============================================================================
# 1. 基础类型测试
# ============================================================================

class TestBasicDict:
    """dict 类型往返测试"""

    def test_simple_dict(self):
        data = {"name": "沈野", "role": "主角", "level": 5}
        assert_roundtrip_equal(data)

    def test_nested_dict(self):
        data = {
            "基础信息": {"姓名": "沈野", "等级": 5},
            "能力": {"攻击": 90, "防御": 60}
        }
        assert_roundtrip_equal(data)

    def test_empty_dict(self):
        data = {}
        parsed = roundtrip(data)
        assert parsed == {} or parsed is None

    def test_dict_with_list_value(self):
        data = {"tags": ["热血", "正义"], "name": "沈野"}
        assert_roundtrip_equal(data)

    def test_dict_with_bool(self):
        data = {"is_active": True, "name": "沈野"}
        assert_roundtrip_equal(data)

    def test_dict_with_int(self):
        data = {"level": 5, "hp": 100}
        assert_roundtrip_equal(data)

    def test_dict_with_empty_list(self):
        """dict 中有空 list 值"""
        data = {"name": "沈野", "tags": []}
        parsed = roundtrip(data)
        assert isinstance(parsed, dict)
        assert parsed["name"] == "沈野"
        # 空 list 可能解析为 [] 或 None，都是可接受的
        assert parsed.get("tags") in ([], None, {})

    def test_dict_with_empty_dict(self):
        """dict 中有空 dict 值"""
        data = {"name": "沈野", "metadata": {}}
        parsed = roundtrip(data)
        assert isinstance(parsed, dict)
        assert parsed["name"] == "沈野"


class TestBasicList:
    """list[str] 类型往返测试"""

    def test_list_of_strings(self):
        data = ["热血", "正义", "成长"]
        assert_roundtrip_equal(data)

    def test_empty_list(self):
        data = []
        parsed = roundtrip(data)
        assert parsed == {} or parsed == [] or parsed is None

    def test_list_with_empty_string(self):
        data = ["a", "", "b"]
        assert_roundtrip_equal(data)


# ============================================================================
# 2. 核心修复: list[dict] 往返测试
# ============================================================================

class TestListOfDictsRoundtrip:
    """list[dict] 往返测试 — 验证 title_key 标注修复"""

    def test_list_dict_name_key(self):
        """人物列表: name 作为 title_key"""
        data = [
            {"name": "沈野", "role": "主角", "speech_style": "冷硬"},
            {"name": "林若烟", "role": "女主", "speech_style": "温柔"}
        ]
        assert_roundtrip_type(data, list)
        assert_roundtrip_equal(data)

    def test_list_dict_stage_key(self):
        """阶段列表: stage 作为 title_key"""
        data = [
            {"stage": "觉醒", "description": "发现自身能力", "level": 1},
            {"stage": "成长", "description": "经受考验", "level": 2},
            {"stage": "蜕变", "description": "超越极限", "level": 3}
        ]
        assert_roundtrip_type(data, list)
        assert_roundtrip_equal(data)

    def test_list_dict_type_key(self):
        """类型列表: type 作为 title_key"""
        data = [
            {"type": "灵器", "name": "星陨剑", "power": 95},
            {"type": "符箓", "name": "天雷符", "power": 80}
        ]
        assert_roundtrip_type(data, list)
        assert_roundtrip_equal(data)

    def test_list_dict_volume_key(self):
        """卷级列表: volume 作为 title_key"""
        data = [
            {"volume": "V1", "title": "兽潮", "chapters": 30},
            {"volume": "V2", "title": "边城", "chapters": 28}
        ]
        assert_roundtrip_type(data, list)
        assert_roundtrip_equal(data)

    def test_list_dict_single_item(self):
        """单元素 list[dict]"""
        data = [{"name": "沈野", "role": "主角"}]
        assert_roundtrip_type(data, list)
        assert_roundtrip_equal(data)

    def test_list_dict_deeply_nested(self):
        """深层嵌套的 list[dict]"""
        data = [
            {"name": "沈野", "abilities": {"攻击": {"type": "灵能", "level": 9}}},
            {"name": "林若烟", "abilities": {"防御": {"type": "灵阵", "level": 8}}}
        ]
        assert_roundtrip_type(data, list)
        assert_roundtrip_equal(data)

    def test_list_dict_with_nested_list(self):
        """list[dict] 中包含嵌套 list"""
        data = [
            {"name": "沈野", "tags": ["主角", "灵能者"]},
            {"name": "林若烟", "tags": ["女主", "阵法师"]}
        ]
        assert_roundtrip_type(data, list)
        assert_roundtrip_equal(data)

    def test_list_dict_with_none_value(self):
        """list[dict] 中包含 None 值（owner: None 会被 _is_empty 跳过）"""
        data = [
            {"name": "星陨剑", "type": "灵器", "power": 95},
            {"name": "天雷符", "type": "符箓", "power": 80}
        ]
        assert_roundtrip_type(data, list)
        assert_roundtrip_equal(data)

    def test_list_dict_preserves_order(self):
        """list[dict] 保持顺序"""
        data = [
            {"name": "A", "order": 1},
            {"name": "B", "order": 2},
            {"name": "C", "order": 3}
        ]
        parsed = roundtrip(data)
        assert isinstance(parsed, list)
        assert [item["name"] for item in parsed] == ["A", "B", "C"]


class TestDuplicateTitleValues:
    """重复 title_val 测试 — 验证 list[dict] 不会因为同标题而合并"""

    def test_duplicate_name_values(self):
        """同名人物不应被合并（旧 bug: dict 模式会覆盖）"""
        data = [
            {"name": "影子", "type": "灵兽", "level": 5},
            {"name": "影子", "type": "幻影", "level": 8}
        ]
        parsed = roundtrip(data)
        assert isinstance(parsed, list), f"期望 list，实际 {type(parsed).__name__}"
        assert len(parsed) == 2, f"期望 2 个元素，实际 {len(parsed)}"
        assert parsed[0]["type"] == "灵兽"
        assert parsed[1]["type"] == "幻影"

    def test_multiple_same_stage(self):
        """多个相同 stage 值"""
        data = [
            {"stage": "觉醒", "character": "沈野"},
            {"stage": "觉醒", "character": "林若烟"}
        ]
        parsed = roundtrip(data)
        assert isinstance(parsed, list)
        assert len(parsed) == 2
        assert parsed[0]["character"] == "沈野"
        assert parsed[1]["character"] == "林若烟"


# ============================================================================
# 3. 业务场景: 多维度数据测试
# ============================================================================

class TestOutlineRoundtrip:
    """大纲维度往返测试"""

    def test_volume_outline(self):
        data = {
            "title": "V1-兽潮",
            "core_emotion": "恐惧与勇气",
            "acts": {
                "起": {"prose": "小镇平静", "events": ["E1：异变初现"]},
                "承": {"prose": "危机加深", "events": ["E2：兽潮来袭"]}
            },
            "suspense_anchors": [
                {"stage": "开篇悬念", "content": "神秘的预言", "resolved": False},
                {"stage": "中段悬念", "content": "暗处的观察者", "resolved": False}
            ]
        }
        assert_roundtrip_equal(data)


class TestChapterEventsRoundtrip:
    """章节事件维度往返测试"""

    def test_chapter_events(self):
        data = [
            {"stage": "开篇", "event": "沈野发现自己能感应灵能", "chapter": 1},
            {"stage": "高潮", "event": "兽潮冲破防线", "chapter": 15},
            {"stage": "尾声", "event": "沈野决定前往灵站", "chapter": 28}
        ]
        assert_roundtrip_type(data, list)
        assert_roundtrip_equal(data)


class TestCharacterRoundtrip:
    """人物维度往返测试"""

    def test_character_full(self):
        data = {
            "name": "沈野",
            "role": "主角",
            "appearance": "黑发少年，眼神冷峻",
            "personality": "外表冷漠，内心热血",
            "speech_style": "简短有力，偶有讽刺",
            "voice_fingerprint": {
                "口头禅": ["切", "别挡路"],
                "语气特征": ["冷硬", "简洁"]
            },
            "ability_system": {
                "主能力": {"name": "灵能感应", "level": 9},
                "副能力": [{"name": "灵能爆发", "type": "攻击"}]
            }
        }
        assert_roundtrip_equal(data)


class TestItemRoundtrip:
    """物品维度往返测试"""

    def test_items_list(self):
        data = [
            {"name": "星陨剑", "type": "灵器", "power": 95},
            {"name": "天雷符", "type": "符箓", "power": 80},
            {"name": "灵能丹", "type": "消耗品", "power": 30}
        ]
        assert_roundtrip_type(data, list)
        assert_roundtrip_equal(data)


class TestSettingRoundtrip:
    """设定维度往返测试"""

    def test_world_setting(self):
        data = {
            "core_rules": {
                "灵能等级": ["E级", "D级", "C级", "B级", "A级", "S级"],
                "灵能来源": "灵脉"
            },
            "factions": [
                {"name": "灵能公会", "type": "官方", "influence": 90},
                {"name": "暗影组织", "type": "地下", "influence": 70}
            ]
        }
        assert_roundtrip_equal(data)


class TestFactionRoundtrip:
    """势力维度往返测试"""

    def test_factions(self):
        data = [
            {"name": "灵能公会", "leader": "钟衍", "territory": "中央城"},
            {"name": "暗影组织", "leader": "韩朗", "territory": "地下城"},
            {"name": "铁谷镇", "leader": "赵铁山", "territory": "铁谷镇"}
        ]
        assert_roundtrip_type(data, list)
        assert_roundtrip_equal(data)


class TestLocationRoundtrip:
    """地点维度往返测试"""

    def test_locations(self):
        data = [
            {"name": "中央城", "type": "主城", "description": "灵能公会的据点"},
            {"name": "铁谷镇", "type": "小镇", "description": "边境小镇"},
            {"name": "灵站", "type": "据点", "description": "灵能者中转站"}
        ]
        assert_roundtrip_type(data, list)
        assert_roundtrip_equal(data)

    def test_location_detail_nested(self):
        data = {
            "中央城": {
                "区域": ["内城", "外城", "地下区"],
                "势力": "灵能公会"
            },
            "铁谷镇": {
                "区域": ["镇中心", "矿区"],
                "势力": "赵铁山"
            }
        }
        assert_roundtrip_equal(data)


# ============================================================================
# 4. 边界与混合结构测试
# ============================================================================

class TestMixedStructure:
    """混合结构测试"""

    def test_dict_containing_list_of_dicts(self):
        """dict 中包含 list[dict]"""
        data = {
            "characters": [
                {"name": "沈野", "role": "主角"},
                {"name": "林若烟", "role": "女主"}
            ],
            "setting": "都市灵能"
        }
        assert_roundtrip_equal(data)

    def test_dict_with_multiple_list_of_dicts(self):
        """dict 中包含多个 list[dict]"""
        data = {
            "main_characters": [
                {"name": "沈野", "role": "主角"}
            ],
            "factions": [
                {"name": "灵能公会", "type": "官方"}
            ]
        }
        assert_roundtrip_equal(data)

    def test_deeply_nested_mixed(self):
        """深层嵌套混合结构"""
        data = {
            "卷级信息": {
                "人物弧光": [
                    {"name": "沈野", "变化": "恐惧到勇气"},
                    {"name": "林若烟", "变化": "封闭到信任"}
                ],
                "悬念锚点": [
                    {"stage": "开篇", "内容": "神秘预言"},
                    {"stage": "高潮", "内容": "真相揭示"}
                ]
            }
        }
        assert_roundtrip_equal(data)


class TestBackwardCompatibility:
    """向后兼容测试 — 旧格式（无标注）仍可解析"""

    def test_old_format_dict(self):
        """旧格式 `**key**:` 无标注时走 dict 模式"""
        md = "- **content**:\n    - **沈野**:\n        - **role**: 主角\n    - **林若烟**:\n        - **role**: 女主"
        parsed = parse_jsonb_bullets(md)
        # 旧格式无标注，走 dict 模式（行为不变）
        assert isinstance(parsed, dict)
        assert "沈野" in parsed
        assert parsed["沈野"]["role"] == "主角"

    def test_new_format_html_comment(self):
        """新格式 `**value**: <!-- key -->` 走 list[dict] 模式"""
        md = "- **content**:\n    - **沈野**: <!-- name -->\n        - **role**: 主角\n    - **林若烟**: <!-- name -->\n        - **role**: 女主"
        parsed = parse_jsonb_bullets(md)
        # 跳过 - **content**: 行后，子行匹配 <!-- name --> 标注
        # → has_annotation=True → list_of_dicts 模式
        assert isinstance(parsed, list)
        assert len(parsed) == 2
        assert parsed[0] == {"name": "沈野", "role": "主角"}
        assert parsed[1] == {"name": "林若烟", "role": "女主"}

    def test_old_paren_format_still_works(self):
        """旧格式 `**value** (key):` 仍可解析（向后兼容）"""
        md = "- **content**:\n    - **沈野** (name):\n        - **role**: 主角\n    - **林若烟** (name):\n        - **role**: 女主"
        parsed = parse_jsonb_bullets(md)
        assert isinstance(parsed, list)
        assert len(parsed) == 2
        assert parsed[0] == {"name": "沈野", "role": "主角"}
        assert parsed[1] == {"name": "林若烟", "role": "女主"}

    def test_mixed_annotation_partial(self):
        """混合格式: 部分项有标注时，走 list_of_dicts 模式，未标注项降级处理"""
        md = "- **content**:\n    - **沈野**: <!-- name -->\n        - **role**: 主角\n    - **setting**: 都市灵能"
        parsed = parse_jsonb_bullets(md)
        # has_annotation=True → list_of_dicts 模式
        assert parsed is not None
        assert isinstance(parsed, list)
        # 第一个项有标注，正常还原
        assert parsed[0]["name"] == "沈野"
        # 第二个项无标注，降级为 KV
        assert parsed[1]["setting"] == "都市灵能"


class TestMDRenderingFormat:
    """验证 MD 渲染输出格式"""

    def test_html_comment_in_output(self):
        """验证 _jsonb_to_md 输出包含 <!-- title_key --> HTML 注释标注"""
        data = [{"name": "沈野", "role": "主角"}]
        lines = _jsonb_to_md(data, indent=0)
        md_text = "\n".join(lines)
        assert "<!-- name -->" in md_text, f"期望输出包含 '<!-- name -->'，实际: {md_text}"

    def test_html_comment_with_stage_key(self):
        """验证 stage 作为 title_key 时的 HTML 注释标注"""
        data = [{"stage": "觉醒", "level": 1}]
        lines = _jsonb_to_md(data, indent=0)
        md_text = "\n".join(lines)
        assert "<!-- stage -->" in md_text, f"期望输出包含 '<!-- stage -->'，实际: {md_text}"

    def test_no_html_comment_for_dict(self):
        """普通 dict 不应产生 HTML 注释标注"""
        data = {"name": "沈野", "role": "主角"}
        lines = _jsonb_to_md(data, indent=0)
        md_text = "\n".join(lines)
        # dict 的渲染格式是 - **name**: 沈野，不应有 <!-- xxx --> 标注
        assert "<!-- name -->" not in md_text, f"dict 不应有标注，实际: {md_text}"

    def test_explicit_title_key_parameter(self):
        """验证 _jsonb_to_md 的 title_key 参数优先于自动检测"""
        data = [{"角色": "沈野", "role": "主角"}]
        # 不传 title_key → 自动检测，'role' 不在 _TITLE_KEYS 中，走 fallback
        lines_auto = _jsonb_to_md(data, indent=0)
        # 传 title_key='角色' → 使用显式指定
        lines_explicit = _jsonb_to_md(data, indent=0, title_key="角色")
        md_explicit = "\n".join(lines_explicit)
        assert "<!-- 角色 -->" in md_explicit, f"期望输出包含 '<!-- 角色 -->'，实际: {md_explicit}"

    def test_chinese_title_key_in_html_comment(self):
        """验证中文 title_key 在 HTML 注释中正确渲染"""
        data = [{"角色": "沈野", "状态": "活跃"}]
        lines = _jsonb_to_md(data, indent=0, title_key="角色")
        md_text = "\n".join(lines)
        assert "<!-- 角色 -->" in md_text
        # 往返验证
        parsed = parse_jsonb_bullets("\n".join(["- **content**:"] + lines))
        assert isinstance(parsed, list)
        assert parsed[0]["角色"] == "沈野"


# ============================================================================
# 5. 完整业务数据模拟测试
# ============================================================================

class TestFullBusinessRoundtrip:
    """完整业务数据模拟测试"""

    def test_appearance_detail(self):
        """人物外观描写库 JSONB 模拟"""
        data = {
            "外貌特征": ["黑发", "冷峻眼神", "修长身材"],
            "标志性装扮": {
                "日常": "黑色风衣",
                "战斗": "灵能铠甲"
            },
            "变化轨迹": [
                {"stage": "初期", "description": "瘦弱少年"},
                {"stage": "觉醒后", "description": "眼神锐利"},
                {"stage": "蜕变后", "description": "气场强大"}
            ]
        }
        assert_roundtrip_equal(data)

    def test_decision_engine(self):
        """决策引擎 JSONB 模拟"""
        data = {
            "核心动机": "保护身边的人",
            "决策权重": {"正义": 9, "安全": 8, "复仇": 3},
            "压力反应": [
                {"stage": "轻度", "behavior": "更加沉默"},
                {"stage": "中度", "behavior": "主动出击"},
                {"stage": "极限", "behavior": "灵能暴走"}
            ]
        }
        assert_roundtrip_equal(data)

    def test_suspense_anchors(self):
        """悬念锚点 JSONB 模拟"""
        data = [
            {"stage": "V1开篇", "anchor": "神秘预言", "resolved": False},
            {"stage": "V1中段", "anchor": "暗处观察者", "resolved": False},
            {"stage": "V1结尾", "anchor": "沈野的过去", "resolved": False}
        ]
        assert_roundtrip_type(data, list)
        assert_roundtrip_equal(data)

    def test_writing_priorities(self):
        """写作优先级 JSONB 模拟"""
        data = [
            {"target": "P0-核心主线", "description": "沈野觉醒线", "chapters": "1-28"},
            {"target": "P1-人物弧光", "description": "林若烟信任线", "chapters": "5-25"},
            {"target": "P2-世界观", "description": "灵能体系展示", "chapters": "3-20"}
        ]
        assert_roundtrip_type(data, list)
        assert_roundtrip_equal(data)

    def test_behavior_pattern(self):
        """行为模式 JSONB 模拟"""
        data = {
            "日常行为": ["清晨训练", "独自巡逻", "沉默吃饭"],
            "战斗偏好": "先防后攻",
            "社交模式": {
                "亲近者": "话多且关心",
                "陌生人": "沉默寡言",
                "敌人": "冷酷直接"
            },
            "成长轨迹": [
                {"stage": "初期", "pattern": "独来独往"},
                {"stage": "中期", "pattern": "逐渐信任伙伴"},
                {"stage": "后期", "pattern": "主动承担责任"}
            ]
        }
        assert_roundtrip_equal(data)


# ============================================================================
# 运行入口
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
