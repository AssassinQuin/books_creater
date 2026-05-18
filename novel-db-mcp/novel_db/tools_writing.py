import json

from .db import mcp, query
from .resolvers import _resolve_novel_id, _resolve_chapter_id
from .constraints import validate_chapter_text, _get_constraints, _enrichment_level
from .prompts import _build_writing_prompt, _build_event_checklist, _get_quality_history
from .sync import _record_db_hash


@mcp.tool
def writing_start(novel_name: str, chapter_number: int) -> str:
    """写章前一键注入上下文：章节信息+前3章摘要+活跃人物索引+未回收伏笔+当前卷规划+硬约束+质量历史。
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

    chars = query("SELECT id, name, role FROM characters "
                  "WHERE novel_id = %s AND is_active = TRUE", (novel_id,))
    result["active_characters"] = [dict(r) for r in chars]

    foreshadows = query(
        "SELECT id, description, planted_chapter_id, importance FROM foreshadows "
        "WHERE novel_id = %s AND status = 'planted' ORDER BY id", (novel_id,))
    result["unresolved_foreshadows"] = [dict(r) for r in foreshadows]

    world = query("SELECT category, name FROM world_settings WHERE novel_id = %s", (novel_id,))
    result["world_settings_index"] = [dict(r) for r in world]

    if ch.get("volume_id"):
        vol = query("SELECT * FROM volumes WHERE id = %s", (ch["volume_id"],), fetch="one")
        if vol:
            result["current_volume"] = dict(vol)

    quality_history = _get_quality_history(novel_id, chapter_number)
    result["quality_history"] = quality_history

    result["writing_prompt"] = _build_writing_prompt(
        ch=result["chapter"],
        summaries=result["recent_summaries"],
        chars=result["active_characters"],
        foreshadows=result["unresolved_foreshadows"],
        world_index=result["world_settings_index"],
        vol=result.get("current_volume", {}),
        quality_history=quality_history,
    )

    return json.dumps(result, ensure_ascii=False, default=str)


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
def chapter_self_check(chapter_text: str, self_report: str = "") -> str:
    """写后自检工具。12项语义检查（刀锋技法/质量方差/废笔配额/角色失控/饱和度不均/留白不点破/节奏断层/AI指纹/叙事意识/人物鲜活/世界观植入/NPC出场）。
    
    用法：
      1. chapter_self_check(chapter_text) → 返回12项检查表
      2. 逐项检查后，调 chapter_self_check(chapter_text, '{"结果": {...}}')
      3. writing_finish 需要传 self_check='passed' 才能存盘
    """
    CHECKLIST = {
        "刀锋技法": {
            "标准": "至少1种:沉默暴击/暴力插入/不回头/尺度崩塌/反高潮/情绪断层/悬而未决。使用后禁解释/升华/自我剖析。",
            "结果": "待检查",
            "说明": ""
        },
        "质量方差": {
            "标准": "2-3个粗糙段/章(无感官/无比喻/纯动作)，相邻段落质量差≥20分。连续精写≤3段。",
            "结果": "待检查",
            "说明": ""
        },
        "废笔配额": {
            "标准": "≥3种废笔/章(角色废话/环境废笔/生活碎片/假伏笔/跑题对话)，真废笔和废线按需使用。",
            "结果": "待检查",
            "说明": ""
        },
        "角色失控": {
            "标准": "1+次/章角色'不对'(说蠢话/情绪过头/跑题/不理性决定)，不是OOC。",
            "结果": "待检查",
            "说明": ""
        },
        "饱和度不均": {
            "标准": "主角超饱和，NPC极简(1个特征反复用)，路人透明。不撒匀。",
            "结果": "待检查",
            "说明": ""
        },
        "留白不点破": {
            "标准": "禁金句总结/升华。主题通过人物行为传达，不用叙事者评论。不解释情感。",
            "结果": "待检查",
            "说明": ""
        },
        "节奏断层": {
            "标准": "1+处/章节奏真的断了(突然加速/停滞/切走/时间塌缩)。",
            "结果": "待检查",
            "说明": ""
        },
        "AI指纹": {
            "标准": "FP-1句号切割法/FP-2解释式展示/FP-3结构对称/FP-4否定转折模式化。≤1处。",
            "结果": "待检查",
            "说明": ""
        },
        "叙事意识": {
            "标准": "焦点(主角>NPC>路人) / 爆炸点(大纲事件章必炸) / 真废笔+废线穿插。",
            "结果": "待检查",
            "说明": ""
        },
        "人物鲜活": {
            "标准": "微动作/微表情代替直白情绪词('紧张'→手指敲桌面)。禁'不舍''难过''留恋'。",
            "结果": "待检查",
            "说明": ""
        },
        "世界观植入": {
            "标准": "≥3个元素自然融入(通过动作/对话/环境展现，非科普)。",
            "结果": "待检查",
            "说明": ""
        },
        "NPC出场": {
            "标准": "≥2个有动机的NPC出现(不止当工具人，有独立的行为逻辑)。",
            "结果": "待检查",
            "说明": ""
        }
    }

    if not self_report:
        return json.dumps({
            "checklist": CHECKLIST,
            "instruction": "逐项检查后，调 chapter_self_check(text, '{\"结果\":{\"刀锋技法\":\"✅\",\"质量方差\":\"⚠\",...}}')",
            "禁止存盘": "12项全部标注✅或⚠后方可调writing_finish(self_check='passed')"
        }, ensure_ascii=False)

    try:
        report = json.loads(self_report)
    except json.JSONDecodeError:
        return json.dumps({"error": "无效JSON格式"}, ensure_ascii=False)

    results = report.get("结果", report.get("results", {}))
    if not results:
        return json.dumps({"error": "缺少'结果'字段"}, ensure_ascii=False)

    passed = 0
    failed = 0
    detail = []
    for key, item in CHECKLIST.items():
        r = results.get(key, "待检查")
        desc = results.get(f"{key}_说明", "")
        if r == "✅":
            passed += 1
        elif r == "⚠":
            passed += 1
        else:
            failed += 1
        detail.append(f"{key}: {r}" + (f" - {desc}" if desc else ""))

    ok = failed == 0
    return json.dumps({
        "self_check_passed": ok,
        "summary": f"✅ {passed}项通过 / ❌ {failed}项不通过",
        "detail": detail,
        "提示": "通过后调 writing_finish(self_check='passed') 存盘" if ok else "修复后重新调 chapter_self_check"
    }, ensure_ascii=False)


@mcp.tool
def writing_finish(novel_name: str, chapter_number: int, summary: str, chapter_text: str,
                   key_events: list = None, characters_involved: list = None,
                   new_foreshadows: list = None, resolved_foreshadows: list = None,
                   ability_level: str = "", location: str = "",
                   timeline_events: list = None,
                   self_check: str = "") -> str:
    """写章后一键更新所有状态：先校验正文→再自检→通过后存摘要+维度+伏笔+时间线。校验或自检不通过会拒绝存盘。
    self_check: 必须传'passed'，表示 chapter_self_check 已完成并全部通过。"""
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

    query(
        "INSERT INTO chapter_summaries (chapter_id, summary, key_events, characters_involved, "
        "new_foreshadows, resolved_foreshadows, dimension_snapshot) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s) "
        "ON CONFLICT (chapter_id) DO UPDATE SET "
        "summary = %s, key_events = %s, characters_involved = %s, "
        "new_foreshadows = %s, resolved_foreshadows = %s, dimension_snapshot = %s",
        (chapter_id, summary, ke, ci, nf, rf, ds_json,
         summary, ke, ci, nf, rf, ds_json),
        fetch="none"
    )

    query("UPDATE chapters SET status = 'written', updated_at = NOW() WHERE id = %s", (chapter_id,), fetch="none")

    for fid in (rf or []):
        query("UPDATE foreshadows SET status = 'recalled', actual_recall_chapter_id = %s, "
               "updated_at = NOW() WHERE id = %s", (chapter_id, fid), fetch="none")

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


@mcp.tool
def foreshadow_recall(novel_name: str, foreshadow_id: int, actual_recall_chapter_id: int) -> str:
    """回收伏笔。
      novel_name: 小说名称（验证归属）
      foreshadow_id: 伏笔ID
      actual_recall_chapter_id: 实际回收章节ID
    """
    novel_id = _resolve_novel_id(novel_name)
    fs = query("SELECT id FROM foreshadows WHERE id=%s AND novel_id=%s", (foreshadow_id, novel_id), fetch="one")
    if not fs:
        return json.dumps({"error": f"伏笔 {foreshadow_id} 不存在或不属于该小说"}, ensure_ascii=False)
    query(
        "UPDATE foreshadows SET status = 'recalled', actual_recall_chapter_id = %s, updated_at = NOW() "
        "WHERE id = %s", (actual_recall_chapter_id, foreshadow_id),
        fetch="none"
    )
    return json.dumps({"ok": True}, ensure_ascii=False)


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
def foreshadow_abandon(novel_name: str, foreshadow_id: int, reason: str = "") -> str:
    """放弃伏笔（不可逆）。百万字长篇中必然有放弃的伏笔。

    参数:
      novel_name: 小说名称
      foreshadow_id: 伏笔ID
      reason: 放弃原因
    """
    novel_id = _resolve_novel_id(novel_name)

    fs = query("SELECT id FROM foreshadows WHERE id=%s AND novel_id=%s", (foreshadow_id, novel_id), fetch="one")
    if not fs:
        return json.dumps({"error": f"伏笔 {foreshadow_id} 不存在"}, ensure_ascii=False)
    query("UPDATE foreshadows SET status='abandoned', updated_at=NOW() WHERE id=%s", (foreshadow_id,), fetch="none")
    _record_db_hash(novel_id, "foreshadow", str(foreshadow_id), "abandoned")
    return json.dumps({"ok": True, "foreshadow_id": foreshadow_id, "status": "abandoned", "reason": reason}, ensure_ascii=False)


@mcp.tool
def foreshadow_update(novel_name: str, foreshadow_id: int,
                      description: str = "", importance: str = "",
                      planned_recall_chapter: int = 0,
                      related_characters: list = None,
                      tags: list = None) -> str:
    """更新伏笔（只传需要修改的字段，空值会被忽略）。可修改描述、重要性、计划回收章等。
      novel_name: 小说名称
      foreshadow_id: 伏笔ID
      description: 新描述
      importance: high/medium/low
      planned_recall_chapter: 计划回收章节号（传0表示清除）
      related_characters: 相关角色ID列表
      tags: 标签列表
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
    if not fields:
        return json.dumps({"ok": False, "error": "no fields to update"}, ensure_ascii=False)

    sets = [f"{k} = %s" for k in fields]
    vals = list(fields.values()) + [foreshadow_id]
    query(f"UPDATE foreshadows SET {', '.join(sets)}, updated_at = NOW() WHERE id = %s",
          tuple(vals), fetch="none")
    _record_db_hash(novel_id, "foreshadow", str(foreshadow_id), json.dumps(fields, ensure_ascii=False))
    return json.dumps({"ok": True, "foreshadow_id": foreshadow_id, "updated_fields": list(fields.keys())},
                      ensure_ascii=False)


