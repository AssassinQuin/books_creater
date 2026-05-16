#!/usr/bin/env python3
"""
Reverse parser: Convert human-readable markdown character sections back to JSON.

Parse logic:
  Every section body is a FLAT DICT (key-value pairs).
  Individual keys may have array values (list of strings or list of objects).

  - "- **key**: value"                → "key": "value"
  - "- **key**: " + indented "- item" → "key": ["item1", "item2"]
  - "- **key**: " + indented "- **id**:" + sub-fields → "key": [{"name":"id", ...}, ...]

Usage:
  python3 tools/parse_char_sections.py 沈鹤
  python3 tools/parse_char_sections.py --all
"""

import re, json, os, sys

CHAR_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                        "novels/这次不一样了/设定/人物")

RICH_SECTIONS = [
    ("appearance_detail", "外观描写库"),
    ("decision_engine", "决策引擎"),
    ("voice_fingerprint", "对话声音指纹"),
    ("ability_system", "能力体系"),
    ("behavior_pattern", "行为模式"),
    ("current_snapshot", "当前快照"),
    ("growth_trajectory", "成长轨迹"),
]


def _indent(line):
    return len(line) - len(line.lstrip())


def parse_section_text(text, section_name=None):
    """
    Parse a section body (starting with '- **field**: ') back into a JSON object.
    Returns (db_field_name, parsed_data).
    """
    lines = text.strip().split('\n')
    if not lines:
        return None, {}
    
    m = re.match(r'^-\s+\*\*([^*]+)\*\*\s*:\s*(.*)', lines[0].strip())
    if not m:
        return None, {}
    
    db_field = m.group(1).strip()
    body_lines = lines[1:]
    
    parsed = _parse_flat_dict(body_lines)
    return db_field, parsed


def _parse_flat_dict(lines):
    """Parse lines into a flat dict. Each field's value is determined by its sub-lines."""
    lines = [l for l in lines if l.strip()]
    if not lines:
        return {}
    
    base_indent = _indent(lines[0])
    
    # Group into items
    items = []
    current = []
    for l in lines:
        li = _indent(l)
        ls = l.lstrip()
        if li == base_indent and ls.startswith("- **") and current:
            items.append(current)
            current = []
        current.append(l)
    if current:
        items.append(current)
    
    result = {}
    for item_lines in items:
        # First line is the key line
        first = item_lines[0].lstrip()
        m = re.match(r'^-\s+\*\*([^*]+)\*\*\s*:\s*(.*)', first)
        if not m:
            continue
        
        key = m.group(1).strip()
        inline_val = m.group(2).strip()
        
        if inline_val:
            result[key] = inline_val
        else:
            # Get sub content (lines at deeper indent)
            sub = _get_sub_lines(item_lines)
            if not sub:
                result[key] = ""
            else:
                val = _parse_value_lines(sub)
                result[key] = val if val is not None else ""
    
    return result


def _get_sub_lines(item_lines):
    """Get lines at deeper indent from an item."""
    if len(item_lines) <= 1:
        return []
    
    first_indent = _indent(item_lines[0])
    sub = []
    for l in item_lines[1:]:
        if _indent(l) > first_indent:
            sub.append(l)
    return sub


