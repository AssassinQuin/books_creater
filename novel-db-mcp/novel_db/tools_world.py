import json
import logging
import os
import re

from .db import mcp, query

logger = logging.getLogger(__name__)
from .resolvers import _resolve_novel_id
from .sync import _record_db_hash, _NOVELS_BASE


# ═══════════════════════════════════════════════════════════
# Volume-range matching helper
# ═══════════════════════════════════════════════════════════

def _parse_volume_number(vol_str: str) -> int:
    """Extract numeric part from volume identifier like 'V3', 'V15', '尾声'."""
    if not vol_str:
        return 0
    vol_str = vol_str.strip()
    if vol_str == "尾声":
        return 99
    m = re.match(r'V?(\d+)', vol_str)
    return int(m.group(1)) if m else 0


def _volume_in_range(volume_number: int, volume_range: str) -> bool:
    """Check if a volume number falls within a volume_range string.
    
    volume_range formats:
      'V1-V14'         → volumes 1 through 14
      'V1-尾声'         → volumes 1 through end
      'V5-V12'         → volumes 5 through 12
      'V2-V14,尾声'     → volumes 2 through 14 plus 尾声
      'V1'             → only volume 1
      'V1-V3'          → volumes 1 through 3
    """
    if not volume_range or not volume_range.strip():
        return True  # No range specified = applicable to all volumes
    
    vr = volume_range.strip()
    
    # Handle comma-separated segments (e.g. 'V2-V14,尾声')
    segments = [s.strip() for s in vr.split(',')]
    
    for seg in segments:
        if '-' in seg:
            parts = seg.split('-', 1)
            start = _parse_volume_number(parts[0])
            end = _parse_volume_number(parts[1])
            if start <= volume_number <= end:
                return True
        else:
            # Single volume
            if _parse_volume_number(seg) == volume_number:
                return True
    
    return False


# ═══════════════════════════════════════════════════════════
# CRUD Operations
# ═══════════════════════════════════════════════════════════

@mcp.tool
def world_upsert(novel_name: str, category: str, name: str, data: dict,
                  keys: str = "", secondary_keys: str = "", tags: str = "",
                  related_ids: str = "", volume_range: str = "", writing_guide: str = "",
                  lorebook_id: str = "", priority: int = 30, is_constant: bool = False,
                  region: str = "", faction_id: int = None) -> str:
    """新增或更新世界观设定。
    
    参数:
      novel_name: 小说名称
      category: 类别(race/faction/location/ability/economy/daily_life/history/bestiary/building/culture/plant/item/core_setting)
      name: 设定名称
      data: 设定数据(JSON对象)
      keys: 主键JSON数组
      secondary_keys: 次键JSON数组
      tags: 标签JSON数组
      related_ids: 关联ID JSON数组
      volume_range: 卷范围(如'V1-V3','V5-V12','V1-尾声')
      writing_guide: 写作指导
      lorebook_id: Lorebook ID
      priority: 优先级(默认30，越高越重要)
      is_constant: 是否常驻(跨卷加载)
      region: 地区(外围/中域/内城/北境/南方密林/东部海岸/西部荒原/北方矿区/全域)
      faction_id: 关联势力ID(可选，关联world_settings中category=faction的条目)
    """
    novel_id = _resolve_novel_id(novel_name)

    data_json = json.dumps(data, ensure_ascii=False)

    extra_cols = ["region", "faction_id"]
    extra_vals_insert = [region if region else "全域", faction_id]
    extra_vals_update = [region if region else "全域", faction_id]

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

    col_str = ", ".join(extra_cols)
    insert_placeholders = ", ".join(["?"] * len(extra_cols))
    update_sets = ", ".join([f"{c} = ?" for c in extra_cols])
    query(
        f"INSERT INTO world_settings (novel_id, category, name, data, {col_str}) "
        f"VALUES (?, ?, ?, ?, {insert_placeholders}) "
        f"ON CONFLICT (novel_id, category, name) DO UPDATE SET data = ?, {update_sets}, updated_at = datetime('now')",
        (novel_id, category, name, data_json, *extra_vals_insert, data_json, *extra_vals_update),
        fetch="none"
    )
    _record_db_hash(novel_id, "world", f"{category}:{name}", data_json)
    from .hooks import fire_post_save
    ws = query("SELECT id FROM world_settings WHERE novel_id = ? AND category = ? AND name = ?",
               (novel_id, category, name), fetch="one")
    if ws:
        fire_post_save(novel_id, "world_setting", ws["id"])
    return json.dumps({"ok": True, "category": category, "name": name}, ensure_ascii=False)


