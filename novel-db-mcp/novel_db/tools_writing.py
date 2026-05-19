import json
from pathlib import Path

from .db import mcp, query, PROJECT_ROOT
from .resolvers import _resolve_novel_id, _resolve_chapter_id
from .tools_chapter import _save_chapter_summary_internal
from .constraints import validate_chapter_text, _get_constraints, _enrichment_level
from .prompts import _build_event_checklist
from .sync import _record_db_hash


@mcp.tool
def rule_detail(rule_key: str) -> str:
    """查看某条创作原则的完整说明。从 writing-constraints.md 加载。"""
    c = _get_constraints()
    guidelines = c.get("guidelines", {})
    rule = guidelines.get(rule_key)
    if not rule:
        return json.dumps({"error": f"rule '{rule_key}' not found. 编辑 writing-constraints.md 添加"},
                           ensure_ascii=False)
    return json.dumps({"key": rule_key, "rule": rule.get("rule",""), "ref": rule.get("ref","")},
                       ensure_ascii=False)


@mcp.tool
def record_new_content(novel_name: str, content_type: str, name: str = "",
                        data: str = "", file_path: str = "") -> str:
    """记录写作中新出现的设定/物品/地点/NPC到DB。
    content_type: 'setting'|'item'|'location'|'npc'|'faction'
    name: 名称。为空时返回该类型的模板结构供填写
    data: JSON字符串，按模板字段填写。先调 record_new_content(novel_name="这次不一样了", 'item') 查看模板

    用法:
      # 查看模板
      record_new_content(novel_name="这次不一样了", 'item')
      # 保存数据
      record_new_content(novel_name="这次不一样了", 'item', '灵能短刀', '{"appearance":"...", "function":"..."}')
      novel_name: 小说名称
    """
    novel_id = _resolve_novel_id(novel_name)

    valid_types = ["setting", "item", "location", "npc", "faction"]
    if content_type not in valid_types:
        return json.dumps({"error": f"type must be one of {valid_types}"}, ensure_ascii=False)

    if not name:
        tmpl = query(
            "SELECT data FROM world_settings WHERE novel_id = %s AND category = 'template' AND name = %s",
            (novel_id, content_type), fetch="one"
        )
        if tmpl:
            return json.dumps({
                "template": tmpl["data"],
                "usage": f"填写后调 record_new_content(novel_name, '{content_type}', name, json_data)"
            }, ensure_ascii=False)
        return json.dumps({"template": f"no template for {content_type}, use generic description"}, ensure_ascii=False)

    parsed_data = {}
    if data:
        try:
            parsed_data = json.loads(data)
        except json.JSONDecodeError as e:
            return json.dumps({"error": f"invalid JSON data: {str(e)}"}, ensure_ascii=False)

    cat_map = {
        "setting": "core_setting",
        "item": "ability",
        "location": "location",
        "faction": "faction",
    }

    if content_type == "npc":
        existing = query(
            "SELECT id FROM characters WHERE novel_id = %s AND name = %s",
            (novel_id, name), fetch="one"
        )
        if existing:
            return json.dumps({"ok": True, "action": "already_exists", "id": existing["id"], "name": name}, ensure_ascii=False)
        desc = parsed_data.get("背景", parsed_data.get("notes", "")) if parsed_data else ""
        r = query(
            "INSERT INTO characters (novel_id, name, role, appearance, personality, speech_style, background, status) "
            "VALUES (%s, %s, 'npc', %s, %s, %s, %s, %s) RETURNING id",
            (novel_id, name,
             parsed_data.get("外观", {}).get("服饰", "") if isinstance(parsed_data.get("外观"), dict) else str(parsed_data.get("外观", "")),
             str(parsed_data.get("性格", {}).get("核心特质", "") if isinstance(parsed_data.get("性格"), dict) else parsed_data.get("性格", "")),
             str(parsed_data.get("性格", {}).get("说话风格", "") if isinstance(parsed_data.get("性格"), dict) else ""),
             str(parsed_data.get("背景", {}).get("出身", "") if isinstance(parsed_data.get("背景"), dict) else desc),
             json.dumps(parsed_data.get("当前状态", {}), ensure_ascii=False) if isinstance(parsed_data.get("当前状态"), dict) else "{}"),
            fetch="one"
        )
        char_id = r["id"] if r else None
        if parsed_data:
            query("""INSERT INTO world_settings (novel_id, category, name, data) VALUES (%s, 'character_detail', %s, %s)
                     ON CONFLICT (novel_id, category, name) DO UPDATE SET data = %s""",
                  (novel_id, f"npc_{name}", json.dumps(parsed_data, ensure_ascii=False),
                   json.dumps(parsed_data, ensure_ascii=False)), fetch="none")
        return json.dumps({"ok": True, "action": "created", "id": char_id, "type": "npc", "name": name}, ensure_ascii=False)
    else:
        cat = cat_map.get(content_type, "core_setting")
        store_data = parsed_data if parsed_data else {"content": data or name, "source": "chapter_writing"}
        if isinstance(store_data, dict):
            store_data["_name"] = name
        query(
            "INSERT INTO world_settings (novel_id, category, name, data) "
            "VALUES (%s, %s, %s, %s) ON CONFLICT (novel_id, category, name) DO UPDATE SET data = %s",
            (novel_id, cat, name, json.dumps(store_data, ensure_ascii=False),
             json.dumps(store_data, ensure_ascii=False)), fetch="none"
        )
        return json.dumps({"ok": True, "action": "saved", "type": content_type, "category": cat, "name": name}, ensure_ascii=False)


