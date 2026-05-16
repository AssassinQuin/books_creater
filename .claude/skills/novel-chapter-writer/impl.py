#!/usr/bin/env python3
"""
novel-chapter-writer 实现代码
基于SKILL.md设计的逐章写作工作流 + 动态加载协议
"""

import json
import sys
import os
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional

# 项目路径
PROJECT_ROOT = Path("/Users/ganjie/code/personal/bywork/books_creater")
NOVEL_DIR = PROJECT_ROOT / "novels/这次不一样了"
LOREBOOK_DIR = NOVEL_DIR / "设定/lorebook/entries"
LOCKED_RULES_FILE = NOVEL_DIR / "设定/锁定设定.md"
CHARACTER_DEEPENING_FILE = NOVEL_DIR / "设定/角色深化.md"
CHARACTER_DIR = NOVEL_DIR / "设定/人物"
WORLDVIEW_DIR = NOVEL_DIR / "设定/世界观"


def load_writing_context(novel_id: int, chapter_number: int) -> Dict[str, Any]:
    """
    四级动态加载协议
    
    Tier 1: DB查询（必须加载）
    Tier 2: Lorebook按需加载
    Tier 3: 角色深化.md深度补充
    Tier 4: 锁定设定.md权威校验
    
    返回完整的写作上下文，包含冲突检测
    """
    context = {
        "novel_id": novel_id,
        "chapter_number": chapter_number,
        "tier1_db": {},
        "tier2_lorebook": {},
        "tier3_deepening": {},
        "tier4_locked": {},
        "conflicts": [],
        "warnings": []
    }
    
    # ===== Tier 1: DB查询（必须加载） =====
    print("\n[Tier 1/4] 加载DB上下文...")
    try:
        # TODO: 实现实际的MCP调用
        # context["tier1_db"] = mcp_call("get_chapter_context", novel_name="这次不一样了", chapter_number=chapter_number)
        
        # 模拟DB数据（实际实现中替换为MCP调用）
        context["tier1_db"] = simulate_db_context(novel_id, chapter_number)
        print(f"  ✓ 加载完成: {len(context['tier1_db'].get('characters', []))} 个角色, "
              f"{len(context['tier1_db'].get('foreshadows', []))} 个伏笔")
    except Exception as e:
        context["warnings"].append(f"DB加载失败: {e}")
        print(f"  ⚠ DB加载失败: {e}")
    
    # ===== Tier 2: Lorebook按需加载 =====
    print("\n[Tier 2/4] 按需加载Lorebook...")
    try:
        # 从DB上下文中提取关键词
        keywords = extract_keywords(context["tier1_db"])
        
        # 按需加载匹配的lorebook条目
        lorebook_entries = load_lorebook_entries(keywords)
        context["tier2_lorebook"] = lorebook_entries
        
        print(f"  ✓ 加载完成: {len(lorebook_entries)} 个条目")
        for entry_id in lorebook_entries:
            print(f"    - {entry_id}")
    except Exception as e:
        context["warnings"].append(f"Lorebook加载失败: {e}")
        print(f"  ⚠ Lorebook加载失败: {e}")
    
    # ===== Tier 3: 人物档案深度补充 =====
    print("\n[Tier 3/4] 加载人物档案...")
    try:
        deepening = load_character_deepening(context["tier1_db"].get("characters", []))
        context["tier3_deepening"] = deepening
        
        print(f"  ✓ 加载完成: {len(deepening)} 个角色深化")
        for char_name in deepening:
            print(f"    - {char_name}")
    except Exception as e:
        context["warnings"].append(f"角色深化加载失败: {e}")
        print(f"  ⚠ 角色深化加载失败: {e}")
    
    # ===== Tier 4: 锁定设定.md权威校验 =====
    print("\n[Tier 4/4] 锁定设定校验...")
    try:
        locked_rules = load_locked_rules()
        context["tier4_locked"] = locked_rules
        
        # 执行冲突检测
        conflicts = detect_conflicts(context)
        context["conflicts"] = conflicts
        
        if conflicts:
            print(f"  ⚠ 发现 {len(conflicts)} 处冲突:")
            for conflict in conflicts:
                print(f"    🔴 [{conflict['type']}] {conflict['detail']}")
        else:
            print("  ✓ 无冲突，所有数据源一致")
            
    except Exception as e:
        context["warnings"].append(f"锁定设定校验失败: {e}")
        print(f"  ⚠ 锁定设定校验失败: {e}")
    
    return context


