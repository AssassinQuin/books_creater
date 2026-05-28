import json

from .db import mcp, query, transaction
from .resolvers import _resolve_novel_id, _resolve_chapter_id, _UNSET, _resolve_entity
from .errors import NotFoundError, mcp_tool
from .sql_utils import build_update_sql, safe_json_loads
from .sync import _record_db_hash


@mcp.tool
@mcp_tool
def character_create(novel_name: str, name: str, role: str = "npc",
                     faction_id: int = None, race: str = "", ability_level: str = "",
                     appearance: str = "", personality: str = "", background: str = "",
                     goals: str = "", weaknesses: str = "", speech_style: str = "",
                     catchphrase: str = "", arc_notes: str = "",
                     first_appearance_chapter: int = None,
                     appearance_detail: str = "", decision_engine: str = "",
                     voice_fingerprint: str = "", ability_system: str = "",
                     behavior_pattern: str = "", current_snapshot: str = "",
                     growth_trajectory: str = "",
                     distillation_tracked: bool = True) -> str:
    """创建人物。role: protagonist/ally/antagonist/mentor/rival/love_interest/npc
    appearance_detail/decision_engine/voice_fingerprint/ability_system/behavior_pattern/current_snapshot/growth_trajectory: JSON字符串
    distillation_tracked: 是否开启人物蒸馏追踪（默认True）。主角/主要配角应追踪；临时NPC可关闭。
      novel_name: 小说名称
    """
    novel_id = _resolve_novel_id(novel_name)

    with transaction():
        _json_fields = {}
        if appearance_detail:
            _json_fields["appearance_detail"] = safe_json_loads(appearance_detail, "appearance_detail")
        if decision_engine:
            _json_fields["decision_engine"] = safe_json_loads(decision_engine, "decision_engine")
        if voice_fingerprint:
            _json_fields["voice_fingerprint"] = safe_json_loads(voice_fingerprint, "voice_fingerprint")
        if ability_system:
            _json_fields["ability_system"] = safe_json_loads(ability_system, "ability_system")
        if behavior_pattern:
            _json_fields["behavior_pattern"] = safe_json_loads(behavior_pattern, "behavior_pattern")
        if current_snapshot:
            _json_fields["current_snapshot"] = safe_json_loads(current_snapshot, "current_snapshot")
        if growth_trajectory:
            _json_fields["growth_trajectory"] = safe_json_loads(growth_trajectory, "growth_trajectory")
        if not distillation_tracked:
            _json_fields["distillation_tracked"] = False

        base_cols = ("novel_id, name, role, faction_id, race, ability_level, "
                     "appearance, personality, background, goals, weaknesses, speech_style, catchphrase, "
                     "arc_notes, first_appearance_chapter")
        base_vals = (novel_id, name, role, faction_id, race, ability_level, appearance,
                     personality, background, goals, weaknesses, speech_style, catchphrase,
                     arc_notes, first_appearance_chapter)

        if _json_fields:
            extra_cols = ", ".join(_json_fields.keys())
            extra_vals = list(_json_fields.values())
            all_cols = f"{base_cols}, {extra_cols}"
            all_vals = base_vals + tuple(extra_vals)
        else:
            all_cols = base_cols
            all_vals = base_vals

        placeholders = ",".join(["?"] * len(all_vals))
        r = query(
            f"INSERT INTO characters ({all_cols}) VALUES ({placeholders})",
            all_vals, fetch="insert"
        )
        _record_db_hash(novel_id, "character", name, json.dumps({"name": name, "role": role, "race": race, "appearance": appearance}, ensure_ascii=False))
        from .hooks import fire_and_report
        fire_and_report(novel_id, "character", r["id"])
    return json.dumps({"ok": True, "id": r["id"], "name": name}, ensure_ascii=False)


