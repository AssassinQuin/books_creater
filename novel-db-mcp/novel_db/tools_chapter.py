import json
from collections import defaultdict

from .db import mcp, query, transaction
from .resolvers import _resolve_novel_id, _resolve_chapter_id, _UNSET, _resolve_entity
from .errors import NotFoundError, mcp_tool
from .sql_utils import build_update_sql


def _resolve_chapter_id_by_number(novel_id: int, number: int) -> int:
    row = query(
        "SELECT id FROM chapters WHERE novel_id = ? AND number = ?",
        (novel_id, number), fetch="one"
    )
    if not row:
        raise NotFoundError(f"章节 {number} 不存在")
    return row["id"]


def _save_chapter_summary_internal(chapter_id: int, summary: str,
                                    key_events: str = "[]",
                                    characters_involved: list = None,
                                    new_foreshadows: list = None,
                                    resolved_foreshadows: list = None,
                                    dimension_snapshot: str = "{}") -> None:
    """Internal: upsert chapter_summaries (shared by chapter_save_summary, chapter_update_metadata, writing_finish)."""
    query(
        "INSERT INTO chapter_summaries (chapter_id, summary, key_events, characters_involved, "
        "new_foreshadows, resolved_foreshadows, dimension_snapshot) "
        "VALUES (?, ?, ?, ?, ?, ?, ?) "
        "ON CONFLICT (chapter_id) DO UPDATE SET "
        "summary = ?, key_events = ?, characters_involved = ?, "
        "new_foreshadows = ?, resolved_foreshadows = ?, dimension_snapshot = ?",
        (chapter_id, summary, key_events, characters_involved or [],
         new_foreshadows or [], resolved_foreshadows or [], dimension_snapshot,
         summary, key_events, characters_involved or [],
         new_foreshadows or [], resolved_foreshadows or [], dimension_snapshot),
        fetch="none"
    )


@mcp.tool
@mcp_tool
def chapter_plan(novel_name: str, number: int, title: str = "",
                 outline: str = "", chapter_type: str = "normal",
                 volume_id: int = None) -> str:
    """规划章节。chapter_type: normal/transition/climax/filler/daily
      novel_name: 小说名称
    """
    novel_id = _resolve_novel_id(novel_name)

    r = query(
        "INSERT INTO chapters (novel_id, number, title, outline, chapter_type, volume_id) "
        "VALUES (?,?,?,?,?,?) ON CONFLICT (novel_id, number) "
        "DO UPDATE SET title = ?, outline = ?, chapter_type = ?, volume_id = ?, updated_at = datetime('now')",
        (novel_id, number, title, outline, chapter_type, volume_id,
         title, outline, chapter_type, volume_id), fetch="insert"
    )
    return json.dumps({"ok": True, "id": r["id"], "number": number}, ensure_ascii=False)


@mcp.tool
@mcp_tool
def chapter_list(novel_name: str, status: str = "") -> str:
    """列出章节。status 可选过滤: planned/drafting/written/reviewed/published
      novel_name: 小说名称
    """
    novel_id = _resolve_novel_id(novel_name)
    if status:
        rows = query("SELECT * FROM chapters WHERE novel_id = ? AND status = ? ORDER BY number",
                     (novel_id, status))
    else:
        rows = query("SELECT * FROM chapters WHERE novel_id = ? ORDER BY number", (novel_id,))
    return json.dumps([dict(r) for r in rows], ensure_ascii=False, default=str)


def _chapter_update_by_id(chapter_id: int, title=_UNSET, status=_UNSET,
                   outline=_UNSET, chapter_type=_UNSET,
                   volume_id=_UNSET) -> str:
    fields = {}
    if title is not _UNSET: fields["title"] = title
    if status is not _UNSET: fields["status"] = status
    if outline is not _UNSET: fields["outline"] = outline
    if chapter_type is not _UNSET: fields["chapter_type"] = chapter_type
    if volume_id is not _UNSET: fields["volume_id"] = volume_id
    if not fields:
        return json.dumps({"ok": False, "error": "no valid fields"}, ensure_ascii=False)
    sql, params = build_update_sql("chapters", fields, "id = ?", (chapter_id,))
    query(sql, params, fetch="none")
    return json.dumps({"ok": True}, ensure_ascii=False)