def extract_keywords(db_context: Dict) -> List[str]:
    """从DB上下文中提取关键词，用于Lorebook按需加载"""
    keywords = []
    
    # 提取角色名
    for char in db_context.get("characters", []):
        keywords.append(char.get("name", ""))
        keywords.append(char.get("role", ""))
    
    # 提取地点
    for location in db_context.get("locations", []):
        keywords.append(location.get("name", ""))
    
    # 提取势力
    for faction in db_context.get("factions", []):
        keywords.append(faction.get("name", ""))
    
    # 提取大纲中的关键词
    outline = db_context.get("chapter", {}).get("outline", "")
    keywords.extend(extract_outline_keywords(outline))
    
    return list(set([k for k in keywords if k]))


def extract_outline_keywords(outline: str) -> List[str]:
    """从大纲文本中提取关键词"""
    # 简单的关键词提取：分词后过滤短词
    words = outline.replace("+", " ").replace("，", " ").replace("。", " ").split()
    return [w for w in words if len(w) >= 2]


def load_lorebook_entries(keywords: List[str]) -> Dict[str, Dict]:
    """按需加载Lorebook条目"""
    entries = {}
    
    if not LOREBOOK_DIR.exists():
        return entries
    
    for category_dir in LOREBOOK_DIR.iterdir():
        if not category_dir.is_dir():
            continue
        
        for yml_file in category_dir.glob("*.yml"):
            try:
                entry = yaml.safe_load(yml_file.read_text(encoding='utf-8'))
                if not entry:
                    continue
                
                entry_id = entry.get("id", yml_file.stem)
                entry_name = entry.get("name", "")
                entry_tags = entry.get("tags", [])
                entry_content = entry.get("content", "")
                
                # 检查是否匹配关键词
                is_match = False
                
                # 匹配名称
                if entry_name in keywords:
                    is_match = True
                
                # 匹配标签
                for tag in entry_tags:
                    if tag in keywords:
                        is_match = True
                        break
                
                # 匹配内容关键词（简单匹配）
                for keyword in keywords:
                    if keyword in entry_content and len(keyword) >= 2:
                        is_match = True
                        break
                
                if is_match:
                    entries[entry_id] = entry
                    
            except Exception as e:
                print(f"  警告: 无法解析 {yml_file}: {e}")
    
    return entries


def load_character_deepening(characters: List[Dict]) -> Dict[str, str]:
    """从人物档案文件加载角色深度描写"""
    deepening = {}
    
    for char in characters:
        char_name = char.get("name", "")
        if not char_name:
            continue
        
        # 在人物档案目录中查找该角色的文件
        char_file = CHARACTER_DIR / f"{char_name}.md"
        if char_file.exists():
            deepening[char_name] = char_file.read_text(encoding='utf-8')
        else:
            # 回退：在角色深化.md中查找（兼容旧结构）
            if CHARACTER_DEEPENING_FILE.exists():
                content = CHARACTER_DEEPENING_FILE.read_text(encoding='utf-8')
                section = extract_markdown_section(content, char_name)
                if section:
                    deepening[char_name] = section
    
    return deepening


def load_locked_rules() -> str:
    """加载锁定设定.md"""
    if LOCKED_RULES_FILE.exists():
        return LOCKED_RULES_FILE.read_text(encoding='utf-8')
    return ""