def _character_update_by_id(character_id: int, name=_UNSET, role=_UNSET, faction_id=_UNSET,
                     race=_UNSET, ability_level=_UNSET, status=_UNSET,
                     appearance=_UNSET, personality=_UNSET, background=_UNSET,
                     goals=_UNSET, weaknesses=_UNSET, speech_style=_UNSET,
                     catchphrase=_UNSET, arc_notes=_UNSET, is_active=_UNSET,
                     status_json=_UNSET,
                     appearance_detail=_UNSET, decision_engine=_UNSET,
                     voice_fingerprint=_UNSET, ability_system=_UNSET,
                     behavior_pattern=_UNSET, current_snapshot=_UNSET,
                     growth_trajectory=_UNSET,
                     distillation_tracked=_UNSET) -> str:
    fields = {}
    if name is not _UNSET: fields["name"] = name
    if role is not _UNSET: fields["role"] = role
    if faction_id is not _UNSET: fields["faction_id"] = faction_id
    if race is not _UNSET: fields["race"] = race
    if ability_level is not _UNSET: fields["ability_level"] = ability_level
    if status_json is not _UNSET:
        fields["status"] = status_json
    elif status is not _UNSET:
        fields["status"] = status
    if appearance is not _UNSET: fields["appearance"] = appearance
    if personality is not _UNSET: fields["personality"] = personality
    if background is not _UNSET: fields["background"] = background
    if goals is not _UNSET: fields["goals"] = goals
    if weaknesses is not _UNSET: fields["weaknesses"] = weaknesses
    if speech_style is not _UNSET: fields["speech_style"] = speech_style
    if catchphrase is not _UNSET: fields["catchphrase"] = catchphrase
    if arc_notes is not _UNSET: fields["arc_notes"] = arc_notes
    if is_active is not _UNSET: fields["is_active"] = is_active
    if appearance_detail is not _UNSET: fields["appearance_detail"] = safe_json_loads(appearance_detail, "appearance_detail")
    if decision_engine is not _UNSET: fields["decision_engine"] = safe_json_loads(decision_engine, "decision_engine")
    if voice_fingerprint is not _UNSET: fields["voice_fingerprint"] = safe_json_loads(voice_fingerprint, "voice_fingerprint")
    if ability_system is not _UNSET: fields["ability_system"] = safe_json_loads(ability_system, "ability_system")
    if behavior_pattern is not _UNSET: fields["behavior_pattern"] = safe_json_loads(behavior_pattern, "behavior_pattern")
    if current_snapshot is not _UNSET: fields["current_snapshot"] = safe_json_loads(current_snapshot, "current_snapshot")
    if growth_trajectory is not _UNSET: fields["growth_trajectory"] = safe_json_loads(growth_trajectory, "growth_trajectory")
    if distillation_tracked is not _UNSET: fields["distillation_tracked"] = distillation_tracked
    if not fields:
        return json.dumps({"ok": False, "error": "no valid fields"}, ensure_ascii=False)
    with transaction():
        sql, params = build_update_sql("characters", fields, "id = ?", (character_id,))
        query(sql, params, fetch="none")
        char = query("SELECT novel_id, name FROM characters WHERE id = ?", (character_id,), fetch="one")
        if char:
            _record_db_hash(char["novel_id"], "character", char["name"], json.dumps(fields, ensure_ascii=False))
            from .hooks import fire_and_report
            fire_and_report(char["novel_id"], "character", character_id)
    return json.dumps({"ok": True}, ensure_ascii=False)


@mcp.tool
@mcp_tool
def character_list(novel_name: str, role: str = "") -> str:
    """列出小说人物。role 可选过滤
      novel_name: 小说名称
    """
    novel_id = _resolve_novel_id(novel_name)
    if role:
        rows = query("SELECT * FROM characters WHERE novel_id = ? AND role = ? AND is_active = 1 ORDER BY role, name",
                     (novel_id, role))
    else:
        rows = query("SELECT * FROM characters WHERE novel_id = ? AND is_active = 1 ORDER BY role, name",
                     (novel_id,))
    return json.dumps([dict(r) for r in rows], ensure_ascii=False, default=str)


def _character_get_by_id(character_id: int) -> str:
    r = query("SELECT * FROM characters WHERE id = ?", (character_id,), fetch="one")
    return json.dumps(dict(r) if r else {"error": "not found"}, ensure_ascii=False, default=str)


def _character_detail_by_id(character_id: int, chapter_number: int = None) -> str:
    char = query("SELECT * FROM characters WHERE id = ?", (character_id,), fetch="one")
    if not char:
        return json.dumps({"error": "character not found"}, ensure_ascii=False)

    result = dict(char)

    rels = query(
        "SELECT cr.relation_type, cr.description, cr.intensity, cr.status, "
        "c1.name as from_name, c2.name as to_name "
        "FROM character_relations cr "
        "JOIN characters c1 ON cr.from_character_id = c1.id "
        "JOIN characters c2 ON cr.to_character_id = c2.id "
        "WHERE cr.novel_id = ? AND (c1.id = ? OR c2.id = ?)",
        (char["novel_id"], character_id, character_id)
    )
    result["relations"] = [dict(r) for r in rels]

    if chapter_number:
        snap = query(
            "SELECT css.* FROM character_state_snapshots css "
            "JOIN chapters c ON css.chapter_id = c.id "
            "WHERE css.character_id = ? AND c.number <= ? "
            "ORDER BY c.number DESC LIMIT 1",
            (character_id, chapter_number), fetch="one"
        )
        if snap:
            result["snapshot"] = dict(snap)
    else:
        snap = query(
            "SELECT css.*, c.number as chapter_number FROM character_state_snapshots css "
            "JOIN chapters c ON css.chapter_id = c.id "
            "WHERE css.character_id = ? ORDER BY c.number DESC LIMIT 1",
            (character_id,), fetch="one"
        )
        if snap:
            result["snapshot"] = dict(snap)

    return json.dumps(result, ensure_ascii=False, default=str)


def _relation_create_by_id(novel_name: str, from_character_id: int, to_character_id: int,
                    relation_type: str, description: str = "",
                    chapter_established: int = None, intensity: int = 5) -> str:
    novel_id = _resolve_novel_id(novel_name)

    r = query(
        "INSERT INTO character_relations (novel_id, from_character_id, to_character_id, "
        "relation_type, description, chapter_established, intensity) "
        "VALUES (?,?,?,?,?,?,?)",
        (novel_id, from_character_id, to_character_id, relation_type,
         description, chapter_established, intensity), fetch="insert"
    )
    from .hooks import fire_and_report
    fire_and_report(novel_id, "character", from_character_id)
    return json.dumps({"ok": True, "id": r["id"]}, ensure_ascii=False)