@mcp.tool
@mcp_tool
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
    _save_chapter_summary_internal(chapter_id, summary, ke, ci, nf, rf, ds)
    return json.dumps({"ok": True}, ensure_ascii=False)


@mcp.tool
@mcp_tool
def get_chapter_context(novel_name: str, chapter_number: int,
                         load_mode: str = "smart",
                         regions: str = "", faction_names: str = "",
                         categories: str = "") -> str:
    """获取写某章所需的精简上下文包（聚合查询，一次调用替代10+单独调用）。
    
    v2 升级：返回蒸馏卡片而非完整档案，伏笔按卷过滤，自动嵌入底色提示和世界状态。
    估计上下文体积缩小 60-70%。
    
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
    
    返回:
      - 章节信息 + 卷级大纲 + 前N章摘要
      - 角色蒸馏卡片（name/role/核心特质/说话风格/当前状态/关系摘要）
      - 本章相关伏笔（按卷范围过滤）+ 活跃线索
      - 分层加载的世界观
      - 世界状态（衰退曲线当前卷锚点）
      - 底色提示（从 writing_rules world_tone 类别提取）
      - 时间线（前3章）
      - 质量历史
      - 写作提示词（含规则+作者DNA）
    """
    novel_id = _resolve_novel_id(novel_name)

    result = {"chapter_number": chapter_number, "_version": 2}

    try:
        chapter_id = _resolve_chapter_id_by_number(novel_id, chapter_number)
    except NotFoundError as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    ch = query("SELECT * FROM chapters WHERE id = ?", (chapter_id,), fetch="one")
    result["chapter"] = dict(ch)

    vol_num = 0
    volume_str = ""
    if ch.get("volume_id"):
        vol = query("SELECT * FROM volumes WHERE id = ?", (ch["volume_id"],), fetch="one")
        if vol:
            vol_num = vol["number"]
            volume_str = f"V{vol_num}"
            result["volume"] = {"number": vol_num, "title": vol["title"],
                                "main_plotlines": vol["main_plotlines"], "notes": vol.get("notes", ""),
                                "core_emotion": vol.get("core_emotion", ""),
                                "pov_anchor": vol.get("pov_anchor", ""),
                                "causal_chain": vol.get("causal_chain", ""),
                                "character_arcs": vol.get("character_arcs", "[]"),
                                "writing_priorities": vol.get("writing_priorities", "{}"),
                                "world_state": vol.get("world_state", "")}

    prev_summaries = query(
        "SELECT cs.*, c.number FROM chapter_summaries cs "
        "JOIN chapters c ON cs.chapter_id = c.id "
        "WHERE c.novel_id = ? AND c.number < ? ORDER BY c.number DESC LIMIT 3",
        (novel_id, chapter_number)
    )
    result["prev_summaries"] = [dict(r) for r in prev_summaries]

    # ── Foreshadows: filter by volume relevance ──
    foreshadows = query(
        "SELECT * FROM foreshadows WHERE novel_id = ? AND status = 'planted' ORDER BY importance, id",
        (novel_id,)
    )
    if vol_num > 0 and foreshadows:
        vol_foreshadows = []
        for f in foreshadows:
            prc = f.get("planned_recall_chapter")
            if f.get("importance") == "high":
                vol_foreshadows.append(f)
            elif prc and isinstance(prc, (int, float)):
                if abs(prc - chapter_number) <= 30:
                    vol_foreshadows.append(f)
            else:
                vol_foreshadows.append(f)
        result["unresolved_foreshadows"] = vol_foreshadows
    else:
        result["unresolved_foreshadows"] = [dict(r) for r in foreshadows]

    try:
        threads = query("SELECT * FROM plot_threads WHERE novel_id = ? AND status = 'active'", (novel_id,))
        result["active_threads"] = [dict(r) for r in threads] if threads else []
    except Exception as e:
        result["active_threads"] = []
        result.setdefault("_errors", []).append(f"plot_threads query failed: {e}")

    echoes = query(
        "SELECT e.source_event, e.echo_type, e.echo_description, e.strong_related, "
        "c1.number as source_ch, c2.number as echo_ch "
        "FROM echoes e "
        "LEFT JOIN chapters c1 ON e.source_chapter_id = c1.id "
        "LEFT JOIN chapters c2 ON e.echo_chapter_id = c2.id "
        "WHERE e.novel_id = ? AND e.echo_chapter_id = ? "
        "ORDER BY e.id", (novel_id, ch["id"]))
    result["active_echoes"] = [dict(r) for r in echoes] if echoes else []

    # ── Characters: distillation cards instead of full profiles ──
    all_chars = query("SELECT id, name, role, personality, speech_style, ability_level, status, goals, arc_notes "
                      "FROM characters WHERE novel_id = ? AND is_active = 1", (novel_id,))

    all_rels = query(
        "SELECT cr.relation_type, cr.description, cr.intensity, cr.status, "
        "cr.from_character_id, cr.to_character_id, "
        "c1.name as from_name, c2.name as to_name "
        "FROM character_relations cr "
        "JOIN characters c1 ON cr.from_character_id = c1.id "
        "JOIN characters c2 ON cr.to_character_id = c2.id "
        "WHERE cr.novel_id = ?",
        (novel_id,)
    )
    rel_map = defaultdict(list)
    for r in (all_rels or []):
        rel_map[r["from_character_id"]].append(f"{r['relation_type']}:{r['to_name']}")
        rel_map[r["to_character_id"]].append(f"{r['relation_type']}:{r['from_name']}")

    latest_snaps = query(
        "SELECT css.character_id as snap_char_id, css.location, css.arc_phase, "
        "css.emotional_state, css.physical_state "
        "FROM character_state_snapshots css "
        "JOIN chapters ch2 ON css.chapter_id = ch2.id "
        "WHERE css.id IN ("
        "  SELECT MAX(css2.id) FROM character_state_snapshots css2 "
        "  JOIN chapters ch3 ON css2.chapter_id = ch3.id "
        "  GROUP BY css2.character_id"
        ")",
        ()
    )
    snap_map = {s["snap_char_id"]: dict(s) for s in (latest_snaps or [])}

    char_cards = []
    for c in (all_chars or []):
        card = {
            "name": c["name"],
            "role": c["role"],
            "personality": (c.get("personality") or "")[:80],
            "speech_style": c.get("speech_style", ""),
            "ability_level": c.get("ability_level", ""),
            "goals": (c.get("goals") or "")[:60],
            "arc_notes": (c.get("arc_notes") or "")[:60],
        }
        status = c.get("status", "")
        if status and status != "{}":
            card["status"] = status
        rels = rel_map.get(c["id"], [])
        if rels:
            card["relations"] = rels[:5]
        snap = snap_map.get(c["id"])
        if snap:
            snap.pop("snap_char_id", None)
            card["snapshot"] = snap
        char_cards.append(card)
    result["character_cards"] = char_cards

    result["relations"] = [dict(r) for r in (all_rels or [])]

    # ── World Settings: Layered Loading ──
    if load_mode == "full":
        world = query(
            "SELECT category, name, data, region, volume_range, faction_id "
            "FROM world_settings WHERE novel_id = ? AND status = 'active'",
            (novel_id,)
        )
        result["world_settings"] = [dict(r) for r in world]
        result["_load_info"] = {"mode": "full", "count": len(world),
                                "warning": "full模式加载全部设定，数据量大"}
    else:
        _load_world_context(result, novel_id, volume_str, load_mode,
                            regions, faction_names, categories)

    # ── World State: decay curve anchor for current volume ──
    if vol_num > 0:
        result["world_state"] = _extract_decay_state(novel_id, vol_num)
        if not result["world_state"].get("descriptions") and not result["volume"].get("world_state"):
            result["world_state"]["hint"] = "衰退曲线数据未找到，请检查 world_settings 表"

    # ── Tone prompts: from writing_rules world_tone category ──
    tone_rules = query(
        "SELECT name, message FROM writing_rules "
        "WHERE novel_id = ? AND category = 'world_tone' AND is_active = 1",
        (novel_id,)
    )
    if tone_rules:
        result["tone_prompts"] = [{"name": r["name"], "message": r["message"]} for r in tone_rules]

    # Timeline (last 3 chapters)
    timeline = query(
        "SELECT te.*, c.number as chapter_number FROM timeline_events te "
        "JOIN chapters c ON te.chapter_id = c.id "
        "WHERE c.novel_id = ? AND c.number >= ? ORDER BY c.number",
        (novel_id, max(1, chapter_number - 3))
    )
    result["timeline"] = [dict(r) for r in timeline] if timeline else []

    # Quality history + writing prompt
    from .prompts import _get_quality_history, _build_writing_prompt
    quality_history = _get_quality_history(novel_id, chapter_number)
    result["quality_history"] = quality_history
    result["writing_prompt"] = _build_writing_prompt(
        ch=dict(ch),
        summaries=[dict(r) for r in prev_summaries],
        chars=[{"id": c["id"], "name": c["name"], "role": c["role"]} for c in (all_chars or [])],
        foreshadows=result["unresolved_foreshadows"],
        world_index=[{"category": cat, "name": w["name"]}
                      for cat, items in result.get("world_settings", {}).items()
                      for w in items] if isinstance(result.get("world_settings"), dict) else [],
        vol=result.get("volume", {}),
        quality_history=quality_history,
        echoes=result.get("active_echoes", []),
        novel_id=novel_id,
    )

    return json.dumps(result, ensure_ascii=False, default=str)