@mcp.tool
def world_query(novel_name: str, category: str = "", name: str = "",
                region: str = "", volume: str = "", faction_id: int = None,
                include_constants: bool = True) -> str:
    """查询世界观设定，支持多维度过滤。
    
    过滤优先级: category+name > 多维过滤 > 全部
    维度: category / region / volume(卷号) / faction_id
    
    参数:
      novel_name: 小说名称
      category: 类别过滤(可选)
      name: 名称精确匹配(可选，需配合category)
      region: 地区过滤(外围/中域/内城/北境/南方密林/东部海岸/西部荒原/北方矿区/全域)
      volume: 卷号过滤(如'V1','V5')，匹配volume_range包含该卷的条目
      faction_id: 势力ID过滤
      include_constants: 是否包含常驻设定(默认True)
    """
    novel_id = _resolve_novel_id(novel_name)
    
    # Exact match mode
    if category and name:
        rows = query("SELECT * FROM world_settings WHERE novel_id = ? AND category = ? AND name = ?",
                     (novel_id, category, name))
        return json.dumps([dict(r) for r in rows], ensure_ascii=False, default=str)
    
    # Multi-dimension filter mode
    conditions = ["novel_id = ?"]
    params = [novel_id]
    
    if category:
        conditions.append("category = ?")
        params.append(category)
    if region:
        conditions.append("(region = ? OR region = '全域')")
        params.append(region)
    if faction_id is not None:
        conditions.append("(faction_id = ? OR faction_id IS NULL)")
        params.append(faction_id)
    
    # Status filter: active or constant
    if not include_constants:
        conditions.append("status = 'active'")
    
    where = " AND ".join(conditions)
    rows = query(f"SELECT * FROM world_settings WHERE {where} ORDER BY category, name", tuple(params))
    
    # Client-side volume_range filtering (volume_range format is complex)
    if volume:
        vol_num = _parse_volume_number(volume)
        filtered = [dict(r) for r in rows if _volume_in_range(vol_num, r.get("volume_range", ""))]
        return json.dumps(filtered, ensure_ascii=False, default=str)
    
    return json.dumps([dict(r) for r in rows], ensure_ascii=False, default=str)


