"""
migrate_characters_from_files.py
一次性迁移：从各数据源提取角色富数据，填充 DB 中空的 JSON 字段。

数据源：
1. 各卷大纲的人物弧光表 → growth_trajectory
2. 各卷大纲的人物互动矩阵 → behavior_pattern
3. 角色快速参考卡 → voice_fingerprint / appearance_detail
4. 人物能力设定方案 → ability_system
5. 卷级目标卡中的角色变化 → growth_trajectory 补充

用法：cd novel-db-mcp && python migrate_characters_from_files.py
"""

import re
import json
import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'novel.db')
NOVEL_BASE = os.path.join(
    os.path.dirname(__file__), '..', 'novels', '这次不一样了', '设定'
)


def parse_md_table(text: str) -> list[dict]:
    rows = []
    header = None
    for line in text.split('\n'):
        line = line.strip()
        if not line or line.startswith('#') or '|' not in line:
            continue
        cells = [c.strip() for c in line.split('|')]
        if cells and cells[0] == '':
            cells = cells[1:]
        if cells and cells[-1] == '':
            cells = cells[:-1]
        if all(re.match(r'^[-:]+$', c) for c in cells):
            continue
        if header is None:
            header = cells
            continue
        if header:
            row = {}
            for i, h in enumerate(header):
                row[h] = cells[i] if i < len(cells) else ''
            rows.append(row)
    return rows


def parse_md_sections(content: str) -> dict[str, str]:
    sections = {}
    current_h2 = None
    current_lines = []
    for line in content.split('\n'):
        m = re.match(r'^## (.+)', line)
        if m:
            if current_h2 is not None:
                sections[current_h2] = '\n'.join(current_lines)
            current_h2 = m.group(1).strip()
            current_lines = []
        else:
            current_lines.append(line)
    if current_h2 is not None:
        sections[current_h2] = '\n'.join(current_lines)
    return sections


def extract_growth_from_volumes(db) -> dict[str, list]:
    """从各卷大纲的人物弧光表提取角色成长轨迹"""
    growth = {}
    rows = db.execute(
        "SELECT number, character_arcs FROM volumes WHERE novel_id=1 ORDER BY number"
    ).fetchall()

    for row in rows:
        vol_num = row[0]
        arcs_text = row[1]
        if not arcs_text or arcs_text in ('[]', ''):
            continue
        try:
            arcs = json.loads(arcs_text)
        except json.JSONDecodeError:
            continue
        for arc in arcs:
            # Find character name — handle various column names
            char_name = arc.get('角色') or arc.get('character') or ''
            if not char_name:
                continue
            # Clean markdown bold
            char_name = char_name.replace('**', '').strip()
            if char_name not in growth:
                growth[char_name] = []
            growth[char_name].append({
                'volume': vol_num,
                'start_state': arc.get('卷初状态', arc.get('start_state', '')),
                'trigger': arc.get('触发事件', arc.get('trigger', '')),
                'end_state': arc.get('卷末状态', arc.get('end_state', '')),
            })

    return growth


def extract_interaction_from_volumes(db) -> dict[str, list]:
    """从各卷大纲的人物互动矩阵提取关系变化"""
    interactions = {}
    rows = db.execute(
        "SELECT number, interaction_matrix FROM volumes WHERE novel_id=1 ORDER BY number"
    ).fetchall()

    for row in rows:
        vol_num = row[0]
        matrix_text = row[1]
        if not matrix_text or matrix_text in ('[]', ''):
            continue
        try:
            matrix = json.loads(matrix_text)
        except json.JSONDecodeError:
            continue
        for item in matrix:
            pair = item.get('互动对', item.get('pair', ''))
            if not pair:
                continue
            # Extract character names from pair (e.g., "沈野↔沈念")
            names = re.split(r'[↔→←]', pair)
            for name in names:
                name = name.replace('**', '').strip()
                if not name:
                    continue
                if name not in interactions:
                    interactions[name] = []
                interactions[name].append({
                    'volume': vol_num,
                    'pair': pair,
                    'relation_type': item.get('关系类型', item.get('relation_type', '')),
                    'start': item.get('卷初关系', item.get('start_relation', '')),
                    'end': item.get('卷末关系', item.get('end_relation', '')),
                    'key_scenes': item.get('关键互动场景', item.get('key_scenes', '')),
                })

    return interactions


def extract_quickref() -> dict[str, dict]:
    """从角色快速参考卡提取语音指纹"""
    fpath = os.path.join(NOVEL_BASE, '角色快速参考卡.md')
    if not os.path.exists(fpath):
        return {}

    with open(fpath, 'r', encoding='utf-8') as f:
        content = f.read()

    result = {}
    # Split by character entries — they're usually ### headings or bold names
    sections = parse_md_sections(content)

    # Try to parse per-character blocks
    current_char = None
    char_data = {}
    for line in content.split('\n'):
        # Look for character name headers
        h3 = re.match(r'^###\s+(.+)', line)
        bold_name = re.match(r'^\*\*(.+?)\*\*', line)
        if h3:
            if current_char and char_data:
                result[current_char] = char_data
            current_char = h3.group(1).strip()
            char_data = {}
        elif bold_name and not current_char:
            current_char = bold_name.group(1).strip()
            char_data = {}

        if current_char:
            # Extract speech style, catchphrase, personality hints
            speech_m = re.match(r'-?\s*\*\*?(?:说话|语言|口吻|speech)\*\*?[：:]\s*(.+)', line)
            if speech_m:
                char_data['speech_hint'] = speech_m.group(1).strip()
            habit_m = re.match(r'-?\s*\*\*?(?:习惯|行为|habit)\*\*?[：:]\s*(.+)', line)
            if habit_m:
                char_data['habit'] = habit_m.group(1).strip()

    if current_char and char_data:
        result[current_char] = char_data

    return result


