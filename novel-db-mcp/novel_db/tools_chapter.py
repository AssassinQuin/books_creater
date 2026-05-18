import json

from .db import mcp, query
from .resolvers import _resolve_novel_id, _resolve_chapter_id


@mcp.tool
def chapter_plan(novel_name: str, number: int, title: str = "",
                 outline: str = "", chapter_type: str = "normal",
                 volume_id: int = None) -> str:
    """规划章节。chapter_type: normal/transition/climax/filler/daily
      novel_name: 小说名称
    """
    novel_id = _resolve_novel_id(novel_name)

    r = query(
        "INSERT INTO chapters (novel_id, number, title, outline, chapter_type, volume_id) "
        "VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT (novel_id, number) "
        "DO UPDATE SET title = %s, outline = %s, chapter_type = %s, volume_id = %s, updated_at = NOW() "
        "RETURNING id",
        (novel_id, number, title, outline, chapter_type, volume_id,
         title, outline, chapter_type, volume_id), fetch="one"
    )
    return json.dumps({"ok": True, "id": r["id"], "number": number}, ensure_ascii=False)


@mcp.tool
def chapter_list(novel_name: str, status: str = "") -> str:
    """列出章节。status 可选过滤: planned/drafting/written/reviewed/published
      novel_name: 小说名称
    """
    novel_id = _resolve_novel_id(novel_name)
    if status:
        rows = query("SELECT * FROM chapters WHERE novel_id = %s AND status = %s ORDER BY number",
                     (novel_id, status))
    else:
        rows = query("SELECT * FROM chapters WHERE novel_id = %s ORDER BY number", (novel_id,))
    return json.dumps([dict(r) for r in rows], ensure_ascii=False, default=str)


def _chapter_update_by_id(chapter_id: int, title: str = "", status: str = "",
                   outline: str = "", chapter_type: str = "",
                   volume_id: int = None) -> str:
    fields = {}
    if title: fields["title"] = title
    if status: fields["status"] = status
    if outline: fields["outline"] = outline
    if chapter_type: fields["chapter_type"] = chapter_type
    if volume_id is not None: fields["volume_id"] = volume_id
    if not fields:
        return json.dumps({"ok": False, "error": "no valid fields"}, ensure_ascii=False)
    sets = [f"{k} = %s" for k in fields]
    vals = list(fields.values()) + [chapter_id]
    query(f"UPDATE chapters SET {', '.join(sets)}, updated_at = NOW() WHERE id = %s", tuple(vals), fetch="none")
    return json.dumps({"ok": True}, ensure_ascii=False)


@mcp.tool
def chapter_save_summary(novel_name: str, chapter_number: int, summary: str,
                         key_events: list = None, characters_involved: list = None,
                         new_foreshadows: list = None, resolved_foreshadows: list = None,
                         dimension_snapshot: dict = None) -> str:
    """保存章节摘要。每章写完后调用
      novel_name: 小说名称
      chapter_number: 章节序号
    """
    chapter_id = _resolve_chapter_id(novel_name, chapter_number)
    ke = json.dumps(key_events or [], ensure_ascii=False)
    ds = json.dumps(dimension_snapshot or {}, ensure_ascii=False)
    ci = characters_involved or []
    nf = new_foreshadows or []
    rf = resolved_foreshadows or []
    query(
        "INSERT INTO chapter_summaries (chapter_id, summary, key_events, characters_involved, "
        "new_foreshadows, resolved_foreshadows, dimension_snapshot) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s) "
        "ON CONFLICT (chapter_id) DO UPDATE SET "
        "summary = %s, key_events = %s, characters_involved = %s, "
        "new_foreshadows = %s, resolved_foreshadows = %s, dimension_snapshot = %s",
        (chapter_id, summary, ke, ci, nf, rf, ds,
         summary, ke, ci, nf, rf, ds),
        fetch="none"
    )
    return json.dumps({"ok": True}, ensure_ascii=False)