def _extract_decay_state(novel_id: int, vol_num: int) -> dict:
    """Extract world state for current volume from novel_config decay_phases."""
    from .db import get_novel_config

    decay_phases = get_novel_config(novel_id, "decay_phases", "world_decay_curve", [])
    phase_name = "未知"
    phase_key = ""
    matched_phase = None

    for phase in decay_phases:
        vr = phase.get("volume_range", "")
        try:
            parts = vr.split("-")
            lo, hi = int(parts[0]), int(parts[-1])
            if lo <= vol_num <= hi:
                phase_name = phase.get("phase_name", "未知")
                phase_key = phase.get("phase_key", "")
                matched_phase = phase
                break
        except (ValueError, IndexError):
            continue

    state = {
        "volume": f"V{vol_num}",
        "phase": phase_name,
    }

    if matched_phase:
        state["danger_level"] = matched_phase.get("danger_level", 1)
        state["env_tone"] = matched_phase.get("env_tone", "")

    if phase_key:
        from .db import query as _q
        phase_row = _q(
            "SELECT data FROM world_settings "
            "WHERE category = 'core_setting' AND name = ?",
            (phase_key,), fetch="one"
        )
        if phase_row and phase_row.get("data"):
            raw = phase_row["data"]
            if isinstance(raw, str):
                try:
                    import json as _json
                    parsed = _json.loads(raw)
                    if isinstance(parsed, list):
                        state["descriptions"] = parsed
                    elif isinstance(parsed, dict):
                        state["descriptions"] = list(parsed.values()) if parsed else []
                except Exception:
                    state["descriptions"] = [raw]
            elif isinstance(raw, list):
                state["descriptions"] = raw

    return state