@mcp.tool
@mcp_tool
def relation_list(novel_name: str) -> str:
    """列出小说的所有人物关系
      novel_name: 小说名称
    """
    novel_id = _resolve_novel_id(novel_name)

    rows = query(
        "SELECT cr.*, c1.name as from_name, c2.name as to_name "
        "FROM character_relations cr "
        "JOIN characters c1 ON cr.from_character_id = c1.id "
        "JOIN characters c2 ON cr.to_character_id = c2.id "
        "WHERE cr.novel_id = ? ORDER BY cr.relation_type",
        (novel_id,)
    )
    return json.dumps([dict(r) for r in rows], ensure_ascii=False, default=str)


@mcp.tool
@mcp_tool
def character_get(novel_name: str, character_name: str) -> str:
    """按角色名获取人物详情（无需ID）。
      novel_name: 小说名称
      character_name: 角色名
    """
    novel_id = _resolve_novel_id(novel_name)
    try:
        char_id = _resolve_entity(novel_id, "characters", character_name, "角色")
    except NotFoundError as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    return _character_get_by_id(char_id)


@mcp.tool
@mcp_tool
def character_detail(novel_name: str, character_name: str, chapter_number: int = None) -> str:
    """按角色名获取角色蒸馏卡片（无需ID）。
      novel_name: 小说名称
      character_name: 角色名
      chapter_number: 章节序号（可选，用于获取该章状态快照）
    """
    novel_id = _resolve_novel_id(novel_name)
    try:
        char_id = _resolve_entity(novel_id, "characters", character_name, "角色")
    except NotFoundError as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    return _character_detail_by_id(char_id, chapter_number)


@mcp.tool
@mcp_tool
def character_update(novel_name: str, character_name: str, name=_UNSET, role=_UNSET, faction_id=_UNSET,
                             race=_UNSET, ability_level=_UNSET, status=_UNSET,
                             appearance=_UNSET, personality=_UNSET, background=_UNSET,
                             goals=_UNSET, weaknesses=_UNSET, speech_style=_UNSET,
                             catchphrase=_UNSET, arc_notes=_UNSET, is_active=_UNSET,
                             status_json=_UNSET,
                             appearance_detail=_UNSET, decision_engine=_UNSET,
                             voice_fingerprint=_UNSET, ability_system=_UNSET,
                             behavior_pattern=_UNSET, current_snapshot=_UNSET,
                             growth_trajectory=_UNSET,
                             distillation_tracked=_UNSET) -> str:
    """按角色名更新人物信息（无需ID）。传入需要修改的字段，未传的字段不会被修改。
    distillation_tracked: 人物蒸馏追踪开关（默认True），设为False可关闭临时NPC的蒸馏记录。
    status_json: 传入完整 JSON 字符串作为 status 字段值（优先于 status 参数）。
      novel_name: 小说名称
      character_name: 角色名
    """
    novel_id = _resolve_novel_id(novel_name)
    try:
        char_id = _resolve_entity(novel_id, "characters", character_name, "角色")
    except NotFoundError as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    return _character_update_by_id(char_id, name, role, faction_id, race, ability_level, status,
                            appearance, personality, background, goals, weaknesses, speech_style,
                            catchphrase, arc_notes, is_active, status_json,
                            appearance_detail, decision_engine, voice_fingerprint, ability_system,
                            behavior_pattern, current_snapshot, growth_trajectory,
                            distillation_tracked=distillation_tracked)


@mcp.tool
@mcp_tool
def relation_create(novel_name: str, from_name: str, to_name: str,
                            relation_type: str, description: str = "",
                            chapter_established: int = None, intensity: int = 5) -> str:
    """按角色名创建人物关系（无需角色ID）。
      novel_name: 小说名称
      from_name: 关系发起方角色名
      to_name: 关系接受方角色名
      relation_type: ally/enemy/mentor/lover/family/rival/subordinate
      description: 关系描述
      chapter_established: 建立章节ID
      intensity: 关系强度(1-10)
    """
    novel_id = _resolve_novel_id(novel_name)
    try:
        from_id = _resolve_entity(novel_id, "characters", from_name, "角色")
    except NotFoundError as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    try:
        to_id = _resolve_entity(novel_id, "characters", to_name, "角色")
    except NotFoundError as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    return _relation_create_by_id(novel_name, from_id, to_id, relation_type, description, chapter_established, intensity)


@mcp.tool
@mcp_tool
def relation_update(novel_name: str, from_name: str, to_name: str,
                    relation_type: str = "", description: str = "",
                    intensity: int = 0, status: str = "") -> str:
    """更新人物关系（增量型）。关系类型/强度/描述/状态均可变更。

    参数:
      novel_name: 小说名称
      from_name: 关系发起方角色名
      to_name: 关系接受方角色名
      relation_type: 新关系类型（空=不变）
      description: 新描述（空=不变）
      intensity: 新强度（0=不变）
      status: 新状态（active/broken/evolved/hidden，空=不变）
    """
    novel_id = _resolve_novel_id(novel_name)

    rel = query(
        "SELECT cr.id, cr.intensity as cur_intensity FROM character_relations cr "
        "JOIN characters c1 ON cr.from_character_id=c1.id "
        "JOIN characters c2 ON cr.to_character_id=c2.id "
        "WHERE cr.novel_id=? AND c1.name=? AND c2.name=?",
        (novel_id, from_name, to_name), fetch="one"
    )
    if not rel:
        return json.dumps({"error": f"关系 '{from_name}'→'{to_name}' 不存在"}, ensure_ascii=False)
    sets = []
    vals = []
    if relation_type:
        sets.append("relation_type = ?")
        vals.append(relation_type)
    if description:
        sets.append("description = ?")
        vals.append(description)
    if intensity > 0:
        sets.append("intensity = ?")
        vals.append(intensity)
    if status:
        sets.append("status = ?")
        vals.append(status)
    if not sets:
        return json.dumps({"ok": False, "error": "Nothing to update"}, ensure_ascii=False)
    vals.append(rel["id"])
    query(f"UPDATE character_relations SET {', '.join(sets)} WHERE id = ?", tuple(vals), fetch="none")
    return json.dumps({"ok": True, "from": from_name, "to": to_name}, ensure_ascii=False)


