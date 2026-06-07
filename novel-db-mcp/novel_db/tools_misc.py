import json
import os
import re
from pathlib import Path

from .db import mcp, query, PROJECT_ROOT
from .resolvers import _resolve_novel_id, _resolve_entity
from .errors import NotFoundError, mcp_tool, get_call_stats, reset_call_stats
from .sync import (
    _ensure_data_hashes_table, _compute_hash, _record_db_hash, _record_file_hash,
    _db_row_to_hashable, _NOVELS_BASE,
)
from .sync_engine import engine as _sync_engine
from .param_utils import coerce_list


@mcp.tool
@mcp_tool
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
        planted_ch_ids = [f["planted_chapter_id"] for f in planted_list if f.get("planted_chapter_id")]
        ch_num_map = {}
        if planted_ch_ids:
            placeholders = ",".join(["?"] * len(planted_ch_ids))
            ch_rows = query(
                f"SELECT id, number FROM chapters WHERE id IN ({placeholders})",
                tuple(planted_ch_ids)
            )
            ch_num_map = {r["id"]: r["number"] for r in ch_rows}
        for f in planted_list:
            pcid = f.get("planted_chapter_id")
            if pcid and pcid in ch_num_map:
                f["age_chapters"] = latest_num - ch_num_map[pcid]
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

    if core_chars and written:
        core_char_ids = [cc["id"] for cc in core_chars]
        placeholders = ",".join(["?"] * len(core_char_ids))
        latest_num = max(c["number"] for c in written)

        recent_rows = query(
            f"SELECT cs.chapter_id, ch.id as char_id, ch2.number as ch_number "
            f"FROM chapter_summaries cs "
            f"JOIN chapters ch2 ON cs.chapter_id = ch2.id, "
            f"json_each(cs.characters_involved) je "
            f"JOIN characters ch ON je.value = ch.id "
            f"WHERE ch2.novel_id = ? AND ch.id IN ({placeholders}) "
            f"ORDER BY ch.id, ch2.number DESC",
            (novel_id, *core_char_ids)
        )

        char_last_ch = {}
        for r in (recent_rows or []):
            cid = r.get("char_id")
            if cid and cid not in char_last_ch:
                char_last_ch[cid] = r.get("ch_number")

        for cc in core_chars:
            last_ch = char_last_ch.get(cc["id"])
            gap = (latest_num - last_ch) if last_ch is not None else None
            char_activity.append({"name": cc["name"], "role": cc["role"],
                                  "last_chapter": last_ch, "gap": gap,
                                  "warning": gap is not None and gap > 10})
    else:
        for cc in core_chars:
            char_activity.append({"name": cc["name"], "role": cc["role"],
                                  "last_chapter": None, "gap": None,
                                  "warning": False})
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
@mcp_tool
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


