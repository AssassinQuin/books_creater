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
def chapter_get_context(novel_name: str, chapter_number: int,
                        load_mode: str = "smart",
                        regions: str = "", faction_names: str = "",
                        categories: str = "") -> str:
    """获取写作上下文：前N章摘要 + 人物状态 + 未回收伏笔 + 世界观（分层加载）+ 章节大纲
    
    加载模式(load_mode):
      - "smart"(默认): 根据章节所属卷级自动推断需要加载的地区和势力，只加载相关设定
      - "volume": 按卷级过滤世界观，加载当前卷相关的设定
      - "targeted": 按 regions/faction_names/categories 参数精准加载
      - "full": 加载全部世界观(仅在需要时使用，数据量大时慎用)
    
    参数:
      novel_name: 小说名称
      chapter_number: 章节序号
      load_mode: 加载模式(smart/volume/targeted/full)
      regions: 逗号分隔地区(仅targeted模式生效，如'外围,北境')
      faction_names: 逗号分隔势力名(仅targeted模式)
      categories: 逗号分隔类别(仅targeted模式，如'ability,location')
    """
    novel_id = _resolve_novel_id(novel_name)

    result = {}

    ch = query("SELECT * FROM chapters WHERE novel_id = %s AND number = %s",
               (novel_id, chapter_number), fetch="one")
    if not ch:
        return json.dumps({"error": f"chapter {chapter_number} not found"}, ensure_ascii=False)
    result["chapter"] = dict(ch)

    # Determine volume from chapter's volume_id
    volume_str = ""
    if ch.get("volume_id"):
        vol = query("SELECT number FROM volumes WHERE id = %s", (ch["volume_id"],), fetch="one")
        if vol:
            volume_str = f"V{vol['number']}"
    
    # Recent chapter summaries
    prev = query(
        "SELECT cs.summary, cs.dimension_snapshot FROM chapter_summaries cs "
        "JOIN chapters c ON cs.chapter_id = c.id "
        "WHERE c.novel_id = %s AND c.number < %s ORDER BY c.number DESC LIMIT 3",
        (novel_id, chapter_number)
    )
    result["recent_summaries"] = [dict(r) for r in prev]

    # Active characters (filtered by volume appearance when possible)
    chars = query("SELECT id, name, role, ability_level, status FROM characters "
                  "WHERE novel_id = %s AND is_active = TRUE", (novel_id,))
    result["active_characters"] = [dict(r) for r in chars]

    # Unresolved foreshadows
    foreshadows = query(
        "SELECT id, description, planted_chapter_id FROM foreshadows "
        "WHERE novel_id = %s AND status = 'planted'", (novel_id,))
    result["unresolved_foreshadows"] = [dict(r) for r in foreshadows]

    # ── World Settings: Layered Loading ──
    if load_mode == "full":
        # Load everything (legacy behavior)
        world = query("SELECT category, name, data, region, volume_range, faction_id FROM world_settings WHERE novel_id = %s AND status = 'active'", (novel_id,))
        result["world_settings"] = [dict(r) for r in world]
        result["_load_info"] = {"mode": "full", "count": len(world), "warning": "full模式加载全部设定，数据量大"}
    else:
        # Use smart/volume/targeted loading via world_load_context logic
        _load_world_context(result, novel_id, volume_str, load_mode, regions, faction_names, categories)

    return json.dumps(result, ensure_ascii=False, default=str)