@mcp.tool
@mcp_tool
def character_snapshot(novel_name: str, character_name: str, chapter_number: int,
                                location: str = "", arc_phase: str = "",
                                emotional_state: str = "", physical_state: str = "",
                                ability_snapshot: str = "[]", inventory_snapshot: str = "[]",
                                knowledge_snapshot: str = "{}", notes: str = "") -> str:
    """按角色名+章节号保存快照（无需查ID）。每章写完后调用。

    参数:
      novel_name: 小说名称
      character_name: 角色名
      chapter_number: 章节序号（如1, 2, 15）
      location: 当前位置
      arc_phase: 弧线阶段
      emotional_state: 情绪状态
      physical_state: 身体状态
      ability_snapshot: 能力快照(JSON)
      inventory_snapshot: 物品快照(JSON)
      knowledge_snapshot: 知识快照(JSON)
      notes: 备注
    """
    novel_id = _resolve_novel_id(novel_name)

    try:
        char_id = _resolve_entity(novel_id, "characters", character_name, "角色")
    except NotFoundError as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    ch = query("SELECT id FROM chapters WHERE novel_id=? AND number=?", (novel_id, chapter_number), fetch="one")
    if not ch:
        return json.dumps({"error": f"章节 {chapter_number} 不存在"}, ensure_ascii=False)
    return _character_snapshot_by_id(char_id, ch["id"], location, arc_phase, emotional_state,
                             physical_state, ability_snapshot, inventory_snapshot, knowledge_snapshot, notes)


@mcp.tool
@mcp_tool
def character_get_latest(novel_name: str, character_name: str) -> str:
    """获取角色最新状态快照（按名称查询，无需ID）。

    参数:
      novel_name: 小说名称
      character_name: 角色名
    """
    novel_id = _resolve_novel_id(novel_name)

    try:
        char_id = _resolve_entity(novel_id, "characters", character_name, "角色")
    except NotFoundError as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    r = query(
        "SELECT css.*, c.number as chapter_number FROM character_state_snapshots css "
        "JOIN chapters c ON css.chapter_id = c.id "
        "WHERE css.character_id = ? ORDER BY c.number DESC LIMIT 1",
        (char_id,), fetch="one"
    )
    if not r:
        return json.dumps({"error": f"'{character_name}' 暂无快照", "character_name": character_name}, ensure_ascii=False)
    result = dict(r)
    result["character_name"] = character_name
    return json.dumps(result, ensure_ascii=False, default=str)


@mcp.tool
@mcp_tool
def relation_snapshot(novel_name: str, from_name: str, to_name: str, chapter_number: int,
                              intensity: int = 5, status: str = "active", notes: str = "") -> str:
    """按角色名保存关系快照（无需查ID）。关系变化时调用。

    参数:
      novel_name: 小说名称
      from_name: 关系发起方角色名
      to_name: 关系接受方角色名
      chapter_number: 章节序号
      intensity: 关系强度(1-10)
      status: 关系状态(active/broken/evolved/hidden)
      notes: 备注
    """
    novel_id = _resolve_novel_id(novel_name)

    rel = query(
        "SELECT cr.id FROM character_relations cr "
        "JOIN characters c1 ON cr.from_character_id=c1.id "
        "JOIN characters c2 ON cr.to_character_id=c2.id "
        "WHERE cr.novel_id=? AND c1.name=? AND c2.name=?",
        (novel_id, from_name, to_name), fetch="one"
    )
    if not rel:
        return json.dumps({"error": f"关系 '{from_name}'→'{to_name}' 不存在"}, ensure_ascii=False)
    ch = query("SELECT id FROM chapters WHERE novel_id=? AND number=?", (novel_id, chapter_number), fetch="one")
    if not ch:
        return json.dumps({"error": f"章节 {chapter_number} 不存在"}, ensure_ascii=False)
    return _relation_snapshot_by_id(rel["id"], ch["id"], intensity, status, notes)


