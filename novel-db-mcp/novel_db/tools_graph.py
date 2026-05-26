import json
import logging

from .db import mcp, query
from .errors import mcp_tool
from .resolvers import _resolve_novel_id

logger = logging.getLogger(__name__)

_ENTITY_TYPE_MAP = {
    "world_setting": "world_settings",
    "character": "characters",
    "chapter": "chapters",
    "foreshadow": "foreshadows",
    "echo": "echoes",
}


def _resolve_entity_id(entity_type: str, entity_name: str, novel_id: int) -> int | None:
    if entity_type == "world_setting":
        row = query(
            "SELECT id FROM world_settings WHERE novel_id = ? AND name = ?",
            (novel_id, entity_name), fetch="one"
        )
    elif entity_type == "character":
        row = query(
            "SELECT id FROM characters WHERE novel_id = ? AND name = ?",
            (novel_id, entity_name), fetch="one"
        )
    elif entity_type == "chapter":
        try:
            ch_num = int(entity_name)
            row = query(
                "SELECT id FROM chapters WHERE novel_id = ? AND number = ?",
                (novel_id, ch_num), fetch="one"
            )
        except ValueError:
            row = query(
                "SELECT id FROM chapters WHERE novel_id = ? AND title = ?",
                (novel_id, entity_name), fetch="one"
            )
    elif entity_type == "foreshadow":
        try:
            fs_id = int(entity_name)
            row = query(
                "SELECT id FROM foreshadows WHERE novel_id = ? AND id = ?",
                (novel_id, fs_id), fetch="one"
            )
        except ValueError:
            row = None
    else:
        row = None
    return row["id"] if row else None


def _resolve_entity_names(pairs: list[tuple[str, int]]) -> dict[tuple[str, int], str]:
    if not pairs:
        return {}
    by_type: dict[str, list[int]] = {}
    for etype, eid in pairs:
        by_type.setdefault(etype, []).append(eid)
    result: dict[tuple[str, int], str] = {}
    for etype, ids in by_type.items():
        table = _ENTITY_TYPE_MAP.get(etype)
        if not table:
            for eid in ids:
                result[(etype, eid)] = str(eid)
            continue
        placeholders = ",".join(["?"] * len(ids))
        rows = query(
            f"SELECT id, name FROM {table} WHERE id IN ({placeholders})",
            tuple(ids)
        )
        id_to_name = {r["id"]: r["name"] for r in (rows or [])}
        if etype == "chapter":
            ch_ids = [eid for eid in ids if eid not in id_to_name or not id_to_name.get(eid)]
            if ch_ids:
                ch_ph = ",".join(["?"] * len(ch_ids))
                ch_rows = query(
                    f"SELECT id, number, title FROM chapters WHERE id IN ({ch_ph})",
                    tuple(ch_ids)
                )
                for r in (ch_rows or []):
                    id_to_name[r["id"]] = r.get("title") or f"Ch{r['number']}"
        for eid in ids:
            result[(etype, eid)] = id_to_name.get(eid, str(eid))
    return result


def _upsert_edge(novel_id: int, from_type: str, from_id: int,
                 to_type: str, to_id: int, edge_type: str,
                 weight: float = 1.0, metadata: str = None):
    query(
        "INSERT INTO entity_edges (novel_id, from_type, from_id, to_type, to_id, edge_type, weight, metadata) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?) "
        "ON CONFLICT (novel_id, from_type, from_id, to_type, to_id, edge_type) DO UPDATE SET "
        "weight = ?, metadata = ?",
        (novel_id, from_type, from_id, to_type, to_id, edge_type, weight, metadata,
         weight, metadata),
        fetch="none"
    )


def _delete_edges_for(novel_id: int, from_type: str, from_id: int,
                      edge_types: list[str] = None):
    if edge_types:
        placeholders = ",".join(["?"] * len(edge_types))
        query(
            f"DELETE FROM entity_edges WHERE novel_id = ? AND from_type = ? AND from_id = ? "
            f"AND edge_type IN ({placeholders})",
            (novel_id, from_type, from_id, *edge_types),
            fetch="none"
        )
    else:
        query(
            "DELETE FROM entity_edges WHERE novel_id = ? AND from_type = ? AND from_id = ?",
            (novel_id, from_type, from_id),
            fetch="none"
        )