def _parse_value_lines(lines):
    """
    Parse value lines into a string, array, or array of objects.
    Returns None if empty/blank.
    """
    if not lines:
        return None
    
    # Check if lines form an array: "- text" without "- **"
    if all(l.lstrip().startswith("- ") and not l.lstrip().startswith("- **") for l in lines):
        items = [l.lstrip()[2:] for l in lines]
        return items
    
    # Check if lines form nested key-value pairs (array of objects or sub-object)
    # Group by indent of the first "- **" level
    base_indent = None
    groups = []
    current = []
    for l in lines:
        ls = l.lstrip()
        if ls.startswith("- **"):
            li = _indent(l)
            if base_indent is None:
                base_indent = li
            if li == base_indent and current:
                groups.append(current)
                current = []
            current.append(l)
        else:
            if current:
                current.append(l)
    if current:
        groups.append(current)
    
    if not groups:
        return None
    
    # Determine: array of objects or flat sub-object?
    # Groups with sub-field lines (- **key**: at deeper indent) → array of objects
    # Groups with only identifier lines (inline values, no sub-fields) → flat sub-object
    has_sub_fields = False
    for group in groups:
        for l in group[1:]:  # skip identifier line
            if l.lstrip().startswith("- **"):
                has_sub_fields = True
                break
        if has_sub_fields:
            break
    
    if has_sub_fields:
        # Array of objects
        objects = []
        for group in groups:
            obj = {}
            for l in group:
                ls = l.lstrip()
                m = re.match(r'^-\s+\*\*([^*]+)\*\*\s*:\s*(.*)', ls)
                if not m:
                    continue
                k = m.group(1).strip()
                v = m.group(2).strip()
                li = _indent(l)
                
                if li == base_indent:
                    obj['name'] = k
                else:
                    if v:
                        obj[k] = v
                    else:
                        deeper = _get_deeper_lines(group, l)
                        if deeper:
                            dv = _parse_value_lines(deeper)
                            obj[k] = dv if dv is not None else ""
                        else:
                            obj[k] = ""
            if obj:
                objects.append(obj)
        return objects
    else:
        # Flat sub-object (simple key=value)
        # All lines are data, no identifier concept
        obj = {}
        for group in groups:
            for l in group:
                ls = l.lstrip()
                m = re.match(r'^-\s+\*\*([^*]+)\*\*\s*:\s*(.*)', ls)
                if not m:
                    continue
                k = m.group(1).strip()
                v = m.group(2).strip()
                obj[k] = v
        return obj


def _get_deeper_lines(group_lines, start_line):
    """Get lines at deeper indent than start_line within the group."""
    try:
        idx = group_lines.index(start_line)
    except ValueError:
        return []
    
    start_indent = _indent(start_line)
    deeper = []
    for l in group_lines[idx + 1:]:
        if _indent(l) > start_indent:
            deeper.append(l)
        elif _indent(l) <= start_indent and l.lstrip():
            break
    return deeper


def parse_file(filepath):
    """Parse all sections in a character file."""
    with open(filepath) as f:
        content = f.read()
    
    results = {}
    for db_field, section_title in RICH_SECTIONS:
        pat = rf'## {re.escape(section_title)}\n(.*?)(?:\n## |\Z)'
        m = re.search(pat, content, re.DOTALL)
        if not m:
            continue
        body = m.group(1).strip()
        if not body or not body.startswith(f"- **{db_field}**"):
            continue
        field, parsed = parse_section_text(body, section_title)
        if parsed and parsed != {}:
            results[db_field] = parsed
    
    return results


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Parse character markdown sections back to JSON")
    parser.add_argument('name', nargs='?', help='Character name')
    parser.add_argument('--all', action='store_true', help='Compare all chars with DB')
    args = parser.parse_args()
    
    if args.name:
        filepath = os.path.join(CHAR_DIR, f"{args.name}.md")
        if not os.path.exists(filepath):
            print(f"Error: {filepath} not found")
            return
        parsed = parse_file(filepath)
        for db_field, data in parsed.items():
            st = next((t for f, t in RICH_SECTIONS if f == db_field), '')
            print(f"\n--- {st} ({db_field}) ---")
            print(json.dumps(data, ensure_ascii=False, indent=2))
    
    elif args.all:
        import psycopg2
        files = sorted([f for f in os.listdir(CHAR_DIR) if f.endswith('.md')])
        conn = psycopg2.connect('postgresql://localhost:5432/fcli')
        cur = conn.cursor()
        
        total = 0
        diffs = 0
        errors = 0
        for fname in files:
            name = fname[:-3]
            filepath = os.path.join(CHAR_DIR, fname)
            parsed = parse_file(filepath)
            
            for db_field, data in parsed.items():
                total += 1
                try:
                    cur.execute(f"SELECT {db_field} FROM characters WHERE name=%s AND novel_id=12", (name,))
                    db_val = cur.fetchone()
                    if db_val and db_val[0]:
                        db_json = json.loads(db_val[0]) if isinstance(db_val[0], str) else db_val[0]
                        if data != db_json:
                            diffs += 1
                            print(f"[DIFF] {name}.{db_field}")
                            print(f"  file: {json.dumps(data, ensure_ascii=False)[:120]}")
                            print(f"  db:   {json.dumps(db_json, ensure_ascii=False)[:120]}")
                except Exception as e:
                    errors += 1
                    print(f"[ERR]  {name}.{db_field}: {e}")
        
        if diffs == 0 and errors == 0:
            print(f"✅ All {total} sections match DB exactly!")
        else:
            print(f"\n{diffs} diffs, {errors} errors out of {total} sections")
        
        cur.close()
        conn.close()
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
