import hashlib
import json
import os
import re

from .db import query, PROJECT_ROOT
from .resolvers import _resolve_novel_id

_NOVELS_BASE = os.path.join(PROJECT_ROOT, "novels")

# ============================================================================
# Hash infrastructure (unchanged)
# ============================================================================


def _ensure_data_hashes_table():
    query("""
        CREATE TABLE IF NOT EXISTS data_hashes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            novel_id INTEGER NOT NULL,
            data_type TEXT NOT NULL,
            data_key TEXT NOT NULL,
            db_hash TEXT NOT NULL DEFAULT '',
            file_hash TEXT NOT NULL DEFAULT '',
            db_updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            file_updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(novel_id, data_type, data_key)
        )
    """, fetch="none")


def _compute_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]


def _upsert_hash(novel_id: int, data_type: str, data_key: str,
                 db_hash: str = "", file_hash: str = ""):
    _ensure_data_hashes_table()
    if db_hash and not file_hash:
        query(
            "INSERT INTO data_hashes (novel_id, data_type, data_key, db_hash, db_updated_at) "
            "VALUES (%s, %s, %s, %s, NOW()) "
            "ON CONFLICT (novel_id, data_type, data_key) DO UPDATE SET db_hash = %s, db_updated_at = NOW()",
            (novel_id, data_type, data_key, db_hash, db_hash), fetch="none"
        )
    elif file_hash and not db_hash:
        query(
            "INSERT INTO data_hashes (novel_id, data_type, data_key, file_hash, file_updated_at) "
            "VALUES (%s, %s, %s, %s, NOW()) "
            "ON CONFLICT (novel_id, data_type, data_key) DO UPDATE SET file_hash = %s, file_updated_at = NOW()",
            (novel_id, data_type, data_key, file_hash, file_hash), fetch="none"
        )
    else:
        sets = []
        vals = []
        if db_hash:
            sets.append("db_hash = %s")
            sets.append("db_updated_at = NOW()")
            vals.append(db_hash)
        if file_hash:
            sets.append("file_hash = %s")
            sets.append("file_updated_at = NOW()")
            vals.append(file_hash)
        if not sets:
            return
        vals.extend([novel_id, data_type, data_key])
        query(
            f"INSERT INTO data_hashes (novel_id, data_type, data_key, {', '.join(['db_hash','file_hash'][:len(sets)])}) "
            f"VALUES (%s, %s, %s, {', '.join(['%s','%s'][:len(sets)])}) "
            f"ON CONFLICT (novel_id, data_type, data_key) DO UPDATE SET {', '.join(sets)}",
            tuple(vals), fetch="none"
        )


def _record_db_hash(novel_id: int, data_type: str, data_key: str, content: str):
    h = _compute_hash(content)
    _upsert_hash(novel_id, data_type, data_key, db_hash=h)


def _record_file_hash(novel_id: int, data_type: str, data_key: str, content: str):
    h = _compute_hash(content)
    _upsert_hash(novel_id, data_type, data_key, file_hash=h)


def _db_row_to_hashable(row: dict) -> str:
    parts = []
    for k in sorted(row.keys()):
        if k in ("id", "created_at", "updated_at"):
            continue
        v = row[k]
        if isinstance(v, (dict, list)):
            v = json.dumps(v, ensure_ascii=False, sort_keys=True)
        parts.append(f"{k}={v}")
    return "|".join(parts)


# ============================================================================
# Formatting helpers
# ============================================================================


def _is_empty(v) -> bool:
    if v is None:
        return True
    if isinstance(v, str):
        return v.strip() == "" or v in ("{}", "[]")
    if isinstance(v, (dict, list)):
        return len(v) == 0
    return False


_TITLE_KEYS = ['name', 'stage', 'volume', 'target', 'scene', 'context', 'type']


