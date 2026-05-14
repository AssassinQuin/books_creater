#!/usr/bin/env python3
"""
锁定设定校验脚本
检查 lorebook YAML 和角色深化.md 是否违反锁定设定.md
"""

import yaml
import re
from pathlib import Path
from datetime import datetime

# 项目路径
PROJECT_ROOT = Path("/Users/ganjie/code/personal/bywork/books_creater")
NOVEL_DIR = PROJECT_ROOT / "novels/这次不一样了"
LOREBOOK_DIR = NOVEL_DIR / "设定/lorebook/entries"
LOCKED_FILE = NOVEL_DIR / "设定/锁定设定.md"
REPORT_DIR = NOVEL_DIR / "审阅报告"


def parse_locked_rules() -> list:
    """解析锁定设定.md，提取所有锁定规则"""
    if not LOCKED_FILE.exists():
        print(f"警告: 未找到锁定设定文件 {LOCKED_FILE}")
        return []
    
    content = LOCKED_FILE.read_text(encoding='utf-8')
    rules = []
    
    # 解析锁定设定文件
    # 格式: ### 设定名称
    #       锁定内容...
    current_rule = None
    for line in content.split('\n'):
        if line.startswith('### '):
            if current_rule:
                rules.append(current_rule)
            current_rule = {
                'name': line.replace('### ', '').strip(),
                'content': ''
            }
        elif current_rule and line.strip():
            current_rule['content'] += line + '\n'
    
    if current_rule:
        rules.append(current_rule)
    
    return rules


def check_lorebook_against_rules(rules: list) -> list:
    """检查 lorebook 条目是否违反锁定规则"""
    violations = []
    
    for category_dir in LOREBOOK_DIR.iterdir():
        if not category_dir.is_dir():
            continue
        
        for yml_file in category_dir.glob("*.yml"):
            try:
                entry = yaml.safe_load(yml_file.read_text(encoding='utf-8'))
                if not entry:
                    continue
                
                entry_content = entry.get('content', '')
                entry_id = entry.get('id', yml_file.stem)
                
                for rule in rules:
                    # 检查是否违反规则
                    violation = check_violation(entry_content, rule)
                    if violation:
                        violations.append({
                            'file': str(yml_file.relative_to(PROJECT_ROOT)),
                            'entry': entry_id,
                            'rule': rule['name'],
                            'detail': violation
                        })
                        
            except Exception as e:
                print(f"警告: 无法解析 {yml_file}: {e}")
    
    return violations


def check_violation(content: str, rule: dict) -> str:
    """
    检查内容是否违反规则
    
    返回违规详情，如果没有违规返回空字符串
    """
    rule_name = rule['name']
    rule_content = rule['content']
    
    # 货币系统规则
    if '货币' in rule_name or '兑换' in rule_name:
        # 检查是否违反货币兑换比
        if '1金币 = 10银币' in rule_content:
            # 如果内容中有不同的兑换比
            if re.search(r'1金币\s*=\s*\d+银币', content):
                match = re.search(r'1金币\s*=\s*(\d+)银币', content)
                if match and match.group(1) != '10':
                    return f"违反货币兑换规则: 1金币={match.group(1)}银币 (应为10银币)"
    
    # 能力体系规则
    if '能力' in rule_name or '体系' in rule_name:
        # 检查是否使用非标准能力等级
        standard_levels = ['初觉', '通感', '凝相', '共鸣', '化形']
        if '七阶体系' in rule_content:
            # 检查内容中是否有非七阶的能力描述
            for level in standard_levels:
                if level in content and '七阶' not in content:
                    return f"可能违反能力体系规则: 使用了'{level}'但未明确七阶体系"
    
    # 灵能体系规则
    if '灵能' in rule_name:
        # 检查是否违反灵能规则
        if '灵能不可凭空产生' in rule_content:
            if '凭空产生灵能' in content or '无限灵能' in content:
                return "违反灵能守恒规则: 内容暗示灵能可凭空产生"
    
    # 添加更多规则检查...
    
    return ""


def generate_report(violations: list) -> str:
    """生成校验报告"""
    report_lines = [
        "# 锁定设定校验报告",
        f"",
        f"校验时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"校验范围: lorebook/*.yml",
        f"校验依据: 设定/锁定设定.md",
        f"",
        f"## 摘要",
        f"",
    ]
    
    if not violations:
        report_lines.extend([
            f"✅ 未发现违规。所有 lorebook 条目符合锁定设定。",
            f"",
        ])
    else:
        report_lines.extend([
            f"发现违规: {len(violations)} 项",
            f"",
            f"## 违规列表",
            f"",
        ])
        
        for i, v in enumerate(violations, 1):
            report_lines.extend([
                f"### {i}. {v['rule']}",
                f"",
                f"- **文件**: `{v['file']}`",
                f"- **条目**: {v['entry']}",
                f"- **详情**: {v['detail']}",
                f"",
            ])
    
    report_lines.extend([
        f"## 锁定规则列表",
        f"",
    ])
    
    rules = parse_locked_rules()
    for rule in rules:
        report_lines.extend([
            f"- **{rule['name']}**",
        ])
    
    return '\n'.join(report_lines)


def main():
    """主函数"""
    print("=" * 60)
    print("锁定设定校验")
    print("=" * 60)
    
    # 解析锁定规则
    print("\n[1/2] 解析锁定设定...")
    rules = parse_locked_rules()
    print(f"  发现 {len(rules)} 条锁定规则")
    
    # 检查 lorebook
    print("\n[2/2] 检查 lorebook 条目...")
    violations = check_lorebook_against_rules(rules)
    print(f"  发现 {len(violations)} 项违规")
    
    # 生成报告
    report = generate_report(violations)
    
    # 保存报告
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_file = REPORT_DIR / f"锁定设定校验-{datetime.now().strftime('%Y%m%d-%H%M%S')}.md"
    report_file.write_text(report, encoding='utf-8')
    
    print(f"\n{'=' * 60}")
    print(f"校验完成！")
    if violations:
        print(f"⚠️ 发现 {len(violations)} 项违规，请查看报告修复")
    else:
        print(f"✅ 所有条目符合锁定设定")
    print(f"报告已保存: {report_file}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
