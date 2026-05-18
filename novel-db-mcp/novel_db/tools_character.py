import json

from .db import mcp, query
from .resolvers import _resolve_novel_id, _resolve_chapter_id
from .sync import _record_db_hash


@mcp.tool
def character_create(novel_name: str, name: str, role: str = "npc",
                     faction_id: int = None, race: str = "", ability_level: str = "",
                     appearance: str = "", personality: str = "", background: str = "",
                     goals: str = "", weaknesses: str = "", speech_style: str = "",
                     catchphrase: str = "", arc_notes: str = "",
                     first_appearance_chapter: int = None,
                     appearance_detail: str = "", decision_engine: str = "",
                     voice_fingerprint: str = "", ability_system: str = "",
                     behavior_pattern: str = "", current_snapshot: str = "",
                     growth_trajectory: str = "") -> str:
    """创建人物。role: protagonist/ally/antagonist/mentor/rival/love_interest/npc
    appearance_detail/decision_engine/voice_fingerprint/ability_system/behavior_pattern/current_snapshot/growth_trajectory: JSON字符串
      novel_name: 小说名称
    """
    novel_id = _resolve_novel_id(novel_name)

    _json_fields = {}
    if appearance_detail:
        _json_fields["appearance_detail"] = json.loads(appearance_detail)
    if decision_engine:
        _json_fields["decision_engine"] = json.loads(decision_engine)
    if voice_fingerprint:
        _json_fields["voice_fingerprint"] = json.loads(voice_fingerprint)
    if ability_system:
        _json_fields["ability_system"] = json.loads(ability_system)
    if behavior_pattern:
        _json_fields["behavior_pattern"] = json.loads(behavior_pattern)
    if current_snapshot:
        _json_fields["current_snapshot"] = json.loads(current_snapshot)
    if growth_trajectory:
        _json_fields["growth_trajectory"] = json.loads(growth_trajectory)

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

    placeholders = ",".join(["%s"] * len(all_vals))
    r = query(
        f"INSERT INTO characters ({all_cols}) VALUES ({placeholders}) RETURNING id",
        all_vals, fetch="one"
    )
    _record_db_hash(novel_id, "character", name, json.dumps({"name": name, "role": role, "race": race, "appearance": appearance}, ensure_ascii=False))
    return json.dumps({"ok": True, "id": r["id"], "name": name}, ensure_ascii=False)


def _character_update_by_id(character_id: int, name: str = "", role: str = "", faction_id: int = 0,
                     race: str = "", ability_level: str = "", status: str = "",
                     appearance: str = "", personality: str = "", background: str = "",
                     goals: str = "", weaknesses: str = "", speech_style: str = "",
                     catchphrase: str = "", arc_notes: str = "", is_active: bool = True,
                     _status_json: str = "",
                     appearance_detail: str = "", decision_engine: str = "",
                     voice_fingerprint: str = "", ability_system: str = "",
                     behavior_pattern: str = "", current_snapshot: str = "",
                     growth_trajectory: str = "") -> str:
    fields = {}
    if name: fields["name"] = name
    if role: fields["role"] = role
    if faction_id: fields["faction_id"] = faction_id
    if race: fields["race"] = race
    if ability_level: fields["ability_level"] = ability_level
    if status: fields["status"] = status
    if _status_json: fields["status"] = _status_json
    if appearance: fields["appearance"] = appearance
    if personality: fields["personality"] = personality
    if background: fields["background"] = background
    if goals: fields["goals"] = goals
    if weaknesses: fields["weaknesses"] = weaknesses
    if speech_style: fields["speech_style"] = speech_style
    if catchphrase: fields["catchphrase"] = catchphrase
    if arc_notes: fields["arc_notes"] = arc_notes
    if not is_active: fields["is_active"] = False
    if appearance_detail: fields["appearance_detail"] = json.loads(appearance_detail)
    if decision_engine: fields["decision_engine"] = json.loads(decision_engine)
    if voice_fingerprint: fields["voice_fingerprint"] = json.loads(voice_fingerprint)
    if ability_system: fields["ability_system"] = json.loads(ability_system)
    if behavior_pattern: fields["behavior_pattern"] = json.loads(behavior_pattern)
    if current_snapshot: fields["current_snapshot"] = json.loads(current_snapshot)
    if growth_trajectory: fields["growth_trajectory"] = json.loads(growth_trajectory)
    if not fields:
        return json.dumps({"ok": False, "error": "no valid fields"}, ensure_ascii=False)
    sets = [f"{k} = %s" for k in fields]
    vals = list(fields.values()) + [character_id]
    query(f"UPDATE characters SET {', '.join(sets)}, updated_at = NOW() WHERE id = %s", tuple(vals), fetch="none")
    char = query("SELECT novel_id, name FROM characters WHERE id = %s", (character_id,), fetch="one")
    if char:
        _record_db_hash(char["novel_id"], "character", char["name"], json.dumps(fields, ensure_ascii=False))
    return json.dumps({"ok": True}, ensure_ascii=False)