@mcp.tool
def chapter_get_context(novel_name: str, chapter_number: int) -> str:
    """获取写作上下文：前N章摘要 + 人物状态 + 未回收伏笔 + 世界观 + 章节大纲
      novel_name: 小说名称
    """
    novel_id = _resolve_novel_id(novel_name)

    result = {}

    ch = query("SELECT * FROM chapters WHERE novel_id = %s AND number = %s",
               (novel_id, chapter_number), fetch="one")
    if not ch:
        return json.dumps({"error": f"chapter {chapter_number} not found"}, ensure_ascii=False)
    result["chapter"] = dict(ch)

    prev = query(
        "SELECT cs.summary, cs.dimension_snapshot FROM chapter_summaries cs "
        "JOIN chapters c ON cs.chapter_id = c.id "
        "WHERE c.novel_id = %s AND c.number < %s ORDER BY c.number DESC LIMIT 3",
        (novel_id, chapter_number)
    )
    result["recent_summaries"] = [dict(r) for r in prev]

    chars = query("SELECT id, name, role, ability_level, status FROM characters "
                  "WHERE novel_id = %s AND is_active = TRUE", (novel_id,))
    result["active_characters"] = [dict(r) for r in chars]

    foreshadows = query(
        "SELECT id, description, planted_chapter_id FROM foreshadows "
        "WHERE novel_id = %s AND status = 'planted'", (novel_id,))
    result["unresolved_foreshadows"] = [dict(r) for r in foreshadows]

    world = query("SELECT category, name, data FROM world_settings WHERE novel_id = %s", (novel_id,))
    result["world_settings"] = [dict(r) for r in world]

    return json.dumps(result, ensure_ascii=False, default=str)


@mcp.tool
def chapter_plan_batch(novel_name: str, chapters_json: str = "[]") -> str:
    """批量规划章节（卷级大纲用，一次创建15-20章）。

    参数:
      novel_name: 小说名称
      chapters_json: 章节数组JSON，每项: {"number": 1, "title": "标题", "outline": "大纲", "chapter_type": "normal", "volume_number": 1}
    """
    novel_id = _resolve_novel_id(novel_name)

    chapters = json.loads(chapters_json)
    results = []
    for ch in chapters:
        vol = query("SELECT id FROM volumes WHERE novel_id=%s AND number=%s", (novel_id, ch.get("volume_number", 1)), fetch="one")
        vol_id = vol["id"] if vol else None
        r = query(
            "INSERT INTO chapters (novel_id, number, title, outline, chapter_type, volume_id) "
            "VALUES (%s, %s, %s, %s, %s, %s) "
            "ON CONFLICT (novel_id, number) DO UPDATE SET title=%s, outline=%s, chapter_type=%s, volume_id=%s, updated_at=NOW() "
            "RETURNING id",
            (novel_id, ch["number"], ch.get("title", ""), ch.get("outline", ""), ch.get("chapter_type", "normal"), vol_id,
             ch.get("title", ""), ch.get("outline", ""), ch.get("chapter_type", "normal"), vol_id),
            fetch="one"
        )
        results.append({"number": ch["number"], "id": r["id"]})
    return json.dumps({"ok": True, "created": len(results), "chapters": results}, ensure_ascii=False)


@mcp.tool
def chapter_update_metadata(novel_name: str, chapter_number: int,
                            summary: str = "", key_events: str = "[]",
                            characters_involved: str = "[]",
                            new_foreshadows: str = "[]",
                            resolved_foreshadows: str = "[]") -> str:
    """更新章节元数据（不重新校验正文）。修订后同步DB用。

    参数:
      novel_name: 小说名称
      chapter_number: 章节序号
      summary: 章节摘要
      key_events: 关键事件(JSON数组)
      characters_involved: 参与角色(JSON数组)
      new_foreshadows: 新埋伏笔(JSON数组)
      resolved_foreshadows: 已回收伏笔(JSON数组)
    """
    novel_id = _resolve_novel_id(novel_name)

    ch = query("SELECT id FROM chapters WHERE novel_id=%s AND number=%s", (novel_id, chapter_number), fetch="one")
    if not ch:
        return json.dumps({"error": f"章节 {chapter_number} 不存在"}, ensure_ascii=False)
    existing = query("SELECT chapter_id FROM chapter_summaries WHERE chapter_id=%s", (ch["id"],), fetch="one")
    if existing:
        sets = []
        vals = []
        if summary:
            sets.append("summary = %s")
            vals.append(summary)
        if key_events != "[]":
            sets.append("key_events = %s::jsonb")
            vals.append(key_events)
        if characters_involved != "[]":
            sets.append("characters_involved = %s::jsonb")
            vals.append(characters_involved)
        if new_foreshadows != "[]":
            sets.append("new_foreshadows = %s::jsonb")
            vals.append(new_foreshadows)
        if resolved_foreshadows != "[]":
            sets.append("resolved_foreshadows = %s::jsonb")
            vals.append(resolved_foreshadows)
        if sets:
            vals.append(ch["id"])
            query(f"UPDATE chapter_summaries SET {', '.join(sets)} WHERE chapter_id = %s", tuple(vals), fetch="none")
    else:
        query(
            "INSERT INTO chapter_summaries (chapter_id, summary, key_events, characters_involved, new_foreshadows, resolved_foreshadows) "
            "VALUES (%s, %s, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb)",
            (ch["id"], summary, key_events, characters_involved, new_foreshadows, resolved_foreshadows),
            fetch="none"
        )
    return json.dumps({"ok": True, "chapter_number": chapter_number}, ensure_ascii=False)


