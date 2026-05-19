import json
import os
import re
from pathlib import Path

from .db import mcp, query, PROJECT_ROOT
from .resolvers import _resolve_novel_id
from .sync import (
    _ensure_data_hashes_table, _compute_hash, _record_db_hash, _record_file_hash,
    _db_row_to_hashable, _sync_world_to_file, _sync_character_to_file,
    _sync_foreshadow_to_file, _sync_volume_to_file, _NOVELS_BASE,
)


@mcp.tool
def health_check(novel_name: str) -> str:
    """一键健康诊断：伏笔积压+配角活跃+升级节奏+日常密度+暗线推进+卷完成度
      novel_name: 小说名称
    """
    novel_id = _resolve_novel_id(novel_name)

    result = {}

    novel = query("SELECT * FROM novels WHERE id = %s", (novel_id,), fetch="one")
    if not novel:
        return json.dumps({"error": "novel not found"}, ensure_ascii=False)

    chapters = query("SELECT id, number, status, chapter_type, volume_id FROM chapters "
                     "WHERE novel_id = %s ORDER BY number", (novel_id,))
    total_chapters = len(chapters)
    written = [c for c in chapters if c["status"] == "written"]
    result["progress"] = {"total": total_chapters, "written": len(written)}

    planted = query("SELECT id, description, planted_chapter_id, importance FROM foreshadows "
                    "WHERE novel_id = %s AND status = 'planted' ORDER BY id", (novel_id,))
    recalled = query("SELECT COUNT(*) as cnt FROM foreshadows "
                     "WHERE novel_id = %s AND status = 'recalled'", (novel_id,), fetch="val")
    total_foreshadows = len(planted) + (recalled or 0)
    recall_rate = (recalled or 0) / total_foreshadows if total_foreshadows > 0 else 1.0

    planted_list = [dict(f) for f in planted]
    if written:
        latest_num = max(c["number"] for c in written)
        for f in planted_list:
            planted_ch = query("SELECT number FROM chapters WHERE id = %s",
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
                  "WHERE novel_id = %s AND is_active = TRUE AND role != 'protagonist'", (novel_id,))
    core_chars = [c for c in chars if c["role"] in ("ally", "rival", "mentor", "love_interest")]
    char_activity = []
    for cc in core_chars:
        recent = query(
            "SELECT cs.chapter_id FROM chapter_summaries cs "
            "JOIN chapters ch ON cs.chapter_id = ch.id "
            "WHERE ch.novel_id = %s AND %s = ANY(cs.characters_involved) "
            "ORDER BY ch.number DESC LIMIT 1",
            (novel_id, cc["id"])
        )
        last_ch = None
        if recent and written:
            ch_num = query("SELECT number FROM chapters WHERE id = %s",
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
        "WHERE dc.novel_id = %s AND dc.dimension = 'ability' ORDER BY c.number",
        (novel_id,)
    )
    result["ability_progression"] = [dict(r) for r in ability_changes]

    volumes = query(
        "SELECT v.*, "
        "(SELECT COUNT(*) FROM chapters WHERE volume_id = v.id AND status = 'written') as written_count, "
        "(SELECT COUNT(*) FROM chapters WHERE volume_id = v.id) as total_count "
        "FROM volumes v WHERE v.novel_id = %s ORDER BY v.number",
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
def db_search(novel_name: str, keyword: str) -> str:
    """在小说所有数据中搜索关键词（世界观/人物/章节/伏笔/时间线）
      novel_name: 小说名称
    """
    novel_id = _resolve_novel_id(novel_name)
    result: dict = {}
    kw = f"%{keyword}%"
    world = query(
        "SELECT category, name, data FROM world_settings "
        "WHERE novel_id = %s AND (name ILIKE %s OR data::text ILIKE %s)",
        (novel_id, kw, kw)
    )
    if world:
        result["world_settings"] = [dict(r) for r in world]
    chars = query(
        "SELECT id, name, role, personality FROM characters "
        "WHERE novel_id = %s AND is_active = TRUE AND "
        "(name ILIKE %s OR personality ILIKE %s OR background ILIKE %s OR goals ILIKE %s)",
        (novel_id, kw, kw, kw, kw)
    )
    if chars:
        result["characters"] = [dict(r) for r in chars]
    chapters = query(
        "SELECT number, title, outline FROM chapters "
        "WHERE novel_id = %s AND (title ILIKE %s OR outline ILIKE %s)",
        (novel_id, kw, kw)
    )
    if chapters:
        result["chapters"] = [dict(r) for r in chapters]
    foreshadows = query(
        "SELECT id, description, status FROM foreshadows "
        "WHERE novel_id = %s AND description ILIKE %s",
        (novel_id, kw)
    )
    if foreshadows:
        result["foreshadows"] = [dict(r) for r in foreshadows]
    return json.dumps(result, ensure_ascii=False, default=str)


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
      data_type: 校验范围，空=全部，可选: world/character/foreshadow/volume/chapter
    返回:
      差异报告，含: db_only(DB有文件无), file_only(文件有DB无), conflict(两端都有但不同)
      每个冲突项标记默认解决方案(以DB为准)
    用法:
      sync_startup(novel_name="这次不一样了")
      sync_startup(novel_name="这次不一样了", data_type="world")
    """
    novel_id = _resolve_novel_id(novel_name)
    _ensure_data_hashes_table()
    results = {
        "db_only": [],
        "file_only": [],
        "conflict": [],
        "consistent": [],
        "summary": {}
    }
    types_to_check = [data_type] if data_type else ["world", "character", "foreshadow", "volume"]

    if "world" in types_to_check:
        db_rows = query(
            "SELECT * FROM world_settings WHERE novel_id = %s",
            (novel_id,)
        )
        db_map = {}
        for row in db_rows:
            key = f"{row['category']}:{row['name']}"
            db_map[key] = row
            db_hash = _compute_hash(_db_row_to_hashable(dict(row)))
            file_path = os.path.join(
                _NOVELS_BASE, novel_name, "设定", "世界观",
                {"core_setting": "核心设定.md", "bestiary": "异灵图鉴.md",
                 "ability": "能力体系.md", "item": "物品装备.md",
                 "economy": "经济体系.md", "daily_life": "日常生活.md",
                 "history": "历史事件.md", "location": "地图.md",
                 "faction": "势力.md", "race": "种族.md"}.get(row["category"], f"{row['category']}.md")
            )
            if os.path.exists(file_path):
                with open(file_path, "r", encoding="utf-8") as f:
                    file_content = f.read()
                marker = f"## {row['category']}: {row['name']}"
                if marker in file_content:
                    file_hash = _compute_hash(file_content)
                    if db_hash != file_hash:
                        results["conflict"].append({
                            "type": "world", "key": key,
                            "db_updated": str(row.get("updated_at", "")),
                            "resolution": "DB→file"
                        })
                    else:
                        results["consistent"].append({"type": "world", "key": key})
                else:
                    results["db_only"].append({"type": "world", "key": key, "note": "DB有但文件中无对应章节"})
            else:
                results["db_only"].append({"type": "world", "key": key, "note": "文件不存在"})
            _record_db_hash(novel_id, "world", key, db_hash)

    if "character" in types_to_check:
        db_rows = query(
            "SELECT * FROM characters WHERE novel_id = %s AND is_active = TRUE",
            (novel_id,)
        )
        for row in db_rows:
            key = row["name"]
            db_hash = _compute_hash(_db_row_to_hashable(dict(row)))
            file_path = os.path.join(_NOVELS_BASE, novel_name, "设定", "人物", f"{key}.md")
            if os.path.exists(file_path):
                with open(file_path, "r", encoding="utf-8") as f:
                    file_content = f.read()
                file_hash = _compute_hash(file_content)
                if db_hash != file_hash:
                    results["conflict"].append({
                        "type": "character", "key": key,
                        "db_updated": str(row.get("updated_at", "")),
                        "resolution": "DB→file"
                    })
                else:
                    results["consistent"].append({"type": "character", "key": key})
            else:
                results["db_only"].append({"type": "character", "key": key, "note": "文件不存在"})
            _record_db_hash(novel_id, "character", key, db_hash)

    if "foreshadow" in types_to_check:
        db_rows = query(
            "SELECT id, description, status, importance, planned_recall_chapter, updated_at "
            "FROM foreshadows WHERE novel_id = %s",
            (novel_id,)
        )
        for row in db_rows:
            key = str(row["id"])
            db_hash = _compute_hash(_db_row_to_hashable(dict(row)))
            _record_db_hash(novel_id, "foreshadow", key, db_hash)
            results["consistent"].append({"type": "foreshadow", "key": key, "desc": row["description"][:40]})

    if "volume" in types_to_check:
        outline_dir = os.path.join(_NOVELS_BASE, novel_name, "设定", "大纲")
        if os.path.isdir(outline_dir):
            for fname in sorted(os.listdir(outline_dir)):
                if not fname.endswith(".md") or fname in ("伏笔清单.md", "附录.md", "兄妹心结-渐进弧线.md"):
                    continue
                fpath = os.path.join(outline_dir, fname)
                with open(fpath, "r", encoding="utf-8") as f:
                    content = f.read()
                file_hash = _compute_hash(content)
                key = fname.replace(".md", "")
                _record_file_hash(novel_id, "volume", key, content)
                vol_match = re.match(r"V(\d+)", fname)
                if vol_match:
                    vol_num = int(vol_match.group(1))
                    vol = query(
                        "SELECT id, notes, updated_at FROM volumes WHERE novel_id = %s AND number = %s",
                        (novel_id, vol_num), fetch="one"
                    )
                    if vol:
                        db_hash = _compute_hash(str(vol.get("notes", "")))
                        if db_hash != file_hash:
                            results["conflict"].append({
                                "type": "volume", "key": key,
                                "db_updated": str(vol.get("updated_at", "")),
                                "resolution": "file→DB"
                            })
                        else:
                            results["consistent"].append({"type": "volume", "key": key})
                    else:
                        results["file_only"].append({"type": "volume", "key": key, "note": "DB中无此卷记录"})
                else:
                    results["file_only"].append({"type": "volume", "key": key, "note": "非标准卷号"})

    results["summary"] = {
        "novel_id": novel_id,
        "novel_name": novel_name,
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
    参数:
      novel_name: 小说名称
      data_type: 同步范围，空=全部，可选: world/character/foreshadow/volume/chapter
      overwrite: True=强制覆盖所有文件，False=只同步有差异的
    用法:
      sync_db_to_files(novel_name="这次不一样了")                    # 同步全部有差异的
      sync_db_to_files(novel_name="这次不一样了", data_type="world")  # 只同步世界观
      sync_db_to_files(novel_name="这次不一样了", overwrite=True)     # 强制全量覆盖
    注: file→DB方向请使用 sync_files_to_db()
    """
    novel_id = _resolve_novel_id(novel_name)
    results = {"synced": [], "skipped": [], "errors": []}
    types_to_sync = [data_type] if data_type else ["world", "character", "foreshadow", "volume"]

    if "world" in types_to_sync:
        rows = query(
            "SELECT * FROM world_settings WHERE novel_id = %s",
            (novel_id,)
        )
        for row in rows:
            key = f"{row['category']}:{row['name']}"
            try:
                _sync_world_to_file(novel_id, novel_name, dict(row))
                results["synced"].append({"type": "world", "key": key, "direction": "DB→file"})
            except Exception as e:
                results["errors"].append({"type": "world", "key": key, "error": str(e)})

    if "character" in types_to_sync:
        rows = query(
            "SELECT * FROM characters WHERE novel_id = %s AND is_active = TRUE",
            (novel_id,)
        )
        for row in rows:
            try:
                _sync_character_to_file(novel_id, novel_name, dict(row))
                results["synced"].append({"type": "character", "key": row["name"], "direction": "DB→file"})
            except Exception as e:
                results["errors"].append({"type": "character", "key": row["name"], "error": str(e)})

    if "foreshadow" in types_to_sync:
        rows = query(
            "SELECT * FROM foreshadows WHERE novel_id = %s",
            (novel_id,)
        )
        for row in rows:
            try:
                _sync_foreshadow_to_file(novel_id, novel_name, dict(row))
                results["synced"].append({"type": "foreshadow", "key": str(row["id"]), "direction": "DB→file"})
            except Exception as e:
                results["errors"].append({"type": "foreshadow", "key": str(row["id"]), "error": str(e)})

    if "volume" in types_to_sync:
        vol_rows = query(
            "SELECT * FROM volumes WHERE novel_id = %s ORDER BY number",
            (novel_id,)
        )
        for vol in vol_rows:
            key = f"V{vol['number']}"
            try:
                created = _sync_volume_to_file(novel_id, novel_name, dict(vol), overwrite=overwrite)
                direction = "DB→file (新建/覆盖)" if created else "file已存在,跳过"
                results["synced"].append({"type": "volume", "key": key, "direction": direction})
            except Exception as e:
                results["errors"].append({"type": "volume", "key": key, "error": str(e)})

    summary = {
        "novel_id": novel_id,
        "novel_name": novel_name,
        "synced_count": len(results["synced"]),
        "skipped_count": len(results["skipped"]),
        "error_count": len(results["errors"]),
        "synced": results["synced"],
        "errors": results["errors"],
    }
    return json.dumps(summary, ensure_ascii=False, default=str)


@mcp.tool
def sync_files_to_db(novel_name: str) -> str:
    """将文件数据同步回DB（单向：file→DB）。当前支持卷级大纲文件→volumes.notes。
    参数:
      novel_name: 小说名称
    用法:
      sync_files_to_db(novel_name="这次不一样了")  # 读取设定/大纲/V*.md → 更新volumes表
    """
    novel_id = _resolve_novel_id(novel_name)
    synced = []
    errors = []

    outline_dir = os.path.join(_NOVELS_BASE, novel_name, "设定", "大纲")
    if not os.path.isdir(outline_dir):
        return json.dumps({"ok": True, "synced": [], "errors": [], "note": "目录不存在"}, ensure_ascii=False)

    for fname in sorted(os.listdir(outline_dir)):
        if not fname.endswith(".md"):
            continue
        fpath = os.path.join(outline_dir, fname)
        vol_match = re.match(r"V(\d+)", fname)
        if not vol_match:
            continue
        vol_num = int(vol_match.group(1))
        vol = query(
            "SELECT id FROM volumes WHERE novel_id = %s AND number = %s",
            (novel_id, vol_num), fetch="one"
        )
        if not vol:
            continue
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()
            query(
                "UPDATE volumes SET notes = %s, updated_at = NOW() WHERE id = %s",
                (content[:2000], vol["id"]), fetch="none"
            )
            synced.append({"type": "volume", "key": fname.replace(".md", ""), "direction": "file→DB"})
        except Exception as e:
            errors.append({"type": "volume", "key": fname.replace(".md", ""), "error": str(e)})

    return json.dumps({
        "ok": True,
        "novel_name": novel_name,
        "synced_count": len(synced),
        "error_count": len(errors),
        "synced": synced,
        "errors": errors,
    }, ensure_ascii=False)
