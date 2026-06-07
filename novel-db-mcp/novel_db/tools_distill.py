import json
import logging

from .db import mcp, query, transaction
from .resolvers import _resolve_novel_id
from .errors import mcp_tool
from .sql_utils import build_update_sql
from .sync import _record_db_hash
from .param_utils import coerce_list, coerce_dict

logger = logging.getLogger(__name__)

# ── Shared helpers ──────────────────────────────────────────


def _validate_borrowable(b: dict) -> tuple:
    """Validate single borrowable's 3 required fields.
    Returns (quality_flag, missing_fields).
    """
    missing = []
    sc = b.get("source_context", "")
    if not sc or len(sc) < 20:
        missing.append("source_context")
    els = b.get("elements")
    if not isinstance(els, list) or len(els) < 1:
        missing.append("elements")
    am = b.get("adaptation_map")
    if not isinstance(am, list) or len(am) < 1:
        missing.append("adaptation_map")
    quality = "complete" if not missing else "partial_quality"
    return quality, missing


def _fill_missing(b: dict, missing: list):
    """Fill placeholder values for missing fields."""
    if "source_context" in missing:
        b["source_context"] = "（未提取，需手动补充）"
    if "elements" in missing:
        b["elements"] = [{"note": "（数据缺失：子agent未返回元素分解，需手动分析）"}]
    if "adaptation_map" in missing:
        b["adaptation_map"] = [{"note": "（数据缺失：未包含适配映射，需手动判断）"}]


def _write_borrowable(novel_id: int, work_name: str, dim: str,
                      b: dict, quality: str, missing: list):
    """Write single borrowable to world_settings (INSERT/UPDATE)."""
    pattern_name = b.get("name", "unnamed")
    db_name = f"{work_name}-{dim}-{pattern_name}"

    data = {
        "source_work": work_name,
        "source_dimension": dim,
        "pattern_name": pattern_name,
        "pattern_detail": b.get("description", ""),
        "source_context": b.get("source_context", ""),
        "elements": b.get("elements", []),
        "adaptation_map": b.get("adaptation_map", []),
        "applicability": b.get("applicability", "adapt"),
        "applicable_genres": b.get("applicable_genres", []),
        "example": b.get("example", ""),
        "source_chapters": b.get("source_chapters", ""),
        "quality": quality,
        "missing_fields": missing,
    }
    data_json = json.dumps(data, ensure_ascii=False)
    tags = json.dumps(
        [work_name, "borrowable", dim, b.get("applicability", "adapt"), quality],
        ensure_ascii=False
    )

    existing = query(
        "SELECT id FROM world_settings WHERE novel_id = ? AND category = ? AND name = ?",
        (novel_id, "ref_borrowable", db_name), fetch="one"
    )

    if existing:
        ws_id = existing["id"]
        sql, params = build_update_sql(
            "world_settings",
            {"data": data_json, "tags": json.loads(tags)},
            "novel_id = ? AND category = ? AND name = ?",
            [novel_id, "ref_borrowable", db_name]
        )
        query(sql, params, fetch="none")
    else:
        ws_id = query(
            "INSERT INTO world_settings (novel_id, category, name, data, tags, priority) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (novel_id, "ref_borrowable", db_name, data_json, tags, 30),
            fetch="insert"
        )["id"]

    _record_db_hash(novel_id, "world", f"ref_borrowable:{db_name}", data_json)

    try:
        from .embedding import mark_dirty
        mark_dirty(novel_id, "world_setting", ws_id)
    except Exception:
        pass

    return db_name


# ── MCP Tools ───────────────────────────────────────────────


def _distill_batch_write(work_name: str, borrowables_json: str) -> str:
    novel_id = _resolve_novel_id("_参考库")
    items = json.loads(borrowables_json)

    if not isinstance(items, list):
        return json.dumps({"error": "borrowables_json 必须是 JSON 数组"}, ensure_ascii=False)

    total = 0
    complete = 0
    partial = 0
    details = []

    with transaction():
        for item in items:
            dim = item.get("dimension", "unknown")
            b = item.get("borrowable", item)

            quality, missing = _validate_borrowable(b)
            _fill_missing(b, missing)

            db_name = _write_borrowable(novel_id, work_name, dim, b, quality, missing)

            if quality == "complete":
                complete += 1
            else:
                partial += 1
            total += 1
            details.append({
                "name": db_name,
                "dimension": dim,
                "quality": quality,
                "missing_fields": missing
            })

    return json.dumps({
        "ok": True,
        "total": total,
        "complete": complete,
        "partial": partial,
        "details": details
    }, ensure_ascii=False)