@mcp.tool
@mcp_tool
def character_increment(novel_name: str, character_name: str,
                        chapter_number: int = 0,
                        location: str = "", arc_phase: str = "",
                        emotional_state: str = "", physical_state: str = "",
                        ability_add: str = "", inventory_add: str = "",
                        knowledge_add: str = "",
                        snapshot_update: str = "",
                        growth_add: str = "") -> str:
    """角色增量更新（只追加，不覆盖档案）。适用于正文写作中角色状态变化。
    叙事状态（location/emotion等）写入 character_state_snapshots，蒸馏字段写入 characters 表。

    参数:
      novel_name: 小说名称
      character_name: 角色名
      chapter_number: 章节序号（叙事状态增量时必填，用于写入快照表）
      location: 新位置（空=沿用最新快照）
      arc_phase: 新弧线阶段（空=沿用最新快照）
      emotional_state: 新情绪（空=沿用最新快照）
      physical_state: 新身体状态（空=沿用最新快照）
      ability_add: 新增能力(JSON字符串, 追加到快照的ability_snapshot)
      inventory_add: 新增物品(JSON字符串, 追加到快照的inventory_snapshot)
      knowledge_add: 新增知识(JSON字符串, 合并到快照的knowledge_snapshot)
      snapshot_update: 蒸馏快照更新(JSON字符串, 合并到characters.current_snapshot)
      growth_add: 成长轨迹追加(JSON字符串, 追加到characters.growth_trajectory数组)
    """
    novel_id = _resolve_novel_id(novel_name)

    try:
        char_id = _resolve_entity(novel_id, "characters", character_name, "角色")
    except NotFoundError as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)

    char = query("SELECT id, current_snapshot, growth_trajectory "
                 "FROM characters WHERE id=?", (char_id,), fetch="one")

    updates = []

    with transaction():
        has_narrative_change = location or arc_phase or emotional_state or physical_state or ability_add or inventory_add or knowledge_add
        if has_narrative_change:
            if not chapter_number:
                return json.dumps({"error": "叙事状态增量需要 chapter_number 参数"}, ensure_ascii=False)
            ch = query("SELECT id FROM chapters WHERE novel_id=? AND number=?", (novel_id, chapter_number), fetch="one")
            if not ch:
                return json.dumps({"error": f"章节 {chapter_number} 不存在"}, ensure_ascii=False)

            base = query(
                "SELECT css.* FROM character_state_snapshots css "
                "JOIN chapters c ON css.chapter_id = c.id "
                "WHERE css.character_id = ? ORDER BY c.number DESC LIMIT 1",
                (char["id"],), fetch="one"
            )

            def _parse_json(text, default):
                if not text:
                    return default
                try:
                    return json.loads(text)
                except (json.JSONDecodeError, TypeError):
                    return default

            base_loc = base["location"] if base else ""
            base_arc = base["arc_phase"] if base else ""
            base_emo = base["emotional_state"] if base else ""
            base_phy = base["physical_state"] if base else ""
            base_abilities = _parse_json(base["ability_snapshot"] if base else "[]", [])
            base_inventory = _parse_json(base["inventory_snapshot"] if base else "[]", [])
            base_knowledge = _parse_json(base["knowledge_snapshot"] if base else "{}", {})

            new_loc = location or base_loc
            new_arc = arc_phase or base_arc
            new_emo = emotional_state or base_emo
            new_phy = physical_state or base_phy
            if ability_add:
                base_abilities.extend(_parse_json(ability_add, []))
            if inventory_add:
                base_inventory.extend(_parse_json(inventory_add, []))
            if knowledge_add:
                base_knowledge.update(_parse_json(knowledge_add, {}))

            _character_snapshot_by_id(
                char["id"], ch["id"],
                new_loc, new_arc, new_emo, new_phy,
                json.dumps(base_abilities, ensure_ascii=False),
                json.dumps(base_inventory, ensure_ascii=False),
                json.dumps(base_knowledge, ensure_ascii=False),
                ""
            )
            updates.append("narrative_snapshot")

        sets = []
        vals = []
        if snapshot_update:
            cur_snap = _parse_json(char.get("current_snapshot") or "{}", {})
            cur_snap.update(_parse_json(snapshot_update, {}))
            sets.append("current_snapshot = ?")
            vals.append(json.dumps(cur_snap, ensure_ascii=False))
            updates.append("current_snapshot")
        if growth_add:
            cur_growth = _parse_json(char.get("growth_trajectory") or "[]", [])
            cur_growth.extend(_parse_json(growth_add, []))
            sets.append("growth_trajectory = ?")
            vals.append(json.dumps(cur_growth, ensure_ascii=False))
            updates.append("growth_trajectory")
        if sets:
            sets.append("updated_at = datetime('now')")
            vals.append(char["id"])
            query(f"UPDATE characters SET {', '.join(sets)} WHERE id = ?", tuple(vals), fetch="none")

    if not updates:
        return json.dumps({"ok": False, "error": "Nothing to update"}, ensure_ascii=False)
    return json.dumps({"ok": True, "character_name": character_name, "updated": updates}, ensure_ascii=False)


