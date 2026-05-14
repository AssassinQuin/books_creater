#!/usr/bin/env python3
"""
Lorebook → DB 同步脚本
将 lorebook YAML 文件同步到 novel-db
"""

import json
import yaml
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


def sync_lorebook_to_db():
    """
    将 lorebook YAML 同步到 novel-db
    
    注意：此脚本需要 MCP novel-db 连接
    当前为框架实现，需要补充实际的 MCP 调用
    """
    print("=" * 60)
    print("Lorebook → DB 同步")
    print("=" * 60)
    
    # 统计 lorebook 条目
    entry_count = 0
    for category_dir in LOREBOOK_DIR.iterdir():
        if category_dir.is_dir():
            entry_count += len(list(category_dir.glob("*.yml")))
    
    print(f"\n发现 {entry_count} 个 lorebook 条目")
    print("\n[提示] 此脚本需要连接到 novel-db MCP 服务器")
    print("[提示] 当前为框架实现，需要补充实际的 MCP 调用")
    print("\n同步逻辑：")
    print("1. 遍历所有 lorebook YAML 文件")
    print("2. 解析条目内容")
    print("3. 调用 world_upsert 同步到 DB")
    print("4. 记录同步时间和内容哈希")
    
    # 更新同步状态
    status = load_sync_status()
    status["last_sync"] = datetime.now().isoformat()
    status["sources"]["lorebook_to_db"] = {
        "last_run": datetime.now().isoformat(),
        "status": "framework_ready",
        "entry_count": entry_count
    }
    save_sync_status(status)
    
    print(f"\n同步状态已更新: {SYNC_STATUS_FILE}")


def main():
    sync_lorebook_to_db()


if __name__ == "__main__":
    main()