def _db_search(novel_name: str, keyword: str, top_k: int = 20,
               mode: str = "keyword", entity_types: list = None, min_score: float = 0.1) -> str:
    # Vector mode: delegate to vector_search
    if mode == "vector":
        from .tools_vector import _get_vector_store, _ensure_vector_index
        novel_id = _resolve_novel_id(novel_name)
        type_list = coerce_list(entity_types)
        store = _get_vector_store()
        _ensure_vector_index(store, novel_id, entity_types=type_list)
        from .tools_vector import _resolve_entity_name
        results = store.search(novel_id, keyword, top_k=top_k,
                               entity_types=type_list, min_score=min_score)
        for r in results:
            r["name"] = _resolve_entity_name(r["type"], r["id"], novel_id)
        return json.dumps({
            "query": keyword,
            "mode": "vector",
            "total": len(results),
            "results": results,
        }, ensure_ascii=False, default=str)
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
@mcp_tool
def search(novel_name: str, keyword: str, action: str = "keyword",
           top_k: int = 20, entity_types: list = None, min_score: float = 0.1,
           rebuild: bool = False, min_missing: int = 1,
           with_suggestions: bool = False, entity_type: str = "",
           field_name: str = "", field_value: str = "",
           dry_run: bool = True) -> str:
    """统一搜索接口。关键词/向量/缺失检测/批量修改。

    Actions:
    - keyword: 关键词精确匹配(快)。用索引列 name/keys/tags。
    - vector: 语义向量匹配。搜"战斗方式"可找到"铸造能力"。
    - incomplete: 查找字段缺失实体。可选 with_suggestions=True 推荐补全。
    - search_update: 向量搜索→批量修改。需 entity_type/field_name/field_value。默认 dry_run=True。

    参数:
      novel_name: 小说名称
      keyword: 搜索关键词或自然语言查询
      action: keyword|vector|incomplete|search_update (默认keyword)
      top_k: 返回最多结果数(默认20)
      entity_types: 实体类型列表过滤(空=全部)，如 ["world_setting", "character"]
      min_score: 最低相似度阈值(默认0.1)
      rebuild: 强制重建向量索引(默认False)
      min_missing: 最少缺失字段数(仅incomplete，默认1)
      with_suggestions: 推荐补全(仅incomplete，默认False)
      entity_type: 目标实体类型(仅search_update)
      field_name: 修改字段名(仅search_update)
      field_value: 新字段值(仅search_update)
      dry_run: 试运行(仅search_update，默认True)
    """
    if action == "keyword":
        return _db_search(novel_name, keyword, top_k, mode="keyword")
    elif action == "vector":
        return _db_search(novel_name, keyword, top_k, mode="vector",
                          entity_types=entity_types, min_score=min_score)
    elif action == "incomplete":
        from .tools_vector import _vector_find_incomplete
        _et_str = ",".join(coerce_list(entity_types) or [])
        return _vector_find_incomplete(novel_name, _et_str, min_missing, with_suggestions)
    elif action == "search_update":
        from .tools_vector import _vector_search_and_update
        return _vector_search_and_update(novel_name, keyword, entity_type,
                                         field_name, field_value, top_k,
                                         min_score or 0.2, dry_run)
    else:
        return json.dumps({"error": f"Unknown action: {action}. Use keyword/vector/incomplete/search_update."}, ensure_ascii=False)


def _engine_list() -> str:
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


def _sync_startup(novel_name: str, data_type: str = "") -> str:
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


def _sync_db_to_files(novel_name: str, data_type: str = "", overwrite: bool = False) -> str:
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
    results = {"synced": [], "skipped": [], "errors": [], "conflicts": []}
    types_to_sync = [data_type] if data_type else _sync_engine.available_types

    for etype in types_to_sync:
        if etype not in _sync_engine.available_types:
            results["errors"].append({"type": etype, "error": f"未注册的同步类型: {etype}"})
            continue
        try:
            r = _sync_engine.db_to_files(novel_name, etype, overwrite=overwrite)
            for item in r.get("errors", []):
                results["errors"].append(item)
            for item in r.get("conflicts", []):
                results["conflicts"].append(item)
            for _ in range(r.get("synced", 0)):
                results["synced"].append({"type": etype, "direction": "DB→file"})
            for _ in range(r.get("skipped", 0)):
                results["skipped"].append({"type": etype, "direction": "跳过"})
        except Exception as e:
            results["errors"].append({"type": etype, "error": str(e)})

    summary = {
        "novel_name": novel_name,
        "engine_types": _sync_engine.available_types,
        "synced_count": len(results["synced"]),
        "skipped_count": len(results["skipped"]),
        "conflict_count": len(results["conflicts"]),
        "error_count": len(results["errors"]),
        "synced": results["synced"],
        "conflicts": results["conflicts"],
        "errors": results["errors"],
    }
    return json.dumps(summary, ensure_ascii=False, default=str)


def _sync_files_to_db(novel_name: str, data_type: str = "") -> str:
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
@mcp_tool
def engine(action: str = "list", engine_type: str = "", scene_types: list = None, novel_name: str = "") -> str:
    """写作引擎管理工具。

    Actions:
    - list: 列出所有可用引擎文件。
    - detail: 加载指定引擎类型的完整内容。需 engine_type + novel_name。
    - resolve: 根据场面类型标签自动解析需加载的引擎。需 scene_types 列表。

    参数:
      action: list|detail|resolve (默认list)
      engine_type: 引擎类型名(仅detail)
      novel_name: 小说名称(仅detail)
      scene_types: 场面类型列表(仅resolve)，如 ["atmosphere", "dialogue"]
    """
    if action == "list":
        return _engine_list()
    elif action == "detail":
        from .tools_world import _engine_detail
        return _engine_detail(engine_type, novel_name)
    elif action == "resolve":
        from .tools_writing import _resolve_engines
        return _resolve_engines(scene_types or [])
    else:
        return json.dumps({"error": f"Unknown action: {action}. Use list/detail/resolve."}, ensure_ascii=False)