@mcp.tool
def scene_create(novel_name: str, chapter_number: int, scene_number: int,
                 location: str = "", characters_involved: list = None,
                 conflict: str = "", emotion_type: str = "",
                 key_beats: list = None, notes: str = "") -> str:
    """创建场景大纲
      novel_name: 小说名称
      chapter_number: 章节序号
    """
    chapter_id = _resolve_chapter_id(novel_name, chapter_number)
    kb = json.dumps(key_beats or [], ensure_ascii=False)
    ci = characters_involved or []
    query(
        "INSERT INTO scene_outlines (chapter_id, scene_number, location, characters_involved, "
        "conflict, emotion_type, key_beats, notes) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s) "
        "ON CONFLICT (chapter_id, scene_number) DO UPDATE SET "
        "location = %s, characters_involved = %s, conflict = %s, emotion_type = %s, "
        "key_beats = %s, notes = %s",
        (chapter_id, scene_number, location, ci,
         conflict, emotion_type, kb, notes,
         location, ci, conflict, emotion_type, kb, notes),
        fetch="none"
    )
    return json.dumps({"ok": True}, ensure_ascii=False)


@mcp.tool
def scene_list(novel_name: str, chapter_number: int) -> str:
    """列出章节的场景大纲
      novel_name: 小说名称
      chapter_number: 章节序号
    """
    chapter_id = _resolve_chapter_id(novel_name, chapter_number)
    rows = query("SELECT * FROM scene_outlines WHERE chapter_id = %s ORDER BY scene_number",
                 (chapter_id,))
    return json.dumps([dict(r) for r in rows], ensure_ascii=False, default=str)


@mcp.tool
def dimension_log(novel_name: str, chapter_id: int, dimension: str,
                  change_type: str, entity_name: str,
                  before_value: dict = None, after_value: dict = None,
                  description: str = "") -> str:
    """记录维度变更。dimension: time/space/ability/economy/character_status
      novel_name: 小说名称
    """
    novel_id = _resolve_novel_id(novel_name)

    bv = json.dumps(before_value or {}, ensure_ascii=False)
    av = json.dumps(after_value or {}, ensure_ascii=False)
    query(
        "INSERT INTO dimension_changes (novel_id, chapter_id, dimension, change_type, "
        "entity_name, before_value, after_value, description) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
        (novel_id, chapter_id, dimension, change_type, entity_name, bv, av, description),
        fetch="none"
    )
    return json.dumps({"ok": True}, ensure_ascii=False)


@mcp.tool
def dimension_query(novel_name: str, dimension: str = "", from_chapter: int = 0,
                    to_chapter: int = 99999) -> str:
    """查询维度变更记录
      novel_name: 小说名称
    """
    novel_id = _resolve_novel_id(novel_name)

    sql = (
        "SELECT dc.*, c.number as chapter_number FROM dimension_changes dc "
        "JOIN chapters c ON dc.chapter_id = c.id "
        "WHERE dc.novel_id = %s AND c.number BETWEEN %s AND %s"
    )
    params: list = [novel_id, from_chapter, to_chapter]
    if dimension:
        sql += " AND dc.dimension = %s"
        params.append(dimension)
    sql += " ORDER BY c.number, dc.id"
    rows = query(sql, tuple(params))
    return json.dumps([dict(r) for r in rows], ensure_ascii=False, default=str)


@mcp.tool
def timeline_add(novel_name: str, chapter_id: int, event_time: str,
                 event_order: int, event_description: str,
                 characters_involved: list = None,
                 location_id: int = None,
                 significance: str = "normal") -> str:
    """添加时间线事件
      novel_name: 小说名称
    """
    novel_id = _resolve_novel_id(novel_name)

    r = query(
        "INSERT INTO timeline_events (novel_id, chapter_id, event_time, event_order, "
        "event_description, characters_involved, location_id, significance) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id",
        (novel_id, chapter_id, event_time, event_order, event_description,
         characters_involved or [], location_id, significance), fetch="one"
    )
    return json.dumps({"ok": True, "id": r["id"]}, ensure_ascii=False)


@mcp.tool
def timeline_query(novel_name: str, from_chapter: int = 0, to_chapter: int = 99999) -> str:
    """查询时间线事件，可按章节范围过滤
      novel_name: 小说名称
    """
    novel_id = _resolve_novel_id(novel_name)
    rows = query(
        "SELECT te.*, c.number as chapter_number FROM timeline_events te "
        "JOIN chapters c ON te.chapter_id = c.id "
        "WHERE te.novel_id = %s AND c.number BETWEEN %s AND %s "
        "ORDER BY te.event_order",
        (novel_id, from_chapter, to_chapter)
    )
    return json.dumps([dict(r) for r in rows], ensure_ascii=False, default=str)
