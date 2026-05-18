import json
import os
import re

from .db import mcp, query
from .resolvers import _resolve_novel_id
from .sync import _record_db_hash

_SYNC_LOREBOOK_BASE = "/Users/ganjie/code/personal/bywork/books_creater/novels"


@mcp.tool
def world_upsert(novel_name: str, category: str, name: str, data: dict,
                  keys: str = "", secondary_keys: str = "", tags: str = "",
                  related_ids: str = "", volume_range: str = "", writing_guide: str = "",
                  lorebook_id: str = "", priority: int = 30, is_constant: bool = False) -> str:
    """新增或更新世界观设定。category: race/faction/location/ability/economy/daily_life/history
    keys/secondary_keys/tags/related_ids: JSON字符串数组，解析后存入TEXT[]列
    volume_range: 卷范围字符串，writing_guide: 写作指导，lorebook_id: Lorebook ID
    priority: 优先级(默认30)，is_constant: 是否常驻
      novel_name: 小说名称
    """
    novel_id = _resolve_novel_id(novel_name)

    data_json = json.dumps(data, ensure_ascii=False)

    extra_cols = []
    extra_vals_insert = []
    extra_vals_update = []

    if keys:
        parsed_keys = json.loads(keys)
        extra_cols.append("keys")
        extra_vals_insert.append(parsed_keys)
        extra_vals_update.append(parsed_keys)
    if secondary_keys:
        parsed_skeys = json.loads(secondary_keys)
        extra_cols.append("secondary_keys")
        extra_vals_insert.append(parsed_skeys)
        extra_vals_update.append(parsed_skeys)
    if tags:
        parsed_tags = json.loads(tags)
        extra_cols.append("tags")
        extra_vals_insert.append(parsed_tags)
        extra_vals_update.append(parsed_tags)
    if related_ids:
        parsed_rids = json.loads(related_ids)
        extra_cols.append("related_ids")
        extra_vals_insert.append(parsed_rids)
        extra_vals_update.append(parsed_rids)
    if volume_range:
        extra_cols.append("volume_range")
        extra_vals_insert.append(volume_range)
        extra_vals_update.append(volume_range)
    if writing_guide:
        extra_cols.append("writing_guide")
        extra_vals_insert.append(writing_guide)
        extra_vals_update.append(writing_guide)
    if lorebook_id:
        extra_cols.append("lorebook_id")
        extra_vals_insert.append(lorebook_id)
        extra_vals_update.append(lorebook_id)
    if priority != 30:
        extra_cols.append("priority")
        extra_vals_insert.append(priority)
        extra_vals_update.append(priority)
    if is_constant:
        extra_cols.append("is_constant")
        extra_vals_insert.append(is_constant)
        extra_vals_update.append(is_constant)

    if extra_cols:
        col_str = ", ".join(extra_cols)
        insert_placeholders = ", ".join(["%s"] * len(extra_cols))
        update_sets = ", ".join([f"{c} = %s" for c in extra_cols])
        query(
            f"INSERT INTO world_settings (novel_id, category, name, data, {col_str}) "
            f"VALUES (%s, %s, %s, %s, {insert_placeholders}) "
            f"ON CONFLICT (novel_id, category, name) DO UPDATE SET data = %s, {update_sets}, updated_at = NOW()",
            (novel_id, category, name, data_json, *extra_vals_insert, data_json, *extra_vals_update),
            fetch="none"
        )
    else:
        query(
            "INSERT INTO world_settings (novel_id, category, name, data) "
            "VALUES (%s, %s, %s, %s) "
            "ON CONFLICT (novel_id, category, name) DO UPDATE SET data = %s, updated_at = NOW()",
            (novel_id, category, name, data_json, data_json),
            fetch="none"
        )
    _record_db_hash(novel_id, "world", f"{category}:{name}", data_json)
    return json.dumps({"ok": True, "category": category, "name": name}, ensure_ascii=False)