@mcp.tool
def character_list(novel_name: str, role: str = "") -> str:
    """列出小说人物。role 可选过滤
      novel_name: 小说名称
    """
    novel_id = _resolve_novel_id(novel_name)
    if role:
        rows = query("SELECT * FROM characters WHERE novel_id = %s AND role = %s AND is_active = TRUE ORDER BY role, name",
                     (novel_id, role))
    else:
        rows = query("SELECT * FROM characters WHERE novel_id = %s AND is_active = TRUE ORDER BY role, name",
                     (novel_id,))
    return json.dumps([dict(r) for r in rows], ensure_ascii=False, default=str)


def _character_get_by_id(character_id: int) -> str:
    r = query("SELECT * FROM characters WHERE id = %s", (character_id,), fetch="one")
    return json.dumps(dict(r) if r else {"error": "not found"}, ensure_ascii=False, default=str)


def _character_detail_by_id(character_id: int, chapter_number: int = None) -> str:
    char = query("SELECT * FROM characters WHERE id = %s", (character_id,), fetch="one")
    if not char:
        return json.dumps({"error": "character not found"}, ensure_ascii=False)

    result = dict(char)

    rels = query(
        "SELECT cr.relation_type, cr.description, cr.intensity, cr.status, "
        "c1.name as from_name, c2.name as to_name "
        "FROM character_relations cr "
        "JOIN characters c1 ON cr.from_character_id = c1.id "
        "JOIN characters c2 ON cr.to_character_id = c2.id "
        "WHERE cr.novel_id = %s AND (c1.id = %s OR c2.id = %s)",
        (char["novel_id"], character_id, character_id)
    )
    result["relations"] = [dict(r) for r in rels]

    if chapter_number:
        snap = query(
            "SELECT css.* FROM character_state_snapshots css "
            "JOIN chapters c ON css.chapter_id = c.id "
            "WHERE css.character_id = %s AND c.number <= %s "
            "ORDER BY c.number DESC LIMIT 1",
            (character_id, chapter_number), fetch="one"
        )
        if snap:
            result["snapshot"] = dict(snap)
    else:
        snap = query(
            "SELECT css.*, c.number as chapter_number FROM character_state_snapshots css "
            "JOIN chapters c ON css.chapter_id = c.id "
            "WHERE css.character_id = %s ORDER BY c.number DESC LIMIT 1",
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
        "VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id",
        (novel_id, from_character_id, to_character_id, relation_type,
         description, chapter_established, intensity), fetch="one"
    )
    return json.dumps({"ok": True, "id": r["id"]}, ensure_ascii=False)


@mcp.tool
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
        "WHERE cr.novel_id = %s ORDER BY cr.relation_type",
        (novel_id,)
    )
    return json.dumps([dict(r) for r in rows], ensure_ascii=False, default=str)


@mcp.tool
def character_get(novel_name: str, character_name: str) -> str:
    """按角色名获取人物详情（无需ID）。
      novel_name: 小说名称
      character_name: 角色名
    """
    novel_id = _resolve_novel_id(novel_name)
    char = query("SELECT id FROM characters WHERE novel_id=%s AND name=%s", (novel_id, character_name), fetch="one")
    if not char:
        return json.dumps({"error": f"角色 '{character_name}' 不存在"}, ensure_ascii=False)
    return _character_get_by_id(char["id"])


