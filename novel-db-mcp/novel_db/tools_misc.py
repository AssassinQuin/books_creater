import json
import os
import re
from pathlib import Path

from .db import mcp, query, PROJECT_ROOT
from .resolvers import _resolve_novel_id
from .sync import (
    _ensure_data_hashes_table, _compute_hash, _record_db_hash, _record_file_hash,
    _db_row_to_hashable, _NOVELS_BASE,
)
from .sync_engine import engine as _sync_engine


@mcp.tool
def health_check(novel_name: str) -> str:
    """一键健康诊断：伏笔积压+配角活跃+升级节奏+日常密度+暗线推进+卷完成度
      novel_name: 小说名称
    """
    novel_id = _resolve_novel_id(novel_name)

    result = {}

    novel = query("SELECT * FROM novels WHERE id = ?", (novel_id,), fetch="one")
    if not novel:
        return json.dumps({"error": "novel not found"}, ensure_ascii=False)

    chapters = query("SELECT id, number, status, chapter_type, volume_id FROM chapters "
                     "WHERE novel_id = ? ORDER BY number", (novel_id,))
    total_chapters = len(chapters)
    written = [c for c in chapters if c["status"] == "written"]
    result["progress"] = {"total": total_chapters, "written": len(written)}

    planted = query("SELECT id, description, planted_chapter_id, importance FROM foreshadows "
                    "WHERE novel_id = ? AND status = 'planted' ORDER BY id", (novel_id,))
    recalled = query("SELECT COUNT(*) as cnt FROM foreshadows "
                     "WHERE novel_id = ? AND status = 'recalled'", (novel_id,), fetch="val")
    total_foreshadows = len(planted) + (recalled or 0)
    recall_rate = (recalled or 0) / total_foreshadows if total_foreshadows > 0 else 1.0

    planted_list = [dict(f) for f in planted]
    if written:
        latest_num = max(c["number"] for c in written)
        for f in planted_list:
            planted_ch = query("SELECT number FROM chapters WHERE id = ?",
                              (f["planted_chapter_id"],), fetch="one")
            if planted_ch:
                f["age_chapters"] = latest_num - planted_ch["number"]
    result["foreshadow"] = {
        "planted": len(planted), "recalled": recalled or 0,
        "recall_rate": round(recall_rate, 2),
        "oldest_planted": max((f.get("age_chapters", 0) for f in planted_list), default=0),
        "warning": recall_rate < 0.5 and len(planted) > 0
    }

    chars = query("SELECT id, name, role FROM characters "
                  "WHERE novel_id = ? AND is_active = 1 AND role != 'protagonist'", (novel_id,))
    core_chars = [c for c in chars if c["role"] in ("ally", "rival", "mentor", "love_interest")]
    char_activity = []
    for cc in core_chars:
        recent = query(
            "SELECT cs.chapter_id FROM chapter_summaries cs "
            "JOIN chapters ch ON cs.chapter_id = ch.id "
            "WHERE ch.novel_id = ? AND EXISTS (SELECT 1 FROM json_each(cs.characters_involved) WHERE value = ?) "
            "ORDER BY ch.number DESC LIMIT 1",
            (novel_id, cc["id"])
        )
        last_ch = None
        if recent and written:
            ch_num = query("SELECT number FROM chapters WHERE id = ?",
                           (recent[0]["chapter_id"],), fetch="val")
            if ch_num:
                last_ch = ch_num
                latest_num = max(c["number"] for c in written)
                gap = latest_num - ch_num
            else:
                gap = None
        else:
            gap = None
        char_activity.append({"name": cc["name"], "role": cc["role"],
                              "last_chapter": last_ch, "gap": gap,
                              "warning": gap is not None and gap > 10})
    result["character_activity"] = char_activity

    ability_changes = query(
        "SELECT dc.after_value, c.number FROM dimension_changes dc "
        "JOIN chapters c ON dc.chapter_id = c.id "
        "WHERE dc.novel_id = ? AND dc.dimension = 'ability' ORDER BY c.number",
        (novel_id,)
    )
    result["ability_progression"] = [dict(r) for r in ability_changes]

    volumes = query(
        "SELECT v.*, "
        "(SELECT COUNT(*) FROM chapters WHERE volume_id = v.id AND status = 'written') as written_count, "
        "(SELECT COUNT(*) FROM chapters WHERE volume_id = v.id) as total_count "
        "FROM volumes v WHERE v.novel_id = ? ORDER BY v.number",
        (novel_id,)
    )
    result["volumes"] = [dict(v) for v in volumes]

    warnings = []
    if result["foreshadow"]["warning"]:
        warnings.append(f"伏笔积压：回收率仅{recall_rate:.0%}，最老伏笔已过{result['foreshadow']['oldest_planted']}章")
    inactive = [c for c in char_activity if c.get("warning")]
    if inactive:
        warnings.append(f"配角遗忘：{', '.join(c['name'] for c in inactive)}超过10章未出场")
    if len(ability_changes) == 0 and total_chapters > 20:
        warnings.append("未记录任何能力等级变更，建议在writing_finish中传入ability_level")
    result["warnings"] = warnings
    result["healthy"] = len(warnings) == 0

    return json.dumps(result, ensure_ascii=False, default=str)