def _distill_validate_json(json_content: str) -> str:
    try:
        data = json.loads(json_content)
    except json.JSONDecodeError as e:
        return json.dumps({"valid": False, "error": f"JSON解析失败: {e}"}, ensure_ascii=False)

    required_top = ["dimension", "data", "borrowable"]
    missing_top = [f for f in required_top if f not in data]
    if missing_top:
        return json.dumps({
            "valid": False,
            "error": f"缺失顶层字段: {missing_top}"
        }, ensure_ascii=False)

    if not isinstance(data["borrowable"], list) or len(data["borrowable"]) == 0:
        return json.dumps({
            "valid": False,
            "error": "borrowable 为空或不是数组"
        }, ensure_ascii=False)

    warnings = []
    complete_count = 0
    partial_count = 0

    for b in data["borrowable"]:
        quality, missing = _validate_borrowable(b)
        _fill_missing(b, missing)

        if quality == "complete":
            complete_count += 1
        else:
            partial_count += 1
            name = b.get("name", "unnamed")
            warnings.append(f"{name}: 缺失 {missing}")

    return json.dumps({
        "valid": True,
        "dimension": data["dimension"],
        "total": len(data["borrowable"]),
        "complete": complete_count,
        "partial": partial_count,
        "warnings": warnings,
        "validated_json": data
    }, ensure_ascii=False)


def _distill_assess_quality(work_name: str,
                            deepen_threshold: int = 5,
                            partial_ratio_threshold: float = 0.5) -> str:
    novel_id = _resolve_novel_id("_参考库")

    rows = query(
        "SELECT name, tags, data FROM world_settings "
        "WHERE novel_id = ? AND category = 'ref_borrowable' AND name LIKE ?",
        (novel_id, f"{work_name}-%"),
        fetch="all"
    )

    if not rows:
        return json.dumps({
            "ok": True, "work_name": work_name, "total": 0,
            "dimensions": {}, "weak_dimensions": [],
            "assessment": f"未找到 {work_name} 的蒸馏数据"
        }, ensure_ascii=False)

    dims = {}
    for row in rows:
        tags = row.get("tags", "[]")
        if isinstance(tags, str):
            tags = json.loads(tags)

        dim = "unknown"
        for t in tags:
            if t in ("borrowable", work_name):
                continue
            if t in ("direct", "adapt", "inspire", "complete", "partial_quality"):
                continue
            dim = t
            break

        data = row.get("data", {})
        if isinstance(data, str):
            data = json.loads(data)
        quality = data.get("quality", "unknown")

        if dim not in dims:
            dims[dim] = {"count": 0, "complete": 0, "partial": 0, "patterns": []}
        dims[dim]["count"] += 1
        dims[dim]["patterns"].append(row["name"])
        if quality == "complete":
            dims[dim]["complete"] += 1
        else:
            dims[dim]["partial"] += 1

    for dim in dims:
        c = dims[dim]
        c["partial_ratio"] = round(c["partial"] / c["count"], 2) if c["count"] > 0 else 0

    weak = []
    for dim, stats in dims.items():
        if stats["count"] < deepen_threshold or stats["partial_ratio"] > partial_ratio_threshold:
            weak.append(dim)

    total = sum(d["count"] for d in dims.values())
    assessment = ""
    if weak:
        reasons = []
        for dim in weak:
            s = dims[dim]
            if s["count"] < deepen_threshold:
                reasons.append(f"{dim} 数量不足({s['count']}/{deepen_threshold})")
            if s["partial_ratio"] > partial_ratio_threshold:
                reasons.append(f"{dim} partial占比过高({int(s['partial_ratio']*100)}%)")
        assessment = f"薄弱维度: {', '.join(reasons)}。建议深化。"
    else:
        assessment = "所有维度质量达标。"

    return json.dumps({
        "ok": True,
        "work_name": work_name,
        "dimensions": dims,
        "total": total,
        "weak_dimensions": weak,
        "assessment": assessment
    }, ensure_ascii=False)