@mcp.tool
def character_detail(novel_name: str, character_name: str, chapter_number: int = None) -> str:
    """按角色名获取角色蒸馏卡片（无需ID）。
      novel_name: 小说名称
      character_name: 角色名
      chapter_number: 章节序号（可选，用于获取该章状态快照）
    """
    novel_id = _resolve_novel_id(novel_name)
    char = query("SELECT id FROM characters WHERE novel_id=%s AND name=%s", (novel_id, character_name), fetch="one")
    if not char:
        return json.dumps({"error": f"角色 '{character_name}' 不存在"}, ensure_ascii=False)
    return _character_detail_by_id(char["id"], chapter_number)


@mcp.tool
def character_update(novel_name: str, character_name: str, name: str = "", role: str = "", faction_id: int = 0,
                             race: str = "", ability_level: str = "", status: str = "",
                             appearance: str = "", personality: str = "", background: str = "",
                             goals: str = "", weaknesses: str = "", speech_style: str = "",
                             catchphrase: str = "", arc_notes: str = "", is_active: bool = True,
                             _status_json: str = "",
                             appearance_detail: str = "", decision_engine: str = "",
                             voice_fingerprint: str = "", ability_system: str = "",
                             behavior_pattern: str = "", current_snapshot: str = "",
                             growth_trajectory: str = "") -> str:
    """按角色名更新人物信息（无需ID）。传入需要修改的字段，空值/零值会被忽略。
      novel_name: 小说名称
      character_name: 角色名
    """
    novel_id = _resolve_novel_id(novel_name)
    char = query("SELECT id FROM characters WHERE novel_id=%s AND name=%s", (novel_id, character_name), fetch="one")
    if not char:
        return json.dumps({"error": f"角色 '{character_name}' 不存在"}, ensure_ascii=False)
    return _character_update_by_id(char["id"], name, role, faction_id, race, ability_level, status,
                            appearance, personality, background, goals, weaknesses, speech_style,
                            catchphrase, arc_notes, is_active, _status_json,
                            appearance_detail, decision_engine, voice_fingerprint, ability_system,
                            behavior_pattern, current_snapshot, growth_trajectory)


@mcp.tool
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
    from_char = query("SELECT id FROM characters WHERE novel_id=%s AND name=%s", (novel_id, from_name), fetch="one")
    if not from_char:
        return json.dumps({"error": f"角色 '{from_name}' 不存在"}, ensure_ascii=False)
    to_char = query("SELECT id FROM characters WHERE novel_id=%s AND name=%s", (novel_id, to_name), fetch="one")
    if not to_char:
        return json.dumps({"error": f"角色 '{to_name}' 不存在"}, ensure_ascii=False)
    return _relation_create_by_id(novel_name, from_char["id"], to_char["id"], relation_type, description, chapter_established, intensity)


@mcp.tool
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
        "WHERE cr.novel_id=%s AND c1.name=%s AND c2.name=%s",
        (novel_id, from_name, to_name), fetch="one"
    )
    if not rel:
        return json.dumps({"error": f"关系 '{from_name}'→'{to_name}' 不存在"}, ensure_ascii=False)
    sets = []
    vals = []
    if relation_type:
        sets.append("relation_type = %s")
        vals.append(relation_type)
    if description:
        sets.append("description = %s")
        vals.append(description)
    if intensity > 0:
        old_i = rel["cur_intensity"]
        sets.append("intensity = %s")
        vals.append(intensity)
        sets.append("intensity_change_log = COALESCE(intensity_change_log, '[]'::jsonb) || %s::jsonb")
        vals.append(json.dumps([{"from": old_i, "to": intensity}]))
    if status:
        sets.append("status = %s")
        vals.append(status)
    if not sets:
        return json.dumps({"ok": False, "error": "Nothing to update"}, ensure_ascii=False)
    vals.append(rel["id"])
    query(f"UPDATE character_relations SET {', '.join(sets)} WHERE id = %s", tuple(vals), fetch="none")
    return json.dumps({"ok": True, "from": from_name, "to": to_name}, ensure_ascii=False)


@mcp.tool
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

    char = query("SELECT id FROM characters WHERE novel_id=%s AND name=%s", (novel_id, character_name), fetch="one")
    if not char:
        return json.dumps({"error": f"角色 '{character_name}' 不存在"}, ensure_ascii=False)
    ch = query("SELECT id FROM chapters WHERE novel_id=%s AND number=%s", (novel_id, chapter_number), fetch="one")
    if not ch:
        return json.dumps({"error": f"章节 {chapter_number} 不存在"}, ensure_ascii=False)
    return _character_snapshot_by_id(char["id"], ch["id"], location, arc_phase, emotional_state,
                             physical_state, ability_snapshot, inventory_snapshot, knowledge_snapshot, notes)