@mcp.tool
@mcp_tool
def sync(novel_name: str, action: str = "startup", data_type: str = "", overwrite: bool = False,
         resolutions: list = None) -> str:
    """数据同步工具。DB↔文件双向同步。

    Actions:
    - startup: 启动时对比DB与文件状态，返回差异报告。
    - db_to_files: DB→文件同步。可选 data_type 过滤(world/character/foreshadow/volume/echo)。
    - files_to_db: 文件→DB同步。可选 data_type 过滤。
    - lorebook: 从设定/世界观/目录同步MD文件到DB。
    - resolve: 解决同步冲突。需 resolutions 参数。

    参数:
      novel_name: 小说名称
      action: startup|db_to_files|files_to_db|lorebook|resolve (默认startup)
      data_type: 同步范围(空=全部)，可选 world/character/foreshadow/volume/echo
      overwrite: 是否强制覆盖(仅db_to_files)
      resolutions: 冲突解决列表(仅resolve)，每项 {"type": "实体类型", "key": "实体标识", "strategy": "overwrite|skip|reverse"}
    """
    if action == "startup":
        return _sync_startup(novel_name, data_type)
    elif action == "db_to_files":
        return _sync_db_to_files(novel_name, data_type, overwrite)
    elif action == "files_to_db":
        return _sync_files_to_db(novel_name, data_type)
    elif action == "lorebook":
        from .tools_world import _sync_lorebook
        return _sync_lorebook(novel_name)
    elif action == "resolve":
        if not resolutions:
            return json.dumps({"error": "resolve 需要 resolutions 参数"}, ensure_ascii=False)
        results = []
        for r in resolutions:
            etype = r.get("type", "")
            key = r.get("key", "")
            strategy = r.get("strategy", "overwrite")
            if etype not in _sync_engine.available_types:
                results.append({"type": etype, "key": key, "error": f"未注册的同步类型: {etype}"})
                continue
            try:
                res = _sync_engine.resolve_conflict(novel_name, etype, key, strategy)
                results.append({"type": etype, "key": key, "strategy": strategy, "result": res})
            except Exception as e:
                results.append({"type": etype, "key": key, "error": str(e)})
        return json.dumps({"resolved": results}, ensure_ascii=False, default=str)
    else:
        return json.dumps({"error": f"Unknown action: {action}. Use startup/db_to_files/files_to_db/lorebook/resolve."}, ensure_ascii=False)


@mcp.tool
@mcp_tool
def tool_stats(action: str = "get") -> str:
    """MCP 工具调用统计。追踪每个工具的调用次数、错误数、平均耗时。

    Actions:
    - get: 获取当前统计快照。
    - reset: 清零所有统计。

    参数:
      action: get|reset (默认 get)
    """
    if action == "reset":
        reset_call_stats()
        return json.dumps({"ok": True, "message": "统计已清零"}, ensure_ascii=False)

    stats = get_call_stats()
    tools = stats.pop("tools", {})
    ranked = sorted(tools.items(), key=lambda x: x[1]["count"], reverse=True)
    tool_details = []
    for name, s in ranked:
        avg_ms = round(s["total_ms"] / s["count"], 1) if s["count"] > 0 else 0
        tool_details.append({
            "tool": name,
            "calls": s["count"],
            "errors": s["errors"],
            "avg_ms": avg_ms,
            "total_ms": round(s["total_ms"], 1),
        })
    return json.dumps({
        "ok": True,
        "total_calls": stats["total_calls"],
        "total_errors": stats["total_errors"],
        "tools": tool_details,
    }, ensure_ascii=False)
