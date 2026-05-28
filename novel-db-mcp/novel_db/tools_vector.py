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


@mcp.tool
@mcp_tool
def vector_find_incomplete(novel_name: str, entity_types: str = "",
                            min_missing: int = 1,
                            with_suggestions: bool = False) -> str:
    """查找字段缺失/不完整的实体，支持向量匹配推荐补全。

    扫描所有实体类型的必填字段，检测缺失项，按缺失数量排序。
    可选开启向量推荐：对缺失字段，找到同类实体中内容最相似的作为参考。

    参数:
      novel_name: 小说名称
      entity_types: 逗号分隔的实体类型过滤(空=全部)。
        可选: world_setting/character/foreshadow/chapter_summary/volume/echo/timeline
      min_missing: 最少缺失字段数(默认1，只显示有缺失的)
      with_suggestions: 是否为缺失字段提供向量匹配推荐(默认False，开启较慢)

    用法:
      vector_find_incomplete("这次不一样了")
      vector_find_incomplete("这次不一样了", entity_types="character")
      vector_find_incomplete("这次不一样了", min_missing=3)
      vector_find_incomplete("这次不一样了", with_suggestions=True)
    """
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


@mcp.tool
@mcp_tool
def vector_search(novel_name: str, query_text: str, top_k: int = 10,
                   entity_types: str = "", min_score: float = 0.1,
                   rebuild: bool = False) -> str:
    """增强版向量语义搜索：覆盖7种实体类型，持久化向量索引。

    与 db_search 的区别：db_search 做关键词精确匹配，vector_search 做语义相似度匹配。
    例如搜"战斗方式"可以找到"铸造能力"，搜"生病"可以找到"灵衰症"，
    搜"主角的敌人"可以找到反派角色。

    参数:
      novel_name: 小说名称
      query_text: 自然语言查询文本
      top_k: 返回最多结果数(默认10)
      entity_types: 逗号分隔的实体类型过滤(空=全部)。
        可选: world_setting/character/foreshadow/chapter_summary/volume/echo/timeline
      min_score: 最低相似度阈值(默认0.1)
      rebuild: 是否强制重建向量索引(默认False，首次搜索自动构建)

    用法:
      vector_search("这次不一样了", "战斗方式")
      vector_search("这次不一样了", "生病", entity_types="world_setting")
      vector_search("这次不一样了", "主角的敌人", entity_types="character")
      vector_search("这次不一样了", "伏笔", entity_types="foreshadow", top_k=20)
    """
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


@mcp.tool
@mcp_tool
def vector_search_and_update(novel_name: str, query_text: str,
                              entity_type: str, field_name: str,
                              field_value: str, top_k: int = 5,
                              min_score: float = 0.2,
                              dry_run: bool = True) -> str:
    """向量搜索→精准定位→批量修改闭环工具。

    流程:
      1. 用自然语言搜索匹配实体
      2. 过滤到指定实体类型
      3. 对匹配结果批量修改指定字段
      4. 自动更新向量索引

    参数:
      novel_name: 小说名称
      query_text: 自然语言查询文本
      entity_type: 目标实体类型(world_setting/character/foreshadow/volume)
      field_name: 要修改的字段名
      field_value: 新字段值
      top_k: 搜索返回最多结果数(默认5)
      min_score: 最低相似度阈值(默认0.2，比普通搜索更严格)
      dry_run: 试运行模式(默认True，只显示将要修改的内容不实际执行)

    用法:
      # 试运行：查看哪些角色会被修改
      vector_search_and_update("这次不一样了", "北境战士", "character", "region", "北境")
      # 实际执行修改
      vector_search_and_update("这次不一样了", "北境战士", "character", "region", "北境", dry_run=False)
      # 修改世界观设定
      vector_search_and_update("这次不一样了", "灵能", "world_setting", "writing_guide", "注意灵能衰减", dry_run=False)
    """
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