@mcp.tool
def character_get_latest(novel_name: str, character_name: str) -> str:
    """获取角色最新状态快照（按名称查询，无需ID）。

    参数:
      novel_name: 小说名称
      character_name: 角色名
    """
    novel_id = _resolve_novel_id(novel_name)

    char = query("SELECT id FROM characters WHERE novel_id=%s AND name=%s", (novel_id, character_name), fetch="one")
    if not char:
        return json.dumps({"error": f"角色 '{character_name}' 不存在"}, ensure_ascii=False)
    r = query(
        "SELECT css.*, c.number as chapter_number FROM character_state_snapshots css "
        "JOIN chapters c ON css.chapter_id = c.id "
        "WHERE css.character_id = %s ORDER BY c.number DESC LIMIT 1",
        (char["id"],), fetch="one"
    )
    if not r:
        return json.dumps({"error": f"'{character_name}' 暂无快照", "character_name": character_name}, ensure_ascii=False)
    result = dict(r)
    result["character_name"] = character_name
    return json.dumps(result, ensure_ascii=False, default=str)


@mcp.tool
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
        "WHERE cr.novel_id=%s AND c1.name=%s AND c2.name=%s",
        (novel_id, from_name, to_name), fetch="one"
    )
    if not rel:
        return json.dumps({"error": f"关系 '{from_name}'→'{to_name}' 不存在"}, ensure_ascii=False)
    ch = query("SELECT id FROM chapters WHERE novel_id=%s AND number=%s", (novel_id, chapter_number), fetch="one")
    if not ch:
        return json.dumps({"error": f"章节 {chapter_number} 不存在"}, ensure_ascii=False)
    return _relation_snapshot_by_id(rel["id"], ch["id"], intensity, status, notes)


@mcp.tool
def character_increment(novel_name: str, character_name: str,
                        location: str = "", arc_phase: str = "",
                        emotional_state: str = "", physical_state: str = "",
                        ability_add: str = "", inventory_add: str = "",
                        knowledge_add: str = "",
                        snapshot_update: str = "",
                        growth_add: str = "") -> str:
    """角色增量更新（只追加，不覆盖档案）。适用于正文写作中角色状态变化。

    参数:
      novel_name: 小说名称
      character_name: 角色名
      location: 新位置（空=不变）
      arc_phase: 新弧线阶段（空=不变）
      emotional_state: 新情绪（空=不变）
      physical_state: 新身体状态（空=不变）
      ability_add: 新增能力(JSON字符串, 追加到ability_progression)
      inventory_add: 新增物品(JSON字符串, 追加到inventory)
      knowledge_add: 新增知识(JSON字符串, 合并到knowledge_state)
      snapshot_update: 当前快照更新(JSON字符串, 合并到current_snapshot)
      growth_add: 成长轨迹追加(JSON字符串, 追加到growth_trajectory数组)
    """
    novel_id = _resolve_novel_id(novel_name)

    char = query("SELECT id, current_location, current_arc_phase, emotional_state, physical_state, "
                 "ability_progression, inventory, knowledge_state, current_snapshot, growth_trajectory "
                 "FROM characters WHERE novel_id=%s AND name=%s", (novel_id, character_name), fetch="one")
    if not char:
        return json.dumps({"error": f"角色 '{character_name}' 不存在"}, ensure_ascii=False)
    sets = []
    vals = []
    if location:
        sets.append("current_location = %s")
        vals.append(location)
    if arc_phase:
        sets.append("current_arc_phase = %s")
        vals.append(arc_phase)
    if emotional_state:
        sets.append("emotional_state = %s")
        vals.append(emotional_state)
    if physical_state:
        sets.append("physical_state = %s")
        vals.append(physical_state)
    if ability_add:
        sets.append("ability_progression = COALESCE(ability_progression, '[]'::jsonb) || %s::jsonb")
        vals.append(ability_add)
    if inventory_add:
        sets.append("inventory = COALESCE(inventory, '[]'::jsonb) || %s::jsonb")
        vals.append(inventory_add)
    if knowledge_add:
        sets.append("knowledge_state = COALESCE(knowledge_state, '{}'::jsonb) || %s::jsonb")
        vals.append(knowledge_add)
    if snapshot_update:
        sets.append("current_snapshot = COALESCE(current_snapshot, '{}'::jsonb) || %s::jsonb")
        vals.append(snapshot_update)
    if growth_add:
        sets.append("growth_trajectory = COALESCE(growth_trajectory, '[]'::jsonb) || %s::jsonb")
        vals.append(growth_add)
    if not sets:
        return json.dumps({"ok": False, "error": "Nothing to update"}, ensure_ascii=False)
    sets.append("updated_at = NOW()")
    vals.append(char["id"])
    query(f"UPDATE characters SET {', '.join(sets)} WHERE id = %s", tuple(vals), fetch="none")
    return json.dumps({"ok": True, "character_name": character_name, "updated_fields": [s.split("=")[0].strip() for s in sets[:-1]]}, ensure_ascii=False)


