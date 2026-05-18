import json

from .db import mcp, query
from .resolvers import _resolve_novel_id


@mcp.tool
def novel_create(name: str, genre: str = "", target_platform: str = "",
                 notes: str = "") -> str:
    """创建小说项目"""
    try:
        r = query(
            "INSERT INTO novels (name, genre, target_platform, notes, status) "
            "VALUES (%s, %s, %s, %s, 'brainstorming') RETURNING id",
            (name, genre, target_platform, notes), fetch="one"
        )
        return json.dumps({"ok": True, "id": r["id"], "name": name}, ensure_ascii=False)
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

    r = query("SELECT * FROM novels WHERE id = %s", (novel_id,), fetch="one")
    return json.dumps(dict(r) if r else {"error": "not found"}, ensure_ascii=False, default=str)


@mcp.tool
def novel_update(novel_name: str, genre: str = "", target_platform: str = "",
                 status: str = "", current_chapter: int = 0,
                 notes: str = "") -> str:
    """更新小说项目。传入需要修改的字段，空值/零值会被忽略
      novel_name: 小说名称
    """
    novel_id = _resolve_novel_id(novel_name)

    fields = {}
    if genre: fields["genre"] = genre
    if target_platform: fields["target_platform"] = target_platform
    if status: fields["status"] = status
    if current_chapter: fields["current_chapter"] = current_chapter
    if notes: fields["notes"] = notes
    if not fields:
        return json.dumps({"ok": False, "error": "no valid fields"}, ensure_ascii=False)
    sets = [f"{k} = %s" for k in fields]
    vals = list(fields.values()) + [novel_id]
    query(f"UPDATE novels SET {', '.join(sets)}, updated_at = NOW() WHERE id = %s", tuple(vals), fetch="none")
    return json.dumps({"ok": True}, ensure_ascii=False)