def _find_title_key(obj: dict) -> tuple:
    for key in _TITLE_KEYS:
        if key in obj and isinstance(obj[key], str) and obj[key].strip():
            return key, obj[key].strip()
    for k, v in obj.items():
        if isinstance(v, str) and v.strip():
            return k, v.strip()
    return None, None


def _jsonb_to_md(data, indent=0) -> list:
    prefix = "    " * indent
    lines = []

    if isinstance(data, dict):
        for k, v in data.items():
            if _is_empty(v):
                continue
            if isinstance(v, dict):
                lines.append(f"{prefix}- **{k}**:")
                lines.extend(_jsonb_to_md(v, indent + 1))
            elif isinstance(v, list):
                lines.append(f"{prefix}- **{k}**:")
                lines.extend(_jsonb_to_md(v, indent + 1))
            else:
                lines.append(f"{prefix}- **{k}**: {v}")
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                title_key, title_val = _find_title_key(item)
                if title_key:
                    lines.append(f"{prefix}- **{title_val}**:")
                    sub_indent = indent + 1
                    sub_prefix = "    " * sub_indent
                    for k, v in item.items():
                        if k == title_key:
                            continue
                        if _is_empty(v):
                            continue
                        if isinstance(v, (dict, list)):
                            lines.append(f"{sub_prefix}- **{k}**:")
                            lines.extend(_jsonb_to_md(v, sub_indent + 1))
                        else:
                            lines.append(f"{sub_prefix}- **{k}**: {v}")
                else:
                    lines.extend(_jsonb_to_md(item, indent))
            elif isinstance(item, str):
                lines.append(f"{prefix}- {item}")
            elif item is not None:
                lines.append(f"{prefix}- {item}")

    return lines


def _md_bullet(key: str, value) -> str:
    if isinstance(value, bool):
        return f"- **{key}**: {'是' if value else '否'}"
    if isinstance(value, (list,)):
        return f"- **{key}**: {json.dumps(value, ensure_ascii=False)}"
    return f"- **{key}**: {value}"


# ============================================================================
# DB → File sync functions
# ============================================================================

_WORLD_CATEGORY_FILES = {
    "core_setting": "核心设定.md",
    "bestiary": "异灵图鉴.md",
    "ability": "能力体系.md",
    "item": "物品装备.md",
    "economy": "经济体系.md",
    "daily_life": "日常生活.md",
    "history": "历史事件.md",
    "location": "地图.md",
    "faction": "势力.md",
    "race": "种族.md",
}