@mcp.tool
def world_load_context(novel_name: str, volume: str = "", regions: str = "",
                       faction_names: str = "", categories: str = "",
                       include_constants: bool = True) -> str:
    """分层加载世界观上下文——写作时按需加载，不加载全部。
    
    核心加载逻辑:
      1. 常驻设定(is_constant=1): 总是加载(如纹路法则等核心规则)
      2. 卷级过滤(volume): 只加载volume_range包含当前卷的条目
      3. 地区过滤(regions): 只加载匹配地区的条目 + 全域条目
      4. 势力过滤(faction_names): 只加载匹配势力的条目
      5. 类别过滤(categories): 只加载指定类别
    
    参数:
      novel_name: 小说名称
      volume: 当前卷号(如'V1','V5')，为空则不过滤卷级
      regions: 逗号分隔的地区列表(如'外围,北境')，为空则不过滤地区
      faction_names: 逗号分隔的势力名称列表(如'壁盾军团,教会')，为空则不过滤势力
      categories: 逗号分隔的类别列表(如'ability,location')，为空则加载所有类别
      include_constants: 是否包含常驻设定(默认True)
    
    返回:
      分层加载结果，含各维度统计和匹配的设定条目
    
    用法示例:
      world_load_context("这次不一样了", volume="V1", regions="外围,北境")
      world_load_context("这次不一样了", volume="V5", faction_names="教会,星火社")
      world_load_context("这次不一样了", volume="V8", categories="ability,faction")
    """
    novel_id = _resolve_novel_id(novel_name)
    
    # Parse multi-value params
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
    
    # Build query conditions
    conditions = ["novel_id = ?", "status = 'active'"]
    params = [novel_id]
    
    # Category filter
    if category_list:
        cat_placeholders = ", ".join(["?"] * len(category_list))
        conditions.append(f"category IN ({cat_placeholders})")
        params.extend(category_list)
    
    # Region filter: match specific regions OR '全域'
    if region_list:
        region_placeholders = ", ".join(["?"] * (len(region_list) + 1))
        conditions.append(f"(region IN ({region_placeholders}))")
        params.extend(region_list + ['全域'])
    
    # Faction filter: match specific faction OR no faction (shared)
    if faction_ids:
        fid_placeholders = ", ".join(["?"] * (len(faction_ids) + 1))
        conditions.append(f"(faction_id IN ({fid_placeholders}) OR faction_id IS NULL)")
        params.extend(faction_ids + [0])  # 0 = shared/global
    
    where = " AND ".join(conditions)
    rows = query(f"SELECT * FROM world_settings WHERE {where} ORDER BY priority DESC, category, name", tuple(params))
    
    # Volume range filtering (client-side due to complex format)
    vol_num = _parse_volume_number(volume) if volume else None
    if vol_num is not None:
        # Separate constants and non-constants
        constant_rows = [r for r in rows if r.get("is_constant")]
        non_constant_rows = [r for r in rows if not r.get("is_constant")]
        
        # Filter non-constants by volume
        volume_matched = [r for r in non_constant_rows if _volume_in_range(vol_num, r.get("volume_range", ""))]
        
        if include_constants:
            result_rows = constant_rows + volume_matched
        else:
            result_rows = volume_matched
    else:
        result_rows = list(rows)
        if not include_constants:
            result_rows = [r for r in result_rows if not r.get("is_constant")]
    
    # Build summary
    cat_stats = {}
    region_stats = {}
    for r in result_rows:
        cat = r.get("category", "")
        reg = r.get("region", "")
        cat_stats[cat] = cat_stats.get(cat, 0) + 1
        region_stats[reg] = region_stats.get(reg, 0) + 1
    
    result = {
        "loaded": len(result_rows),
        "filters": {
            "volume": volume or "all",
            "regions": region_list or "all",
            "factions": faction_name_list or "all",
            "categories": category_list or "all",
            "include_constants": include_constants,
        },
        "stats": {
            "by_category": cat_stats,
            "by_region": region_stats,
        },
        "settings": [dict(r) for r in result_rows],
    }
    
    return json.dumps(result, ensure_ascii=False, default=str)