@mcp.tool
def world_query(novel_name: str, category: str = "", name: str = "") -> str:
    """查询世界观设定。category 和 name 可选，为空返回全部
      novel_name: 小说名称
    """
    novel_id = _resolve_novel_id(novel_name)
    if category and name:
        rows = query("SELECT * FROM world_settings WHERE novel_id = %s AND category = %s AND name = %s",
                     (novel_id, category, name))
    elif category:
        rows = query("SELECT * FROM world_settings WHERE novel_id = %s AND category = %s",
                     (novel_id, category))
    else:
        rows = query("SELECT * FROM world_settings WHERE novel_id = %s ORDER BY category, name",
                     (novel_id,))
    return json.dumps([dict(r) for r in rows], ensure_ascii=False, default=str)


@mcp.tool
def world_delete(novel_name: str, category: str, name: str) -> str:
    """删除世界观设定
      novel_name: 小说名称
    """
    novel_id = _resolve_novel_id(novel_name)

    query("DELETE FROM world_settings WHERE novel_id = %s AND category = %s AND name = %s",
          (novel_id, category, name), fetch="none")
    return json.dumps({"ok": True}, ensure_ascii=False)


@mcp.tool
def world_deactivate(novel_name: str, category: str, name: str, reason: str = "") -> str:
    """世界观元素停用（不可逆型：地点毁灭、势力解散、物品消耗等）。
    参数:
      novel_name: 小说名称
      category: 类别(location/faction/ability/economy等)
      name: 元素名称
      reason: 停用原因
    """
    novel_id = _resolve_novel_id(novel_name)
    ws = query("SELECT id, data FROM world_settings WHERE novel_id=%s AND category=%s AND name=%s",
               (novel_id, category, name), fetch="one")
    if not ws:
        return json.dumps({"error": f"世界元素 '{category}:{name}' 不存在"}, ensure_ascii=False)
    data = ws["data"] if isinstance(ws["data"], dict) else {}
    data["_deactivated"] = True
    data["_deactivation_reason"] = reason
    query("UPDATE world_settings SET status='inactive', data=%s, updated_at=NOW() WHERE id=%s",
          (json.dumps(data, ensure_ascii=False), ws["id"]), fetch="none")
    return json.dumps({"ok": True, "category": category, "name": name, "status": "inactive", "reason": reason}, ensure_ascii=False)