@mcp.tool
def event_checklist(novel_name: str, chapter_number: int) -> str:
    """获取本章事件清单+检查表。基于大纲自动解析，写前确认事件序列，写中逐项勾选。
      novel_name: 小说名称
      chapter_number: 章节序号
    """
    novel_id = _resolve_novel_id(novel_name)
    ch = query("SELECT * FROM chapters WHERE novel_id = %s AND number = %s",
               (novel_id, chapter_number), fetch="one")
    if not ch:
        return json.dumps({"error": "chapter not found"}, ensure_ascii=False)

    checklist = _build_event_checklist(dict(ch))

    result = {
        "chapter_id": ch["id"],
        "chapter_title": ch.get("title", ""),
        "chapter_number": ch.get("number", 0),
        "chapter_type": ch.get("chapter_type", "normal"),
        "full_outline": ch.get("outline", ""),
        "event_checklist": checklist,
        "usage": "写前确认事件序列→写中每完成一个勾选[✅]→写后确认全部覆盖→调writing_finish"
    }
    return json.dumps(result, ensure_ascii=False)


@mcp.tool
def validate_chapter(chapter_text: str) -> str:
    """校验正文是否满足硬约束。返回 violations + stats + enrichment（字数不足时的充实指引）。约束从 writing-constraints.md 加载。"""
    result = validate_chapter_text(chapter_text)
    stats = result.get("stats", {})
    wc = stats.get("word_count", 0)
    c = _get_constraints()
    hard_abs = c.get("hard_abs", {})
    min_words = hard_abs.get("word_count", {}).get("min", 0)
    if wc < min_words:
        result["enrichment"] = _enrichment_level(wc, min_words)
    return json.dumps(result, ensure_ascii=False)


