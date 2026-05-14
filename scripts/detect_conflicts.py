#!/usr/bin/env python3
"""
冲突检测脚本
检测 novel-db、lorebook YAML、角色深化.md 之间的冲突
"""

import json
import yaml
import hashlib
import os
from pathlib import Path
from typing import List, Dict, Any

# 项目路径
PROJECT_ROOT = Path("/Users/ganjie/code/personal/bywork/books_creater")
NOVEL_DIR = PROJECT_ROOT / "novels/这次不一样了"
LOREBOOK_DIR = NOVEL_DIR / "设定/lorebook/entries"
SYNC_STATUS_FILE = NOVEL_DIR / "设定/.sync_status.json"
REPORT_DIR = NOVEL_DIR / "审阅报告"


def get_file_hash(filepath: Path) -> str:
    """计算文件内容哈希"""
    if not filepath.exists():
        return ""
    content = filepath.read_text(encoding='utf-8')
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def load_sync_status() -> Dict:
    """加载同步状态"""
    if SYNC_STATUS_FILE.exists():
        return json.loads(SYNC_STATUS_FILE.read_text(encoding='utf-8'))
    return {
        "last_sync": "",
        "sources": {}
    }


def detect_lorebook_vs_locked_rules() -> List[Dict]:
    """检测 lorebook 条目是否违反锁定设定"""
    conflicts = []
    locked_file = NOVEL_DIR / "设定/锁定设定.md"
    
    if not locked_file.exists():
        return conflicts
    
    locked_content = locked_file.read_text(encoding='utf-8')
    
    # 遍历所有 lorebook 条目
    for category_dir in LOREBOOK_DIR.iterdir():
        if not category_dir.is_dir():
            continue
        for yml_file in category_dir.glob("*.yml"):
            try:
                entry = yaml.safe_load(yml_file.read_text(encoding='utf-8'))
                if not entry:
                    continue
                
                content = entry.get('content', '')
                entry_id = entry.get('id', yml_file.stem)
                
                # 检查是否违反货币系统锁定设定
                if '1金币' in content and '10银币' not in locked_content:
                    # 检查货币兑换比是否一致
                    if '1金币 = 10银币' not in locked_content and '1金币' in locked_content:
                        conflicts.append({
                            'type': '货币系统冲突',
                            'source': f'lorebook:{entry_id}',
                            'file': str(yml_file.relative_to(PROJECT_ROOT)),
                            'detail': f'条目中的货币兑换可能与锁定设定不一致',
                            'severity': 'high'
                        })
                
                # 检查是否违反能力体系锁定设定
                if '七阶' in content or '初觉' in content or '通感' in content:
                    if '七阶体系' not in locked_content and '能力体系' not in locked_content:
                        conflicts.append({
                            'type': '能力体系冲突',
                            'source': f'lorebook:{entry_id}',
                            'file': str(yml_file.relative_to(PROJECT_ROOT)),
                            'detail': '条目涉及能力体系，但未在锁定设定中找到对应规范',
                            'severity': 'medium'
                        })
                        
            except Exception as e:
                print(f"警告: 无法解析 {yml_file}: {e}")
    
    return conflicts


def detect_character_deepening_vs_lorebook() -> List[Dict]:
    """检测角色深化.md 与 lorebook 人物条目之间的冲突"""
    conflicts = []
    
    deepening_file = NOVEL_DIR / "设定/角色深化.md"
    if not deepening_file.exists():
        return conflicts
    
    deepening_content = deepening_file.read_text(encoding='utf-8')
    
    # 检查 lorebook 人物条目
    person_dir = LOREBOOK_DIR / "人物"
    if person_dir.exists():
        for yml_file in person_dir.glob("*.yml"):
            try:
                entry = yaml.safe_load(yml_file.read_text(encoding='utf-8'))
                if not entry:
                    continue
                
                entry_id = entry.get('id', '')
                entry_name = entry.get('name', '')
                content = entry.get('content', '')
                
                # 检查角色深化.md 中是否有该角色的描述
                if entry_name and entry_name in deepening_content:
                    # 检查关键属性是否一致
                    # 例如：检查能力等级
                    if '能力等级' in content:
                        # 提取能力等级描述
                        import re
                        ability_match = re.search(r'能力等级[：:]\s*(\S+)', content)
                        if ability_match:
                            lorebook_ability = ability_match.group(1)
                            # 在角色深化.md中查找对应描述
                            deepening_section = extract_section(deepening_content, entry_name)
                            if deepening_section and lorebook_ability not in deepening_section:
                                # 可能存在冲突，需要人工确认
                                conflicts.append({
                                    'type': '角色能力描述差异',
                                    'source1': f'lorebook:{entry_id}',
                                    'source2': f'角色深化.md:{entry_name}',
                                    'file': str(yml_file.relative_to(PROJECT_ROOT)),
                                    'detail': f'lorebook中能力等级为"{lorebook_ability}"，角色深化中描述可能不同',
                                    'severity': 'medium'
                                })
                                
            except Exception as e:
                print(f"警告: 无法解析 {yml_file}: {e}")
    
    return conflicts