def detect_conflicts(context: Dict) -> List[Dict]:
    """检测多源之间的冲突"""
    conflicts = []
    
    # 检测1: DB人物 vs Lorebook人物
    db_characters = context["tier1_db"].get("characters", [])
    lorebook_entries = context["tier2_lorebook"]
    
    for char in db_characters:
        char_name = char.get("name", "")
        char_ability = char.get("ability_level", "")
        
        # 在lorebook中查找对应条目
        for entry_id, entry in lorebook_entries.items():
            if entry.get("name") == char_name:
                entry_content = entry.get("content", "")
                
                # 检查能力等级是否一致
                if char_ability and char_ability not in entry_content:
                    # 可能不一致，需要人工确认
                    conflicts.append({
                        "type": "人物能力差异",
                        "source1": f"DB:{char_name}",
                        "source2": f"Lorebook:{entry_id}",
                        "detail": f"DB中能力等级为'{char_ability}'，Lorebook中描述可能不同",
                        "severity": "medium"
                    })
    
    # 检测2: 锁定设定 vs Lorebook
    locked_rules = context["tier4_locked"]
    if locked_rules:
        for entry_id, entry in lorebook_entries.items():
            entry_content = entry.get("content", "")
            
            # 检查货币系统
            if "1金币" in entry_content and "1金币 = 10银币" not in locked_rules:
                # 如果锁定设定中没有货币规则，不报错
                pass
            
            # 检查能力体系
            if "七阶" in entry_content and "七阶体系" not in locked_rules:
                conflicts.append({
                    "type": "可能违反锁定设定",
                    "source": f"Lorebook:{entry_id}",
                    "detail": "条目涉及七阶体系，但锁定设定中未明确规范",
                    "severity": "low"
                })
    
    # 检测3: 角色深化 vs DB状态
    deepening = context["tier3_deepening"]
    for char_name, char_deepening in deepening.items():
        # 查找DB中对应角色
        db_char = next((c for c in db_characters if c.get("name") == char_name), None)
        if db_char:
            db_status = db_char.get("status", "")
            # 简单检查：如果DB状态与深化描写明显矛盾
            if db_status and "死亡" in db_status and "活着" in char_deepening:
                conflicts.append({
                    "type": "角色状态矛盾",
                    "source1": f"DB:{char_name}",
                    "source2": f"角色深化:{char_name}",
                    "detail": f"DB状态为'{db_status}'，但角色深化中描写矛盾",
                    "severity": "high"
                })
    
    return conflicts


def extract_markdown_section(content: str, section_name: str) -> str:
    """从markdown内容中提取指定章节"""
    lines = content.split('\n')
    section_lines = []
    in_section = False
    
    for line in lines:
        if line.startswith(f'### {section_name}') or line.startswith(f'## {section_name}'):
            in_section = True
            continue
        if in_section and line.startswith('#'):
            break
        if in_section:
            section_lines.append(line)
    
    return '\n'.join(section_lines).strip()


def simulate_db_context(novel_id: int, chapter_number: int) -> Dict:
    """模拟DB上下文（实际实现中替换为MCP调用）"""
    # 这里应该调用 MCP novel-db 工具
    # 例如：
    # return mcp_call("mcp_novel-db_chapter_get_context", novel_id=novel_id, chapter_number=chapter_number)
    
    return {
        "novel": {"id": novel_id, "name": "这次不一样了"},
        "chapter": {
            "id": chapter_number,
            "number": chapter_number,
            "title": "兽潮",
            "outline": "开场拾荒+灵站暗线+兽潮夜+妹妹发病+方岩给路+出发"
        },
        "volume": {"id": 1, "title": "兽潮"},
        "characters": [
            {"id": 1, "name": "沈野", "role": "protagonist", "ability_level": "铸造型"},
            {"id": 2, "name": "沈念", "role": "ally", "ability_level": "未觉醒"},
            {"id": 3, "name": "方岩", "role": "ally", "ability_level": "感知型"}
        ],
        "locations": [
            {"id": 1, "name": "第七管道聚落"},
            {"id": 2, "name": "灵站"}
        ],
        "factions": [
            {"id": 1, "name": "灵枢"},
            {"id": 2, "name": "壁盾军团"}
        ],
        "foreshadows": [
            {"id": 1, "description": "F1: 无法识别的残片"},
            {"id": 2, "description": "F2: 灵站异常"}
        ]
    }