def _load_volume_context_map(novel_id: int) -> dict:
    """Load volume→region/faction mapping from DB. Falls back to empty if not configured.
    
    DB entries are stored in world_settings(category='volume_context_map', name='V{num}').
    Each entry's data field: {"regions": "外围,北境", "factions": "壁盾军团"}
    """
    rows = query(
        "SELECT name, data FROM world_settings WHERE novel_id = ? AND category = 'volume_context_map'",
        (novel_id,)
    )
    mapping = {}
    for row in rows:
        vol_num = 0
        vname = row["name"]
        if vname.startswith("V"):
            try:
                vol_num = int(vname[1:])
            except ValueError:
                continue
        d = row["data"]
        if isinstance(d, dict) and ("regions" in d or "factions" in d):
            mapping[vol_num] = d
    return mapping


def _load_world_context(result: dict, novel_id: int, volume_str: str,
                         load_mode: str, regions: str, faction_names: str, categories: str):
    """Internal: layered world context loading for chapter_get_context / get_chapter_context."""
    
    # Smart mode: load only world settings relevant to current volume
    if load_mode == "smart" and volume_str:
        vol_num = int(volume_str.replace("V", "")) if volume_str.startswith("V") else 0
        vol_mapping = _load_volume_context_map(novel_id)
        mapping = vol_mapping.get(vol_num, {})
        regions = mapping.get("regions", "")
        faction_names = mapping.get("factions", "")

        # When no explicit mapping, infer from volume outline using novel_config
        if not regions and vol_num > 0:
            from .db import get_novel_config
            vol_row = query(
                "SELECT notes, main_plotlines FROM volumes WHERE novel_id = ? AND number = ?",
                (novel_id, vol_num), fetch="one"
            )
            if vol_row:
                text = (vol_row.get("notes", "") or "") + " " + (vol_row.get("main_plotlines", "") or "")
                _region_keywords = get_novel_config(novel_id, "context_inference", "region_keywords", {})
                if _region_keywords:
                    inferred = []
                    for region, keywords in _region_keywords.items():
                        if any(kw in text for kw in keywords):
                            inferred.append(region)
                    if inferred:
                        regions = ",".join(inferred)
                    else:
                        regions = "全域"

        # Infer categories from volume outline using novel_config
        if not categories and vol_num > 0:
            from .db import get_novel_config
            vol_row = query(
                "SELECT notes FROM volumes WHERE novel_id = ? AND number = ?",
                (novel_id, vol_num), fetch="one"
            )
            if vol_row and vol_row.get("notes"):
                text = vol_row["notes"]
                _cat_keywords = get_novel_config(novel_id, "context_inference", "category_keywords", {})
                if _cat_keywords:
                    inferred_cats = []
                    for cat, keywords in _cat_keywords.items():
                        if any(kw in text for kw in keywords):
                            inferred_cats.append(cat)
                    if inferred_cats:
                        categories = ",".join(inferred_cats)
    elif load_mode == "volume":
        # Just filter by volume, no region/faction inference
        regions = ""
        faction_names = ""
    
    # Build query
    conditions = ["novel_id = ?", "status = 'active'"]
    params = [novel_id]
    
    region_list = [r.strip() for r in regions.split(',') if r.strip()] if regions else []
    faction_name_list = [f.strip() for f in faction_names.split(',') if f.strip()] if faction_names else []
    category_list = [c.strip() for c in categories.split(',') if c.strip()] if categories else []
    
    # Resolve faction names to IDs
    faction_ids = []
    if faction_name_list:
        for fn in faction_name_list:
            frow = query(
                "SELECT id FROM world_settings WHERE novel_id = ? AND category = 'faction' AND name = ?",
                (novel_id, fn), fetch="one"
            )
            if frow:
                faction_ids.append(frow["id"])
    
    # Category filter
    if category_list:
        cat_placeholders = ", ".join(["?"] * len(category_list))
        conditions.append(f"category IN ({cat_placeholders})")
        params.extend(category_list)
    
    # Region filter
    if region_list:
        region_placeholders = ", ".join(["?"] * (len(region_list) + 1))
        conditions.append(f"(region IN ({region_placeholders}))")
        params.extend(region_list + ['全域'])
    
    # Faction filter
    if faction_ids:
        fid_placeholders = ", ".join(["?"] * (len(faction_ids) + 1))
        conditions.append(f"(faction_id IN ({fid_placeholders}) OR faction_id IS NULL)")
        params.extend(faction_ids + [0])
    
    where = " AND ".join(conditions)
    rows = query(f"SELECT category, name, data, region, volume_range, faction_id FROM world_settings WHERE {where} ORDER BY priority DESC, category, name", tuple(params))
    
    # Volume range filtering
    vol_num = int(volume_str.replace("V", "")) if volume_str.startswith("V") else None
    if vol_num is not None:
        from .tools_world import _volume_in_range
        constant_rows = [r for r in rows if r.get("is_constant")]
        non_constant = [r for r in rows if not r.get("is_constant")]
        volume_matched = [r for r in non_constant if _volume_in_range(vol_num, r.get("volume_range", ""))]
        result_rows = constant_rows + volume_matched
    else:
        result_rows = list(rows)

    # Compact world settings: strip index metadata from data field
    # Smart mode: for entries with wide volume_range (V1-V14), only include name index
    compact_rows = []
    _strip_keys = {"keys", "secondary_keys", "tags", "related", "source_file"}
    _wide_range_patterns = {"V1-V14", "V1-尾声"}
    for r in result_rows:
        entry = {"category": r["category"], "name": r["name"]}
        if r.get("region"):
            entry["region"] = r["region"]

        vr = r.get("volume_range", "")
        is_wide = any(p in str(vr) for p in _wide_range_patterns)
        include_data = not (is_wide and load_mode == "smart")

        if include_data:
            raw_data = r.get("data")
            if raw_data:
                if isinstance(raw_data, dict):
                    compact_data = {k: v for k, v in raw_data.items() if k not in _strip_keys}
                    if compact_data:
                        entry["data"] = compact_data
                elif isinstance(raw_data, list):
                    entry["data"] = raw_data
                elif isinstance(raw_data, str):
                    try:
                        import json as _json
                        parsed = _json.loads(raw_data)
                        if isinstance(parsed, dict):
                            compact_data = {k: v for k, v in parsed.items() if k not in _strip_keys}
                            if compact_data:
                                entry["data"] = compact_data
                        else:
                            entry["data"] = parsed
                    except Exception:
                        if len(raw_data) <= 500:
                            entry["data"] = raw_data
        compact_rows.append(entry)

    result["world_settings"] = compact_rows
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
@mcp_tool
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
        "VALUES (?,?,?,?,?,?,?,?) "
        "ON CONFLICT (chapter_id, scene_number) DO UPDATE SET "
        "location = ?, characters_involved = ?, conflict = ?, emotion_type = ?, "
        "key_beats = ?, notes = ?",
        (chapter_id, scene_number, location, ci,
         conflict, emotion_type, kb, notes,
         location, ci, conflict, emotion_type, kb, notes),
        fetch="none"
    )
    return json.dumps({"ok": True}, ensure_ascii=False)


