#!/usr/bin/env python3
"""蒸馏输出校验脚本。用法: python3 validate-distill.py <work_dir> [dim1,dim2,...]"""
import json, sys, os, glob

REQUIRED_BORROWABLE_FIELDS = [
    "name", "description", "example", "source_chapters",
    "applicability", "applicable_genres", "source_context",
    "elements", "adaptation_map", "project_relevance"
]

# 原作术语黑名单（中性化审计）
TERM_BLACKLIST = {
    "玄幻": ["灵气", "修仙", "渡劫", "飞升", "金丹", "元婴", "宗门", "道法"],
    "诡秘": ["非凡特性", "序列", "扮演法", "亵渎石板", "塔罗牌"],
    "将夜": ["昊天", "书院", "夫子", "神符", "知命", "洞玄", "不惑"],
}

def validate_file(path):
    errors, warnings = [], []
    try:
        with open(path) as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return [f"JSON 解析失败: {e}"], []

    dim = data.get("dimension", "unknown")
    borrowables = data.get("borrowable", [])

    if not borrowables:
        errors.append(f"[{dim}] 无 borrowable")

    for i, b in enumerate(borrowables):
        # 字段完整性
        missing = [f for f in REQUIRED_BORROWABLE_FIELDS if f not in b]
        if missing:
            errors.append(f"[{dim}][{i}] {b.get('name','?')}: 缺字段 {missing}")

        # source_context 长度
        sc = b.get("source_context", "")
        if len(sc) < 20:
            warnings.append(f"[{dim}][{i}] {b.get('name','?')}: source_context 仅{len(sc)}字（需≥20）")

        # name 长度
        name = b.get("name", "")
        if len(name) > 15:
            warnings.append(f"[{dim}][{i}] name 过长: '{name}' ({len(name)}字，建议≤10)")

        # example 长度
        ex = b.get("example", "")
        if len(ex) > 250:
            warnings.append(f"[{dim}][{i}] {name}: example {len(ex)}字（限200）")

        # 中性化审计：source_context 不应含原作术语
        for _, terms in TERM_BLACKLIST.items():
            for term in terms:
                if term in sc:
                    errors.append(f"[{dim}][{i}] {name}: source_context 含原作术语 '{term}'")
                    break

        # project_relevance 结构
        pr = b.get("project_relevance", {})
        for proj, info in pr.items():
            if "score" not in info:
                warnings.append(f"[{dim}][{i}] {name}: project_relevance.{proj} 缺 score")
            score = info.get("score", 0)
            if not (1 <= score <= 5):
                errors.append(f"[{dim}][{i}] {name}: score={score} 超范围[1-5]")
            if not info.get("reason"):
                warnings.append(f"[{dim}][{i}] {name}: project_relevance.{proj} 缺 reason")

    return errors, warnings

def main():
    if len(sys.argv) < 2:
        print("用法: python3 validate-distill.py <work_dir> [dim1,dim2,...]")
        sys.exit(1)

    work_dir = sys.argv[1]
    dims = sys.argv[2].split(",") if len(sys.argv) > 2 else None

    if not os.path.isdir(work_dir):
        print(f"目录不存在: {work_dir}")
        sys.exit(1)

    files = glob.glob(os.path.join(work_dir, "*.json"))
    if dims:
        files = [f for f in files if any(d in os.path.basename(f) for d in dims)]

    if not files:
        print("无 JSON 文件可校验")
        sys.exit(0)

    total_errors, total_warnings = 0, 0
    for f in sorted(files):
        errors, warnings = validate_file(f)
        name = os.path.basename(f)
        if errors:
            print(f"\n✗ {name}: {len(errors)} 错误")
            for e in errors:
                print(f"  ✗ {e}")
            total_errors += len(errors)
        if warnings:
            print(f"\n⚠ {name}: {len(warnings)} 警告")
            for w in warnings:
                print(f"  ⚠ {w}")
            total_warnings += len(warnings)
        if not errors and not warnings:
            print(f"✓ {name}")

    print(f"\n总计: {len(files)} 文件, {total_errors} 错误, {total_warnings} 警告")
    sys.exit(1 if total_errors > 0 else 0)

if __name__ == "__main__":
    main()
