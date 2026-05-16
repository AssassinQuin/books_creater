#!/usr/bin/env python3
"""
Single-pass: directly insert human-readable rich sections from DB data.
No JSON extraction needed - we read from DB and format directly.
"""

import json, os, re

CHAR_DIR = "/Users/ganjie/code/personal/bywork/books_creater/novels/这次不一样了/设定/人物"
DB_FILE = "/tmp/characters_db.json"

# Load DB
with open(DB_FILE) as f:
    DB_CHARS = {c['name']: c for c in json.load(f)}

RICH_SECTIONS = [
    ("appearance_detail", "外观描写库"),
    ("decision_engine", "决策引擎"),
    ("voice_fingerprint", "对话声音指纹"),
    ("ability_system", "能力体系"),
    ("behavior_pattern", "行为模式"),
    ("current_snapshot", "当前快照"),
    ("growth_trajectory", "成长轨迹"),
]

###############################################################################
# JSON → Human-Readable Markdown converter
###############################################################################

def _find_key(obj):
    if not isinstance(obj, dict):
        return None
    for k in ['name', 'scene', 'context', 'target', 'stage', 'teammate', 'volume', 'chapter']:
        if k in obj:
            return k
    return None

def to_md(value, indent=0):
    """Convert JSON value to markdown lines."""
    p = "  " * indent
    lines = []
    
    if value is None or value == "":
        lines.append("")
    elif isinstance(value, str):
        lines.append(value)
    elif isinstance(value, bool):
        lines.append(str(value).lower())
    elif isinstance(value, (int, float)):
        lines.append(str(value))
    elif isinstance(value, list):
        if not value:
            lines.append("")
        elif all(isinstance(v, str) for v in value):
            for item in value:
                lines.append(f"{p}  - {item}")
        elif all(isinstance(v, dict) for v in value):
            for item in value:
                kf = _find_key(item)
                if kf and item.get(kf):
                    ik = str(item[kf])
                    lines.append(f"{p}  - **{ik}**: ")
                    for sk, sv in item.items():
                        if sk == kf:
                            continue
                        sub_lines = to_md(sv, indent + 2)
                        if not sub_lines or (len(sub_lines) == 1 and sub_lines[0] == ""):
                            lines.append(f"{p}    - **{sk}**: ")
                        elif len(sub_lines) == 1:
                            lines.append(f"{p}    - **{sk}**: {sub_lines[0]}")
                        else:
                            lines.append(f"{p}    - **{sk}**: ")
                            for sl in sub_lines:
                                lines.append(f"{p}    {sl}")
                else:
                    for sk, sv in item.items():
                        sub_lines = to_md(sv, indent + 2)
                        if not sub_lines or (len(sub_lines) == 1 and sub_lines[0] == ""):
                            lines.append(f"{p}  - **{sk}**: ")
                        elif len(sub_lines) == 1:
                            lines.append(f"{p}  - **{sk}**: {sub_lines[0]}")
                        else:
                            lines.append(f"{p}  - **{sk}**: ")
                            for sl in sub_lines:
                                lines.append(f"{p}    {sl}")
        else:
            lines.append(json.dumps(value, ensure_ascii=False))
    elif isinstance(value, dict):
        # Check if flat string map (like emotion_writing)
        if value and all(isinstance(v, str) for v in value.values()):
            for sk, sv in value.items():
                lines.append(f"{p}  - **{sk}**: {sv}")
        else:
            for sk, sv in value.items():
                sub_lines = to_md(sv, indent + 1)
                if isinstance(sv, (list, dict)):
                    # Always multi-line for complex types
                    lines.append(f"{p}  - **{sk}**: ")
                    for sl in sub_lines:
                        lines.append(f"{p}  {sl}")
                elif not sub_lines or (len(sub_lines) == 1 and sub_lines[0] == ""):
                    lines.append(f"{p}  - **{sk}**: ")
                elif len(sub_lines) == 1:
                    lines.append(f"{p}  - **{sk}**: {sub_lines[0]}")
                else:
                    lines.append(f"{p}  - **{sk}**: ")
                    for sl in sub_lines:
                        lines.append(f"{p}  {sl}")
    
    return lines


def format_section(db_field, data):
    """Generate full section text from DB data."""
    if data is None or data == {} or data == [] or data == [{}]:
        return None
    
    md_lines = to_md(data)
    # Indent body by 2 spaces
    body = "\n".join("  " + line if line.strip() else line for line in md_lines)
    return f"- **{db_field}**: \n{body}\n"


###############################################################################
# File handling
###############################################################################

def has_section(content, title):
    return f"\n## {title}\n" in content or content.startswith(f"## {title}\n")


def process_file(fname):
    name = fname[:-3]
    filepath = os.path.join(CHAR_DIR, fname)
    db = DB_CHARS.get(name)
    if not db:
        return False
    
    with open(filepath) as f:
        content = f.read()
    
    original = content
    
    for db_field, section_title in RICH_SECTIONS:
        if has_section(content, section_title):
            continue  # already exists
        
        data = db.get(db_field)
        sec_text = format_section(db_field, data)
        if sec_text is None:
            continue  # no data
        
        full_section = f"\n## {section_title}\n{sec_text}\n"
        
        # Insert before 关系 section if exists
        marker = "\n## 关系\n"
        idx = content.find(marker)
        if idx >= 0:
            content = content[:idx] + full_section + content[idx:]
        else:
            content += full_section
        
        print(f"  [{name}] Added {section_title}")
    
    if content != original:
        with open(filepath, 'w') as f:
            f.write(content)
        return True
    return False


def main():
    files = sorted([f for f in os.listdir(CHAR_DIR) if f.endswith('.md')])
    
    print("=== Inserting human-readable rich sections ===\n")
    updated = 0
    for fname in files:
        if process_file(fname):
            updated += 1
    
    print(f"\nDone. Updated {updated} files.")
    print("Sections are in human-readable format:" )
    print("  - **key**: value          # simple string")
    print("  - **key**:                # string array")
    print("    - item")
    print("  - **key**:                # nested object")
    print("    - **subkey**: value")
    print("  - **key**:                # array of objects")
    print("    - **identifier**:")

if __name__ == '__main__':
    main()
