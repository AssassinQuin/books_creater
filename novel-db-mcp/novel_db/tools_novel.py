import json

from .db import mcp, query
from .resolvers import _resolve_novel_id, _UNSET
from .sql_utils import build_update_sql


@mcp.tool
def novel_create(name: str, genre: str = "", target_platform: str = "",
                 notes: str = "") -> str:
    """创建小说项目"""
    try:
        r = query(
            "INSERT INTO novels (name, genre, target_platform, notes, status) "
            "VALUES (?, ?, ?, ?, 'brainstorming')",
            (name, genre, target_platform, notes), fetch="insert"
        )
        return json.dumps({"ok": True, "id": r, "name": name}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)


@mcp.tool
def novel_list() -> str:
    """列出所有小说项目"""
    rows = query("SELECT id, name, genre, status, current_chapter, target_platform FROM novels ORDER BY updated_at DESC")
    return json.dumps([dict(r) for r in rows], ensure_ascii=False, default=str)


@mcp.tool
def novel_get(novel_name: str) -> str:
    """获取小说项目详情
      novel_name: 小说名称
    """
    novel_id = _resolve_novel_id(novel_name)

    r = query("SELECT * FROM novels WHERE id = ?", (novel_id,), fetch="one")
    return json.dumps(dict(r) if r else {"error": "not found"}, ensure_ascii=False, default=str)


@mcp.tool
def novel_update(novel_name: str, genre=_UNSET, target_platform=_UNSET,
                 status=_UNSET, current_chapter=_UNSET,
                 notes=_UNSET) -> str:
    """更新小说项目。传入需要修改的字段，空值/零值会被忽略
      novel_name: 小说名称
    """
    novel_id = _resolve_novel_id(novel_name)

    fields = {}
    if genre is not _UNSET: fields["genre"] = genre
    if target_platform is not _UNSET: fields["target_platform"] = target_platform
    if status is not _UNSET: fields["status"] = status
    if current_chapter is not _UNSET: fields["current_chapter"] = current_chapter
    if notes is not _UNSET: fields["notes"] = notes
    if not fields:
        return json.dumps({"ok": False, "error": "no valid fields"}, ensure_ascii=False)
    sql, params = build_update_sql("novels", fields, "id = ?", (novel_id,))
    query(sql, params, fetch="none")
    return json.dumps({"ok": True}, ensure_ascii=False)
