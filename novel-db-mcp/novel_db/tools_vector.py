import json

from .db import mcp, query
from .embedding import VectorStore, _ENTITY_FIELD_SPECS
from .resolvers import _resolve_novel_id
from .errors import mcp_tool


_EDITABLE_FIELDS = {
    "world_setting": {"writing_guide", "region", "volume_range", "priority", "is_constant"},
    "character": {"personality", "speech_style", "goals", "background", "appearance",
                  "weaknesses", "catchphrase", "arc_notes", "role", "race",
                  "ability_level", "status"},
    "foreshadow": {"description", "importance", "tags", "status", "reveal_strategy"},
    "volume": {"title", "core_emotion", "causal_chain", "notes"},
}


def _get_vector_store() -> VectorStore:
    return VectorStore(query)


def _resolve_entity_name(entity_type: str, entity_id: int, novel_id: int) -> str:
    spec = _ENTITY_FIELD_SPECS.get(entity_type)
    if not spec:
        return str(entity_id)

    name_col = spec["name_col"]

    if entity_type == "chapter_summary":
        row = query(
            "SELECT c.title, c.number FROM chapter_summaries cs "
            "JOIN chapters c ON cs.chapter_id = c.id WHERE cs.chapter_id = ?",
            (entity_id,), fetch="one"
        )
        return row.get("title") or f"第{row.get('number', '?')}章" if row else str(entity_id)
    elif entity_type == "volume":
        row = query("SELECT number, title FROM volumes WHERE id = ?", (entity_id,), fetch="one")
        return row.get("title") or f"V{row.get('number', '?')}" if row else str(entity_id)
    elif entity_type in ("foreshadow", "echo", "timeline"):
        return f"{entity_type}#{entity_id}"
    else:
        row = query(f"SELECT {name_col} as name FROM {spec['table']} WHERE id = ?", (entity_id,), fetch="one")
        return row["name"] if row else str(entity_id)


def _ensure_vector_index(store: VectorStore, novel_id: int, entity_types: list[str] = None):
    count_row = query(
        "SELECT COUNT(*) as cnt FROM embedding_vectors WHERE novel_id = ?",
        (novel_id,), fetch="val"
    )
    if not count_row:
        store.rebuild_index(novel_id, entity_types=entity_types)


def _vector_find_incomplete(novel_name: str, entity_types: str = "",
                            min_missing: int = 1,
                            with_suggestions: bool = False) -> str:
    novel_id = _resolve_novel_id(novel_name)

    type_list = [t.strip() for t in entity_types.split(",") if t.strip()] if entity_types else None

    store = _get_vector_store()
    results = store.find_incomplete(novel_id, entity_types=type_list, min_missing=min_missing)

    for r in results:
        r["name"] = _resolve_entity_name(r["type"], r["id"], novel_id)

    if with_suggestions and results:
        store.rebuild_index(novel_id, entity_types=type_list)

        for r in results[:10]:
            for mf in r.get("missing_fields", []):
                suggestions = store.vector_match_suggestions(
                    novel_id, r["type"], r["id"], mf["label"], top_k=3
                )
                for s in suggestions:
                    s["name"] = _resolve_entity_name(r["type"], s["id"], novel_id)
                mf["suggestions"] = suggestions

    stats = {}
    for r in results:
        t = r["type"]
        stats[t] = stats.get(t, 0) + 1

    return json.dumps({
        "novel_name": novel_name,
        "total_incomplete": len(results),
        "by_type": stats,
        "results": results,
    }, ensure_ascii=False, default=str)


def _vector_search(novel_name: str, query_text: str, top_k: int = 10,
                   entity_types: str = "", min_score: float = 0.1,
                   rebuild: bool = False) -> str:
    novel_id = _resolve_novel_id(novel_name)

    type_list = [t.strip() for t in entity_types.split(",") if t.strip()] if entity_types else None

    store = _get_vector_store()

    if rebuild:
        store.rebuild_index(novel_id, entity_types=type_list)
    else:
        _ensure_vector_index(store, novel_id, entity_types=type_list)

    results = store.search(novel_id, query_text, top_k=top_k,
                           entity_types=type_list, min_score=min_score)

    for r in results:
        r["name"] = _resolve_entity_name(r["type"], r["id"], novel_id)

    return json.dumps({
        "query": query_text,
        "mode": "persistent_vector",
        "total": len(results),
        "results": results,
    }, ensure_ascii=False, default=str)


def _vector_search_and_update(novel_name: str, query_text: str,
                              entity_type: str, field_name: str,
                              field_value: str, top_k: int = 5,
                              min_score: float = 0.2,
                              dry_run: bool = True) -> str:
    novel_id = _resolve_novel_id(novel_name)

    allowed = _EDITABLE_FIELDS.get(entity_type, set())
    if field_name not in allowed:
        return json.dumps({
            "error": f"field '{field_name}' is not editable for {entity_type}. Allowed: {sorted(allowed)}"
        }, ensure_ascii=False)

    store = _get_vector_store()
    _ensure_vector_index(store, novel_id, entity_types=[entity_type])

    results = store.search(novel_id, query_text, top_k=top_k,
                           entity_types=[entity_type], min_score=min_score)

    if not results:
        return json.dumps({
            "query": query_text,
            "entity_type": entity_type,
            "matches": 0,
            "message": "未找到匹配的实体，尝试降低 min_score 或修改查询文本"
        }, ensure_ascii=False)

    update_plan = []
    for r in results:
        name = _resolve_entity_name(r["type"], r["id"], novel_id)
        update_plan.append({
            "type": r["type"],
            "id": r["id"],
            "name": name,
            "score": r["score"],
            "field": field_name,
            "new_value": field_value,
        })

    if dry_run:
        return json.dumps({
            "mode": "dry_run",
            "query": query_text,
            "entity_type": entity_type,
            "field_name": field_name,
            "field_value": field_value,
            "matches": len(update_plan),
            "plan": update_plan,
            "message": "试运行模式，未实际修改。设置 dry_run=False 执行修改"
        }, ensure_ascii=False, default=str)

    updated = []
    errors = []
    for plan_item in update_plan:
        etype = plan_item["type"]
        eid = plan_item["id"]

        try:
            from .sql_utils import build_update_sql

            table_map = {
                "world_setting": "world_settings",
                "character": "characters",
                "foreshadow": "foreshadows",
                "volume": "volumes",
            }

            table = table_map.get(etype)
            if not table:
                errors.append({
                    "type": etype, "id": eid,
                    "error": f"不支持批量修改实体类型: {etype}"
                })
                continue

            fields = {field_name: field_value}
            sql, params = build_update_sql(table, fields, "id = ?", [eid])
            query(sql, params, fetch="none")
            updated.append(plan_item)

        except Exception as e:
            errors.append({
                "type": etype, "id": eid, "name": plan_item["name"],
                "error": str(e)
            })

    if updated:
        store.rebuild_index(novel_id, entity_types=[entity_type])

    return json.dumps({
        "mode": "executed",
        "query": query_text,
        "entity_type": entity_type,
        "field_name": field_name,
        "field_value": field_value,
        "matched": len(update_plan),
        "updated": len(updated),
        "errors": len(errors),
        "updates": updated,
        "error_details": errors,
    }, ensure_ascii=False, default=str)
