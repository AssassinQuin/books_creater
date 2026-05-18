import json

from .db import mcp, query
from .resolvers import _resolve_novel_id


@mcp.tool
def volume_create(novel_name: str, number: int, title: str = "",
                  main_plotlines: list = None, notes: str = "") -> str:
    """创建卷。main_plotlines: [{name, description, purpose}]
      novel_name: 小说名称
    """
    novel_id = _resolve_novel_id(novel_name)

    mp = json.dumps(main_plotlines or [], ensure_ascii=False)
    r = query(
        "INSERT INTO volumes (novel_id, number, title, main_plotlines, notes) "
        "VALUES (%s, %s, %s, %s, %s) ON CONFLICT (novel_id, number) "
        "DO UPDATE SET title = %s, main_plotlines = %s, notes = %s, updated_at = NOW() "
        "RETURNING id",
        (novel_id, number, title, mp, notes, title, mp, notes), fetch="one"
    )
    return json.dumps({"ok": True, "id": r["id"], "number": number}, ensure_ascii=False)


@mcp.tool
def volume_list(novel_name: str) -> str:
    """列出小说所有卷
      novel_name: 小说名称
    """
    novel_id = _resolve_novel_id(novel_name)

    rows = query(
        "SELECT v.*, "
        "(SELECT COUNT(*) FROM chapters WHERE volume_id = v.id) as chapter_count "
        "FROM volumes v WHERE v.novel_id = %s ORDER BY v.number",
        (novel_id,)
    )
    return json.dumps([dict(r) for r in rows], ensure_ascii=False, default=str)


def _volume_get_by_id(volume_id: int) -> str:
    v = query("SELECT * FROM volumes WHERE id = %s", (volume_id,), fetch="one")
    if not v:
        return json.dumps({"error": "not found"}, ensure_ascii=False)
    chapters = query(
        "SELECT id, number, title, status, chapter_type FROM chapters "
        "WHERE volume_id = %s ORDER BY number", (volume_id,)
    )
    result = dict(v)
    result["chapters"] = [dict(c) for c in chapters]
    return json.dumps(result, ensure_ascii=False, default=str)


def _volume_update_by_id(volume_id: int, title: str = "",
                  main_plotlines: list = None, notes: str = "") -> str:
    fields = {}
    if title: fields["title"] = title
    if main_plotlines is not None:
        fields["main_plotlines"] = json.dumps(main_plotlines, ensure_ascii=False)
    if notes: fields["notes"] = notes
    if not fields:
        return json.dumps({"ok": False, "error": "no valid fields"}, ensure_ascii=False)
    sets = [f"{k} = %s" for k in fields]
    vals = list(fields.values()) + [volume_id]
    query(f"UPDATE volumes SET {', '.join(sets)}, updated_at = NOW() WHERE id = %s", tuple(vals), fetch="none")
    return json.dumps({"ok": True}, ensure_ascii=False)


@mcp.tool
def volume_get(novel_name: str, number: int) -> str:
    """按卷号获取卷详情（无需volume_id）。
      novel_name: 小说名称
      number: 卷号（如1, 2, 3）
    """
    novel_id = _resolve_novel_id(novel_name)
    vol = query("SELECT id FROM volumes WHERE novel_id=%s AND number=%s", (novel_id, number), fetch="one")
    if not vol:
        return json.dumps({"error": f"卷 {number} 不存在"}, ensure_ascii=False)
    return _volume_get_by_id(vol["id"])


@mcp.tool
def volume_update(novel_name: str, number: int, title: str = "",
                            main_plotlines: list = None, notes: str = "") -> str:
    """按卷号更新卷信息（无需volume_id）。传入需要修改的字段，空值会被忽略。
      novel_name: 小说名称
      number: 卷号
    """
    novel_id = _resolve_novel_id(novel_name)
    vol = query("SELECT id FROM volumes WHERE novel_id=%s AND number=%s", (novel_id, number), fetch="one")
    if not vol:
        return json.dumps({"error": f"卷 {number} 不存在"}, ensure_ascii=False)
    return _volume_update_by_id(vol["id"], title, main_plotlines, notes)
