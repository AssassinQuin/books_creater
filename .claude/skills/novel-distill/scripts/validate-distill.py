#!/usr/bin/env python3
"""蒸馏输出校验脚本。用法: python3 validate-distill.py <work_dir> [dim1,dim2,...]"""
import json, sys, os, glob

REQUIRED_BORROWABLE_FIELDS = [
    "name", "description", "example", "source_chapters",
    "applicability", "applicable_genres", "source_context",
    "elements", "adaptation_map", "project_relevance",
    "trigger_signals", "quality"
]

# 原作术语黑名单（中性化审计）
TERM_BLACKLIST = {
    "玄幻": ["灵气", "修仙", "渡劫", "飞升", "金丹", "元婴", "宗门", "道法"],
    "诡秘": ["非凡特性", "序列", "扮演法", "亵渎石板", "塔罗牌"],
    "将夜": ["昊天", "书院", "夫子", "神符", "知命", "洞玄", "不惑"],
}

# V3 独特性黑名单：常识型 borrowable 检测（组合关键词）
# 命中即标 V3 不通过 → 应移入 rejected/
COMMON_SENSE_KEYWORDS = {
    "主角动机类": ["动机", "目标", "愿望"],          # 需配合指令性词
    "冲突驱动类": ["冲突", "矛盾", "对抗"],
    "成长弧线类": ["成长", "变化", "转变"],
    "节奏通用类": ["起伏", "张弛", "节奏感"],
    "情感通用类": ["共鸣", "代入感"],
}
INSTRUCTIVE_WORDS = ["需要", "应该", "要有", "必须", "清晰", "强烈", "真实"]

# V1 跨域：source_chapters 中独立场景的最小数量
MIN_CROSS_DOMAIN_CHAPTERS = 2

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

        # trigger_signals 校验（3-5 条，强制非空）
        ts = b.get("trigger_signals", [])
        if not isinstance(ts, list):
            errors.append(f"[{dim}][{i}] {name}: trigger_signals 必须是数组")
        else:
            if len(ts) == 0:
                errors.append(f"[{dim}][{i}] {name}: trigger_signals 为空（需3-5条）")
            elif len(ts) < 3:
                warnings.append(f"[{dim}][{i}] {name}: trigger_signals 仅{len(ts)}条（建议3-5）")
            elif len(ts) > 7:
                warnings.append(f"[{dim}][{i}] {name}: trigger_signals {len(ts)}条过多（建议≤5）")
            abstract_signals = [s for s in ts if isinstance(s, str) and ("用户需要" in s or "当用户" in s) and "说" not in s and "问" not in s]
            if abstract_signals:
                warnings.append(f"[{dim}][{i}] {name}: trigger_signals 含抽象描述（应写实际语言信号）: {abstract_signals[:1]}")

        # V1V2V3 quality 校验
        q = b.get("quality", {})
        if not isinstance(q, dict):
            errors.append(f"[{dim}][{i}] {name}: quality 必须是对象")
        else:
            # V1 跨域
            v1 = q.get("v1_cross_domain", {})
            v1_passed = v1.get("passed")
            v1_ev = v1.get("evidence", [])
            if v1_passed is None:
                warnings.append(f"[{dim}][{i}] {name}: quality.v1_cross_domain.passed=None（NEEDS_MANUAL_REVIEW）")
            elif v1_passed and len(v1_ev) < MIN_CROSS_DOMAIN_CHAPTERS:
                warnings.append(f"[{dim}][{i}] {name}: V1 通过但 evidence 仅{len(v1_ev)}条（需≥{MIN_CROSS_DOMAIN_CHAPTERS}）")
            elif v1_passed is False:
                errors.append(f"[{dim}][{i}] {name}: V1 不通过 → 应移入 rejected/，不应留在 borrowable")

            # V2 预测力
            v2 = q.get("v2_predictive_power", {})
            v2_passed = v2.get("passed")
            if v2_passed is None:
                warnings.append(f"[{dim}][{i}] {name}: quality.v2_predictive_power.passed=None（NEEDS_MANUAL_REVIEW）")
            elif v2_passed and not v2.get("novel_question"):
                warnings.append(f"[{dim}][{i}] {name}: V2 通过但缺 novel_question")
            elif v2_passed is False:
                errors.append(f"[{dim}][{i}] {name}: V2 不通过 → 应移入 rejected/")

            # V3 独特性
            v3 = q.get("v3_exclusivity", {})
            v3_passed = v3.get("passed")
            why = v3.get("why_not_common", "")
            if v3_passed is None:
                warnings.append(f"[{dim}][{i}] {name}: quality.v3_exclusivity.passed=None（NEEDS_MANUAL_REVIEW）")
            elif v3_passed and not why:
                warnings.append(f"[{dim}][{i}] {name}: V3 通过但缺 why_not_common")
            elif v3_passed is False:
                errors.append(f"[{dim}][{i}] {name}: V3 不通过 → 应移入 rejected/")
            # V3 自动检测：常识型 borrowable（关键词组合 + 指令性词）
            desc_full = (b.get("description", "") + b.get("name", ""))
            for category, kws in COMMON_SENSE_KEYWORDS.items():
                has_kw = any(k in desc_full for k in kws)
                has_instructive = any(w in desc_full for w in INSTRUCTIVE_WORDS)
                if has_kw and has_instructive:
                    errors.append(f"[{dim}][{i}] {name}: V3 自动检测命中常识模式 [{category}]（关键词+指令性词同时出现）→ 应移入 rejected/")
                    break

        # related 校验（可选字段，但有则结构必须正确）
        rel = b.get("related", [])
        if rel and isinstance(rel, list):
            valid_relations = {"composes-with", "contrasts-with", "depends-on"}
            for j, r in enumerate(rel):
                if not isinstance(r, dict):
                    warnings.append(f"[{dim}][{i}] {name}: related[{j}] 必须是对象")
                    continue
                if not r.get("slug"):
                    warnings.append(f"[{dim}][{i}] {name}: related[{j}] 缺 slug")
                if r.get("relation") not in valid_relations:
                    warnings.append(f"[{dim}][{i}] {name}: related[{j}].relation='{r.get('relation')}' 不在 {valid_relations}")

    return errors, warnings