def _sync_world_to_file(novel_id: int, novel_name: str, row: dict):
    """Sync a world_settings row to its file. Each category maps to a file;
    multiple entries of the same category are sections within that file."""
    base = os.path.join(_NOVELS_BASE, novel_name, "设定", "世界观")
    os.makedirs(base, exist_ok=True)

    category = row["category"]
    name = row["name"]
    data = row.get("data") or {}
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except (json.JSONDecodeError, TypeError):
            data = {"content": data}

    target_file = _WORLD_CATEGORY_FILES.get(category, f"{category}.md")
    fpath = os.path.join(base, target_file)

    # Build entry matching template format: ## {category}: {name}
    lines = [f"\n## {category}: {name}\n"]

    # Metadata fields (from dedicated columns, not from data JSONB)
    meta_items = [
        ("keys", row.get("keys")),
        ("secondary_keys", row.get("secondary_keys")),
        ("tags", row.get("tags")),
        ("related", row.get("related_ids")),
        ("region", row.get("region")),
        ("volume_range", row.get("volume_range")),
        ("faction_id", row.get("faction_id")),
        ("writing_guide", row.get("writing_guide")),
    ]
    for key, val in meta_items:
        if _is_empty(val):
            continue
        lines.append(_md_bullet(key, val))

    priority = row.get("priority")
    if priority is not None and priority != 30:
        lines.append(f"- **priority**: {priority}")
    if row.get("is_constant"):
        lines.append("- **is_constant**: 是")
    if row.get("first_appearance_chapter"):
        lines.append(f"- **首次出场**: Ch{row['first_appearance_chapter']}")

    # Category-specific data fields (from data JSONB, excluding 'content')
    if data:
        for k, v in data.items():
            if k == "content":
                continue
            if _is_empty(v):
                continue
            if isinstance(v, (dict, list)):
                lines.append(f"- **{k}**:")
                lines.extend(_jsonb_to_md(v, 1))
            elif isinstance(v, bool):
                lines.append(f"- **{k}**: {'是' if v else '否'}")
            else:
                lines.append(f"- **{k}**: {v}")

    # Narrative content
    content_text = data.get("content", "") if isinstance(data, dict) else ""
    if content_text:
        lines.append("")
        lines.append(content_text)

    entry_text = "\n".join(lines) + "\n"

    # Merge into existing file: replace matching section or append
    if os.path.exists(fpath):
        with open(fpath, "r", encoding="utf-8") as f:
            content = f.read()
        marker = f"## {category}: {name}"
        if marker in content:
            start = content.index(marker)
            next_h2 = content.find("\n## ", start + len(marker))
            if next_h2 == -1:
                next_h2 = len(content)
            content = content[:start] + entry_text + content[next_h2:]
        else:
            content += entry_text
    else:
        title = target_file.replace(".md", "")
        content = f"# {title}\n{entry_text}"

    with open(fpath, "w", encoding="utf-8") as f:
        f.write(content)
    _record_file_hash(novel_id, "world", f"{category}:{name}", content)