def _load_world_context(result: dict, novel_id: int, volume_str: str,
                         load_mode: str, regions: str, faction_names: str, categories: str):
    """Internal: layered world context loading for chapter_get_context."""
    
    # Smart mode: infer regions and factions from volume
    if load_mode == "smart" and volume_str:
        vol_num = int(volume_str.replace("V", "")) if volume_str.startswith("V") else 0
        
        # Volume-to-region-faction mapping (based on the story outline)
        vol_mapping = {
            1: {"regions": "外围,北境", "factions": "壁盾军团"},
            2: {"regions": "外围,中域", "factions": "壁盾军团,灵枢"},
            3: {"regions": "外围,北境", "factions": "壁盾军团"},
            4: {"regions": "中域,内城", "factions": "灵枢"},
            5: {"regions": "中域,全域", "factions": "星火社,教会"},
            6: {"regions": "全域", "factions": "壁盾军团,灵枢,教会"},
            7: {"regions": "全域", "factions": "灵枢,星火社"},
            8: {"regions": "全域", "factions": "灵枢,教会"},
            9: {"regions": "全域", "factions": "灵枢,教会,壁盾军团"},
            10: {"regions": "全域", "factions": "裔族,教会"},
            11: {"regions": "内城,全域", "factions": "灵枢"},
            12: {"regions": "全域", "factions": "教会,裔族"},
            13: {"regions": "全域", "factions": "灵枢,教会"},
            14: {"regions": "全域", "factions": "壁盾军团,灵枢,教会,裔族"},
            15: {"regions": "全域", "factions": ""},
        }
        
        mapping = vol_mapping.get(vol_num, {"regions": "全域", "factions": ""})
        regions = mapping["regions"]
        faction_names = mapping["factions"]
    elif load_mode == "volume":
        # Just filter by volume, no region/faction inference
        regions = ""
        faction_names = ""
    
    # Build query
    conditions = ["novel_id = %s", "status = 'active'"]
    params = [novel_id]
    
    region_list = [r.strip() for r in regions.split(',') if r.strip()] if regions else []
    faction_name_list = [f.strip() for f in faction_names.split(',') if f.strip()] if faction_names else []
    category_list = [c.strip() for c in categories.split(',') if c.strip()] if categories else []
    
    # Resolve faction names to IDs
    faction_ids = []
    if faction_name_list:
        for fn in faction_name_list:
            frow = query(
                "SELECT id FROM world_settings WHERE novel_id = %s AND category = 'faction' AND name = %s",
                (novel_id, fn), fetch="one"
            )
            if frow:
                faction_ids.append(frow["id"])
    
    # Category filter
    if category_list:
        cat_placeholders = ", ".join(["%s"] * len(category_list))
        conditions.append(f"category IN ({cat_placeholders})")
        params.extend(category_list)
    
    # Region filter
    if region_list:
        region_placeholders = ", ".join(["%s"] * (len(region_list) + 1))
        conditions.append(f"(region IN ({region_placeholders}))")
        params.extend(region_list + ['全域'])
    
    # Faction filter
    if faction_ids:
        fid_placeholders = ", ".join(["%s"] * (len(faction_ids) + 1))
        conditions.append(f"(faction_id IN ({fid_placeholders}) OR faction_id IS NULL)")
        params.extend(faction_ids + [0])
    
    where = " AND ".join(conditions)
    rows = query(f"SELECT category, name, data, region, volume_range, faction_id FROM world_settings WHERE {where} ORDER BY priority DESC, category, name", tuple(params))
    
    # Volume range filtering
    vol_num = int(volume_str.replace("V", "")) if volume_str.startswith("V") else None
    if vol_num is not None:
        from .tools_world import _volume_in_range
        # Always include constants
        constant_rows = [r for r in rows if r.get("is_constant")]
        non_constant = [r for r in rows if not r.get("is_constant")]
        volume_matched = [r for r in non_constant if _volume_in_range(vol_num, r.get("volume_range", ""))]
        result_rows = constant_rows + volume_matched
    else:
        result_rows = list(rows)
    
    result["world_settings"] = [dict(r) for r in result_rows]
    result["_load_info"] = {
        "mode": load_mode,
        "volume": volume_str,
        "regions": region_list or "all",
        "factions": faction_name_list or "all",
        "categories": category_list or "all",
        "count": len(result_rows),
        "total_available": len(list(rows)),
    }


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


@mcp.tool
def scene_update(novel_name: str, chapter_number: int, scene_number: int,
                 location: str = "", characters_involved: list = None,
                 conflict: str = "", emotion_type: str = "",
                 key_beats: list = None, notes: str = "") -> str:
    """更新场景大纲（只传需要修改的字段，空值会被忽略）
      novel_name: 小说名称
      chapter_number: 章节序号
      scene_number: 场景序号
    """
    chapter_id = _resolve_chapter_id(novel_name, chapter_number)
    fields = {}
    if location:
        fields["location"] = location
    if characters_involved is not None:
        fields["characters_involved"] = characters_involved
    if conflict:
        fields["conflict"] = conflict
    if emotion_type:
        fields["emotion_type"] = emotion_type
    if key_beats is not None:
        fields["key_beats"] = json.dumps(key_beats, ensure_ascii=False)
    if notes:
        fields["notes"] = notes
    if not fields:
        return json.dumps({"ok": False, "error": "no fields to update"}, ensure_ascii=False)
    sets = [f"{k} = %s" for k in fields]
    vals = list(fields.values()) + [chapter_id, scene_number]
    query(
        f"UPDATE scene_outlines SET {', '.join(sets)} WHERE chapter_id = %s AND scene_number = %s",
        tuple(vals), fetch="none"
    )
    return json.dumps({"ok": True}, ensure_ascii=False)


@mcp.tool
def scene_delete(novel_name: str, chapter_number: int, scene_number: int) -> str:
    """删除场景大纲
      novel_name: 小说名称
      chapter_number: 章节序号
      scene_number: 场景序号
    """
    chapter_id = _resolve_chapter_id(novel_name, chapter_number)
    query("DELETE FROM scene_outlines WHERE chapter_id = %s AND scene_number = %s",
          (chapter_id, scene_number), fetch="none")
    return json.dumps({"ok": True}, ensure_ascii=False)


@mcp.tool
def timeline_update(novel_name: str, event_id: int,
                    event_description: str = "", event_time: str = "",
                    characters_involved: list = None,
                    significance: str = "") -> str:
    """更新时间线事件（只传需要修改的字段）
      novel_name: 小说名称
      event_id: 时间线事件ID
    """
    _resolve_novel_id(novel_name)
    fields = {}
    if event_description:
        fields["event_description"] = event_description
    if event_time:
        fields["event_time"] = event_time
    if characters_involved is not None:
        fields["characters_involved"] = characters_involved
    if significance:
        fields["significance"] = significance
    if not fields:
        return json.dumps({"ok": False, "error": "no fields to update"}, ensure_ascii=False)
    sets = [f"{k} = %s" for k in fields]
    vals = list(fields.values()) + [event_id]
    query(f"UPDATE timeline_events SET {', '.join(sets)} WHERE id = %s",
          tuple(vals), fetch="none")
    return json.dumps({"ok": True}, ensure_ascii=False)


@mcp.tool
def timeline_delete(novel_name: str, event_id: int) -> str:
    """删除时间线事件
      novel_name: 小说名称
      event_id: 时间线事件ID
    """
    _resolve_novel_id(novel_name)
    query("DELETE FROM timeline_events WHERE id = %s", (event_id,), fetch="none")
    return json.dumps({"ok": True}, ensure_ascii=False)
