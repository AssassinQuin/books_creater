import json

from .db import mcp, query, transaction
from .resolvers import _resolve_novel_id

# JSON-type fields that need json.dumps serialization
_JSON_FIELDS = {
    'main_plotlines', 'act_intro', 'act_rise', 'act_twist', 'act_resolution',
    'character_arcs', 'interaction_matrix', 'boundaries', 'suspense_anchors',
    'key_dialogues', 'writing_priorities', 'hard_constraints',
    'next_volume_bridge', 'info_pacing', 'rhythm_allocation',
}
# Plain text fields — empty string means "no update"
_TEXT_FIELDS = {
    'title', 'notes', 'core_emotion', 'pov_anchor',
    'time_span', 'voice_mapping', 'causal_chain',
}


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
        "VALUES (?, ?, ?, ?, ?) ON CONFLICT (novel_id, number) "
        "DO UPDATE SET title = ?, main_plotlines = ?, notes = ?, updated_at = datetime('now')",
        (novel_id, number, title, mp, notes, title, mp, notes), fetch="insert"
    )
    return json.dumps({"ok": True, "id": r, "number": number}, ensure_ascii=False)


@mcp.tool
def volume_list(novel_name: str) -> str:
    """列出小说所有卷
      novel_name: 小说名称
    """
    novel_id = _resolve_novel_id(novel_name)

    rows = query(
        "SELECT v.*, "
        "(SELECT COUNT(*) FROM chapters WHERE volume_id = v.id) as chapter_count "
        "FROM volumes v WHERE v.novel_id = ? ORDER BY v.number",
        (novel_id,)
    )
    return json.dumps([dict(r) for r in rows], ensure_ascii=False, default=str)


def _volume_get_by_id(volume_id: int) -> str:
    v = query("SELECT * FROM volumes WHERE id = ?", (volume_id,), fetch="one")
    if not v:
        return json.dumps({"error": "not found"}, ensure_ascii=False)
    chapters = query(
        "SELECT id, number, title, status, chapter_type FROM chapters "
        "WHERE volume_id = ? ORDER BY number", (volume_id,)
    )
    result = dict(v)
    result["chapters"] = [dict(c) for c in chapters]
    return json.dumps(result, ensure_ascii=False, default=str)


def _volume_update_by_id(volume_id: int, **kwargs) -> str:
    fields = {}
    for key, val in kwargs.items():
        if key in _JSON_FIELDS:
            if val is None:
                continue
            fields[key] = json.dumps(val, ensure_ascii=False)
        elif key in _TEXT_FIELDS:
            if not val:
                continue
            fields[key] = val
        else:
            continue

    if not fields:
        return json.dumps({"ok": False, "error": "no valid fields"}, ensure_ascii=False)
    sets = [f"{k} = ?" for k in fields]
    vals = list(fields.values()) + [volume_id]
    query(f"UPDATE volumes SET {', '.join(sets)}, updated_at = datetime('now') WHERE id = ?", tuple(vals), fetch="none")
    return json.dumps({"ok": True}, ensure_ascii=False)


@mcp.tool
def volume_get(novel_name: str, number: int) -> str:
    """按卷号获取卷详情（无需volume_id）。
      novel_name: 小说名称
      number: 卷号（如1, 2, 3）
    """
    novel_id = _resolve_novel_id(novel_name)
    vol = query("SELECT id FROM volumes WHERE novel_id=? AND number=?", (novel_id, number), fetch="one")
    if not vol:
        return json.dumps({"error": f"卷 {number} 不存在"}, ensure_ascii=False)
    return _volume_get_by_id(vol["id"])


@mcp.tool
def volume_update(novel_name: str, number: int, title: str = "",
                  main_plotlines: list = None, notes: str = "",
                  core_emotion: str = "", pov_anchor: str = "",
                  time_span: str = "", voice_mapping: str = "",
                  causal_chain: str = "",
                  act_intro: dict = None, act_rise: dict = None,
                  act_twist: dict = None, act_resolution: dict = None,
                  character_arcs: list = None, interaction_matrix: list = None,
                  boundaries: list = None, suspense_anchors: dict = None,
                  key_dialogues: list = None, writing_priorities: dict = None,
                  hard_constraints: dict = None,
                  next_volume_bridge: list = None, info_pacing: list = None,
                  rhythm_allocation: list = None) -> str:
    """按卷号更新卷信息（无需volume_id）。传入需要修改的字段，空值会被忽略。支持富数据字段（因果链/四幕/人物弧光等）。
      novel_name: 小说名称
      number: 卷号
      core_emotion: 核心情绪（如"紧迫——妹妹要死了"）
      causal_chain: 卷级因果链（纯文本段落）
      act_intro: 起段数据 {"prose":"","events":[],"feibi_notes":[]}
      act_rise: 承段数据
      act_twist: 转段数据
      act_resolution: 合段数据
      character_arcs: 人物弧光表 [{"角色":"","卷初状态":"","触发事件":"","卷末状态":""}]
      interaction_matrix: 人物互动矩阵
      boundaries: "不做的"边界清单 ["...",...]
      suspense_anchors: 悬念锚点 {"answered":[],"new_questions":[]}
      key_dialogues: 核心对话锚点
      writing_priorities: 写作优先级 {"P0":[],"P1":[],"P2":[]}
      hard_constraints: 硬约束自检数据
      next_volume_bridge: 下卷衔接表
      info_pacing: 信息投放节奏
      rhythm_allocation: 节奏分配
    """
    novel_id = _resolve_novel_id(novel_name)
    vol = query("SELECT id FROM volumes WHERE novel_id=? AND number=?", (novel_id, number), fetch="one")
    if not vol:
        return json.dumps({"error": f"卷 {number} 不存在"}, ensure_ascii=False)
    return _volume_update_by_id(vol["id"],
        title=title, main_plotlines=main_plotlines, notes=notes,
        core_emotion=core_emotion, pov_anchor=pov_anchor,
        time_span=time_span, voice_mapping=voice_mapping,
        causal_chain=causal_chain,
        act_intro=act_intro, act_rise=act_rise,
        act_twist=act_twist, act_resolution=act_resolution,
        character_arcs=character_arcs, interaction_matrix=interaction_matrix,
        boundaries=boundaries, suspense_anchors=suspense_anchors,
        key_dialogues=key_dialogues, writing_priorities=writing_priorities,
        hard_constraints=hard_constraints,
        next_volume_bridge=next_volume_bridge, info_pacing=info_pacing,
        rhythm_allocation=rhythm_allocation,
    )