def _sync_character_to_file(novel_id: int, novel_name: str, char: dict):
    """Sync a character row to its file. Generates full template-format file
    from DB data including JSONB rich fields and relations."""
    base = os.path.join(_NOVELS_BASE, novel_name, "设定", "人物")
    os.makedirs(base, exist_ok=True)

    name = char["name"]
    fpath = os.path.join(base, f"{name}.md")

    # Resolve faction name from world_settings
    faction_display = ""
    if char.get("faction_id"):
        frow = query(
            "SELECT name FROM world_settings WHERE id = %s",
            (char["faction_id"],), fetch="val"
        )
        faction_display = frow or str(char["faction_id"])

    sections = [f"# {name}\n"]

    # -- 基本信息 --
    sec_lines = []
    for k in ["role", "race", "ability_level"]:
        v = char.get(k)
        if not _is_empty(v):
            sec_lines.append(f"- **{k}**: {v}")
    if faction_display:
        sec_lines.append(f"- **faction**: {faction_display}")
    if sec_lines:
        sections.append("\n## 基本信息\n")
        sections.extend(sec_lines)

    # -- 外观与性格 --
    sec_lines = []
    for k in ["appearance", "personality", "speech_style", "catchphrase"]:
        v = char.get(k)
        if not _is_empty(v):
            sec_lines.append(f"- **{k}**: {v}")
    if sec_lines:
        sections.append("\n## 外观与性格\n")
        sections.extend(sec_lines)

    # -- 背景与动机 --
    sec_lines = []
    for k in ["background", "goals", "weaknesses"]:
        v = char.get(k)
        if not _is_empty(v):
            sec_lines.append(f"- **{k}**: {v}")
    if sec_lines:
        sections.append("\n## 背景与动机\n")
        sections.extend(sec_lines)

    # -- 弧线 --
    sec_lines = []
    for k in ["arc_notes"]:
        v = char.get(k)
        if not _is_empty(v):
            sec_lines.append(f"- **{k}**: {v}")
    v = char.get("first_appearance_chapter")
    if v is not None:
        sec_lines.append(f"- **first_appearance_chapter**: {v}")
    v = char.get("status")
    if not _is_empty(v):
        sec_lines.append(f"- **status**: {v}")
    if sec_lines:
        sections.append("\n## 弧线\n")
        sections.extend(sec_lines)

    # -- JSONB rich sections (静态档案：基础设定 + 终局快照) --
    # 注意：growth_trajectory 为纯动态数据，不在文件中同步
    # current_snapshot 为终局快照，属于静态档案的一部分
    for heading, col in [
        ("外观描写库", "appearance_detail"),
        ("决策引擎", "decision_engine"),
        ("对话声音指纹", "voice_fingerprint"),
        ("能力体系", "ability_system"),
        ("行为模式", "behavior_pattern"),
    ]:
        val = char.get(col)
        if val and not _is_empty(val):
            sections.append(f"\n## {heading}\n")
            sections.append(f"- **{col}**:")
            sections.extend(_jsonb_to_md(val, 1))

    # -- 当前快照（终局） --
    # current_snapshot JSONB: identity, goal, knows, ability_end_state,
    #   core_discovery, relationships_end, journey_summary 等
    snapshot = _parse_json_field(char.get("current_snapshot"))
    if snapshot and not _is_empty(snapshot):
        sections.append("\n## 当前快照（终局）\n")
        sections.append("- **current_snapshot**:")
        sections.extend(_jsonb_to_md(snapshot, 1))
    else:
        # Fallback: 从基础字段和动态列拼凑简化版
        snap_lines = []
        for k in ["current_location", "current_arc_phase", "emotional_state",
                  "physical_state"]:
            v = char.get(k)
            if not _is_empty(v):
                snap_lines.append(f"- **{k}**: {v}")
        for col in ["ability_progression", "inventory", "knowledge_state"]:
            val = char.get(col)
            if val and not _is_empty(val):
                snap_lines.append(f"- **{col}**:")
                snap_lines.extend(_jsonb_to_md(val, 1))
        if snap_lines:
            sections.append("\n## 当前快照（终局）\n")
            sections.extend(snap_lines)

    # -- 动态追踪指针 --
    sections.append("\n## 动态追踪（不在此文件维护）\n")
    sections.append("> 人物动态状态见 DB：`character_state_snapshots`（状态快照） / `character_distillation_evolution`（蒸馏演化）")

    # -- 关系 --
    # 优先使用 growth_trajectory 中的 relationships_end（终局关系总结）
    # 否则从 character_relations 表实时查询
    growth = _parse_json_field(char.get("growth_trajectory"))
    rels_end = None
    if growth and isinstance(growth, dict):
        rels_end = growth.get("relationships_end")

    if rels_end and not _is_empty(rels_end):
        # 终局关系总结：直接输出列表
        sections.append("\n## 关系\n")
        if isinstance(rels_end, list):
            for item in rels_end:
                if isinstance(item, str):
                    sections.append(f"- {item}")
                elif isinstance(item, dict):
                    sections.extend(_jsonb_to_md(item, 0))
        elif isinstance(rels_end, str):
            sections.append(f"- {rels_end}")

    # 实时关系查询（始终输出完整活跃关系）
    rels = query(
        "SELECT cr.relation_type, cr.description, cr.intensity, "
        "c1.name as from_name, c2.name as to_name, "
        "cr.dialogue_adjustment, cr.micro_expressions, cr.subtext_design "
        "FROM character_relations cr "
        "JOIN characters c1 ON cr.from_character_id = c1.id "
        "JOIN characters c2 ON cr.to_character_id = c2.id "
        "WHERE cr.novel_id = %s AND (cr.from_character_id = %s OR cr.to_character_id = %s) "
        "AND cr.status = 'active' "
        "ORDER BY cr.intensity DESC",
        (novel_id, char["id"], char["id"])
    )
    if rels:
        sections.append("\n## 关系\n")
        for r in rels:
            desc = r.get("description", "")
            line = f"- **{r['relation_type']}** ({r['from_name']} → {r['to_name']}, 强度{r['intensity']})"
            if desc:
                line += f": {desc}"
            sections.append(line)
            if r.get("subtext_design") and not _is_empty(r["subtext_design"]):
                sections.append(f"    - **弦外之音**: {r['subtext_design']}")
            if r.get("dialogue_adjustment") and not _is_empty(r["dialogue_adjustment"]):
                sections.append("    - **对话调整**:")
                sections.extend(_jsonb_to_md(r["dialogue_adjustment"], 2))

    content = "\n".join(sections) + "\n"

    with open(fpath, "w", encoding="utf-8") as f:
        f.write(content)
    _record_file_hash(novel_id, "character", name, content)