@mcp.tool
def world_delete(novel_name: str, category: str, name: str) -> str:
    """删除世界观设定
      novel_name: 小说名称
    """
    novel_id = _resolve_novel_id(novel_name)

    query("DELETE FROM world_settings WHERE novel_id = ? AND category = ? AND name = ?",
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
    ws = query("SELECT id, data FROM world_settings WHERE novel_id=? AND category=? AND name=?",
               (novel_id, category, name), fetch="one")
    if not ws:
        return json.dumps({"error": f"世界元素 '{category}:{name}' 不存在"}, ensure_ascii=False)
    data = ws["data"] if isinstance(ws["data"], dict) else {}
    data["_deactivated"] = True
    data["_deactivation_reason"] = reason
    query("UPDATE world_settings SET status='inactive', data=?, updated_at=datetime('now') WHERE id=?",
          (json.dumps(data, ensure_ascii=False), ws["id"]), fetch="none")
    return json.dumps({"ok": True, "category": category, "name": name, "status": "inactive", "reason": reason}, ensure_ascii=False)


@mcp.tool
def world_batch_update_meta(novel_name: str, updates_json: str) -> str:
    """批量更新世界观条目的元数据(region/volume_range/faction_id/priority/is_constant)。
    
    参数:
      novel_name: 小说名称
      updates_json: JSON数组，每项: {"category":"...", "name":"...", "region":"...", "volume_range":"...", "faction_id":int, "priority":int, "is_constant":bool}
    
    用法:
      world_batch_update_meta("这次不一样了", '[{"category":"ability","name":"震刃","region":"北境","faction_id":6}]')
    """
    novel_id = _resolve_novel_id(novel_name)
    updates = json.loads(updates_json)
    
    updated = 0
    errors = []
    for u in updates:
        cat = u.get("category", "")
        name = u.get("name", "")
        if not cat or not name:
            errors.append({"category": cat, "name": name, "error": "missing category or name"})
            continue
        
        sets = []
        vals = []
        if "region" in u:
            sets.append("region = ?")
            vals.append(u["region"])
        if "volume_range" in u:
            sets.append("volume_range = ?")
            vals.append(u["volume_range"])
        if "faction_id" in u:
            sets.append("faction_id = ?")
            vals.append(u["faction_id"])
        if "priority" in u:
            sets.append("priority = ?")
            vals.append(u["priority"])
        if "is_constant" in u:
            sets.append("is_constant = ?")
            vals.append(u["is_constant"])
        
        if not sets:
            continue
        
        vals.extend([novel_id, cat, name])
        query(
            f"UPDATE world_settings SET {', '.join(sets)}, updated_at = datetime('now') WHERE novel_id = ? AND category = ? AND name = ?",
            tuple(vals), fetch="none"
        )
        updated += 1
    
    return json.dumps({"ok": True, "updated": updated, "errors": errors}, ensure_ascii=False)


@mcp.tool
def sync_lorebook(novel_name: str) -> str:
    """从 设定/世界观/ 目录下的 MD 文件同步数据到 DB。
    解析 ## category: name 格式，upsert 到 world_settings 表。
    每次写作前调一次，确保 DB 与文件一致。"""
    novel_dir = os.path.join(_NOVELS_BASE, novel_name, "设定", "世界观")
    if not os.path.isdir(novel_dir):
        return json.dumps({"error": f"novel dir not found: {novel_dir}"}, ensure_ascii=False)

    novel = query("SELECT id FROM novels WHERE name = ?", (novel_name,), fetch="one")
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

            data = {"content": content}
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
            region = meta.get("region", "全域")
            if not isinstance(region, str):
                region = str(region)
            faction_id = meta.get("faction_id", None)

            try:
                query(
                    "INSERT INTO world_settings (novel_id, category, name, data, keys, secondary_keys, tags, related_ids, volume_range, priority, is_constant, region, faction_id) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
                    "ON CONFLICT (novel_id, category, name) DO UPDATE SET "
                    "data = EXCLUDED.data, keys = EXCLUDED.keys, secondary_keys = EXCLUDED.secondary_keys, "
                    "tags = EXCLUDED.tags, related_ids = EXCLUDED.related_ids, volume_range = EXCLUDED.volume_range, "
                    "priority = EXCLUDED.priority, is_constant = EXCLUDED.is_constant, "
                    "region = EXCLUDED.region, faction_id = EXCLUDED.faction_id, updated_at = datetime('now')",
                    (novel_id, category, name, data_json,
                     keys_val if keys_val else None,
                     secondary_keys_val if secondary_keys_val else None,
                     tags_val if tags_val else None,
                     related_val if related_val else None,
                     volume_range or None,
                     priority if priority != 30 else None,
                     is_constant or None,
                     region,
                     faction_id),
                    fetch="none"
                )
                _record_db_hash(novel_id, "world", f"{category}:{name}", data_json)
                cat_key = category
                changes[cat_key] = changes.get(cat_key, 0) + 1
            except Exception as e:
                logger.warning(f"sync_lorebook skip {category}:{name}: {e}")

    return json.dumps({"ok": True, "novel_id": novel_id, "changes": changes}, ensure_ascii=False)


@mcp.tool
def engine_detail(engine_type: str, novel_name: str) -> str:
    """加载写作引擎参考。从 world_settings 读取，模型可自定义覆盖。
      novel_name: 小说名称
    """
    novel_id = _resolve_novel_id(novel_name)

    row = query(
        "SELECT data FROM novel_config WHERE novel_id = ? AND config_type = 'engine_reference' AND name = ?",
        (novel_id, engine_type), fetch="one"
    )
    if row:
        data = row["data"]
        if isinstance(data, dict) and "content" in data:
            return json.dumps({"engine": engine_type, "content": data["content"], "source": "db"}, ensure_ascii=False)

    row = query(
        "SELECT data FROM novel_config WHERE novel_id = ? AND config_type = 'engine_reference' AND name = ?",
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
        "SELECT name, data FROM novel_config WHERE novel_id = ? AND config_type = 'author_voice'",
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
        "SELECT name, data FROM novel_config WHERE novel_id = ? AND config_type = 'writing_spec'",
        (novel_id,)
    )
    if rows:
        specs = [dict(r) for r in rows]
        return json.dumps({"specs": specs}, ensure_ascii=False)
    return json.dumps({"specs": [], "note": "未设置写作规范。用 world_upsert(category='writing_spec') 添加"}, ensure_ascii=False)