@mcp.tool
def writing_finish(novel_name: str, chapter_number: int, summary: str, chapter_text: str,
                   key_events: list = None, characters_involved: list = None,
                   new_foreshadows: list = None, resolved_foreshadows: list = None,
                   ability_level: str = "", location: str = "",
                   timeline_events: list = None,
                   self_check: str = "") -> str:
    """写章后一键更新所有状态：先校验正文→再自检→通过后存摘要+维度+伏笔+时间线。校验或自检不通过会拒绝存盘。
    self_check: 必须传'passed'，表示正文自检已完成并全部通过。"""
    novel_id = _resolve_novel_id(novel_name)
    ch = query("SELECT id, novel_id, number FROM chapters WHERE novel_id=%s AND number=%s", (novel_id, chapter_number), fetch="one")
    if not ch:
        return json.dumps({"error": f"章节 {chapter_number} 不存在"}, ensure_ascii=False)
    chapter_id = ch["id"]

    validation = validate_chapter_text(chapter_text)
    if not validation["passed"]:
        err = {
            "ok": False,
            "error": "硬约束校验不通过，拒绝存盘",
            "violations": validation["violations"],
            "stats": validation["stats"],
        }
        stats = validation["stats"]
        wc = stats.get("word_count", 0)
        c = _get_constraints()
        hard_abs = c.get("hard_abs", {})
        min_words = hard_abs.get("word_count", {}).get("min", 0)
        if wc < min_words:
            err["enrichment"] = _enrichment_level(wc, min_words)
        return json.dumps(err, ensure_ascii=False)

    if self_check != "passed":
        return json.dumps({
            "ok": False,
            "error": "自检未完成，拒绝存盘",
            "hint": "调 chapter_self_check(chapter_text) → 逐项检查 → 修复 → 再调 writing_finish(self_check='passed')"
        }, ensure_ascii=False)

    ke = json.dumps(key_events or [], ensure_ascii=False)
    ds = {}
    if ability_level:
        ds["ability"] = ability_level
    if location:
        ds["location"] = location
    ds_json = json.dumps(ds, ensure_ascii=False)
    ci = characters_involved or []
    nf = new_foreshadows or []
    rf = resolved_foreshadows or []

    _save_chapter_summary_internal(chapter_id, summary, ke, ci, nf, rf, ds_json)

    query("UPDATE chapters SET status = 'written', updated_at = NOW() WHERE id = %s", (chapter_id,), fetch="none")

    for fid in (rf or []):
        _foreshadow_recall_internal(ch["novel_id"], fid, chapter_id)

    if ability_level:
        query(
            "INSERT INTO dimension_changes (novel_id, chapter_id, dimension, change_type, "
            "entity_name, after_value, description) VALUES (%s,%s,'ability','update','主角',%s,'等级变更')",
            (ch["novel_id"], chapter_id, json.dumps({"level": ability_level})),
            fetch="none"
        )
    if location:
        query(
            "INSERT INTO dimension_changes (novel_id, chapter_id, dimension, change_type, "
            "entity_name, after_value, description) VALUES (%s,%s,'space','move','主角',%s,'位置变更')",
            (ch["novel_id"], chapter_id, json.dumps({"location": location})),
            fetch="none"
        )

    for evt in (timeline_events or []):
        if isinstance(evt, dict) and evt.get("event_description"):
            query(
                "INSERT INTO timeline_events (novel_id, chapter_id, event_time, event_order, "
                "event_description, characters_involved) VALUES (%s,%s,%s,%s,%s,%s)",
                (ch["novel_id"], chapter_id,
                 evt.get("event_time", ""), evt.get("event_order", 0),
                 evt["event_description"], evt.get("characters_involved", [])),
                fetch="none"
            )

    stats = validation["stats"]
    query(
        "INSERT INTO chapter_quality (chapter_id, novel_id, "
        "em_dash_count, ellipsis_count, semicolon_count, exclamation_count, wave_count, "
        "negation_count, word_count, long_paragraphs, avg_punct_types_per_para, "
        "dialogue_breaks, banned_patterns, violations, passed) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
        "ON CONFLICT (chapter_id) DO UPDATE SET "
        "em_dash_count=%s, ellipsis_count=%s, semicolon_count=%s, exclamation_count=%s, wave_count=%s, "
        "negation_count=%s, word_count=%s, long_paragraphs=%s, avg_punct_types_per_para=%s, "
        "dialogue_breaks=%s, banned_patterns=%s, violations=%s, passed=%s",
        (chapter_id, ch["novel_id"],
         stats["em_dash_count"], stats["ellipsis_count"], stats["semicolon_count"],
         stats["exclamation_count"], stats["wave_count"],
         stats["negation_count"], stats["word_count"], stats["long_paragraphs"],
         stats["avg_punct_types_per_para"], stats["dialogue_breaks"],
         stats["banned_patterns"], json.dumps(validation["violations"]), validation["passed"],
         stats["em_dash_count"], stats["ellipsis_count"], stats["semicolon_count"],
         stats["exclamation_count"], stats["wave_count"],
         stats["negation_count"], stats["word_count"], stats["long_paragraphs"],
         stats["avg_punct_types_per_para"], stats["dialogue_breaks"],
         stats["banned_patterns"], json.dumps(validation["violations"]), validation["passed"]),
        fetch="none"
    )

    return json.dumps({
        "ok": True,
        "updated": ["summary", "status", "foreshadows", "dimensions", "timeline", "quality"],
        "quality": {"passed": True, "stats": stats},
        "warnings": validation.get("warnings", []),
        "post_save_checklist": {
            "新地点": "本章是否出现了新地点？→ record_new_content(novel_name, 'location', '地名', json_data)",
            "新NPC": "本章是否出现了新NPC？→ record_new_content(novel_name, 'npc', '人名', json_data)",
            "新物品": "本章是否出现了新物品？→ record_new_content(novel_name, 'item', '物品名', json_data)",
            "新设定": "本章是否有新增世界观设定？→ record_new_content(novel_name, 'setting', '设定名', json_data)",
            "新伏笔": "本章是否埋了新伏笔？→ foreshadow_plant(novel_name=\"这次不一样了\", '描述', importance, tags)",
            "角色变化": "本章是否有角色状态变化？→ character_update(novel_name, character_name, status=...)",
            "线索追踪": "本章是否有新线索出现？→ 记录到设定/大纲/线索追踪.md"
        }
    }, ensure_ascii=False)