def _sync_foreshadow_to_file(novel_id: int, novel_name: str, fs: dict):
    """Sync a foreshadow row to 伏笔清单.md using template format."""
    base = os.path.join(_NOVELS_BASE, novel_name, "设定", "大纲")
    os.makedirs(base, exist_ok=True)
    fpath = os.path.join(base, "伏笔清单.md")

    # Resolve chapter numbers
    planted_ch = ""
    if fs.get("planted_chapter_id"):
        ch = query("SELECT number FROM chapters WHERE id = %s",
                   (fs["planted_chapter_id"],), fetch="val")
        if ch:
            planted_ch = f"Ch{ch}"

    # Build entry matching template format
    lines = [f"\n## foreshadow: {fs['id']}\n"]

    for k in ["description", "status", "importance"]:
        v = fs.get(k)
        if not _is_empty(v):
            lines.append(f"- **{k}**: {v}")

    if planted_ch:
        lines.append(f"- **planted_chapter**: {planted_ch}")
    if fs.get("planned_recall_chapter"):
        lines.append(f"- **planned_recall_chapter**: Ch{fs['planned_recall_chapter']}")

    for k in ["related_characters", "tags"]:
        v = fs.get(k)
        if v and not _is_empty(v):
            lines.append(f"- **{k}**: {json.dumps(v, ensure_ascii=False)}")

    entry_text = "\n".join(lines) + "\n"

    # Merge into existing file
    if os.path.exists(fpath):
        with open(fpath, "r", encoding="utf-8") as f:
            content = f.read()
        marker = f"## foreshadow: {fs['id']}"
        if marker in content:
            start = content.index(marker)
            next_h2 = content.find("\n## ", start + len(marker))
            if next_h2 == -1:
                next_h2 = len(content)
            content = content[:start] + entry_text + content[next_h2:]
        else:
            content += entry_text
    else:
        content = f"# 伏笔清单\n{entry_text}"

    with open(fpath, "w", encoding="utf-8") as f:
        f.write(content)
    _record_file_hash(novel_id, "foreshadow", str(fs["id"]), content)


def _render_md_table(rows: list[dict], columns: list[str] | None = None) -> list[str]:
    """Render a list of dicts as a markdown table."""
    if not rows:
        return []
    if columns is None:
        columns = list(rows[0].keys())
    lines = ['| ' + ' | '.join(columns) + ' |']
    lines.append('|' + '|'.join(['------' for _ in columns]) + '|')
    for row in rows:
        cells = [str(row.get(c, '')).replace('|', '\\|') for c in columns]
        lines.append('| ' + ' | '.join(cells) + ' |')
    return lines


def _parse_json_field(val) -> any:
    """Parse a JSON text field, returning the parsed object or None."""
    if val is None:
        return None
    if isinstance(val, (dict, list)):
        return val
    if isinstance(val, str):
        val = val.strip()
        if not val or val in ('{}', '[]', ''):
            return None
        try:
            return json.loads(val)
        except (json.JSONDecodeError, TypeError):
            return None
    return None