@mcp.tool
@mcp_tool
def plot_thread_create(novel_name: str, name: str,
                        thread_type: str = "mainline",
                        description: str = "",
                        start_chapter_id: int = 0,
                        volume_scope: str = "[]",
                        related_characters: str = "[]",
                        related_foreshadows: str = "[]") -> str:
    """创建线索/暗线。thread_type: mainline/subplot/darkline/mystery/clue

    参数:
      novel_name: 小说名称
      name: 线索名称
      thread_type: mainline/subplot/darkline/mystery/clue
      description: 描述
      start_chapter_id: 起始章节ID
      volume_scope: 涉及卷号(JSON数组)
      related_characters: 关联角色(JSON数组)
      related_foreshadows: 关联伏笔ID(JSON数组)
    """
    novel_id = _resolve_novel_id(novel_name)

    r = query(
        "INSERT INTO plot_threads "
        "(novel_id, name, thread_type, description, start_chapter_id, "
        "volume_scope, related_characters, related_foreshadows) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?) "
        "ON CONFLICT (novel_id, name) DO UPDATE SET "
        "thread_type=?, description=?, start_chapter_id=?, "
        "volume_scope=?, related_characters=?, related_foreshadows=?, updated_at=datetime('now')",
        (novel_id, name, thread_type, description, start_chapter_id or None,
         volume_scope, related_characters, related_foreshadows,
         thread_type, description, start_chapter_id or None,
         volume_scope, related_characters, related_foreshadows),
        fetch="insert"
    )
    return json.dumps({"ok": True, "id": r["id"], "name": name}, ensure_ascii=False)


@mcp.tool
@mcp_tool
def plot_thread_list(novel_name: str, thread_type: str = "") -> str:
    """列出线索/暗线。thread_type可选过滤。
      novel_name: 小说名称
    """
    novel_id = _resolve_novel_id(novel_name)
    if thread_type:
        rows = query(
            "SELECT * FROM plot_threads WHERE novel_id = ? AND thread_type = ? ORDER BY id",
            (novel_id, thread_type)
        )
    else:
        rows = query("SELECT * FROM plot_threads WHERE novel_id = ? ORDER BY id", (novel_id,))
    return json.dumps([dict(r) for r in rows], ensure_ascii=False, default=str)


@mcp.tool
@mcp_tool
def plot_thread_update(novel_name: str, thread_id: int, status: str = "",
                       end_chapter_number: int = 0,
                       progress_notes: str = "[]") -> str:
    """更新线索/暗线状态。每卷结束时调用。

    参数:
      novel_name: 小说名称
      thread_id: 线索ID
      status: active/resolved/dormant/abandoned
      end_chapter_number: 结束章节序号
      progress_notes: 进展备注(JSON数组，追加)
    """
    novel_id = _resolve_novel_id(novel_name)
    t = query("SELECT id FROM plot_threads WHERE id = ? AND novel_id = ?",
              (thread_id, novel_id), fetch="one")
    if not t:
        return json.dumps({"ok": False, "error": f"thread {thread_id} not found in novel '{novel_name}'"}, ensure_ascii=False)
    sets = []
    vals = []
    if status:
        sets.append("status = ?")
        vals.append(status)
    if end_chapter_number:
        end_chapter_id = _resolve_chapter_id(novel_name, end_chapter_number)
        sets.append("end_chapter_id = ?")
        vals.append(end_chapter_id)
    if progress_notes and progress_notes != "[]":
        new_notes = json.loads(progress_notes) if isinstance(progress_notes, str) else progress_notes
        current = query("SELECT progress_notes FROM plot_threads WHERE id = ?", (thread_id,), fetch="val")
        existing = json.loads(current) if current and current != "[]" else []
        merged = json.dumps(existing + new_notes, ensure_ascii=False)
        sets.append("progress_notes = ?")
        vals.append(merged)
    if not sets:
        return json.dumps({"ok": False, "error": "Nothing to update"}, ensure_ascii=False)
    sets.append("updated_at = datetime('now')")
    vals.append(thread_id)
    with transaction():
        query(f"UPDATE plot_threads SET {', '.join(sets)} WHERE id = ?", tuple(vals), fetch="none")
    return json.dumps({"ok": True, "thread_id": thread_id}, ensure_ascii=False)


def _character_snapshot_by_id(character_id: int, chapter_id: int,
                       location: str = "", arc_phase: str = "",
                       emotional_state: str = "", physical_state: str = "",
                       ability_snapshot: str = "[]", inventory_snapshot: str = "[]",
                       knowledge_snapshot: str = "{}", notes: str = "") -> str:
    query(
        "INSERT INTO character_state_snapshots "
        "(character_id, chapter_id, location, arc_phase, emotional_state, physical_state, "
        "ability_snapshot, inventory_snapshot, knowledge_snapshot, notes) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
        "ON CONFLICT (character_id, chapter_id) DO UPDATE SET "
        "location=?, arc_phase=?, emotional_state=?, physical_state=?, "
        "ability_snapshot=?, inventory_snapshot=?, knowledge_snapshot=?, notes=?",
        (character_id, chapter_id, location, arc_phase, emotional_state, physical_state,
         ability_snapshot, inventory_snapshot, knowledge_snapshot, notes,
         location, arc_phase, emotional_state, physical_state,
         ability_snapshot, inventory_snapshot, knowledge_snapshot, notes),
        fetch="none"
    )
    return json.dumps({"ok": True, "character_id": character_id, "chapter_id": chapter_id}, ensure_ascii=False)


def _relation_snapshot_by_id(relation_id: int, chapter_id: int,
                      intensity: int = 5, status: str = "active",
                      notes: str = "") -> str:
    query(
        "INSERT INTO relation_state_snapshots "
        "(relation_id, chapter_id, intensity, status, notes) "
        "VALUES (?, ?, ?, ?, ?) "
        "ON CONFLICT (relation_id, chapter_id) DO UPDATE SET "
        "intensity=?, status=?, notes=?",
        (relation_id, chapter_id, intensity, status, notes,
         intensity, status, notes),
        fetch="none"
    )
    return json.dumps({"ok": True, "relation_id": relation_id, "chapter_id": chapter_id}, ensure_ascii=False)