@mcp.tool
def foreshadow_plant(novel_name: str, description: str,
                     planted_chapter_id: int = None,
                     planned_recall_chapter: int = None,
                     importance: str = "medium",
                     related_characters: list = None,
                     tags: list = None) -> str:
    """埋设伏笔
      novel_name: 小说名称
    """
    novel_id = _resolve_novel_id(novel_name)

    r = query(
        "INSERT INTO foreshadows (novel_id, description, planted_chapter_id, "
        "planned_recall_chapter, importance, related_characters, tags) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id",
        (novel_id, description, planted_chapter_id, planned_recall_chapter,
         importance, related_characters or [], tags or []), fetch="one"
    )
    _record_db_hash(novel_id, "foreshadow", str(r["id"]), json.dumps({"description": description, "importance": importance}, ensure_ascii=False))
    return json.dumps({"ok": True, "id": r["id"]}, ensure_ascii=False)


def _foreshadow_recall_internal(novel_id: int, foreshadow_id: int, chapter_id: int) -> dict:
    """Internal: recall a foreshadow (shared between writing_finish and foreshadow_recall tool)."""
    fs = query("SELECT id FROM foreshadows WHERE id=%s AND novel_id=%s", (foreshadow_id, novel_id), fetch="one")
    if not fs:
        return {"ok": False, "error": f"伏笔 {foreshadow_id} 不存在或不属于该项目"}
    query(
        "UPDATE foreshadows SET status = 'recalled', actual_recall_chapter_id = %s, updated_at = NOW() "
        "WHERE id = %s", (chapter_id, foreshadow_id),
        fetch="none"
    )
    return {"ok": True}


@mcp.tool
def foreshadow_recall(novel_name: str, foreshadow_id: int, actual_recall_chapter_id: int) -> str:
    """回收伏笔。
      novel_name: 小说名称（验证归属）
      foreshadow_id: 伏笔ID
      actual_recall_chapter_id: 实际回收章节ID
    """
    novel_id = _resolve_novel_id(novel_name)
    result = _foreshadow_recall_internal(novel_id, foreshadow_id, actual_recall_chapter_id)
    return json.dumps(result, ensure_ascii=False)


@mcp.tool
def foreshadow_list(novel_name: str, status: str = "") -> str:
    """列出伏笔。status 可选: planted/recalled/abandoned
      novel_name: 小说名称
    """
    novel_id = _resolve_novel_id(novel_name)

    if status:
        rows = query("SELECT * FROM foreshadows WHERE novel_id = %s AND status = %s ORDER BY id",
                     (novel_id, status))
    else:
        rows = query("SELECT * FROM foreshadows WHERE novel_id = %s ORDER BY id", (novel_id,))
    return json.dumps([dict(r) for r in rows], ensure_ascii=False, default=str)