@mcp.tool
@mcp_tool
def scene_list(novel_name: str, chapter_number: int) -> str:
    """列出章节的场景大纲
      novel_name: 小说名称
      chapter_number: 章节序号
    """
    chapter_id = _resolve_chapter_id(novel_name, chapter_number)
    rows = query("SELECT * FROM scene_outlines WHERE chapter_id = ? ORDER BY scene_number",
                 (chapter_id,))
    return json.dumps([dict(r) for r in rows], ensure_ascii=False, default=str)


@mcp.tool
@mcp_tool
def dimension_log(novel_name: str, chapter_id: int, dimension: str,
                  change_type: str, entity_name: str,
                  before_value: dict = None, after_value: dict = None,
                  description: str = "") -> str:
    """[DEPRECATED] 此工具已废弃，维度变更已由 character_state_snapshots 追踪。请使用 character_state_snapshots 替代。"""
    return json.dumps({"error": "dimension_log 已废弃，请使用 character_state_snapshots 替代"}, ensure_ascii=False)


@mcp.tool
@mcp_tool
def dimension_query(novel_name: str, dimension: str = "", from_chapter: int = 0,
                    to_chapter: int = 99999) -> str:
    """[DEPRECATED] 此工具已废弃，维度变更已由 character_state_snapshots 追踪。请使用 character_state_snapshots 替代。"""
    return json.dumps({"error": "dimension_query 已废弃，请使用 character_state_snapshots 替代"}, ensure_ascii=False)