def _distill_generate_report(work_name: str) -> str:
    novel_id = _resolve_novel_id("_参考库")

    # 查询 meta
    meta_row = query(
        "SELECT data FROM world_settings WHERE novel_id = ? AND category = 'ref_meta' AND name = ?",
        (novel_id, work_name), fetch="one"
    )
    meta = {}
    if meta_row:
        meta = meta_row["data"] if isinstance(meta_row["data"], dict) else json.loads(meta_row["data"])

    # 查询所有 borrowable
    borrowables = query(
        "SELECT name, tags, data FROM world_settings "
        "WHERE novel_id = ? AND category = 'ref_borrowable' AND name LIKE ?",
        (novel_id, f"{work_name}-%"),
        fetch="all"
    )

    # 按维度分组
    dim_groups = {}
    for row in borrowables:
        tags = row.get("tags", "[]")
        if isinstance(tags, str):
            tags = json.loads(tags)
        dim = "unknown"
        for t in tags:
            if t in ("borrowable", work_name, "direct", "adapt", "inspire", "complete", "partial_quality"):
                continue
            dim = t
            break

        data = row["data"] if isinstance(row["data"], dict) else json.loads(row["data"])
        if dim not in dim_groups:
            dim_groups[dim] = []
        dim_groups[dim].append(data)

    total_b = len(borrowables)
    complete_b = sum(1 for rows in dim_groups.values() for b in rows if b.get("quality") == "complete")
    partial_b = total_b - complete_b

    genre = meta.get("genre", meta.get("work_profile", {}).get("type_signature", "未知"))
    volumes = meta.get("volumes", [])
    if not isinstance(volumes, list):
        volumes = []

    # ── 生成报告 Markdown ──
    lines = [f"# {work_name} 蒸馏报告\n"]
    lines.append("## 基础信息")
    lines.append(f"- 类型：{genre}")
    lines.append(f"- 卷数：{len(volumes)}")
    lines.append(f"- borrowable 总计：{total_b} 条（complete: {complete_b} / partial: {partial_b}）\n")

    lines.append("## 已蒸馏维度")
    dim_names = {"world": "世界观", "ability": "能力体系", "characters": "人物",
                 "narrative": "叙事手法", "rhythm": "节奏结构", "highlight": "核心亮点"}
    for dim, patterns in dim_groups.items():
        cn = dim_names.get(dim, dim)
        c = sum(1 for p in patterns if p.get("quality") == "complete")
        p = len(patterns) - c
        lines.append(f"- [x] {cn}：{len(patterns)} 条模式（complete {c} / partial {p}）")

    lines.append("\n## 可借鉴模式")
    lines.append("| # | 模式 | 来源维度 | 适用性 | 质量 |")
    lines.append("|---|------|---------|--------|------|")
    idx = 1
    for dim, patterns in dim_groups.items():
        cn = dim_names.get(dim, dim)
        for p in patterns:
            name = p.get("pattern_name", "unnamed")
            app = p.get("applicability", "?")
            q = p.get("quality", "?")
            lines.append(f"| {idx} | {name} | {cn} | {app} | {q} |")
            idx += 1

    lines.append(f"\n## 检索验证")
    lines.append(f"- vector_search(\"{work_name}\") → 命中 {total_b} 条")
    lines.append(f"- ctx_search(source=\"ref-patterns-{work_name}\") → 已索引")

    report_md = "\n".join(lines)

    # ── 生成 patterns_table ──
    pt_lines = [f"# {work_name} 可借鉴模式清单\n"]
    for dim, patterns in dim_groups.items():
        cn = dim_names.get(dim, dim)
        pt_lines.append(f"\n## {cn}（{len(patterns)} 条）")
        pt_lines.append("| # | 模式名 | 适用性 | source_context | quality |")
        pt_lines.append("|---|--------|--------|----------------|---------|")
        for i, p in enumerate(patterns, 1):
            sc = p.get("source_context", "")[:50]
            pt_lines.append(f"| {i} | {p.get('pattern_name', '?')} | {p.get('applicability', '?')} | {sc} | {p.get('quality', '?')} |")
    patterns_table = "\n".join(pt_lines)

    # ── 生成 adaptation_summary ──
    sa_lines = [f"# {work_name} 适配速查\n"]
    sa_lines.append("\n## 快速适配")
    sa_lines.append("| 模式 | 核心 elements（1项） | 关键 replacement_guide |")
    sa_lines.append("|------|---------------------|----------------------|")

    all_patterns = []
    for dim, patterns in dim_groups.items():
        for p in patterns:
            all_patterns.append((dim, p))

    # TOP 5 by quality=complete first
    all_patterns.sort(key=lambda x: (0 if x[1].get("quality") == "complete" else 1, x[0]))
    for dim, p in all_patterns[:5]:
        els = p.get("elements", [])
        el_summary = els[0].get("component", els[0].get("technique", els[0].get("archetype", "?"))) if els else "?"
        am = p.get("adaptation_map", [])
        rg = am[0].get("replacement_guide", "?")[:60] if am else "?"
        sa_lines.append(f"| {p.get('pattern_name', '?')} | {el_summary} | {rg} |")

    sa_lines.append(f"\n## 检索入口")
    sa_lines.append(f"- db_search('_参考库', keyword='{work_name}', category='ref_borrowable', top_k=5)")
    sa_lines.append(f"- vector_search('_参考库', query_text='{{需求描述}}')")
    sa_lines.append(f"- 文件：novels/_参考库/{work_name}/borrowable-{{维度}}.md")
    adaptation_summary = "\n".join(sa_lines)

    return json.dumps({
        "ok": True,
        "work_name": work_name,
        "stats": {"dimensions": len(dim_groups), "borrowables": total_b,
                  "complete": complete_b, "partial": partial_b},
        "report_markdown": report_md,
        "ctx_files": {
            f"ref-distill-{work_name}": report_md,
            f"ref-patterns-{work_name}": patterns_table,
            f"ref-summary-{work_name}": adaptation_summary,
        }
    }, ensure_ascii=False)


