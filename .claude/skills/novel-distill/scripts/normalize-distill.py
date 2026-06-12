#!/usr/bin/env python3
"""蒸馏输出规范化脚本。在子agent写入后、validate-distill.py校验前运行。
自动修复子agent常见的schema偏差，避免主agent手动Python脚本修复。

用法: python3 normalize-distill.py <work_dir> [dim1,dim2,...]
"""
import json, sys, os, glob, re

# 子agent常见维度→适用品类映射
DEFAULT_GENRES = {
    "characters": ["玄幻", "奇幻", "冒险", "暗黑奇幻"],
    "narrative": ["东方玄幻", "暗黑奇幻", "长篇网文"],
    "rhythm": ["东方玄幻", "暗黑奇幻", "长篇网文"],
    "highlight": ["东方玄幻", "暗黑奇幻", "长篇网文"],
    "world": ["暗黑奇幻", "奇幻", "科幻"],
    "ability": ["玄幻", "奇幻", "升级流"],
}

def try_json_loads(text):
    """尝试多种方式解析可能含语法错误的JSON"""
    # 1. 直接解析
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 2. 修复常见问题：unquoted string values（如 metadata 中的裸字符串）
    # 匹配模式: "key": unquoted_value（非数字非布尔非null非数组非对象）
    fixed = text
    # 修复 value 位置上的裸字符串（含空格/括号/百分号等）
    fixed = re.sub(
        r':\s*([A-Za-z][A-Za-z0-9\s\(\)%\-\.\/,]+?)([,\n\r\}])',
        lambda m: ': "' + m.group(1).strip() + '"' + m.group(2) if not m.group(1).strip().startswith('"') else m.group(0),
        fixed
    )
    try:
        return json.loads(fixed)
    except json.JSONDecodeError:
        pass

    # 3. 移除尾部逗号
    fixed = re.sub(r',\s*([}\]])', r'\1', text)
    try:
        return json.loads(fixed)
    except json.JSONDecodeError:
        pass

    return None

def normalize_borrowable(b, dim, idx):
    """修复单条borrowable的常见字段问题"""
    fixes = []

    # name 长度截断（保留≤15字）
    name = b.get("name", f"{dim}-unnamed-{idx}")
    if len(name) > 15:
        b["name"] = name[:15]
        fixes.append(f"name截断: {name} → {b['name']}")

    # 缺失 description：从 technique/effect/innovation 提取
    if "description" not in b or not b["description"]:
        for src_field in ["technique", "effect", "innovation", "source_context"]:
            val = b.get(src_field, "")
            if val and isinstance(val, str) and len(val) > 10:
                b["description"] = val[:100]
                fixes.append(f"description ← {src_field}")
                break

    # 缺失 example：从 source_context 截取前200字
    if "example" not in b or not b["example"]:
        sc = b.get("source_context", "")
        if sc and isinstance(sc, str):
            b["example"] = sc[:200]
            fixes.append("example ← source_context[:200]")

    # 缺失 source_chapters
    if "source_chapters" not in b or not b["source_chapters"]:
        b["source_chapters"] = "Ch1-513"
        fixes.append("source_chapters ← default")

    # 缺失 applicability
    if "applicability" not in b or not b["applicability"]:
        b["applicability"] = "adapt"
        fixes.append("applicability ← adapt")

    # 缺失 applicable_genres
    if "applicable_genres" not in b or not b["applicable_genres"]:
        b["applicable_genres"] = DEFAULT_GENRES.get(dim, ["长篇网文"])
        fixes.append(f"applicable_genres ← default({dim})")

    # 缺失 project_relevance
    if "project_relevance" not in b or not b["project_relevance"]:
        b["project_relevance"] = {
            "这次不一样": {"score": 3, "reason": "跨品类蒸馏，需适配到西幻世界观"}
        }
        fixes.append("project_relevance ← default")

    # adaptation_map: dict → array 转换
    am = b.get("adaptation_map")
    if isinstance(am, dict):
        arr = []
        if "replacement_guide" in am:
            arr.append({
                "aspect": am.get("target_element", "核心适配"),
                "original": am.get("original", ""),
                "abstract_role": "目标项目适配指引",
                "replacement_guide": am["replacement_guide"]
            })
        else:
            for k, v in am.items():
                if isinstance(v, dict) and ("replacement_guide" in v or "original" in v):
                    arr.append({
                        "aspect": k,
                        "original": v.get("original", ""),
                        "abstract_role": v.get("abstract_role", ""),
                        "replacement_guide": v.get("replacement_guide", str(v)[:200])
                    })
                elif isinstance(v, str):
                    arr.append({
                        "aspect": k,
                        "original": "",
                        "abstract_role": k,
                        "replacement_guide": v
                    })
        if arr:
            b["adaptation_map"] = arr
            fixes.append("adaptation_map: dict→array")

    # trigger_signals: 缺失或格式错误 → 从 description 提取候选
    ts = b.get("trigger_signals")
    if not ts or not isinstance(ts, list) or len(ts) == 0:
        desc = b.get("description", "")
        name = b.get("name", "")
        candidates = []
        if desc:
            candidates.append(f"用户在寻找{desc[:30]}相关的处理方式时")
        if name:
            candidates.append(f"用户提到'{name}'或类似概念时")
        candidates.append(f"用户在写{dim}相关场景需要参考时")
        b["trigger_signals"] = candidates[:3]
        fixes.append("trigger_signals ← auto-extracted(需人工校核)")

    # quality (V1V2V3): 缺失 → 默认结构（标记 NEEDS_MANUAL_REVIEW）
    q = b.get("quality")
    if not q or not isinstance(q, dict):
        b["quality"] = {
            "v1_cross_domain": {"passed": None, "evidence": [], "_note": "NEEDS_MANUAL_REVIEW"},
            "v2_predictive_power": {"passed": None, "novel_question": "", "derived_answer": "", "_note": "NEEDS_MANUAL_REVIEW"},
            "v3_exclusivity": {"passed": None, "why_not_common": "", "_note": "NEEDS_MANUAL_REVIEW"}
        }
        fixes.append("quality ← default-pending-review")

    # related: 缺失 → 空数组
    if "related" not in b or not isinstance(b.get("related"), list):
        b["related"] = []
        fixes.append("related ← []")

    # elements: string → array 转换
    el = b.get("elements")
    if isinstance(el, str):
        items = [s.strip().strip("- ") for s in el.split("\n") if s.strip()]
        b["elements"] = [{"component": item} for item in items if item]
        fixes.append("elements: string→array")

    return fixes