@mcp.tool
def sync_lorebook(novel_name: str) -> str:
    """从 设定/世界观/ 目录下的 MD 文件同步数据到 DB。
    解析 ## category: name 格式，upsert 到 world_settings 表。
    每次写作前调一次，确保 DB 与文件一致。"""
    novel_dir = os.path.join(_SYNC_LOREBOOK_BASE, novel_name, "设定", "世界观")
    if not os.path.isdir(novel_dir):
        return json.dumps({"error": f"novel dir not found: {novel_dir}"}, ensure_ascii=False)

    novel = query("SELECT id FROM novels WHERE name = %s", (novel_name,), fetch="one")
    if not novel:
        return json.dumps({"error": f"novel '{novel_name}' not found in DB"}, ensure_ascii=False)
    novel_id = novel["id"]

    changes = {}
    md_files = sorted(
        f for f in os.listdir(novel_dir)
        if f.endswith(".md") and not f.startswith("_")
    )

    for fname in md_files:
        fpath = os.path.join(novel_dir, fname)
        with open(fpath, "r", encoding="utf-8") as f:
            text = f.read()

        parts = re.split(r"^## (.+)$", text, flags=re.MULTILINE)
        if len(parts) < 3:
            continue

        for i in range(1, len(parts), 2):
            header = parts[i].strip()
            body = parts[i + 1].strip()

            m = re.match(r"^(\w+):\s+(.+)$", header)
            if not m:
                continue

            category = m.group(1)
            name = m.group(2)

            meta = {}
            content_lines = []
            in_meta = True

            for line in body.split("\n"):
                if in_meta and line.startswith("- **"):
                    fm = re.match(r"^- \*\*(\w+)\*\*:\s*(.+)$", line)
                    if fm:
                        key = fm.group(1)
                        val_str = fm.group(2).strip()
                        try:
                            val = json.loads(val_str)
                        except (json.JSONDecodeError, ValueError):
                            val = val_str
                        meta[key] = val
                    else:
                        in_meta = False
                        content_lines.append(line)
                elif in_meta and line.strip() == "":
                    in_meta = False
                else:
                    in_meta = False
                    content_lines.append(line)

            content = "\n".join(content_lines).strip()
            content = re.sub(r"^---\s*$", "", content, flags=re.MULTILINE).strip()

            data = dict(meta)
            data["content"] = content
            data_json = json.dumps(data, ensure_ascii=False)

            keys_val = meta.get("keys", [])
            if isinstance(keys_val, str):
                keys_val = [k.strip() for k in keys_val.split(",")]
            secondary_keys_val = meta.get("secondary_keys", [])
            if isinstance(secondary_keys_val, str):
                secondary_keys_val = [k.strip() for k in secondary_keys_val.split(",")]
            tags_val = meta.get("tags", [])
            if isinstance(tags_val, str):
                tags_val = [k.strip() for k in tags_val.split(",")]
            related_val = meta.get("related", [])
            if isinstance(related_val, str):
                related_val = [k.strip() for k in related_val.split(",")]
            volume_range = meta.get("volume_range", "")
            if not isinstance(volume_range, str):
                volume_range = str(volume_range)
            priority = meta.get("priority", 30)
            if isinstance(priority, str):
                try:
                    priority = int(priority)
                except ValueError:
                    priority = 30
            is_constant = meta.get("is_constant", False)
            if isinstance(is_constant, str):
                is_constant = is_constant.lower() in ("true", "1", "yes")

            try:
                query(
                    "INSERT INTO world_settings (novel_id, category, name, data, keys, secondary_keys, tags, related_ids, volume_range, priority, is_constant) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) "
                    "ON CONFLICT (novel_id, category, name) DO UPDATE SET "
                    "data = EXCLUDED.data, keys = EXCLUDED.keys, secondary_keys = EXCLUDED.secondary_keys, "
                    "tags = EXCLUDED.tags, related_ids = EXCLUDED.related_ids, volume_range = EXCLUDED.volume_range, "
                    "priority = EXCLUDED.priority, is_constant = EXCLUDED.is_constant, updated_at = NOW()",
                    (novel_id, category, name, data_json,
                     keys_val if keys_val else None,
                     secondary_keys_val if secondary_keys_val else None,
                     tags_val if tags_val else None,
                     related_val if related_val else None,
                     volume_range or None,
                     priority if priority != 30 else None,
                     is_constant or None),
                    fetch="none"
                )
                _record_db_hash(novel_id, "world", f"{category}:{name}", data_json)
                cat_key = category
                changes[cat_key] = changes.get(cat_key, 0) + 1
            except Exception as e:
                pass

    return json.dumps({"ok": True, "novel_id": novel_id, "changes": changes}, ensure_ascii=False)


@mcp.tool
def seed_engine_data(novel_name: str, engine_type: str = "", content: str = "") -> str:
    """写入或更新引擎参考内容到 DB。engine_type: scene/action/dialogue/environment/item/snapshot/ability/causality。
    模型可从 skill 文件中读取内容后调此工具写入。content 为空则返回当前内容供参考。
      novel_name: 小说名称
    """
    novel_id = _resolve_novel_id(novel_name)

    if not engine_type:
        rows = query(
            "SELECT name, data FROM world_settings WHERE novel_id = %s AND category = 'engine_reference'",
            (novel_id,)
        )
        result = {}
        for r in rows:
            d = r["data"]
            result[r["name"]] = d.get("content","")[:100] if isinstance(d, dict) else ""
        return json.dumps({"engines": result, "count": len(result)}, ensure_ascii=False)

    if not content:
        row = query(
            "SELECT data FROM world_settings WHERE novel_id = %s AND category = 'engine_reference' AND name = %s",
            (novel_id, engine_type), fetch="one"
        )
        if row:
            d = row["data"]
            return json.dumps({"engine": engine_type, "content": d.get("content","") if isinstance(d, dict) else d}, ensure_ascii=False)
        return json.dumps({"engine": engine_type, "content": None}, ensure_ascii=False)

    query(
        "INSERT INTO world_settings (novel_id, category, name, data) "
        "VALUES (%s, 'engine_reference', %s, %s) "
        "ON CONFLICT (novel_id, category, name) DO UPDATE SET data = %s, updated_at = NOW()",
        (novel_id, engine_type, json.dumps({"content": content}), json.dumps({"content": content})),
        fetch="none"
    )
    return json.dumps({"ok": True, "engine_type": engine_type, "content_length": len(content)}, ensure_ascii=False)