def _sync_edges(novel_id: int, entity_type: str, entity_id: int):
    if entity_type == "world_setting":
        _sync_world_edges(novel_id, entity_id)
    elif entity_type == "character":
        _sync_character_edges(novel_id, entity_id)
    elif entity_type == "foreshadow":
        _sync_foreshadow_edges(novel_id, entity_id)
    elif entity_type == "chapter":
        _sync_chapter_edges(novel_id, entity_id)


def _sync_world_edges(novel_id: int, ws_id: int):
    ws = query("SELECT id, category, name, related_ids, region, faction_id, keys FROM world_settings WHERE id = ?",
               (ws_id,), fetch="one")
    if not ws:
        return
    _delete_edges_for(novel_id, "world_setting", ws_id,
                      ["related_setting", "has_location", "belongs_to_faction", "has_ability"])

    related = ws.get("related_ids", [])
    if isinstance(related, str):
        try:
            related = json.loads(related)
        except (json.JSONDecodeError, TypeError):
            related = []
    for rid in related:
        if rid:
            _upsert_edge(novel_id, "world_setting", ws_id, "world_setting", rid, "related_setting")

    region = ws.get("region", "")
    if region and region != "全域":
        loc = query(
            "SELECT id FROM world_settings WHERE novel_id = ? AND category = 'location' AND region = ? LIMIT 1",
            (novel_id, region), fetch="one"
        )
        if loc:
            _upsert_edge(novel_id, "world_setting", ws_id, "world_setting", loc["id"], "has_location")

    faction_id = ws.get("faction_id")
    if faction_id:
        _upsert_edge(novel_id, "world_setting", ws_id, "world_setting", faction_id, "belongs_to_faction")

    if ws["category"] == "ability":
        keys = ws.get("keys", [])
        if isinstance(keys, str):
            try:
                keys = json.loads(keys)
            except (json.JSONDecodeError, TypeError):
                keys = []
        if keys:
            key_names = [k for k in keys if isinstance(k, str)]
            if key_names:
                placeholders = ",".join(["?"] * len(key_names))
                chars = query(
                    f"SELECT id, name FROM characters WHERE novel_id = ? AND name IN ({placeholders})",
                    (novel_id, *key_names)
                )
                for char in (chars or []):
                    _upsert_edge(novel_id, "character", char["id"],
                                 "world_setting", ws_id, "has_ability")


def _sync_character_edges(novel_id: int, char_id: int):
    char = query("SELECT id, faction_id FROM characters WHERE id = ?", (char_id,), fetch="one")
    if not char:
        return
    _delete_edges_for(novel_id, "character", char_id, ["belongs_to_faction", "character_relation"])

    faction_id = char.get("faction_id")
    if faction_id:
        _upsert_edge(novel_id, "character", char_id, "world_setting", faction_id, "belongs_to_faction")

    rels = query(
        "SELECT to_character_id, relation_type, intensity FROM character_relations "
        "WHERE novel_id = ? AND from_character_id = ?",
        (novel_id, char_id)
    )
    for rel in (rels or []):
        weight = (rel["intensity"] / 10.0) if rel.get("intensity") else 0.5
        _upsert_edge(novel_id, "character", char_id, "character", rel["to_character_id"],
                     "character_relation", weight=weight,
                     metadata=json.dumps({"relation_type": rel.get("relation_type", "")}, ensure_ascii=False))


def _sync_foreshadow_edges(novel_id: int, fs_id: int):
    fs = query("SELECT id, planted_chapter_id, actual_recall_chapter_id, related_characters FROM foreshadows WHERE id = ?",
               (fs_id,), fetch="one")
    if not fs:
        return
    _delete_edges_for(novel_id, "foreshadow", fs_id,
                      ["planted_in", "recalled_in", "relates_character"])

    planted = fs.get("planted_chapter_id")
    if planted:
        _upsert_edge(novel_id, "foreshadow", fs_id, "chapter", planted, "planted_in")

    recalled = fs.get("actual_recall_chapter_id")
    if recalled:
        _upsert_edge(novel_id, "foreshadow", fs_id, "chapter", recalled, "recalled_in")

    related_chars = fs.get("related_characters", [])
    if isinstance(related_chars, str):
        try:
            related_chars = json.loads(related_chars)
        except (json.JSONDecodeError, TypeError):
            related_chars = []
    for cid in (related_chars or []):
        if cid:
            _upsert_edge(novel_id, "foreshadow", fs_id, "character", cid, "relates_character")