@mcp.tool
@mcp_tool
def timeline_add(novel_name: str, chapter_number: int, event_time: str,
                 event_order: int, event_description: str,
                 characters_involved: list = None,
                 location_id: int = None,
                 significance: str = "normal",
                 chapter_id: int = 0) -> str:
    """添加时间线事件。优先使用 chapter_number，兼容旧 chapter_id。
      novel_name: 小说名称
      chapter_number: 章节序号（推荐）
      chapter_id: 章节ID（兼容旧调用，优先级低于 chapter_number）
    """
    novel_id = _resolve_novel_id(novel_name)

    if chapter_number and not chapter_id:
        try:
            chapter_id = _resolve_chapter_id_by_number(novel_id, chapter_number)
        except NotFoundError:
            pass

    r = query(
        "INSERT INTO timeline_events (novel_id, chapter_id, event_time, event_order, "
        "event_description, characters_involved, location_id, significance) "
        "VALUES (?,?,?,?,?,?,?,?)",
        (novel_id, chapter_id, event_time, event_order, event_description,
         characters_involved or [], location_id, significance), fetch="insert"
    )
    return json.dumps({"ok": True, "id": r["id"]}, ensure_ascii=False)


@mcp.tool
@mcp_tool
def timeline_query(novel_name: str, from_chapter: int = 0, to_chapter: int = 99999) -> str:
    """查询时间线事件，可按章节范围过滤
      novel_name: 小说名称
    """
    novel_id = _resolve_novel_id(novel_name)
    rows = query(
        "SELECT te.*, c.number as chapter_number FROM timeline_events te "
        "JOIN chapters c ON te.chapter_id = c.id "
        "WHERE te.novel_id = ? AND c.number BETWEEN ? AND ? "
        "ORDER BY te.event_order",
        (novel_id, from_chapter, to_chapter)
    )
    return json.dumps([dict(r) for r in rows], ensure_ascii=False, default=str)