@mcp.tool
def foreshadow_update(novel_name: str, foreshadow_id: int,
                      description: str = "", importance: str = "",
                      planned_recall_chapter: int = 0,
                      related_characters: list = None,
                      tags: list = None,
                      status: str = "", reason: str = "") -> str:
    """更新伏笔（只传需要修改的字段，空值会被忽略）。可修改描述、重要性、计划回收章、状态等。
      novel_name: 小说名称
      foreshadow_id: 伏笔ID
      description: 新描述
      importance: high/medium/low
      planned_recall_chapter: 计划回收章节号（传0表示清除）
      related_characters: 相关角色ID列表
      tags: 标签列表
      status: 状态变更（planted/recalled/abandoned）。传空=不变
      reason: 放弃/回收原因（仅 status=abandoned/recalled 时记录）
    """
    novel_id = _resolve_novel_id(novel_name)
    fs = query("SELECT id FROM foreshadows WHERE id=%s AND novel_id=%s",
               (foreshadow_id, novel_id), fetch="one")
    if not fs:
        return json.dumps({"error": f"伏笔 {foreshadow_id} 不存在"}, ensure_ascii=False)

    fields = {}
    if description:
        fields["description"] = description
    if importance:
        fields["importance"] = importance
    if planned_recall_chapter != 0:
        fields["planned_recall_chapter"] = planned_recall_chapter
    if related_characters is not None:
        fields["related_characters"] = json.dumps(related_characters, ensure_ascii=False)
    if tags is not None:
        fields["tags"] = json.dumps(tags, ensure_ascii=False)
    if status:
        fields["status"] = status

    if not fields:
        return json.dumps({"ok": False, "error": "no fields to update"}, ensure_ascii=False)

    sets = [f"{k} = %s" for k in fields]
    vals = list(fields.values()) + [foreshadow_id]
    query(f"UPDATE foreshadows SET {', '.join(sets)}, updated_at = NOW() WHERE id = %s",
          tuple(vals), fetch="none")
    _record_db_hash(novel_id, "foreshadow", str(foreshadow_id), json.dumps(fields, ensure_ascii=False))
    return json.dumps({"ok": True, "foreshadow_id": foreshadow_id, "updated_fields": list(fields.keys()), "reason": reason},
                      ensure_ascii=False)


# ─── Echoes（回响 — 大事件余波的自然回溯）──────────────────


@mcp.tool
def echo_create(novel_name: str, source_chapter_id: int, echo_chapter_id: int,
                source_event: str, echo_type: str,
                echo_description: str = "", strong_related: bool = False,
                tags: list = None) -> str:
    """创建回响记录。回响是大事件后在日常场景中自然回溯的人/物/地点/梗。
      密度规则：普通回响≤2次/卷，强相关不限，跨卷≤1次/间隔。
      融入方式：必须融入世界呼吸或角色日常动作，不能是独立段落。

      参数:
        novel_name: 小说名称
        source_chapter_id: 原始事件发生章节ID（被回溯的源）
        echo_chapter_id: 回响出现章节ID
        source_event: 被回溯的原始事件/人/物品/地点/梗（一句话描述）
        echo_type: 回响类型 — character_habit/physical_trace/catchphrase/location_change/item/memory
        echo_description: 回响的具体写法（一句话，如"沈野翻背包碰到缺角铁壶，停了一下"）
        strong_related: 是否强相关（True=不受密度限制，如角色死亡影响后续所有资源分配场景）
        tags: 标签列表
    """
    novel_id = _resolve_novel_id(novel_name)

    # Resolve volume_id from echo_chapter
    vol_id = None
    ch = query("SELECT volume_id FROM chapters WHERE id = %s AND novel_id = %s",
               (echo_chapter_id, novel_id), fetch="one")
    if ch:
        vol_id = ch.get("volume_id")

    r = query(
        "INSERT INTO echoes (novel_id, source_chapter_id, echo_chapter_id, volume_id, "
        "source_event, echo_type, echo_description, strong_related, tags) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id",
        (novel_id, source_chapter_id, echo_chapter_id, vol_id,
         source_event, echo_type, echo_description,
         1 if strong_related else 0,
         tags or []), fetch="one"
    )
    _record_db_hash(novel_id, "echo", str(r["id"]),
                    json.dumps({"source_event": source_event, "echo_type": echo_type}, ensure_ascii=False))
    return json.dumps({"ok": True, "id": r["id"]}, ensure_ascii=False)


