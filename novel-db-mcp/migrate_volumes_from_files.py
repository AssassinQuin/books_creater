"""
migrate_volumes_from_files.py
一次性迁移：解析 V1-V15 大纲文件，填充 volumes 表新增列。

用法：cd novel-db-mcp && python migrate_volumes_from_files.py
"""

import re
import json
import os
import sqlite3
import glob


DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'novel.db')
OUTLINES_DIR = os.path.join(
    os.path.dirname(__file__), '..', 'novels', '这次不一样了', '设定', '大纲'
)


def parse_md_sections(content: str) -> dict[str, str]:
    """Split file content by ## headers into a dict."""
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


def parse_md_table(text: str) -> list[dict]:
    """Parse a markdown table into list of dicts using header row as keys."""
    rows = []
    header = None
    for line in text.split('\n'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if '|' not in line:
            continue
        cells = [c.strip() for c in line.split('|')]
        # Remove empty first/last from split
        if cells and cells[0] == '':
            cells = cells[1:]
        if cells and cells[-1] == '':
            cells = cells[:-1]
        # Skip separator row (all dashes/colons)
        if all(re.match(r'^[-:]+$', c) for c in cells):
            continue
        if header is None:
            header = cells
            continue
        if header and len(cells) >= 1:
            row = {}
            for i, h in enumerate(header):
                row[h] = cells[i] if i < len(cells) else ''
            rows.append(row)
    return rows


def extract_blockquote_fields(text: str) -> dict:
    """Extract > **label**: value pairs from blockquotes."""
    result = {}
    for m in re.finditer(r'>\s*\*\*(.+?)\*\*[：:]\s*(.+)', text):
        label = m.group(1).strip()
        value = m.group(2).strip()
        result[label] = value
    return result


def parse_volume_file(filepath: str) -> dict:
    """Parse a single volume outline file into structured data."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    sections = parse_md_sections(content)
    result = {}

    # ── 卷级信息 ──
    info = sections.get('卷级信息', '')
    bq = extract_blockquote_fields(info)
    label_map = {
        '核心情绪': 'core_emotion',
        'POV锚点': 'pov_anchor',
        '时间跨度': 'time_span',
        '声音适配': 'voice_mapping',
    }
    for label, key in label_map.items():
        if label in bq:
            result[key] = bq[label]

    # ── 卷级因果链 ──
    chain = sections.get('卷级因果链', '').strip()
    if chain:
        # Remove leading empty lines
        chain = '\n'.join(l for l in chain.split('\n') if l.strip())
        result['causal_chain'] = chain

    # ── 故事脉络 → 四幕 ──
    story = sections.get('故事脉络', '')
    if story:
        act_parts = re.split(r'(?=^###\s)', story, flags=re.MULTILINE)
        act_key_map = {'起': 'act_intro', '承': 'act_rise', '转': 'act_twist', '合': 'act_resolution'}
        for part in act_parts:
            h3 = re.match(r'^###\s*(.)', part)
            if not h3:
                continue
            char = h3.group(1)
            if char not in act_key_map:
                continue
            act_content = part[h3.end():].strip()

            # Extract events (E1: ...  or - E1：...)
            events = []
            for em in re.finditer(r'E\d+[：:]\s*(.+)', act_content):
                events.append(em.group(1).strip())

            # Extract feibi notes
            feibi_notes = []
            for fm in re.finditer(r'费笔\d+[：:]\s*(.+)', act_content):
                feibi_notes.append(fm.group(1).strip())

            # Extract list items
            list_items = []
            for lm in re.finditer(r'^-\s+(.+)', act_content, re.MULTILINE):
                item = lm.group(1).strip()
                if not item.startswith('E') and not item.startswith('费笔'):
                    list_items.append(item)

            # Prose = everything before structured lists
            prose = act_content
            for marker in ['事件清单', '费笔清单', '支线在此', '下卷钩子', '罕见组合']:
                idx = prose.find(marker)
                if idx > 0:
                    prose = prose[:idx]
            # Also trim trailing list items
            prose_lines = []
            for line in prose.split('\n'):
                if re.match(r'^-\s+E\d+', line):
                    break
                if re.match(r'^-\s+费笔', line):
                    break
                prose_lines.append(line)
            prose = '\n'.join(prose_lines).strip()

            act_data = {}
            if prose:
                act_data['prose'] = prose
            if events:
                act_data['events'] = events
            if feibi_notes:
                act_data['feibi_notes'] = feibi_notes
            if list_items:
                act_data['list_items'] = list_items

            if act_data:
                result[act_key_map[char]] = json.dumps(act_data, ensure_ascii=False)

    # ── 人物弧光 ──
    arcs_text = sections.get('人物弧光', '')
    if arcs_text:
        rows = parse_md_table(arcs_text)
        if rows:
            result['character_arcs'] = json.dumps(rows, ensure_ascii=False)

    # ── 人物互动矩阵 ──
    matrix_text = sections.get('人物互动矩阵', '')
    if matrix_text:
        rows = parse_md_table(matrix_text)
        if rows:
            result['interaction_matrix'] = json.dumps(rows, ensure_ascii=False)

    # ── 不做的 ──
    boundaries_text = sections.get('不做的', '')
    if boundaries_text:
        items = []
        for line in boundaries_text.split('\n'):
            line = line.strip()
            if line.startswith('- '):
                items.append(line[2:])
        if items:
            result['boundaries'] = json.dumps(items, ensure_ascii=False)

    # ── 悬念锚点 ──
    suspense_text = sections.get('悬念锚点', '')
    if suspense_text:
        answered = []
        new_questions = []
        parts = re.split(r'本卷新提出的疑问', suspense_text)
        if len(parts) >= 1:
            for line in parts[0].split('\n'):
                m = re.match(r'^-\s*(.+)', line)
                if m:
                    answered.append(m.group(1).strip())
        if len(parts) >= 2:
            rows = parse_md_table(parts[1])
            new_questions = rows
        result['suspense_anchors'] = json.dumps({
            'answered': answered,
            'new_questions': new_questions
        }, ensure_ascii=False)

    # ── 核心对话锚点 ──
    dialogue_text = sections.get('核心对话锚点', '')
    if dialogue_text:
        # Try table format first
        rows = parse_md_table(dialogue_text)
        if rows:
            result['key_dialogues'] = json.dumps(rows, ensure_ascii=False)
        else:
            # Fallback: extract quoted dialogues
            dialogues = []
            for dm in re.finditer(r'>\s*\*\*(.+?)\*\*[：:]\s*["""](.+?)["""]', dialogue_text):
                dialogues.append({
                    'character': dm.group(1).strip(),
                    'dialogue': dm.group(2).strip()
                })
            if dialogues:
                result['key_dialogues'] = json.dumps(dialogues, ensure_ascii=False)

    # ── 写作优先级 ──
    priority_text = sections.get('写作优先级', '')
    if priority_text:
        priorities = {'P0': [], 'P1': [], 'P2': []}
        current_level = None
        for line in priority_text.split('\n'):
            if 'P0' in line and '不可删' in line:
                current_level = 'P0'
            elif 'P1' in line and '强烈' in line:
                current_level = 'P1'
            elif 'P2' in line and '可压缩' in line:
                current_level = 'P2'
            elif current_level and re.match(r'^\d+\.\s', line.strip()):
                item = re.sub(r'^\d+\.\s+', '', line.strip())
                priorities[current_level].append(item)
        if any(priorities.values()):
            result['writing_priorities'] = json.dumps(priorities, ensure_ascii=False)

    # ── 硬约束自检 ──
    constraints_text = sections.get('硬约束自检', '')
    if constraints_text:
        result['hard_constraints'] = json.dumps({'raw': constraints_text.strip()}, ensure_ascii=False)

    # ── 下卷衔接表 ──
    bridge_text = sections.get('下卷衔接', '')
    if not bridge_text:
        bridge_text = sections.get('下卷衔接表', '')
    if bridge_text:
        rows = parse_md_table(bridge_text)
        if rows:
            result['next_volume_bridge'] = json.dumps(rows, ensure_ascii=False)

    # ── 信息投放节奏 ──
    pacing_text = sections.get('信息投放节奏', '')
    if not pacing_text:
        pacing_text = sections.get('信息投放节奏表', '')
    if pacing_text:
        rows = parse_md_table(pacing_text)
        if rows:
            result['info_pacing'] = json.dumps(rows, ensure_ascii=False)

    # ── 节奏分配 ──
    rhythm_text = sections.get('节奏分配', '')
    if not rhythm_text:
        rhythm_text = sections.get('节奏分配表', '')
    if rhythm_text:
        rows = parse_md_table(rhythm_text)
        if rows:
            result['rhythm_allocation'] = json.dumps(rows, ensure_ascii=False)

    return result


def main():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row

    # Get novel_id
    row = db.execute("SELECT id FROM novels WHERE name='这次不一样了'").fetchone()
    if not row:
        print("ERROR: novel not found")
        return
    novel_id = row['id']

    # Find and process each volume file
    outline_files = sorted(glob.glob(os.path.join(OUTLINES_DIR, 'V*-*.md')))
    # Exclude non-volume files
    exclude = {'全书框架', '全书脉络', '卷级目标卡', '跨卷伏笔总图', '全书框架审计', '支线总图', '附录', '伏笔清单', '兄妹心结'}

    stats = {'total': 0, 'updated': 0, 'skipped': 0, 'errors': []}

    for fpath in outline_files:
        fname = os.path.basename(fpath)
        # Extract volume number
        vm = re.match(r'V(\d+)-', fname)
        if not vm:
            continue
        vol_num = int(vm.group(1))

        # Check if this is a volume file (not a special file)
        base_name = fname.replace('.md', '')
        if any(ex in base_name for ex in exclude):
            continue

        stats['total'] += 1
        print(f"Processing V{vol_num} ({fname})...", end=' ')

        try:
            data = parse_volume_file(fpath)
            if not data:
                print("SKIP (no extractable data)")
                stats['skipped'] += 1
                continue

            # Build UPDATE statement
            sets = []
            vals = []
            for key, value in data.items():
                sets.append(f"{key} = ?")
                vals.append(value)

            vals.append(novel_id)
            vals.append(vol_num)

            sql = f"UPDATE volumes SET {', '.join(sets)}, updated_at = CURRENT_TIMESTAMP WHERE novel_id = ? AND number = ?"
            cursor = db.execute(sql, vals)
            if cursor.rowcount > 0:
                db.commit()
                fields_count = len(sets)
                print(f"OK ({fields_count} fields updated)")
                stats['updated'] += 1
            else:
                print("SKIP (no matching volume in DB)")
                stats['skipped'] += 1
        except Exception as e:
            print(f"ERROR: {e}")
            stats['errors'].append(f"V{vol_num}: {e}")

    db.close()

    print(f"\n=== Migration Summary ===")
    print(f"Total files: {stats['total']}")
    print(f"Updated: {stats['updated']}")
    print(f"Skipped: {stats['skipped']}")
    print(f"Errors: {len(stats['errors'])}")
    for e in stats['errors']:
        print(f"  - {e}")


if __name__ == '__main__':
    main()
