#!/usr/bin/env python3
"""
DB → Lorebook 同步脚本
将 novel-db 中的世界观数据同步到 lorebook YAML 文件
"""

import json
import yaml
import os
from pathlib import Path
from datetime import datetime

# 项目路径
PROJECT_ROOT = Path("/Users/ganjie/code/personal/bywork/books_creater")
NOVEL_DIR = PROJECT_ROOT / "novels/这次不一样了"
LOREBOOK_DIR = NOVEL_DIR / "设定/lorebook/entries"
SYNC_STATUS_FILE = NOVEL_DIR / "设定/.sync_status.json"


def load_sync_status() -> dict:
    """加载同步状态"""
    if SYNC_STATUS_FILE.exists():
        return json.loads(SYNC_STATUS_FILE.read_text(encoding='utf-8'))
    return {"last_sync": "", "sources": {}}


def save_sync_status(status: dict):
    """保存同步状态"""
    SYNC_STATUS_FILE.write_text(json.dumps(status, indent=2, ensure_ascii=False), encoding='utf-8')


def sync_world_from_db():
    """
    从 novel-db 同步世界观数据到 lorebook YAML
    
    注意：此脚本需要 MCP novel-db 连接
    当前为框架实现，需要补充实际的 MCP 调用
    """
    print("=" * 60)
    print("DB → Lorebook 同步")
    print("=" * 60)
    
    # TODO: 实现实际的 MCP 调用
    # 示例：
    # from mcp import Client
    # client = Client()
    # world_data = client.call("mcp_novel-db_world_query", {"novel_id": 1})
    
    print("\n[提示] 此脚本需要连接到 novel-db MCP 服务器")
    print("[提示] 当前为框架实现，需要补充实际的 MCP 调用")
    print("\n同步逻辑：")
    print("1. 从 DB 查询所有世界观条目 (world_query)")
    print("2. 对比 lorebook YAML 文件的内容")
    print("3. 如果 DB 更新，更新对应的 YAML 文件")
    print("4. 记录同步时间和内容哈希")
    
    # 更新同步状态
    status = load_sync_status()
    status["last_sync"] = datetime.now().isoformat()
    status["sources"]["db_to_lorebook"] = {
        "last_run": datetime.now().isoformat(),
        "status": "framework_ready"
    }
    save_sync_status(status)
    
    print(f"\n同步状态已更新: {SYNC_STATUS_FILE}")


def main():
    sync_world_from_db()


if __name__ == "__main__":
    main()