def auto_reject_failed(work_dir, dims=None):
    """--auto-reject 模式：将 V1V2V3 失败项自动移入 rejected/{dim}.json。
    解决 audit 发现的 MEDIUM 风险：rejected 路由无脚本强制。"""
    rejected_dir = os.path.join(work_dir, "rejected")
    os.makedirs(rejected_dir, exist_ok=True)

    files = glob.glob(os.path.join(work_dir, "*.json"))
    if dims:
        files = [f for f in files if any(d in os.path.basename(f) for d in dims)]

    moved_count = 0
    for f in sorted(files):
        if "rejected" in f:
            continue
        try:
            with open(f) as fp:
                data = json.load(fp)
        except (json.JSONDecodeError, IOError):
            continue

        dim = data.get("dimension", os.path.basename(f).replace(".json", ""))
        borrowables = data.get("borrowable", [])
        kept = []
        rejected = []

        for b in borrowables:
            if not isinstance(b, dict):
                kept.append(b)
                continue
            q = b.get("quality", {})
            failed_at = []
            for vk in ["v1_cross_domain", "v2_predictive_power", "v3_exclusivity"]:
                v = q.get(vk, {})
                if v.get("passed") is False:
                    failed_at.append(vk.split("_")[0].upper())
            if failed_at:
                rejected.append({
                    "name": b.get("name", "?"),
                    "description": b.get("description", ""),
                    "failed_at": "/".join(failed_at),
                    "reason": "V1V2V3 自动检测不通过",
                    "source_chapters": b.get("source_chapters", ""),
                    "salvage_hint": f"补充 {failed_at} 的 evidence/novel_question/why_not_common 后可重新评估"
                })
            else:
                kept.append(b)

        if rejected:
            data["borrowable"] = kept
            with open(f, "w", encoding="utf-8") as fp:
                json.dump(data, fp, ensure_ascii=False, indent=2)
            rej_path = os.path.join(rejected_dir, f"{dim}.json")
            existing = []
            if os.path.exists(rej_path):
                try:
                    with open(rej_path) as rfp:
                        existing = json.load(rfp).get("rejected", [])
                except (json.JSONDecodeError, IOError):
                    pass
            existing.extend(rejected)
            with open(rej_path, "w", encoding="utf-8") as rfp:
                json.dump({"dimension": dim, "rejected": existing}, rfp, ensure_ascii=False, indent=2)
            print(f"  → {dim}: 移除 {len(rejected)} 条到 rejected/{dim}.json")
            moved_count += len(rejected)

    return moved_count

def main():
    if len(sys.argv) < 2:
        print("用法: python3 validate-distill.py <work_dir> [dim1,dim2,...] [--auto-reject]")
        print("  --auto-reject: V1V2V3 失败项自动移入 rejected/{dim}.json（强制执行 Phase 2b.6）")
        sys.exit(1)

    args = sys.argv[1:]
    auto_reject = "--auto-reject" in args
    if auto_reject:
        args = [a for a in args if a != "--auto-reject"]

    work_dir = args[0]
    dims = args[1].split(",") if len(args) > 1 else None

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

    if auto_reject:
        print("\n--- auto-reject 模式: 处理 V1V2V3 失败项 ---")
        moved = auto_reject_failed(work_dir, dims)
        print(f"总计移入 rejected/: {moved} 条")

    sys.exit(1 if total_errors > 0 else 0)

if __name__ == "__main__":
    main()