def _sync_chapter_edges(novel_id: int, chapter_id: int):
    cs = query("SELECT characters_involved FROM chapter_summaries WHERE chapter_id = ?",
               (chapter_id,), fetch="one")
    if not cs:
        return
    _delete_edges_for(novel_id, "chapter", chapter_id, ["appears_in"])

    chars = cs.get("characters_involved", [])
    if isinstance(chars, str):
        try:
            chars = json.loads(chars)
        except (json.JSONDecodeError, TypeError):
            chars = []
    for cid in (chars or []):
        if cid:
            _upsert_edge(novel_id, "character", cid, "chapter", chapter_id, "appears_in")


@mcp.tool
@mcp_tool
def graph_query(novel_name: str, entity_type: str, entity_name: str,
                depth: int = 2, edge_types: list = None,
                direction: str = "both", max_results: int = 50) -> str:
    """从指定实体出发，递归遍历关系网络。

    参数:
      novel_name: 小说名称
      entity_type: 实体类型(world_setting/character/chapter/foreshadow)
      entity_name: 实体名称(world_setting用name, character用name, chapter用编号, foreshadow用id)
      depth: 遍历深度(默认2)
      edge_types: 只遍历指定边类型(空=全部)
      direction: 遍历方向(both/outgoing/incoming)
      max_results: 最大返回结果数(默认50)
    """
    novel_id = _resolve_novel_id(novel_name)
    entity_id = _resolve_entity_id(entity_type, entity_name, novel_id)
    if entity_id is None:
        return json.dumps({"error": f"实体 '{entity_type}:{entity_name}' 不存在"}, ensure_ascii=False)

    et_ph = ""
    et_params: list = []
    if edge_types:
        et_ph = "AND e.edge_type IN (" + ",".join(["?"] * len(edge_types)) + ")"
        et_params = list(edge_types)

    if direction == "outgoing":
        base_cond = "e.from_type = ? AND e.from_id = ?"
        base_params = [entity_type, entity_id]
        join_cond = "e.novel_id = g.novel_id AND e.from_type = g.to_type AND e.from_id = g.to_id"
    elif direction == "incoming":
        base_cond = "e.to_type = ? AND e.to_id = ?"
        base_params = [entity_type, entity_id]
        join_cond = "e.novel_id = g.novel_id AND e.to_type = g.from_type AND e.to_id = g.from_id"
    else:
        base_cond = "(e.from_type = ? AND e.from_id = ?) OR (e.to_type = ? AND e.to_id = ?)"
        base_params = [entity_type, entity_id, entity_type, entity_id]
        join_cond = ("(e.novel_id = g.novel_id AND e.from_type = g.to_type AND e.from_id = g.to_id) "
                     "OR (e.novel_id = g.novel_id AND e.to_type = g.from_type AND e.to_id = g.from_id)")

    sql = f"""
    WITH RECURSIVE graph AS (
        SELECT e.*, 0 as depth
        FROM entity_edges e
        WHERE e.novel_id = ? AND ({base_cond}) {et_ph}
        UNION ALL
        SELECT e.*, g.depth + 1
        FROM entity_edges e
        JOIN graph g ON ({join_cond})
        WHERE g.depth < ?
        {et_ph}
    )
    SELECT DISTINCT from_type, from_id, to_type, to_id, edge_type, depth, weight
    FROM graph LIMIT ?
    """

    all_params = (
        [novel_id] + base_params + et_params
        + [depth] + et_params
        + [max_results]
    )
    rows = query(sql, tuple(all_params))

    node_pairs = set()
    edges = []
    for r in (rows or []):
        ft, fi, tt, ti = r["from_type"], r["from_id"], r["to_type"], r["to_id"]
        node_pairs.add((ft, fi))
        node_pairs.add((tt, ti))
        edges.append({
            "from": f"{ft}:{fi}",
            "to": f"{tt}:{ti}",
            "edge_type": r["edge_type"],
            "depth": r["depth"],
            "weight": r["weight"],
        })

    names = _resolve_entity_names(list(node_pairs))
    nodes = {}
    for (etype, eid) in node_pairs:
        key = f"{etype}:{eid}"
        nodes[key] = {
            "type": etype,
            "id": eid,
            "name": names.get((etype, eid), str(eid)),
        }

    return json.dumps({
        "source": {"type": entity_type, "name": entity_name, "id": entity_id},
        "nodes": list(nodes.values()),
        "edges": edges,
        "stats": {"node_count": len(nodes), "edge_count": len(edges)},
    }, ensure_ascii=False, default=str)