_SKILL_BASE_PATH = os.path.join(PROJECT_ROOT, ".claude", "skills")

_SKILL_LOADER_CACHE: dict = {}


def _resolve_skill_path(skill: str, level: str, resource: str, project: str = None) -> list:
    paths = []
    if project:
        paths.append(os.path.join(_SKILL_BASE_PATH, skill, "overrides", project, f"{level}s", f"{resource}.md"))
    paths.append(os.path.join(_SKILL_BASE_PATH, skill, f"{level}s", f"{resource}.md"))
    paths.append(os.path.join(_SKILL_BASE_PATH, f"{level}s", f"{resource}.md"))
    return paths


def _load_skill_file(skill: str, level: str, resource: str, project: str = None) -> dict:
    paths = _resolve_skill_path(skill, level, resource, project)
    checked = []

    for p in paths:
        checked.append(p)
        if not os.path.exists(p):
            continue
        if not os.path.isfile(p):
            continue
        if not os.access(p, os.R_OK):
            return {"error": "PERMISSION_DENIED", "path": p}
        try:
            with open(p, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            return {"error": "PERMISSION_DENIED", "path": p, "detail": str(e)}
        if not content.strip():
            return {"error": "EMPTY_FILE", "path": p}

        if project and p.startswith(os.path.join(_SKILL_BASE_PATH, skill, "overrides", project)):
            source = f"project:{project}"
        elif p.startswith(os.path.join(_SKILL_BASE_PATH, skill)):
            source = f"skill:{skill}"
        else:
            source = "global"

        return {"content": content, "path": p, "source": source}

    return {"error": "NOT_FOUND", "paths_checked": checked}


@mcp.tool
def skill_loader(skill: str, level: str, resource: str, project: str = "") -> str:
    """渐进式加载协议：按需加载 skill 子文件。三级优先级：project overrides > skill专属 > 全局共享。

    参数:
      skill: skill名称，如 "novel-planner"
      level: 加载层级，如 "phase" | "engine" | "example" | "agent"
      resource: 资源名，如 "b1-volume" | "environment" | "dialogue"
      project: 项目专属覆盖名，如 "这次不一样了"（可选）

    用法示例:
      skill_loader("novel-planner", "phase", "b1-volume")
      skill_loader("novel-chapter-writer", "engine", "environment", "这次不一样了")
      skill_loader("novel-chapter-writer", "example", "dialogue")
      skill_loader("novel-planner", "agent", "event-architect")
    """
    cache_key = f"{skill}:{level}:{resource}:{project or ''}"

    if cache_key in _SKILL_LOADER_CACHE:
        cached = _SKILL_LOADER_CACHE[cache_key]
        return json.dumps({
            "content": cached["content"],
            "path": cached["path"],
            "source": cached["source"],
            "cached": True
        }, ensure_ascii=False)

    result = _load_skill_file(skill, level, resource, project if project else None)

    if "error" in result:
        return json.dumps(result, ensure_ascii=False)

    _SKILL_LOADER_CACHE[cache_key] = {
        "content": result["content"],
        "path": result["path"],
        "source": result["source"]
    }

    return json.dumps({
        "content": result["content"],
        "path": result["path"],
        "source": result["source"],
        "cached": False
    }, ensure_ascii=False)


@mcp.tool
def db_search(novel_name: str, keyword: str, top_k: int = 20) -> str:
    """搜索小说数据（世界观/人物/章节/伏笔），返回排序摘要结果。

    搜索策略：用索引列（name/keys/tags）匹配，不扫 data blob。
    评分：name 匹配=10分，keys 匹配=5分，tags 匹配=3分。
    返回格式：每个结果只包含 name/category/summary(150字)/score，不返回完整 data。

      novel_name: 小说名称
      keyword: 搜索关键词
      top_k: 返回最多结果数(默认20)
    """
    novel_id = _resolve_novel_id(novel_name)
    kw = f"%{keyword}%"
    results = []

    _SEARCH_SPECS = [
        {
            "sql": ("SELECT id, category, name, data, keys, tags FROM world_settings "
                    "WHERE novel_id = ? AND status = 'active' AND "
                    "(name LIKE ? OR keys LIKE ? OR tags LIKE ?)"),
            "params": (novel_id, kw, kw, kw),
            "result_type": "world_setting",
            "name_col": "name",
            "category_col": "category",
            "score_fn": lambda r, kw=keyword: (
                (10 if kw.lower() in (r.get("name") or "").lower() else 0)
                + (5 if isinstance(r.get("keys"), str) and kw.lower() in r["keys"].lower() else 0)
                + (3 if isinstance(r.get("tags"), str) and kw.lower() in r["tags"].lower() else 0)
                or 1
            ),
            "summary_fn": lambda r: _extract_world_summary(r),
        },
        {
            "sql": ("SELECT id, name, role, personality FROM characters "
                    "WHERE novel_id = ? AND is_active = 1 AND "
                    "(name LIKE ? OR personality LIKE ?)"),
            "params": (novel_id, kw, kw),
            "result_type": "character",
            "name_col": "name",
            "category_col": "role",
            "score_fn": lambda r, kw=keyword: (
                10 if kw.lower() in (r.get("name") or "").lower() else 5
            ),
            "summary_fn": lambda r: (r.get("personality") or "")[:150],
        },
        {
            "sql": ("SELECT number, title, outline FROM chapters "
                    "WHERE novel_id = ? AND (title LIKE ? OR outline LIKE ?)"),
            "params": (novel_id, kw, kw),
            "result_type": "chapter",
            "name_col": "title",
            "category_col": None,
            "score_fn": lambda r, kw=keyword: (
                10 if kw.lower() in (r.get("title") or "").lower() else 5
            ),
            "summary_fn": lambda r: (r.get("outline") or "")[:150],
            "name_fmt": lambda r: r.get("title") or f"第{r['number']}章",
            "category_fmt": lambda r: f"Ch{r['number']}",
        },
        {
            "sql": ("SELECT id, description, status, tags FROM foreshadows "
                    "WHERE novel_id = ? AND (description LIKE ? OR tags LIKE ?)"),
            "params": (novel_id, kw, kw),
            "result_type": "foreshadow",
            "name_col": None,
            "category_col": "status",
            "score_fn": lambda r, kw=keyword: (
                5 if kw.lower() in (r.get("description") or "").lower() else 3
            ),
            "summary_fn": lambda r: (r.get("description") or "")[:150],
            "name_fmt": lambda r: f"伏笔#{r['id']}",
        },
    ]

    for spec in _SEARCH_SPECS:
        rows = query(spec["sql"], spec["params"])
        for r in (rows or []):
            name = spec.get("name_fmt", lambda r: r.get(spec["name_col"], ""))(r)
            category = spec.get("category_fmt", lambda r: r.get(spec["category_col"], ""))(r) if spec.get("category_col") or spec.get("category_fmt") else ""
            results.append({
                "type": spec["result_type"],
                "category": category,
                "name": name,
                "summary": spec["summary_fn"](r),
                "score": spec["score_fn"](r),
            })

    results.sort(key=lambda x: x["score"], reverse=True)
    results = results[:top_k]

    return json.dumps({
        "keyword": keyword,
        "total": len(results),
        "results": results,
    }, ensure_ascii=False, default=str)


def _extract_world_summary(r: dict) -> str:
    data = r.get("data", {})
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except (json.JSONDecodeError, TypeError):
            data = {}
    if isinstance(data, dict):
        content = data.get("content", "")
        return content[:150] if content else json.dumps(data, ensure_ascii=False)[:150]
    return ""


@mcp.tool
def engine_list() -> str:
    """罗列可用写作引擎文件，自动解析 # Title + > Summary。

    引擎文件是权威源——新增引擎只需放入 engines/ 目录即被自动发现。
    编排器不将引擎元数据存 DB，避免双源同步。

    用法:
      engine_list()  # 返回全部引擎的名称、标题、摘要
    """
    engine_dir = Path(PROJECT_ROOT) / ".claude" / "skills" / "engines"
    if not engine_dir.exists():
        return json.dumps({"error": f"引擎目录不存在: {engine_dir}"}, ensure_ascii=False)

    engines = []
    for f in sorted(engine_dir.glob("*.md")):
        content = f.read_text(encoding="utf-8")
        lines = content.strip().split("\n")
        title = ""
        summary = ""
        for line in lines:
            if line.startswith("# ") and not title:
                title = line[2:].strip()
            elif line.startswith(">") and not summary:
                summary = line[1:].strip()
            if title and summary:
                break

        engines.append({
            "file": f.name,
            "name": f.stem,
            "title": title or f.stem,
            "summary": summary or "",
        })

    # 检测未注册引擎：磁盘有但 ENGINE_MATRIX 无映射
    from .tools_writing import ENGINE_MATRIX
    registered = set()
    for names in ENGINE_MATRIX.values():
        registered.update(names)
    on_disk = {e["name"] for e in engines}
    unregistered = sorted(on_disk - registered)

    result = {"engines": engines}
    if unregistered:
        result["unregistered"] = unregistered

    return json.dumps(result, ensure_ascii=False)


@mcp.tool
def sync_startup(novel_name: str, data_type: str = "") -> str:
    """启动时双向对比DB与文件状态，检测冲突，返回差异报告供用户确认。
    新数据流：skill→DB直接操作，文件为可选副本。启动时对比两端，冲突默认以DB为准。
    参数:
      novel_name: 小说名称
      data_type: 校验范围，空=全部，可选: world/character/foreshadow/volume/echo
    返回:
      差异报告，含: db_only(DB有文件无), file_only(文件有DB无), conflict(两端都有但不同)
      每个冲突项标记默认解决方案(以权威源为准)
    用法:
      sync_startup(novel_name="这次不一样了")
      sync_startup(novel_name="这次不一样了", data_type="world")
      sync_startup(novel_name="这次不一样了", data_type="echo")
    """
    _ensure_data_hashes_table()
    results = {
        "db_only": [],
        "file_only": [],
        "conflict": [],
        "consistent": [],
        "summary": {}
    }
    default_types = _sync_engine.available_types
    types_to_check = [data_type] if data_type else default_types

    for etype in types_to_check:
        try:
            diff = _sync_engine.diff(novel_name, etype)
            for item in diff.get("db_only", []):
                item["note"] = item.get("note", "文件不存在")
                results["db_only"].append(item)
            results["file_only"].extend(diff.get("file_only", []))
            results["conflict"].extend(diff.get("conflict", []))
            results["consistent"].extend(diff.get("consistent", []))
        except Exception as e:
            results["errors"] = results.get("errors", [])
            results["errors"].append({"type": etype, "error": str(e)})

    results["summary"] = {
        "novel_name": novel_name,
        "engine_types": _sync_engine.available_types,
        "total_checked": len(results["consistent"]) + len(results["conflict"]) + len(results["db_only"]) + len(results["file_only"]),
        "consistent": len(results["consistent"]),
        "conflict": len(results["conflict"]),
        "db_only": len(results["db_only"]),
        "file_only": len(results["file_only"]),
    }
    return json.dumps(results, ensure_ascii=False, default=str)


@mcp.tool
def sync_db_to_files(novel_name: str, data_type: str = "", overwrite: bool = False) -> str:
    """将DB数据同步到文件（单向：DB→file）。skill操作只写DB，用户选择何时同步到文件。
    通过 SyncEngine 模板驱动，支持 YAML manifest 扩展的实体类型。
    参数:
      novel_name: 小说名称
      data_type: 同步范围，空=全部，可选: world/character/foreshadow/volume/echo
      overwrite: True=强制覆盖所有文件，False=只同步有差异的
    用法:
      sync_db_to_files(novel_name="这次不一样了")                    # 同步全部
      sync_db_to_files(novel_name="这次不一样了", data_type="world")  # 只同步世界观
      sync_db_to_files(novel_name="这次不一样了", data_type="echo")   # 只同步回响
      sync_db_to_files(novel_name="这次不一样了", overwrite=True)     # 强制全量覆盖
    注: file→DB方向请使用 sync_files_to_db()
    """
    results = {"synced": [], "skipped": [], "errors": []}
    types_to_sync = [data_type] if data_type else _sync_engine.available_types

    for etype in types_to_sync:
        if etype not in _sync_engine.available_types:
            results["errors"].append({"type": etype, "error": f"未注册的同步类型: {etype}"})
            continue
        try:
            r = _sync_engine.db_to_files(novel_name, etype, overwrite=overwrite)
            for item in r.get("errors", []):
                results["errors"].append(item)
            for _ in range(r.get("synced", 0)):
                results["synced"].append({"type": etype, "direction": "DB→file"})
            for _ in range(r.get("skipped", 0)):
                results["skipped"].append({"type": etype, "direction": "跳过（skip_existing）"})
        except Exception as e:
            results["errors"].append({"type": etype, "error": str(e)})

    summary = {
        "novel_name": novel_name,
        "engine_types": _sync_engine.available_types,
        "synced_count": len(results["synced"]),
        "skipped_count": len(results["skipped"]),
        "error_count": len(results["errors"]),
        "synced": results["synced"],
        "errors": results["errors"],
    }
    return json.dumps(summary, ensure_ascii=False, default=str)


@mcp.tool
def sync_files_to_db(novel_name: str, data_type: str = "") -> str:
    """将文件数据结构化解析后同步回DB（单向：file→DB，无损转换）。

    通过 SyncEngine 模板驱动，按字段映射写入对应 DB 列（无截断）。
    支持: volume(完整17段解析), character(全部字段+JSONB), world(聚合解析), foreshadow, echo

    参数:
      novel_name: 小说名称
      data_type: 同步范围，空=全部，可选: world/character/foreshadow/volume/echo
    用法:
      sync_files_to_db(novel_name="这次不一样了")                      # 全部实体类型
      sync_files_to_db(novel_name="这次不一样了", data_type="volume")  # 只同步卷级大纲
      sync_files_to_db(novel_name="这次不一样了", data_type="character") # 只同步人物
    注: DB→file方向请使用 sync_db_to_files()
    """
    results = {"synced": [], "skipped": [], "errors": []}
    types_to_sync = [data_type] if data_type else _sync_engine.available_types

    for etype in types_to_sync:
        if etype not in _sync_engine.available_types:
            results["errors"].append({"type": etype, "error": f"未注册的同步类型: {etype}"})
            continue
        try:
            r = _sync_engine.files_to_db(novel_name, etype)
            if "error" in r:
                results["errors"].append({"type": etype, "error": r["error"]})
                continue
            for detail in r.get("details", []):
                results["synced"].append({"type": etype, "key": detail.get("key", "?"), "direction": "file→DB"})
            for item in r.get("errors", []):
                results["errors"].append({"type": etype, **item})
        except Exception as e:
            results["errors"].append({"type": etype, "error": str(e)})

    summary = {
        "novel_name": novel_name,
        "engine_types": _sync_engine.available_types,
        "synced_count": len(results["synced"]),
        "error_count": len(results["errors"]),
        "synced": results["synced"],
        "errors": results["errors"],
    }
    return json.dumps(summary, ensure_ascii=False, default=str)


@mcp.tool
def sync_roundtrip(novel_name: str, data_type: str = "") -> str:
    """双向无损验证：File→DB→File round-trip 测试。

    流程: 读取文件 → 解析写入DB → DB渲染回文件 → 对比两次文件内容
    用于验证同步引擎的格式转换保真度。

    参数:
      novel_name: 小说名称
      data_type: 测试范围，空=全部，可选: character/volume/foreshadow/world/echo
    用法:
      sync_roundtrip(novel_name="这次不一样了")                      # 全部测试
      sync_roundtrip(novel_name="这次不一样了", data_type="volume")  # 只测试卷级大纲
    """
    results = {}
    types_to_test = [data_type] if data_type else _sync_engine.available_types

    for etype in types_to_test:
        if etype not in _sync_engine.available_types:
            results[etype] = {"error": f"未注册的同步类型: {etype}"}
            continue
        try:
            r = _sync_engine.roundtrip(novel_name, etype)
            results[etype] = r
        except Exception as e:
            results[etype] = {"error": str(e)}

    all_lossless = all(
        r.get("lossless", False) for r in results.values() if "error" not in r
    ) if results else True

    summary = {
        "novel_name": novel_name,
        "all_lossless": all_lossless,
        "details": results,
    }
    return json.dumps(summary, ensure_ascii=False, default=str)


@mcp.tool
def semantic_search(novel_name: str, query_text: str, top_k: int = 10) -> str:
    """语义搜索：用自然语言查询找到相关实体（TF-IDF 零依赖方案）。

    与 db_search 的区别：db_search 做关键词精确匹配，semantic_search 做语义相似度匹配。
    例如搜"战斗方式"可以找到"铸造能力"，搜"生病"可以找到"灵衰症"。

    参数:
      novel_name: 小说名称
      query_text: 自然语言查询文本
      top_k: 返回最多结果数(默认10)
    """
    from .embedding import get_engine_for_novel

    novel_id = _resolve_novel_id(novel_name)
    engine = get_engine_for_novel(novel_id, query)
    results = engine.search(query_text, top_k=top_k)

    for r in results:
        text = r.pop("text", "")
        r["summary"] = text[:200]

    return json.dumps({
        "query": query_text,
        "total": len(results),
        "results": results,
    }, ensure_ascii=False, default=str)
