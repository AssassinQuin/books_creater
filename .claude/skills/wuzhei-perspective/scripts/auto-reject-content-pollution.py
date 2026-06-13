#!/usr/bin/env python3
"""V3 内容污染检测脚本

检测目标文件是否含黑名单关键词作为方法论输出（非 [案例] 标注）。
命中即 exit 1。

用法：python3 auto-reject-content-pollution.py <target_file>
"""
import sys

CONTENT_BLACKLIST = [
    '克苏鲁', '塔罗会', '塔罗牌', '蒸汽朋克', '非凡者序列', '22 途径', '22途径',
    '扮演法', '晋升仪式', '魔药消化',
    '克莱恩', '格尔曼·斯帕罗', '愚者', '阿蒙', '罗塞尔', '卢米安', '桑桑',
    '鲁恩王国', '贝克兰德', '值夜者', '灰雾之上',
    'Lovecraft',
]

CASE_MARKERS = ['[案例', '[禁止搬运]', '[案例参考']

EXEMPTION_CONTEXT_MARKERS = CASE_MARKERS + [
    '不输出', '不要输出', '不要照搬', '不要', '禁止', '不可', '不应',
    '反模式', '❌',
    '黑名单', '关键词',
    '替代输出', '抽象方法',
    '具体作品元素', '具体实现',
    '抽象为', '→ 抽象', '抽象到方法论',
    '世界观基调', '基调检测', '标记世界观', '基调',
    '默认豁免', '豁免',
    '题材',
    '素材', '连载', '我现在在做什么', '身份卡',
    '创作经验', '创作素材', '主角',
]

FILE_LEVEL_DECLARATION_MARKERS = [
    '本文件声明',
    'file-case-declaration',
    '调研笔记',
    '仅供背景理解',
    '仅供模型背景理解',
]


def has_file_level_declaration(text):
    """检查文件前 10 行是否含文件级案例声明（全文件豁免）"""
    head = '\n'.join(text.split('\n')[:10])
    return any(m in head for m in FILE_LEVEL_DECLARATION_MARKERS)


def find_violations(text):
    if has_file_level_declaration(text):
        return []
    violations = []
    lines = text.split('\n')
    for i, line in enumerate(lines, 1):
        for kw in CONTENT_BLACKLIST:
            if kw in line:
                has_case_marker = any(m in line for m in EXEMPTION_CONTEXT_MARKERS)
                if not has_case_marker:
                    violations.append({
                        'line': i,
                        'keyword': kw,
                        'content': line.strip()[:120],
                    })
    return violations


def main():
    if len(sys.argv) < 2:
        print("用法: python3 auto-reject-content-pollution.py <target_file>")
        sys.exit(2)

    target = sys.argv[1]
    try:
        with open(target, 'r', encoding='utf-8') as f:
            text = f.read()
    except Exception as e:
        print(f"ERROR: 无法读取 {target}: {e}")
        sys.exit(2)

    violations = find_violations(text)

    if not violations:
        if has_file_level_declaration(text):
            print(f"PASS: {target} - 文件级声明豁免（调研笔记，全文件案例引用）")
        else:
            print(f"PASS: {target} - 无内容污染（黑名单关键词未作为方法论输出）")
        sys.exit(0)

    print(f"FAIL: {target} - 检测到 {len(violations)} 处内容污染")
    print("(黑名单关键词作为方法论输出，未加 [案例] 标注)")
    for v in violations[:15]:
        print(f"  L{v['line']} [{v['keyword']}]: {v['content']}")
    if len(violations) > 15:
        print(f"  ... (剩余 {len(violations) - 15} 处)")
    sys.exit(1)


if __name__ == '__main__':
    main()