@mcp.tool
@mcp_tool
def character_batch_detail(novel_name: str, character_names: list) -> str:
    """批量获取多个角色的完整档案。避免N次单独调用。
      novel_name: 小说名称
      character_names: 角色名列表，如 ["沈野", "方岩", "陆沉"]
    """
    novel_id = _resolve_novel_id(novel_name)
    if not character_names:
        return json.dumps([], ensure_ascii=False)

    placeholders = ",".join(["?"] * len(character_names))
    rows = query(
        f"SELECT * FROM characters WHERE novel_id = ? AND is_active = 1 AND name IN ({placeholders})",
        (novel_id, *character_names)
    )
    result = []
    for row in rows:
        char = dict(row)
        rels = query(
            "SELECT cr.relation_type, cr.description, cr.intensity, cr.subtext_design, "
            "c1.name as from_name, c2.name as to_name "
            "FROM character_relations cr "
            "JOIN characters c1 ON cr.from_character_id = c1.id "
            "JOIN characters c2 ON cr.to_character_id = c2.id "
            "WHERE cr.novel_id = ? AND (cr.from_character_id = ? OR cr.to_character_id = ?) "
            "AND cr.status = 'active' ORDER BY cr.intensity DESC",
            (novel_id, char["id"], char["id"])
        )
        char["relations"] = [dict(r) for r in rels]
        result.append(char)
    return json.dumps(result, ensure_ascii=False, default=str)


# ═══════════════════════════════════════════════════════
# Character Distillation Evolution
# ═══════════════════════════════════════════════════════

@mcp.tool
@mcp_tool
def distillation_evolve(novel_name: str, character_name: str, chapter_number: int,
                        decision_delta: str = "[]", new_knowledge: str = "[]",
                        changed_beliefs: str = "[]", relation_shifts: str = "[]",
                        voice_changes: str = "{}", ability_changes: str = "{}",
                        arc_transition: str = "{}", key_decision: str = "{}",
                        notes: str = "") -> str:
    """记录人物蒸馏模型的演化增量。每章写完后调用，追踪人物决策、认知、关系、声音的演变。

    参数:
      novel_name: 小说名称
      character_name: 角色名
      chapter_number: 章节序号
      decision_delta: 决策引擎变化(JSON数组)。如 [{"trigger": "得知真相", "rule_name": "保护城镇", "before": "默默观察", "after": "主动警告"}]
      new_knowledge: 新获取信息(JSON数组)。如 ["焱的真实目的", "教会秘密"]
      changed_beliefs: 信念变化(JSON数组)。如 [{"belief": "人类值得保护", "before": true, "after": false, "reason": "被保护的人杀死了它"}]
      relation_shifts: 关系变化(JSON数组)。如 [{"target": "沈野", "aspect": "信任", "before": 5, "after": 8}]
      voice_changes: 声音指纹变化(JSON对象)。如 {"pace_change": "从沉默变急促", "new_habits": ["开始反问"]}
      ability_changes: 能力变化(JSON对象)。如 {"unlocked": ["情绪共鸣"], "weakened": ["拟态稳定性"]}
      arc_transition: 弧线阶段推进(JSON对象)。如 {"from": "渗透潜伏", "to": "身份暴露", "trigger": "兽潮中被迫使用真身"}
      key_decision: 本章关键抉择(JSON对象)。如 {"situation": "是否暴露身份", "choice": "暴露", "alternatives": ["继续隐藏"], "consequence": "被人类杀死"}
      notes: 写作备注
    """
    novel_id = _resolve_novel_id(novel_name)

    try:
        char_id = _resolve_entity(novel_id, "characters", character_name, "角色")
    except NotFoundError as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    ch = query("SELECT id FROM chapters WHERE novel_id=? AND number=?", (novel_id, chapter_number), fetch="one")
    if not ch:
        return json.dumps({"error": f"章节 {chapter_number} 不存在"}, ensure_ascii=False)

    with transaction():
        query(
            "INSERT INTO character_distillation_evolution "
            "(novel_id, character_id, chapter_id, decision_delta, new_knowledge, "
            "changed_beliefs, relation_shifts, voice_changes, ability_changes, "
            "arc_transition, key_decision, notes) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT DO NOTHING",
            (novel_id, char_id, ch["id"],
             decision_delta, new_knowledge, changed_beliefs, relation_shifts,
             voice_changes, ability_changes, arc_transition, key_decision, notes),
            fetch="none"
        )
    return json.dumps({"ok": True, "character": character_name, "chapter": chapter_number}, ensure_ascii=False)