@mcp.tool
def echo_list(novel_name: str, volume_id: int = 0, echo_chapter_id: int = 0) -> str:
    """列出回响记录。可按卷或章节过滤，用于检查密度是否超标（普通回响≤2次/卷）。
      novel_name: 小说名称
      volume_id: 按卷过滤（0=全部）
      echo_chapter_id: 按回响出现章节过滤（0=全部）
    """
    novel_id = _resolve_novel_id(novel_name)

    if volume_id:
        rows = query("SELECT e.*, c1.number as source_ch, c2.number as echo_ch "
                     "FROM echoes e "
                     "LEFT JOIN chapters c1 ON e.source_chapter_id = c1.id "
                     "LEFT JOIN chapters c2 ON e.echo_chapter_id = c2.id "
                     "WHERE e.novel_id = %s AND e.volume_id = %s ORDER BY e.id",
                     (novel_id, volume_id))
    elif echo_chapter_id:
        rows = query("SELECT e.*, c1.number as source_ch, c2.number as echo_ch "
                     "FROM echoes e "
                     "LEFT JOIN chapters c1 ON e.source_chapter_id = c1.id "
                     "LEFT JOIN chapters c2 ON e.echo_chapter_id = c2.id "
                     "WHERE e.novel_id = %s AND e.echo_chapter_id = %s ORDER BY e.id",
                     (novel_id, echo_chapter_id))
    else:
        rows = query("SELECT e.*, c1.number as source_ch, c2.number as echo_ch "
                     "FROM echoes e "
                     "LEFT JOIN chapters c1 ON e.source_chapter_id = c1.id "
                     "LEFT JOIN chapters c2 ON e.echo_chapter_id = c2.id "
                     "WHERE e.novel_id = %s ORDER BY e.id", (novel_id,))

    # Density check: count non-strong echoes per volume
    density_warn = []
    if not volume_id:
        vol_counts = query(
            "SELECT e.volume_id, COUNT(*) as cnt FROM echoes e "
            "WHERE e.novel_id = %s AND e.strong_related = 0 AND e.volume_id IS NOT NULL "
            "GROUP BY e.volume_id", (novel_id,))
        for vc in vol_counts:
            if vc["cnt"] > 2:
                density_warn.append(f"V{vc['volume_id']}有{vc['cnt']}次普通回响（上限2次）")

    result = {
        "echoes": [dict(r) for r in rows],
        "density_warnings": density_warn
    }
    return json.dumps(result, ensure_ascii=False, default=str)