@mcp.tool
def engine_detail(engine_type: str, novel_name: str) -> str:
    """加载写作引擎参考。从 world_settings 读取，模型可自定义覆盖。
      novel_name: 小说名称
    """
    novel_id = _resolve_novel_id(novel_name)

    row = query(
        "SELECT data FROM world_settings WHERE novel_id = %s AND category = 'engine_reference' AND name = %s",
        (novel_id, engine_type), fetch="one"
    )
    if row:
        data = row["data"]
        if isinstance(data, dict) and "content" in data:
            return json.dumps({"engine": engine_type, "content": data["content"], "source": "db"}, ensure_ascii=False)

    row = query(
        "SELECT data FROM world_settings WHERE novel_id = %s AND category = 'engine_reference' AND name = %s",
        (0, engine_type), fetch="one"
    )
    if row:
        data = row["data"]
        if isinstance(data, dict) and "content" in data:
            return json.dumps({"engine": engine_type, "content": data["content"], "source": "global"}, ensure_ascii=False)

    return json.dumps({"error": f"engine '{engine_type}' not found. 用 seed_engine_data(novel_name, '{engine_type}', content=...) 添加"}, ensure_ascii=False)


@mcp.tool
def author_voice(novel_name: str) -> str:
    """加载本小说的作者声音维度。存储在 world_settings(category='author_voice') 中。
      novel_name: 小说名称
    """
    novel_id = _resolve_novel_id(novel_name)

    rows = query(
        "SELECT name, data FROM world_settings WHERE novel_id = %s AND category = 'author_voice'",
        (novel_id,)
    )
    if rows:
        result = {"voices": [dict(r) for r in rows]}
    else:
        result = {"voices": [
            {"name": "审美偏执", "content": "用旧了的东西好看。管壁锈痕、工具磨损、棉衣补丁——天然会注意这些"},
            {"name": "比喻体系", "content": "身体感受＞文学形容。用'牙齿磕牙齿'代替'刺骨'，禁安全牌比喻"},
            {"name": "不点破留白", "content": "叙事默认不总结不解释不升华。动作先上，解释延后"},
            {"name": "细节集中", "content": "一个场景只给1个核心特写，其他全部模糊带过"},
            {"name": "疯劲密度", "content": "情绪高潮时事件不喘气地接。写完觉得'会不会太过'——留着，是对的"},
            {"name": "世界呼吸", "content": "冰冷静止的世界里，角色有自己的瞬间——踩石头走平衡、哼跑调的曲子"}
        ], "note": "默认声音，可通过 world_upsert(category='author_voice') 覆盖"}
    return json.dumps(result, ensure_ascii=False)


@mcp.tool
def writing_spec(novel_name: str) -> str:
    """加载本小说的写作执行规范。存储在 world_settings(category='writing_spec') 中。
      novel_name: 小说名称
    """
    novel_id = _resolve_novel_id(novel_name)

    rows = query(
        "SELECT name, data FROM world_settings WHERE novel_id = %s AND category = 'writing_spec'",
        (novel_id,)
    )
    if rows:
        specs = [dict(r) for r in rows]
        return json.dumps({"specs": specs}, ensure_ascii=False)
    return json.dumps({"specs": [], "note": "未设置写作规范。用 world_upsert(category='writing_spec') 添加"}, ensure_ascii=False)