def _sync_volume_to_file(novel_id: int, novel_name: str, vol: dict,
                         overwrite: bool = False):
    """Sync a volume from DB to file.
    For existing files: skip unless overwrite=True.
    For new volumes or overwrite: generate full template from DB rich data."""
    base = os.path.join(_NOVELS_BASE, novel_name, "设定", "大纲")
    os.makedirs(base, exist_ok=True)

    num = vol["number"]
    title = vol.get("title", "")
    fname = f"V{num}-{title}.md" if title else f"V{num}.md"
    fpath = os.path.join(base, fname)

    if os.path.exists(fpath) and not overwrite:
        with open(fpath, "r", encoding="utf-8") as f:
            content = f.read()
        _record_file_hash(novel_id, "volume", fname.replace(".md", ""), content)
        return False  # did not create/overwrite

    lines = [f"# V{num}：{title}\n"]

    # ── 卷级信息 ──
    lines.append("\n## 卷级信息\n")
    lines.append(f"- **number**: {num}")
    lines.append(f"- **title**: {title}")
    mp = _parse_json_field(vol.get("main_plotlines"))
    if mp:
        for pl in mp:
            lines.append(f"- **main_plotlines**: {pl}")
    # Blockquote fields
    for label, key in [("核心情绪", "core_emotion"), ("POV锚点", "pov_anchor"),
                        ("时间跨度", "time_span"), ("声音适配", "voice_mapping")]:
        val = vol.get(key, "")
        if val:
            lines.append(f"> **{label}**：{val}")

    # ── 卷级因果链 ──
    chain = vol.get("causal_chain", "")
    if chain:
        lines.append(f"\n## 卷级因果链\n")
        lines.append(chain)

    # ── 故事脉络（四幕）──
    act_labels = [("起", "act_intro"), ("承", "act_rise"),
                  ("转", "act_twist"), ("合", "act_resolution")]
    has_acts = any(_parse_json_field(vol.get(k)) for _, k in act_labels)
    if has_acts:
        lines.append("\n## 故事脉络\n")
        for label, key in act_labels:
            act = _parse_json_field(vol.get(key))
            if not act:
                continue
            lines.append(f"\n### {label}\n")
            prose = act.get("prose", "")
            if prose:
                lines.append(prose)
            events = act.get("events", [])
            if events:
                lines.append("\n事件清单：")
                for i, evt in enumerate(events, 1):
                    lines.append(f"- E{i}：{evt}")
            feibi = act.get("feibi_notes", [])
            if feibi:
                lines.append("\n费笔清单：")
                for i, fb in enumerate(feibi, 1):
                    lines.append(f"- 费笔{i}：{fb}")
            list_items = act.get("list_items", [])
            if list_items:
                for item in list_items:
                    lines.append(f"- {item}")

    # ── 下卷衔接表 ──
    bridge = _parse_json_field(vol.get("next_volume_bridge"))
    if bridge:
        lines.append("\n## 下卷衔接\n")
        lines.extend(_render_md_table(bridge))

    # ── 人物弧光 ──
    arcs = _parse_json_field(vol.get("character_arcs"))
    if arcs:
        lines.append("\n## 人物弧光\n")
        cols = list(arcs[0].keys()) if arcs else []
        lines.extend(_render_md_table(arcs, cols))

    # ── 人物互动矩阵 ──
    matrix = _parse_json_field(vol.get("interaction_matrix"))
    if matrix:
        lines.append("\n## 人物互动矩阵\n")
        cols = list(matrix[0].keys()) if matrix else []
        lines.extend(_render_md_table(matrix, cols))

    # ── 不做的 ──
    bounds = _parse_json_field(vol.get("boundaries"))
    if bounds:
        lines.append("\n## 不做的\n")
        for b in bounds:
            lines.append(f"- {b}")

    # ── 悬念锚点 ──
    suspense = _parse_json_field(vol.get("suspense_anchors"))
    if suspense:
        lines.append("\n## 悬念锚点\n")
        answered = suspense.get("answered", [])
        if answered:
            lines.append("### 本卷回答了什么疑问\n")
            for a in answered:
                lines.append(f"- {a}")
        new_q = suspense.get("new_questions", [])
        if new_q:
            lines.append("\n### 本卷新提出的疑问\n")
            cols = list(new_q[0].keys()) if new_q else []
            lines.extend(_render_md_table(new_q, cols))

    # ── 核心对话锚点 ──
    dialogues = _parse_json_field(vol.get("key_dialogues"))
    if dialogues:
        lines.append("\n## 核心对话锚点\n")
        cols = list(dialogues[0].keys()) if dialogues else []
        lines.extend(_render_md_table(dialogues, cols))

    # ── 写作优先级 ──
    priorities = _parse_json_field(vol.get("writing_priorities"))
    if priorities:
        lines.append("\n## 写作优先级\n")
        for level in ["P0", "P1", "P2"]:
            items = priorities.get(level, [])
            if items:
                desc = {"P0": "不可删减", "P1": "强烈建议保留", "P2": "可压缩但建议保留"}.get(level, "")
                lines.append(f"\n### {level}（{desc}）\n")
                for i, item in enumerate(items, 1):
                    lines.append(f"{i}. {item}")

    # ── 硬约束自检 ──
    constraints = _parse_json_field(vol.get("hard_constraints"))
    if constraints:
        lines.append("\n## 硬约束自检\n")
        raw = constraints.get("raw", "")
        if raw:
            lines.append(raw)

    # ── 信息投放节奏 ──
    pacing = _parse_json_field(vol.get("info_pacing"))
    if pacing:
        lines.append("\n## 信息投放节奏\n")
        cols = list(pacing[0].keys()) if pacing else []
        lines.extend(_render_md_table(pacing, cols))

    # ── 节奏分配 ──
    rhythm = _parse_json_field(vol.get("rhythm_allocation"))
    if rhythm:
        lines.append("\n## 节奏分配\n")
        cols = list(rhythm[0].keys()) if rhythm else []
        lines.extend(_render_md_table(rhythm, cols))

    # ── 备注 ──
    notes = vol.get("notes", "")
    if notes:
        lines.append(f"\n## 备注\n")
        lines.append(notes)

    content = "\n".join(lines) + "\n"
    with open(fpath, "w", encoding="utf-8") as f:
        f.write(content)
    _record_file_hash(novel_id, "volume", fname.replace(".md", ""), content)
    return True  # created/overwrote file