@mcp.tool
@mcp_tool
def scene_update(novel_name: str, chapter_number: int, scene_number: int,
                 location=_UNSET, characters_involved=_UNSET,
                 conflict=_UNSET, emotion_type=_UNSET,
                 key_beats=_UNSET, notes=_UNSET) -> str:
    """更新场景大纲（只传需要修改的字段，未传的字段不会被修改）
      novel_name: 小说名称
      chapter_number: 章节序号
      scene_number: 场景序号
    """
    chapter_id = _resolve_chapter_id(novel_name, chapter_number)
    fields = {}
    if location is not _UNSET:
        fields["location"] = location
    if characters_involved is not _UNSET:
        fields["characters_involved"] = characters_involved
    if conflict is not _UNSET:
        fields["conflict"] = conflict
    if emotion_type is not _UNSET:
        fields["emotion_type"] = emotion_type
    if key_beats is not _UNSET:
        fields["key_beats"] = json.dumps(key_beats, ensure_ascii=False)
    if notes is not _UNSET:
        fields["notes"] = notes
    if not fields:
        return json.dumps({"ok": False, "error": "no fields to update"}, ensure_ascii=False)
    sql, params = build_update_sql("scene_outlines", fields,
                                   "chapter_id = ? AND scene_number = ?",
                                   (chapter_id, scene_number))
    query(sql, params, fetch="none")
    return json.dumps({"ok": True}, ensure_ascii=False)


@mcp.tool
@mcp_tool
def scene_delete(novel_name: str, chapter_number: int, scene_number: int) -> str:
    """删除场景大纲
      novel_name: 小说名称
      chapter_number: 章节序号
      scene_number: 场景序号
    """
    chapter_id = _resolve_chapter_id(novel_name, chapter_number)
    query("DELETE FROM scene_outlines WHERE chapter_id = ? AND scene_number = ?",
          (chapter_id, scene_number), fetch="none")
    return json.dumps({"ok": True}, ensure_ascii=False)


@mcp.tool
@mcp_tool
def timeline_update(novel_name: str, event_id: int,
                    event_description=_UNSET, event_time=_UNSET,
                    characters_involved=_UNSET,
                    significance=_UNSET) -> str:
    """更新时间线事件（只传需要修改的字段）
      novel_name: 小说名称
      event_id: 时间线事件ID
    """
    _resolve_novel_id(novel_name)
    fields = {}
    if event_description is not _UNSET:
        fields["event_description"] = event_description
    if event_time is not _UNSET:
        fields["event_time"] = event_time
    if characters_involved is not _UNSET:
        fields["characters_involved"] = characters_involved
    if significance is not _UNSET:
        fields["significance"] = significance
    if not fields:
        return json.dumps({"ok": False, "error": "no fields to update"}, ensure_ascii=False)
    sql, params = build_update_sql("timeline_events", fields, "id = ?", (event_id,))
    query(sql, params, fetch="none")
    return json.dumps({"ok": True}, ensure_ascii=False)


@mcp.tool
@mcp_tool
def timeline_delete(novel_name: str, event_id: int) -> str:
    """删除时间线事件
      novel_name: 小说名称
      event_id: 时间线事件ID
    """
    _resolve_novel_id(novel_name)
    query("DELETE FROM timeline_events WHERE id = ?", (event_id,), fetch="none")
    return json.dumps({"ok": True}, ensure_ascii=False)