def normalize_file(path):
    """规范化单个维度JSON文件"""
    fixes = []
    dim = os.path.basename(path).replace(".json", "")

    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()

    data = try_json_loads(raw)
    if data is None:
        return [f"JSON解析失败，无法自动修复"], []

    # 修复1: 裸数组 → 包裹结构
    if isinstance(data, list):
        borrowables = data
        data = {
            "dimension": dim,
            "data": {"summary": f"规范化导入，原为裸数组"},
            "borrowable": borrowables,
            "metadata": {"normalized": True}
        }
        fixes.append("裸数组 → 包裹结构")

    # 修复2: borrowables → borrowable 键名
    if "borrowables" in data and "borrowable" not in data:
        data["borrowable"] = data.pop("borrowables")
        fixes.append("borrowables → borrowable")

    borrowable = data.get("borrowable", [])
    if not borrowable:
        borrowable = data.get("borrowables", [])

    # 修复3: 逐条修复 borrowable 字段
    for i, b in enumerate(borrowable):
        if not isinstance(b, dict):
            continue
        item_fixes = normalize_borrowable(b, dim, i)
        fixes.extend([f"[{i}]{b.get('name','?')}: {f}" for f in item_fixes])

    data["borrowable"] = borrowable
    if "dimension" not in data:
        data["dimension"] = dim

    # 写回文件
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return fixes, []

def main():
    if len(sys.argv) < 2:
        print("用法: python3 normalize-distill.py <work_dir> [dim1,dim2,...]")
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
        print("无 JSON 文件可规范化")
        sys.exit(0)

    total_fixes = 0
    for f in sorted(files):
        fixes, _ = normalize_file(f)
        name = os.path.basename(f)
        if fixes:
            print(f"\n~ {name}: {len(fixes)} 处修复")
            for fix in fixes:
                print(f"  + {fix}")
            total_fixes += len(fixes)
        else:
            print(f"✓ {name}: 无需修复")

    print(f"\n总计: {len(files)} 文件, {total_fixes} 处修复")
    sys.exit(0)

if __name__ == "__main__":
    main()