# ============================================================================
# File → DB sync functions (for startup reconciliation)
# ============================================================================


def _sync_world_to_db(novel_id: int, category: str, name: str, file_content: str):
    data = {"content": file_content[:4000]}
    data_json = json.dumps(data, ensure_ascii=False)
    query(
        "INSERT INTO world_settings (novel_id, category, name, data) "
        "VALUES (%s, %s, %s, %s) "
        "ON CONFLICT (novel_id, category, name) DO UPDATE SET data = %s, updated_at = NOW()",
        (novel_id, category, name, data_json, data_json), fetch="none"
    )
    _record_db_hash(novel_id, "world", f"{category}:{name}", data_json)


def _sync_character_to_db(novel_id: int, char_name: str, file_content: str):
    existing = query(
        "SELECT id FROM characters WHERE novel_id = %s AND name = %s",
        (novel_id, char_name), fetch="one"
    )
    if existing:
        data = {"content": file_content[:4000]}
        data_json = json.dumps(data, ensure_ascii=False)
        query(
            "UPDATE characters SET status = %s, updated_at = NOW() WHERE id = %s",
            (data_json, existing["id"]), fetch="none"
        )
        _record_db_hash(novel_id, "character", char_name, data_json)


def _sync_foreshadow_to_db(novel_id: int, fs_id: int, status: str, file_content: str):
    if status == "recalled":
        query(
            "UPDATE foreshadows SET status = 'recalled', updated_at = NOW() WHERE id = %s",
            (fs_id,), fetch="none"
        )
    _record_db_hash(novel_id, "foreshadow", str(fs_id), file_content)