def _distill_import_file(work_name: str, file_path: str) -> str:
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            raw = f.read()
    except Exception as e:
        return json.dumps({"ok": False, "error": f"文件读取失败: {e}"}, ensure_ascii=False)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        return json.dumps({"ok": False, "error": f"JSON解析失败: {e}"}, ensure_ascii=False)

    required_top = ["dimension", "data", "borrowable"]
    missing_top = [f for f in required_top if f not in data]
    if missing_top:
        return json.dumps({
            "ok": False, "error": f"缺失顶层字段: {missing_top}"
        }, ensure_ascii=False)

    if not isinstance(data["borrowable"], list) or len(data["borrowable"]) == 0:
        return json.dumps({"ok": False, "error": "borrowable 为空"}, ensure_ascii=False)

    novel_id = _resolve_novel_id("_参考库")
    dim = data["dimension"]

    total = 0
    complete = 0
    partial = 0
    details = []

    with transaction():
        for b in data["borrowable"]:
            quality, missing = _validate_borrowable(b)
            _fill_missing(b, missing)

            db_name = _write_borrowable(novel_id, work_name, dim, b, quality, missing)

            if quality == "complete":
                complete += 1
            else:
                partial += 1
            total += 1
            details.append({
                "name": db_name,
                "quality": quality,
                "missing_fields": missing
            })

    return json.dumps({
        "ok": True,
        "imported": True,
        "file": file_path,
        "dimension": dim,
        "total": total,
        "complete": complete,
        "partial": partial,
        "details": details
    }, ensure_ascii=False)