# ===== 原有函数（保持不变） =====

def main(args):
    """主函数：处理skill调用参数"""
    
    if len(args) == 0:
        print("错误：缺少参数")
        print("用法：写第N章 / 继续写 / 写一章")
        print("示例：写第1章 / 继续写")
        return
    
    cmd = args[0]
    
    if cmd.startswith("写第"):
        parts = cmd.split("第")
        if len(parts) >= 2:
            try:
                chapter_num = int(parts[1].split("章")[0])
            except ValueError:
                print("错误：无法解析章节号")
                return
        else:
            print("错误：格式不正确，应为 '写第N章'")
            return
        
        title = ""
        if "，标题是" in cmd:
            title = cmd.split("，标题是")[1]
        
        write_chapter(chapter_num, title)
    
    elif cmd == "继续写":
        continue_writing()
    
    elif cmd == "写一章":
        write_next_chapter()
    
    else:
        print(f"错误：未知命令 '{cmd}'")


def write_chapter(chapter_num, title=""):
    """写单个章节的核心流程"""
    
    print(f"\n{'='*60}")
    print(f"开始第{chapter_num}章写作")
    print(f"标题：{title if title else '未命名'}")
    print(f"{'='*60}")
    
    # Step 1: 注入全量上下文（使用新的动态加载协议）
    print("\n[Step 1] 注入全量上下文...")
    context = load_writing_context(novel_name="这次不一样了", chapter_number=chapter_num)
    
    # 检查冲突
    if context["conflicts"]:
        print(f"\n⚠️  发现 {len(context['conflicts'])} 处冲突！")
        print("请先解决冲突后再写作。")
        for conflict in context["conflicts"]:
            print(f"  - [{conflict['type']}] {conflict['detail']}")
        return
    
    # Step 2: 写正文
    print("\n[Step 2] 写正文...")
    
    specs = read_specs()
    event_sequence = generate_event_sequence(chapter_num, context["tier1_db"])
    character_analysis = generate_character_analysis(context)
    
    print(f"\n事件序列：\n{event_sequence}")
    print(f"\n人物分析：\n{character_analysis}")
    
    print("\n[写作] 开始生成章节内容...")
    print("  [提示] 完整写作流程需要进一步实现")


def continue_writing():
    """继续上一章的写作"""
    print("\n继续写作功能需要实现")


def write_next_chapter():
    """自动获取下一章号并写作"""
    print("\n写下一章功能需要实现")


def read_specs():
    """读取写作执行规范"""
    specs_path = os.path.join(os.path.dirname(__file__), "写作执行规范.md")
    if os.path.exists(specs_path):
        with open(specs_path, 'r', encoding='utf-8') as f:
            return f.read()
    return ""


def generate_event_sequence(chapter_num, context):
    """根据大纲生成事件序列"""
    outline = context["chapter"]["outline"]
    events = [e.strip() for e in outline.split('+') if e.strip()]
    
    events_table = "| 序号 | 事件内容 | 涉及人物 | 预期目标 | 线索埋设 |\n"
    events_table += "|------|----------|----------|----------|----------|----------|\n"
    
    for i, event in enumerate(events, 1):
        events_table += f"| E{i} | {event} |\n"
    
    return events_table


def generate_character_analysis(context):
    """生成人物分析指导"""
    # 使用 tier1_db 中的角色数据
    db_context = context.get("tier1_db", {})
    characters = db_context.get("characters", [])
    
    # 使用 tier3_deepening 中的深度描写
    deepening = context.get("tier3_deepening", {})
    
    table = "| 姓名 | 当前处境 | 压力源 | 冲突对象 | 说话风格 | 行动倾向 | 对话立场 | 深化描写 |\n"
    
    for char in characters:
        name = char["name"]
        has_deepening = "✓" if name in deepening else "✗"
        table += f"| {name} | 哨站日常/拾荒中 | Ghost(创伤) | | 冷漠+少话 | 被动/犹豫 | 冷漠 | {has_deepening} |\n"
    
    return table


if __name__ == "__main__":
    main(sys.argv[1:])
