import json

from .db import mcp, query, transaction
from .errors import mcp_tool
from .sync import _record_db_hash, _auto_sync_to_files
from .resolvers import _resolve_novel_id, _UNSET
from .sql_utils import build_update_sql

_JSON_FIELDS = {
    'main_plotlines', 'act_intro', 'act_rise', 'act_twist', 'act_resolution',
    'character_arcs', 'interaction_matrix', 'boundaries', 'suspense_anchors',
    'key_dialogues', 'writing_priorities', 'hard_constraints',
    'next_volume_bridge', 'info_pacing', 'rhythm_allocation',
}
_TEXT_FIELDS = {
    'title', 'notes', 'core_emotion', 'pov_anchor',
    'time_span', 'voice_mapping', 'causal_chain',
}


@mcp.tool
@mcp_tool
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
    _record_db_hash(novel_id, "volume", str(number), mp)
    _sync_warning = _auto_sync_to_files(novel_name, "volume", str(number))
    result = {"ok": True, "id": r, "number": number}
    if _sync_warning:
        result["auto_sync"] = json.loads(_sync_warning)
    return json.dumps(result, ensure_ascii=False)


@mcp.tool
@mcp_tool
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


def _volume_update_by_id(volume_id: int, novel_id: int = 0, **kwargs) -> str:
    fields = {}
    for key, val in kwargs.items():
        if val is _UNSET:
            continue
        if key in _JSON_FIELDS:
            if val is None:
                continue
            fields[key] = json.dumps(val, ensure_ascii=False)
        elif key in _TEXT_FIELDS:
            fields[key] = val
        else:
            continue

    if not fields:
        return json.dumps({"ok": False, "error": "no valid fields"}, ensure_ascii=False)
    sql, params = build_update_sql("volumes", fields, "id = ?", (volume_id,))
    query(sql, params, fetch="none")
    if novel_id:
        from .hooks import fire_and_report
        fire_and_report(novel_id, "volume", volume_id)
        vol_row = query("SELECT number FROM volumes WHERE id = ?", (volume_id,), fetch="one")
        if vol_row:
            _record_db_hash(novel_id, "volume", str(vol_row["number"]), json.dumps(fields, ensure_ascii=False))
            novel_name_row = query("SELECT name FROM novels WHERE id = ?", (novel_id,), fetch="one")
            if novel_name_row:
                _sync_warning = _auto_sync_to_files(novel_name_row["name"], "volume", str(vol_row["number"]))
                if _sync_warning:
                    return json.dumps({"ok": True, "auto_sync": json.loads(_sync_warning)}, ensure_ascii=False)
    return json.dumps({"ok": True}, ensure_ascii=False)


@mcp.tool
@mcp_tool
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
@mcp_tool
def volume_update(novel_name: str, number: int, title=_UNSET,
                  main_plotlines=_UNSET, notes=_UNSET,
                  core_emotion=_UNSET, pov_anchor=_UNSET,
                  time_span=_UNSET, voice_mapping=_UNSET,
                  causal_chain=_UNSET,
                  act_intro=_UNSET, act_rise=_UNSET,
                  act_twist=_UNSET, act_resolution=_UNSET,
                  character_arcs=_UNSET, interaction_matrix=_UNSET,
                  boundaries=_UNSET, suspense_anchors=_UNSET,
                  key_dialogues=_UNSET, writing_priorities=_UNSET,
                  hard_constraints=_UNSET,
                  next_volume_bridge=_UNSET, info_pacing=_UNSET,
                  rhythm_allocation=_UNSET) -> str:
    """按卷号更新卷信息（无需volume_id）。传入需要修改的字段，未传的字段不会被修改。支持富数据字段（因果链/四幕/人物弧光等）。
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
    return _volume_update_by_id(vol["id"], novel_id=novel_id,
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