@mcp.tool
def echo_density_check(novel_name: str, volume_id: int) -> str:
    """检查某卷的回响密度。返回普通回响/强相关回响/跨卷回响的数量和具体列表。
      novel_name: 小说名称
      volume_id: 要检查的卷ID
    """
    novel_id = _resolve_novel_id(novel_name)

    normal = query(
        "SELECT e.*, c1.number as source_ch, c2.number as echo_ch "
        "FROM echoes e "
        "LEFT JOIN chapters c1 ON e.source_chapter_id = c1.id "
        "LEFT JOIN chapters c2 ON e.echo_chapter_id = c2.id "
        "WHERE e.novel_id = %s AND e.volume_id = %s AND e.strong_related = 0 "
        "ORDER BY e.id",
        (novel_id, volume_id))

    strong = query(
        "SELECT e.*, c1.number as source_ch, c2.number as echo_ch "
        "FROM echoes e "
        "LEFT JOIN chapters c1 ON e.source_chapter_id = c1.id "
        "LEFT JOIN chapters c2 ON e.echo_chapter_id = c2.id "
        "WHERE e.novel_id = %s AND e.volume_id = %s AND e.strong_related = 1 "
        "ORDER BY e.id",
        (novel_id, volume_id))

    # Cross-volume echoes: source from different volume
    cross_vol = query(
        "SELECT e.*, c1.number as source_ch, c2.number as echo_ch, "
        "cv.number as source_vol "
        "FROM echoes e "
        "LEFT JOIN chapters c1 ON e.source_chapter_id = c1.id "
        "LEFT JOIN chapters c2 ON e.echo_chapter_id = c2.id "
        "LEFT JOIN chapters cv ON e.source_chapter_id = cv.id "
        "LEFT JOIN volumes v ON cv.volume_id = v.id "
        "WHERE e.novel_id = %s AND e.volume_id = %s "
        "AND cv.volume_id != %s "
        "ORDER BY e.id",
        (novel_id, volume_id, volume_id))

    exceeded = len(normal) > 2
    return json.dumps({
        "volume_id": volume_id,
        "normal_echoes": {"count": len(normal), "limit": 2, "exceeded": exceeded,
                         "items": [dict(r) for r in normal]},
        "strong_echoes": {"count": len(strong), "limit": "unlimited",
                          "items": [dict(r) for r in strong]},
        "cross_volume_echoes": {"count": len(cross_vol), "limit": 1,
                                "items": [dict(r) for r in cross_vol]},
        "status": "exceeded" if exceeded else "ok"
    }, ensure_ascii=False, default=str)


# ──────────────────────────────────────────
# ENGINE_MATRIX: 场面类型 → 引擎映射表
# 硬编码在编排器层，不交给模型选——防偷懒/错选。
# 新增引擎 → 先放 engines/*.md，再加一行映射。无其他配置。
# ──────────────────────────────────────────

ENGINE_MATRIX: dict[str, list[str]] = {
    "_always": [
        "author-voice",
        "anti-ai-quickref",
        "writing-style",
        "world-element-registry",
    ],
    "atmosphere": ["environment"],
    "dialogue": ["dialogue"],
    "battle": ["action", "battle", "author-voice-battle"],
    "emotion": ["author-voice-emotion"],
    "daily": ["author-voice-daily"],
    "mystery": ["author-voice-mystery"],
    "item_use": ["item"],
    "multi_char": ["scene-composition"],
    "deepening": ["scene-deepening"],
}


@mcp.tool
def resolve_engines(scene_types: list[str]) -> str:
    """根据 Agent 3 标注的场面 AES 类型，自动解析需加载的引擎文件内容。

    编排器在收到 Agent 3 的场面类型标签后调用此工具。
    返回所有匹配引擎的完整内容（_always 引擎始终包含）。
    Agent 3 不再负责读文件——只标类型，编排器自动 resolve。

    参数:
      scene_types: 场面类型列表，由 Agent 3 从 AES 标签提取。
                   如 ["atmosphere", "dialogue"] 或 Agent 3 输出的原始标签。

    用法:
      resolve_engines(["atmosphere", "dialogue"])
      resolve_engines(["battle", "emotion", "daily"])

    返回:
      JSON 对象，key=引擎名，value=引擎文件完整内容
    """
    # 收集需加载的引擎名（去重+保持顺序）
    seen: set[str] = set()
    ordered: list[str] = []

    def _add(names: list[str]) -> None:
        for n in names:
            if n not in seen:
                seen.add(n)
                ordered.append(n)

    _add(ENGINE_MATRIX.get("_always", []))
    for st in scene_types:
        key = st.removeprefix("AES:").strip()
        _add(ENGINE_MATRIX.get(key, []))

    # 读取引擎文件
    engine_dir = Path(PROJECT_ROOT) / ".claude" / "skills" / "engines"
    result: dict[str, str] = {}
    missing: list[str] = []

    for eng in ordered:
        fp = engine_dir / f"{eng}.md"
        if fp.exists():
            result[eng] = fp.read_text(encoding="utf-8")
        else:
            result[eng] = f"[engine file not found: {eng}.md]"
            missing.append(eng)

    payload = {"engines": result, "scene_types": scene_types}
    if missing:
        payload["missing"] = missing

    return json.dumps(payload, ensure_ascii=False)