@mcp.tool
@mcp_tool
def graph_neighbors(novel_name: str, entity_type: str, entity_name: str,
                    edge_types: list = None) -> str:
    """获取实体的直接关系邻居（单层遍历）。

    参数:
      novel_name: 小说名称
      entity_type: 实体类型(world_setting/character/chapter/foreshadow)
      entity_name: 实体名称
      edge_types: 只返回指定边类型(空=全部)
    """
    novel_id = _resolve_novel_id(novel_name)
    entity_id = _resolve_entity_id(entity_type, entity_name, novel_id)
    if entity_id is None:
        return json.dumps({"error": f"实体 '{entity_type}:{entity_name}' 不存在"}, ensure_ascii=False)

    outgoing = query(
        "SELECT to_type, to_id, edge_type, weight FROM entity_edges "
        "WHERE novel_id = ? AND from_type = ? AND from_id = ?",
        (novel_id, entity_type, entity_id)
    )
    incoming = query(
        "SELECT from_type, from_id, edge_type, weight FROM entity_edges "
        "WHERE novel_id = ? AND to_type = ? AND to_id = ?",
        (novel_id, entity_type, entity_id)
    )

    neighbor_pairs = set()
    raw_neighbors = []
    for r in (outgoing or []):
        if edge_types and r["edge_type"] not in edge_types:
            continue
        neighbor_pairs.add((r["to_type"], r["to_id"]))
        raw_neighbors.append(("outgoing", r["to_type"], r["to_id"], r["edge_type"], r["weight"]))
    for r in (incoming or []):
        if edge_types and r["edge_type"] not in edge_types:
            continue
        neighbor_pairs.add((r["from_type"], r["from_id"]))
        raw_neighbors.append(("incoming", r["from_type"], r["from_id"], r["edge_type"], r["weight"]))

    names = _resolve_entity_names(list(neighbor_pairs))
    neighbors = []
    for direction, ntype, nid, etype, weight in raw_neighbors:
        neighbors.append({
            "direction": direction,
            "neighbor_type": ntype,
            "neighbor_id": nid,
            "neighbor_name": names.get((ntype, nid), str(nid)),
            "edge_type": etype,
            "weight": weight,
        })

    return json.dumps({
        "source": {"type": entity_type, "name": entity_name, "id": entity_id},
        "neighbors": neighbors,
        "count": len(neighbors),
    }, ensure_ascii=False, default=str)


@mcp.tool
@mcp_tool
def graph_cascade(novel_name: str, entity_type: str, entity_name: str) -> str:
    """级联影响分析：修改该实体会影响哪些其他实体。从实体出发全图遍历，返回影响范围。

    参数:
      novel_name: 小说名称
      entity_type: 实体类型(world_setting/character/chapter/foreshadow)
      entity_name: 实体名称
    """
    novel_id = _resolve_novel_id(novel_name)
    entity_id = _resolve_entity_id(entity_type, entity_name, novel_id)
    if entity_id is None:
        return json.dumps({"error": f"实体 '{entity_type}:{entity_name}' 不存在"}, ensure_ascii=False)

    sql = """
    WITH RECURSIVE cascade AS (
        SELECT e.*, 0 as depth
        FROM entity_edges e
        WHERE e.novel_id = ? AND e.from_type = ? AND e.from_id = ?
        UNION ALL
        SELECT e.*, c.depth + 1
        FROM entity_edges e
        JOIN cascade c ON (
            e.novel_id = c.novel_id AND e.from_type = c.to_type AND e.from_id = c.to_id
        )
        WHERE c.depth < 5
    )
    SELECT DISTINCT to_type, to_id, edge_type, depth FROM cascade
    """

    rows = query(sql, (novel_id, entity_type, entity_id))

    affected_pairs = set()
    affected_raw = []
    for r in (rows or []):
        affected_pairs.add((r["to_type"], r["to_id"]))
        affected_raw.append(r)

    names = _resolve_entity_names(list(affected_pairs))

    by_depth = {}
    affected = []
    for r in affected_raw:
        d = r["depth"]
        if d not in by_depth:
            by_depth[d] = []
        entry = {
            "type": r["to_type"],
            "id": r["to_id"],
            "name": names.get((r["to_type"], r["to_id"]), str(r["to_id"])),
            "edge_type": r["edge_type"],
            "depth": d,
        }
        by_depth[d].append(entry)
        affected.append(entry)

    return json.dumps({
        "source": {"type": entity_type, "name": entity_name, "id": entity_id},
        "total_affected": len(affected),
        "by_depth": by_depth,
        "affected": affected,
    }, ensure_ascii=False, default=str)