def extract_ability_from_db(db) -> dict[str, dict]:
    """从 world_settings 中提取能力相关数据"""
    abilities = {}
    rows = db.execute(
        "SELECT name, data FROM world_settings WHERE novel_id=1 AND category='ability' ORDER BY name"
    ).fetchall()

    for row in rows:
        name = row[0]
        data_text = row[1]
        try:
            data = json.loads(data_text) if data_text else {}
        except json.JSONDecodeError:
            data = {}
        abilities[name] = data

    return abilities


def build_voice_fingerprint(char_name: str, char_row: dict, quickref: dict) -> dict:
    """构建声音指纹"""
    voice = {}
    speech_style = char_row.get('speech_style', '')
    catchphrase = char_row.get('catchphrase', '')

    if speech_style:
        voice['speech_style'] = speech_style
    if catchphrase:
        voice['catchphrase'] = catchphrase.split('。') if '。' in catchphrase else [catchphrase]

    # From quickref
    qr = quickref.get(char_name, {})
    if 'speech_hint' in qr:
        voice['speech_hint'] = qr['speech_hint']
    if 'habit' in qr:
        voice['habit'] = qr['habit']

    return voice if voice else {}


def build_ability_system(char_name: str, char_row: dict, ability_data: dict) -> dict:
    """构建能力系统"""
    ability = {}
    level = char_row.get('ability_level', '')
    if level:
        ability['level_progression'] = level

    goals = char_row.get('goals', '')
    if goals:
        ability['goals_by_phase'] = goals

    # Find related abilities from world_settings
    related = []
    for abil_name, abil_data in ability_data.items():
        abil_str = json.dumps(abil_data, ensure_ascii=False)
        if char_name in abil_str:
            related.append(abil_name)
    if related:
        ability['related_abilities'] = related

    return ability if ability else {}


def main():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row

    # Load source data
    growth_data = extract_growth_from_volumes(db)
    interaction_data = extract_interaction_from_volumes(db)
    quickref_data = extract_quickref()
    ability_data = extract_ability_from_db(db)

    print(f"Sources loaded:")
    print(f"  Growth data: {len(growth_data)} characters")
    print(f"  Interaction data: {len(interaction_data)} characters")
    print(f"  Quickref data: {len(quickref_data)} characters")
    print(f"  Ability data: {len(ability_data)} abilities")

    # Process each character
    chars = db.execute(
        "SELECT id, name, appearance, personality, speech_style, catchphrase, goals, arc_notes, ability_level, weaknesses FROM characters WHERE novel_id=1"
    ).fetchall()

    stats = {'updated': 0, 'skipped': 0}

    for char in chars:
        name = char['name']
        updates = {}

        # growth_trajectory
        if name in growth_data:
            updates['growth_trajectory'] = json.dumps(growth_data[name], ensure_ascii=False)

        # behavior_pattern (from interactions)
        if name in interaction_data:
            updates['behavior_pattern'] = json.dumps({
                'interactions': interaction_data[name][:10]  # Top 10 most relevant
            }, ensure_ascii=False)

        # voice_fingerprint
        voice = build_voice_fingerprint(name, dict(char), quickref_data)
        if voice:
            updates['voice_fingerprint'] = json.dumps(voice, ensure_ascii=False)

        # ability_system
        ability = build_ability_system(name, dict(char), ability_data)
        if ability:
            updates['ability_system'] = json.dumps(ability, ensure_ascii=False)

        # appearance_detail (from appearance field + enhancements)
        appearance = char['appearance']
        if appearance:
            updates['appearance_detail'] = json.dumps({
                'base': appearance,
                'scenes': []  # To be filled by chapter writing
            }, ensure_ascii=False)

        # decision_engine (from goals + weaknesses)
        goals = char['goals'] or ''
        weaknesses = char['weaknesses'] or ''
        if goals or weaknesses:
            engine = {}
            if goals:
                engine['goals'] = goals
            if weaknesses:
                engine['constraints'] = weaknesses
            updates['decision_engine'] = json.dumps(engine, ensure_ascii=False)

        if not updates:
            print(f"  {name}: SKIP (no data to fill)")
            stats['skipped'] += 1
            continue

        # Build UPDATE
        sets = [f"{k} = ?" for k in updates]
        vals = list(updates.values()) + [char['id']]
        db.execute(
            f"UPDATE characters SET {', '.join(sets)} WHERE id = ?",
            vals
        )

        fields = ', '.join(updates.keys())
        print(f"  {name}: OK ({fields})")
        stats['updated'] += 1

    db.commit()
    db.close()

    print(f"\n=== Character Migration Summary ===")
    print(f"Updated: {stats['updated']}")
    print(f"Skipped: {stats['skipped']}")


if __name__ == '__main__':
    main()