@mcp.tool
@mcp_tool
def distill(action: str, work_name: str = "", borrowables_json: str = "",
            json_content: str = "", deepen_threshold: int = 5,
            partial_ratio_threshold: float = 0.5, file_path: str = "") -> str:
    """参考作品蒸馏工具集。

    Actions:
    - batch_write: 批量写入 borrowable 模式。需 work_name + borrowables_json。
    - validate: 校验蒸馏 JSON 数据完整性。需 json_content。
    - assess: 评估作品蒸馏质量。需 work_name。可选 deepen_threshold/partial_ratio_threshold。
    - report: 生成蒸馏报告 + ctx 文件。需 work_name。
    - import: 从文件导入蒸馏数据。需 work_name + file_path。

    参数:
      action: batch_write|validate|assess|report|import
      work_name: 作品名（batch_write/assess/report/import 必填）
      borrowables_json: JSON 数组（仅 batch_write）
      json_content: JSON 字符串（仅 validate）
      deepen_threshold: 数量阈值（仅 assess，默认5）
      partial_ratio_threshold: partial 占比阈值（仅 assess，默认0.5）
      file_path: JSON 文件路径（仅 import）
    """
    if action == "batch_write":
        return _distill_batch_write(work_name, borrowables_json)
    elif action == "validate":
        return _distill_validate_json(json_content)
    elif action == "assess":
        return _distill_assess_quality(work_name, deepen_threshold, partial_ratio_threshold)
    elif action == "report":
        return _distill_generate_report(work_name)
    elif action == "import":
        return _distill_import_file(work_name, file_path)
    else:
        return json.dumps({"error": f"Unknown action: {action}. Use batch_write/validate/assess/report/import."}, ensure_ascii=False)


@mcp.tool
@mcp_tool
def distillation(novel_name: str, character_name: str, action: str = "get",
                 chapter_number: int = 0, decision_delta: list = None,
                 new_knowledge: list = None, changed_beliefs: list = None,
                 relation_shifts: list = None, voice_changes: dict = None,
                 ability_changes: dict = None, arc_transition: dict = None,
                 key_decision: dict = None, notes: str = "",
                 chapter_a: int = 0, chapter_b: int = 0,
                 dimension: str = "decision_delta") -> str:
    """人物蒸馏演化追踪。记录/查询/对比人物决策、认知、关系的演变。

    Actions:
    - evolve: 记录本章蒸馏增量。需 chapter_number。可选 decision_delta/new_knowledge/changed_beliefs/relation_shifts/voice_changes/ability_changes/arc_transition/key_decision/notes。
    - get: 获取蒸馏记录。可选 chapter_number(0=全部)。
    - timeline: 获取指定维度时间线。可选 dimension。
    - compare: 对比两个章节间的蒸馏变化。需 chapter_a, chapter_b。
    """
    from .tools_character import _distillation_evolve, _distillation_get, _distillation_timeline, _distillation_compare
    if action == "evolve":
        _dd = json.dumps(coerce_list(decision_delta) or [], ensure_ascii=False)
        _nk = json.dumps(coerce_list(new_knowledge) or [], ensure_ascii=False)
        _cb = json.dumps(coerce_list(changed_beliefs) or [], ensure_ascii=False)
        _rs = json.dumps(coerce_list(relation_shifts) or [], ensure_ascii=False)
        _vc = json.dumps(coerce_dict(voice_changes) or {}, ensure_ascii=False)
        _ac = json.dumps(coerce_dict(ability_changes) or {}, ensure_ascii=False)
        _at = json.dumps(coerce_dict(arc_transition) or {}, ensure_ascii=False)
        _kd = json.dumps(coerce_dict(key_decision) or {}, ensure_ascii=False)
        return _distillation_evolve(novel_name, character_name, chapter_number,
                                    _dd, _nk, _cb, _rs, _vc, _ac, _at, _kd, notes)
    elif action == "get":
        return _distillation_get(novel_name, character_name, chapter_number)
    elif action == "timeline":
        return _distillation_timeline(novel_name, character_name, dimension)
    elif action == "compare":
        return _distillation_compare(novel_name, character_name, chapter_a, chapter_b)
    else:
        return json.dumps({"error": f"Unknown action: {action}. Use evolve/get/timeline/compare."}, ensure_ascii=False)