@mcp.tool
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
        "VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s::jsonb) "
        "ON CONFLICT (novel_id, name) DO UPDATE SET "
        "thread_type=%s, description=%s, start_chapter_id=%s, "
        "volume_scope=%s::jsonb, related_characters=%s::jsonb, related_foreshadows=%s::jsonb, updated_at=NOW() "
        "RETURNING id",
        (novel_id, name, thread_type, description, start_chapter_id or None,
         volume_scope, related_characters, related_foreshadows,
         thread_type, description, start_chapter_id or None,
         volume_scope, related_characters, related_foreshadows),
        fetch="one"
    )
    return json.dumps({"ok": True, "id": r["id"], "name": name}, ensure_ascii=False)


@mcp.tool
def plot_thread_list(novel_name: str, thread_type: str = "") -> str:
    """列出线索/暗线。thread_type可选过滤。
      novel_name: 小说名称
    """
    novel_id = _resolve_novel_id(novel_name)
    if thread_type:
        rows = query(
            "SELECT * FROM plot_threads WHERE novel_id = %s AND thread_type = %s ORDER BY id",
            (novel_id, thread_type)
        )
    else:
        rows = query("SELECT * FROM plot_threads WHERE novel_id = %s ORDER BY id", (novel_id,))
    return json.dumps([dict(r) for r in rows], ensure_ascii=False, default=str)


@mcp.tool
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
    t = query("SELECT id FROM plot_threads WHERE id = %s AND novel_id = %s",
              (thread_id, novel_id), fetch="one")
    if not t:
        return json.dumps({"ok": False, "error": f"thread {thread_id} not found in novel '{novel_name}'"}, ensure_ascii=False)
    sets = []
    vals = []
    if status:
        sets.append("status = %s")
        vals.append(status)
    if end_chapter_number:
        end_chapter_id = _resolve_chapter_id(novel_name, end_chapter_number)
        sets.append("end_chapter_id = %s")
        vals.append(end_chapter_id)
    if progress_notes and progress_notes != "[]":
        sets.append("progress_notes = progress_notes || %s::jsonb")
        vals.append(progress_notes)
    if not sets:
        return json.dumps({"ok": False, "error": "Nothing to update"}, ensure_ascii=False)
    sets.append("updated_at = NOW()")
    vals.append(thread_id)
    query(f"UPDATE plot_threads SET {', '.join(sets)} WHERE id = %s", tuple(vals), fetch="none")
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
        "VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s::jsonb, %s) "
        "ON CONFLICT (character_id, chapter_id) DO UPDATE SET "
        "location=%s, arc_phase=%s, emotional_state=%s, physical_state=%s, "
        "ability_snapshot=%s::jsonb, inventory_snapshot=%s::jsonb, knowledge_snapshot=%s::jsonb, notes=%s",
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
        "VALUES (%s, %s, %s, %s, %s) "
        "ON CONFLICT (relation_id, chapter_id) DO UPDATE SET "
        "intensity=%s, status=%s, notes=%s",
        (relation_id, chapter_id, intensity, status, notes,
         intensity, status, notes),
        fetch="none"
    )
    return json.dumps({"ok": True, "relation_id": relation_id, "chapter_id": chapter_id}, ensure_ascii=False)
