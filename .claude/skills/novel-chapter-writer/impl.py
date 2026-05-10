#!/usr/bin/env python3
"""
novel-chapter-writer 实现代码
基于SKILL.md设计的逐章写作工作流
"""

import json
import sys
import os

# MCP客户端导入 - 连接到novel-db
from mcp import Client


def main(args):
    """主函数：处理skill调用参数"""

    # 解析参数
    if len(args) == 0:
        print("错误：缺少参数")
        print("用法：写第N章 / 继续写 / 写一章")
        print("示例：写第1章 / 继续写")
        return

    # 解析章节指令
    cmd = args[0]

    if cmd.startswith("写第"):
        # 提取章节号
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

        # 提取标题（如果存在）
        title = ""
        if "，标题是" in cmd:
            title = cmd.split("，标题是")[1]

        write_chapter(chapter_num, title)

    elif cmd == "继续写":
        # 继续上一章的写作
        continue_writing()

    elif cmd == "写一章":
        # 自动获取下一章号
        write_next_chapter()

    else:
        print(f"错误：未知命令 '{cmd}'")
        return


def write_chapter(chapter_num, title=""):
    """写单个章节的核心流程"""

    print(f"\n{'='*60}")
    print(f"开始第{chapter_num}章写作")
    print(f"标题：{title if title else '未命名'}")
    print(f"{'='*60}")

    # Step 1: 注入全量上下文
    print("\n[Step 1] 注入全量上下文...")

    # 调用MCP获取上下文
    # 注意：实际实现中需要连接到MCP服务器
    print("  → 调用 writing_start(novel_id=1, chapter_number=...) 获取上下文")
    print("  [提示] 此处需要MCP服务器连接和novel-db数据库")
    print("  [提示] 当前为设计实现阶段，需要配置MCP连接")

    # 模拟获取上下文（演示）
    context = simulate_get_context(chapter_num)

    # Step 2: 写正文
    print("\n[Step 2] 写正文...")

    # 读取写作执行规范
    specs = read_specs()

    # 根据大纲生成事件序列
    event_sequence = generate_event_sequence(chapter_num, context)
    print(f"\n事件序列：\n{event_sequence}")

    # 生成人物分析指导
    character_analysis = generate_character_analysis(context)
    print(f"\n人物分析：\n{character_analysis}")

    # 执行写作（这里需要完整实现）
    print("\n[写作] 开始生成章节内容...")
    print("  [提示] 完整写作流程需要进一步实现")
    print("  [提示] 当前可使用SKILL.md框架手动写作")


def continue_writing():
    """继续上一章的写作"""
    print("\n继续写作功能需要实现")


def write_next_chapter():
    """自动获取下一章号并写作"""
    print("\n写下一章功能需要实现")


def simulate_get_context(chapter_num):
    """模拟获取上下文（设计阶段）"""
    return {
        "chapter": {
            "id": chapter_num,
            "number": chapter_num,
            "title": "兽潮",
            "outline": "开场拾荒+灵站暗线+兽潮夜+妹妹发病+方岩给路+出发"
        },
        "active_characters": [
            {"id": 1, "name": "沈野", "role": "protagonist"},
            {"id": 4, "name": "沈念", "role": "ally"},
            {"id": 7, "name": "方岩", "role": "ally"}
        ],
        "unresolved_foreshadows": [
            {"id": 1, "description": "F1: 无法识别的残片"}
        ],
        "world_settings": {},
        "current_volume": {"id": 1, "title": "兽潮"}
    }


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

    # 解析大纲（用 + 分隔）
    events = [e.strip() for e in outline.split('+') if e.strip()]

    events_table = "| 序号 | 事件内容 | 涉及人物 | 预期目标 | 线索埋设 |\n"
    events_table += "|------|----------|----------|----------|----------|----------|\n"

    for i, event in enumerate(events, 1):
        events_table += f"| E{i} | {event} |\n"

    return events_table


def generate_character_analysis(context):
    """生成人物分析指导"""
    characters = context.get("active_characters", [])

    table = "| 姓名 | 当前处境 | 压力源 | 冲突对象 | 说话风格 | 行动倾向 | 对话立场 | 口头禅 |\n"

    for char in characters:
        name = char["name"]
        # 简化处理
        table += f"| {name} | 哨站日常/拾荒中 | Ghost(创伤) | | 冷漠+少话 | 被动/犹豫 | 冷漠 | |\n"

    return table


if __name__ == "__main__":
    main(sys.argv[1:])