def detect_worldview_vs_lorebook() -> List[Dict]:
    """检测世界观/*.md 与 lorebook 之间的过期信息"""
    conflicts = []
    
    worldview_dir = NOVEL_DIR / "设定/世界观"
    if not worldview_dir.exists():
        return conflicts
    
    # 读取所有世界观文件的最后修改时间
    worldview_mtimes = {}
    for md_file in worldview_dir.glob("*.md"):
        worldview_mtimes[md_file.stem] = md_file.stat().st_mtime
    
    # 检查 lorebook 条目是否比世界观文件旧
    for category_dir in LOREBOOK_DIR.iterdir():
        if not category_dir.is_dir():
            continue
        for yml_file in category_dir.glob("*.yml"):
            try:
                entry = yaml.safe_load(yml_file.read_text(encoding='utf-8'))
                if not entry:
                    continue
                
                entry_id = entry.get('id', '')
                entry_name = entry.get('name', '')
                tags = entry.get('tags', [])
                
                # 检查是否有对应的世界观文件更新
                for worldview_name, mtime in worldview_mtimes.items():
                    yml_mtime = yml_file.stat().st_mtime
                    if mtime > yml_mtime:
                        # 世界观文件比 lorebook 条目新，可能已过期
                        if any(tag in worldview_name for tag in tags):
                            conflicts.append({
                                'type': 'lorebook可能过期',
                                'source': f'lorebook:{entry_id}',
                                'file': str(yml_file.relative_to(PROJECT_ROOT)),
                                'detail': f'世界观文件"{worldview_name}.md"比lorebook条目新，可能需要同步',
                                'severity': 'low'
                            })
                            
            except Exception as e:
                print(f"警告: 无法解析 {yml_file}: {e}")
    
    return conflicts


def extract_section(content: str, section_name: str) -> str:
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
    
    return '\n'.join(section_lines)


def generate_report(conflicts: List[Dict]) -> str:
    """生成冲突检测报告"""
    report_lines = [
        "# 冲突检测报告",
        f"",
        f"检测时间: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"检测范围: novel-db / lorebook / 角色深化.md / 世界观/*.md / 锁定设定.md",
        f"",
        f"## 摘要",
        f"",
        f"- 发现冲突/差异: {len(conflicts)} 项",
        f"- 高风险: {len([c for c in conflicts if c.get('severity') == 'high'])} 项",
        f"- 中风险: {len([c for c in conflicts if c.get('severity') == 'medium'])} 项",
        f"- 低风险: {len([c for c in conflicts if c.get('severity') == 'low'])} 项",
        f"",
        f"## 详细列表",
        f"",
    ]
    
    if not conflicts:
        report_lines.append("✅ 未发现冲突。所有数据源一致。")
    else:
        for i, conflict in enumerate(conflicts, 1):
            severity_emoji = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}.get(conflict.get('severity', 'low'), '⚪')
            report_lines.extend([
                f"### {i}. {severity_emoji} {conflict['type']}",
                f"",
                f"- **来源**: {conflict.get('source', 'N/A')}",
            ])
            if 'source2' in conflict:
                report_lines.append(f"- **对比源**: {conflict['source2']}")
            report_lines.extend([
                f"- **文件**: `{conflict.get('file', 'N/A')}`",
                f"- **详情**: {conflict['detail']}",
                f"- **严重级别**: {conflict.get('severity', 'unknown')}",
                f"",
            ])
    
    report_lines.extend([
        f"## 修复建议",
        f"",
        f"1. **高风险冲突**: 必须立即修复，以锁定设定.md为准",
        f"2. **中风险冲突**: 建议在下一次写作前修复",
        f"3. **低风险冲突**: 可在定期维护时处理",
        f"",
        f"## 维护记录",
        f"",
        f"- 上次同步: {load_sync_status().get('last_sync', '从未同步')}",
        f"- 建议: 运行 `scripts/sync_db_to_lorebook.py` 和 `scripts/sync_lorebook_to_db.py` 进行同步",
    ])
    
    return '\n'.join(report_lines)


def main():
    """主函数"""
    print("=" * 60)
    print("开始冲突检测...")
    print("=" * 60)
    
    all_conflicts = []
    
    # 检测1: lorebook vs 锁定设定
    print("\n[1/3] 检测 lorebook 是否违反锁定设定...")
    conflicts = detect_lorebook_vs_locked_rules()
    all_conflicts.extend(conflicts)
    print(f"  发现 {len(conflicts)} 项冲突")
    
    # 检测2: 角色深化 vs lorebook
    print("\n[2/3] 检测角色深化.md 与 lorebook 之间的差异...")
    conflicts = detect_character_deepening_vs_lorebook()
    all_conflicts.extend(conflicts)
    print(f"  发现 {len(conflicts)} 项冲突")
    
    # 检测3: 世界观 vs lorebook（过期检测）
    print("\n[3/3] 检测 lorebook 是否过期...")
    conflicts = detect_worldview_vs_lorebook()
    all_conflicts.extend(conflicts)
    print(f"  发现 {len(conflicts)} 项冲突")
    
    # 生成报告
    report = generate_report(all_conflicts)
    
    # 保存报告
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_file = REPORT_DIR / f"冲突检测-{__import__('datetime').datetime.now().strftime('%Y%m%d-%H%M%S')}.md"
    report_file.write_text(report, encoding='utf-8')
    
    print(f"\n{'=' * 60}")
    print(f"检测完成！")
    print(f"总计发现: {len(all_conflicts)} 项冲突/差异")
    print(f"报告已保存: {report_file}")
    print(f"{'=' * 60}")
    
    # 打印摘要
    if all_conflicts:
        print("\n冲突摘要:")
        for conflict in all_conflicts:
            emoji = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}.get(conflict.get('severity', 'low'), '⚪')
            print(f"  {emoji} [{conflict['type']}] {conflict.get('source', 'N/A')}")
    else:
        print("\n✅ 未发现冲突。所有数据源一致。")


if __name__ == "__main__":
    main()