@mcp.tool
@mcp_tool
def distillation_get(novel_name: str, character_name: str, chapter_number: int = 0) -> str:
    """获取人物蒸馏演化记录。可查询特定章节或全部历史。

    参数:
      novel_name: 小说名称
      character_name: 角色名
      chapter_number: 章节序号，0=返回全部历史
    """
    novel_id = _resolve_novel_id(novel_name)

    try:
        char_id = _resolve_entity(novel_id, "characters", character_name, "角色")
    except NotFoundError as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)

    if chapter_number > 0:
        ch = query("SELECT id FROM chapters WHERE novel_id=? AND number=?", (novel_id, chapter_number), fetch="one")
        if not ch:
            return json.dumps({"error": f"章节 {chapter_number} 不存在"}, ensure_ascii=False)
        rows = query(
            "SELECT cde.*, c.number as chapter_number "
            "FROM character_distillation_evolution cde "
            "JOIN chapters c ON cde.chapter_id = c.id "
            "WHERE cde.character_id = ? AND cde.chapter_id = ? "
            "ORDER BY c.number",
            (char_id, ch["id"])
        )
    else:
        rows = query(
            "SELECT cde.*, c.number as chapter_number "
            "FROM character_distillation_evolution cde "
            "JOIN chapters c ON cde.chapter_id = c.id "
            "WHERE cde.character_id = ? "
            "ORDER BY c.number",
            (char_id,)
        )

    result = {
        "character": character_name,
        "chapter_filter": chapter_number if chapter_number > 0 else "all",
        "records": [dict(r) for r in rows]
    }
    return json.dumps(result, ensure_ascii=False, default=str)


@mcp.tool
@mcp_tool
def distillation_timeline(novel_name: str, character_name: str,
                          dimension: str = "decision_delta") -> str:
    """获取人物在某一维度的完整时间线。用于分析人物如何逐步演变。

    参数:
      novel_name: 小说名称
      character_name: 角色名
      dimension: 维度名。可选: decision_delta/new_knowledge/changed_beliefs/relation_shifts/voice_changes/ability_changes/arc_transition/key_decision
    """
    novel_id = _resolve_novel_id(novel_name)

    try:
        char_id = _resolve_entity(novel_id, "characters", character_name, "角色")
    except NotFoundError as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)

    _COL_MAP = {
        "decision_delta": "decision_delta",
        "new_knowledge": "new_knowledge",
        "changed_beliefs": "changed_beliefs",
        "relation_shifts": "relation_shifts",
        "voice_changes": "voice_changes",
        "ability_changes": "ability_changes",
        "arc_transition": "arc_transition",
        "key_decision": "key_decision",
    }
    col = _COL_MAP.get(dimension)
    if not col:
        valid = ", ".join(_COL_MAP)
        return json.dumps({"error": f"无效维度 '{dimension}'。可选: {valid}"}, ensure_ascii=False)

    sql = (
        f"SELECT cde.{col} as value, c.number as chapter_number, c.title as chapter_title "
        "FROM character_distillation_evolution cde "
        "JOIN chapters c ON cde.chapter_id = c.id "
        f"WHERE cde.character_id = ? AND cde.{col} IS NOT NULL "
        f"AND cde.{col} != '{{}}' AND cde.{col} != '[]' "
        "ORDER BY c.number"
    )
    rows = query(sql, (char_id,))

    result = {
        "character": character_name,
        "dimension": dimension,
        "timeline": [dict(r) for r in rows]
    }
    return json.dumps(result, ensure_ascii=False, default=str)


@mcp.tool
@mcp_tool
def distillation_compare(novel_name: str, character_name: str,
                         chapter_a: int, chapter_b: int) -> str:
    """对比人物在两个章节之间的蒸馏模型变化。用于检验人物一致性/演变合理性。

    参数:
      novel_name: 小说名称
      character_name: 角色名
      chapter_a: 较早章节号
      chapter_b: 较晚章节号
    """
    novel_id = _resolve_novel_id(novel_name)

    try:
        char_id = _resolve_entity(novel_id, "characters", character_name, "角色")
    except NotFoundError as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)

    ch_a = query("SELECT id, number FROM chapters WHERE novel_id=? AND number=?", (novel_id, chapter_a), fetch="one")
    ch_b = query("SELECT id, number FROM chapters WHERE novel_id=? AND number=?", (novel_id, chapter_b), fetch="one")
    if not ch_a or not ch_b:
        missing = []
        if not ch_a: missing.append(chapter_a)
        if not ch_b: missing.append(chapter_b)
        return json.dumps({"error": f"章节不存在: {missing}"}, ensure_ascii=False)

    snap_a = query(
        "SELECT * FROM character_state_snapshots WHERE character_id=? AND chapter_id=?",
        (char_id, ch_a["id"]), fetch="one"
    )
    snap_b = query(
        "SELECT * FROM character_state_snapshots WHERE character_id=? AND chapter_id=?",
        (char_id, ch_b["id"]), fetch="one"
    )

    evolutions = query(
        "SELECT cde.*, c.number as chapter_number "
        "FROM character_distillation_evolution cde "
        "JOIN chapters c ON cde.chapter_id = c.id "
        "WHERE cde.character_id = ? AND c.number > ? AND c.number <= ? "
        "ORDER BY c.number",
        (char_id, chapter_a, chapter_b)
    )

    result = {
        "character": character_name,
        "range": f"Ch{chapter_a} → Ch{chapter_b}",
        "snapshot_a": dict(snap_a) if snap_a else None,
        "snapshot_b": dict(snap_b) if snap_b else None,
        "evolutions_between": [dict(r) for r in evolutions]
    }
    return json.dumps(result, ensure_ascii=False, default=str)