@mcp.tool
def get_chapter_context(novel_name: str, chapter_number: int) -> str:
    """获取写某章所需的全部上下文（聚合查询，一次调用替代10+单独调用）。
    返回:
    - 章节信息 + 卷级大纲 + 前N章摘要
    - 出场角色深度信息（外观/性格/说话风格/能力/状态/关系）
    - 未回收伏笔 + 活跃线索
    - 世界观全分类数据（location/faction/ability/economy/daily_life/race/history）
    - 人物关系
    - 时间线（前3章）
    - 质量历史
    - 写作提示词（含规则+作者DNA）
    参数:
      novel_name: 小说名称
      chapter_number: 章节序号
    """
    novel_id = _resolve_novel_id(novel_name)
    result = {"chapter_number": chapter_number}
    ch = query("SELECT * FROM chapters WHERE novel_id=%s AND number=%s", (novel_id, chapter_number), fetch="one")
    if not ch:
        return json.dumps({"error": f"章节 {chapter_number} 不存在"}, ensure_ascii=False)
    result["chapter"] = dict(ch)
    if ch.get("volume_id"):
        vol = query("SELECT * FROM volumes WHERE id=%s", (ch["volume_id"],), fetch="one")
        if vol:
            result["volume"] = {"number": vol["number"], "title": vol["title"], "main_plotlines": vol["main_plotlines"], "notes": vol.get("notes", "")}
    prev_summaries = query(
        "SELECT cs.*, c.number FROM chapter_summaries cs "
        "JOIN chapters c ON cs.chapter_id=c.id "
        "WHERE c.novel_id=%s AND c.number < %s ORDER BY c.number DESC LIMIT 3",
        (novel_id, chapter_number)
    )
    result["prev_summaries"] = [dict(r) for r in prev_summaries]
    foreshadows = query(
        "SELECT * FROM foreshadows WHERE novel_id=%s AND status='planted' ORDER BY importance, id",
        (novel_id,)
    )
    result["unresolved_foreshadows"] = [dict(r) for r in foreshadows]
    threads = query("SELECT * FROM plot_threads WHERE novel_id=%s AND status='active'", (novel_id,))
    result["active_threads"] = [dict(r) for r in threads]
    all_chars = query("SELECT * FROM characters WHERE novel_id=%s AND is_active=TRUE", (novel_id,))
    char_details = []
    for c in all_chars:
        cd = dict(c)
        rels = query(
            "SELECT cr.relation_type, cr.description, cr.intensity, cr.status, "
            "c1.name as from_name, c2.name as to_name "
            "FROM character_relations cr "
            "JOIN characters c1 ON cr.from_character_id=c1.id "
            "JOIN characters c2 ON cr.to_character_id=c2.id "
            "WHERE cr.novel_id=%s AND (c1.id=%s OR c2.id=%s)",
            (novel_id, c["id"], c["id"])
        )
        cd["relations"] = [dict(r) for r in rels]
        snap = query(
            "SELECT css.* FROM character_state_snapshots css "
            "JOIN chapters ch2 ON css.chapter_id=ch2.id "
            "WHERE css.character_id=%s ORDER BY ch2.number DESC LIMIT 1",
            (c["id"],), fetch="one"
        )
        if snap:
            cd["latest_snapshot"] = dict(snap)
        char_details.append(cd)
    result["character_details"] = char_details
    relations = query(
        "SELECT cr.relation_type, cr.description, cr.intensity, cr.status, "
        "c1.name as from_name, c2.name as to_name "
        "FROM character_relations cr "
        "JOIN characters c1 ON cr.from_character_id=c1.id "
        "JOIN characters c2 ON cr.to_character_id=c2.id "
        "WHERE cr.novel_id=%s",
        (novel_id,)
    )
    result["relations"] = [dict(r) for r in relations]
    world_categories = ["location", "faction", "ability", "economy", "daily_life", "race", "history"]
    world_data = {}
    for cat in world_categories:
        rows = query("SELECT name, data FROM world_settings WHERE novel_id=%s AND category=%s", (novel_id, cat))
        if rows:
            world_data[cat] = [{**dict(r)} for r in rows]
    result["world_settings"] = world_data
    timeline = query(
        "SELECT te.*, c.number as chapter_number FROM timeline_events te "
        "JOIN chapters c ON te.chapter_id=c.id "
        "WHERE c.novel_id=%s AND c.number >= %s ORDER BY c.number",
        (novel_id, max(1, chapter_number - 3))
    )
    result["timeline"] = [dict(r) for r in timeline]
    quality_history = _get_quality_history(novel_id, chapter_number)
    result["quality_history"] = quality_history
    result["writing_prompt"] = _build_writing_prompt(
        ch=dict(ch),
        summaries=[dict(r) for r in prev_summaries],
        chars=[{"id": c["id"], "name": c["name"], "role": c["role"]} for c in all_chars],
        foreshadows=[dict(r) for r in foreshadows],
        world_index=[{"category": cat, "name": w["name"]} for cat, items in world_data.items() for w in items],
        vol=result.get("volume", {}),
        quality_history=quality_history,
    )
    return json.dumps(result, ensure_ascii=False, default=str)
