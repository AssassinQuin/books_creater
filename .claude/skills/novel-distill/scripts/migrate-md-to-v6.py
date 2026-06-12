#!/usr/bin/env python3
"""v6.0 迁移脚本：把 v5.0 之前的 borrowable-*.md 解析为 v6.0 JSON schema。
解析格式：
  ## 模式N：{name}（{applicability}）
  **核心**：{description}
  **操作要点**：{可选}
  **适用场景**：{applicable_genres}
  **文本示例**：\n> {example}

用法: python3 migrate-md-to-v6.py <work_dir>
输入: <work_dir>/borrowable-{维度}.md
输出: <work_dir>/.distill-tmp/{dim}.json
"""
import json, os, re, sys, glob

DIM_FILE_MAP = {
    "世界观": "world",
    "能力体系": "ability",
    "人物": "characters",
    "叙事手法": "narrative",
    "节奏结构": "rhythm",
}

HEADER_PATTERN = re.compile(r'^##\s*模式\s*(\d+)\s*[:：]\s*(.+?)(?:（|\()(.+?)(?:）|\))?\s*$', re.MULTILINE)

def parse_md(text):
    """切分 .md 为 borrowable 块"""
    blocks = []
    matches = list(HEADER_PATTERN.finditer(text))
    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i+1].start() if i+1 < len(matches) else len(text)
        body = text[start:end].strip()
        blocks.append({
            "idx": int(m.group(1)),
            "name": m.group(2).strip(),
            "applicability_raw": m.group(3).strip() if m.group(3) else "adapt",
            "body": body,
        })
    return blocks

def extract_field(body, field_name):
    """提取 **{field_name}：... 到下一个 ** 或段尾"""
    pattern = rf'\*\*{re.escape(field_name)}[：:]\*\*\s*(.*?)(?=\n\*\*|\n---|\Z)'
    m = re.search(pattern, body, re.DOTALL)
    if not m:
        return ""
    content = m.group(1).strip()
    content = re.sub(r'^\s*', '', content, flags=re.MULTILINE)
    return content.strip()

def extract_example(body):
    """提取 > 引用块"""
    pattern = r'>\s*(.*?)(?=\n\s*---|\Z)'
    matches = re.findall(pattern, body, re.DOTALL)
    if not matches:
        return ""
    example = " ".join(m.strip() for m in matches if m.strip())
    return example[:250]

def parse_applicability(raw):
    """'direct' / 'adapt' / 'inspire' / '高' / '极高' → standardize"""
    raw_lower = raw.lower()
    if "direct" in raw_lower or "直接" in raw:
        return "direct"
    if "inspire" in raw_lower or "灵感" in raw:
        return "inspire"
    return "adapt"

def parse_genres(scenes_text):
    """"西幻/克苏鲁/都市奇幻" → ["西幻", "克苏鲁", "都市奇幻"]"""
    if not scenes_text:
        return ["长篇网文"]
    parts = re.split(r'[/\s、，,]+', scenes_text)
    return [p.strip() for p in parts if p.strip() and len(p.strip()) <= 10][:5]

def migrate_file(md_path, dim, work_dir):
    with open(md_path, "r", encoding="utf-8") as f:
        text = f.read()

    blocks = parse_md(text)
    borrowables = []
    for b in blocks:
        name = b["name"]
        if len(name) > 15:
            name = name[:15]

        desc = extract_field(b["body"], "核心")
        if not desc:
            desc = b["name"]

        scenes = extract_field(b["body"], "适用场景")
        example = extract_example(b["body"])

        applicability = parse_applicability(b["applicability_raw"])
        genres = parse_genres(scenes)

        borrowables.append({
            "name": name,
            "description": desc[:200],
            "example": example,
            "source_chapters": "V1-V7",
            "applicability": applicability,
            "applicable_genres": genres,
            "source_context": desc[:200] if len(desc) >= 20 else (desc + "（基于诡秘之主原作多卷场景）")[:200],
            "elements": [{"component": name}],
            "adaptation_map": [{
                "aspect": "核心适配",
                "original": name,
                "abstract_role": "可借鉴的叙事/设定技法",
                "replacement_guide": f"将'{name}'抽象为通用模式，按 adaptation_map 替换具体设定"
            }],
            "project_relevance": {
                "这次不一样": {"score": 3, "reason": "待 v6.0 V1V2V3 评估后填充"}
            },
            "_migration_meta": {
                "original_idx": b["idx"],
                "original_applicability": b["applicability_raw"],
                "original_scenes": scenes,
            }
        })

    return {
        "dimension": dim,
        "data": {
            "summary": f"v6.0 迁移自 .md，原 {len(borrowables)} 条",
            "source_format": "borrowable-{维度}.md",
        },
        "borrowable": borrowables,
        "metadata": {
            "migrated_at": "2026-06-12",
            "source_md": os.path.basename(md_path),
            "v6_schema": True,
        }
    }

def main():
    if len(sys.argv) < 2:
        print("用法: python3 migrate-md-to-v6.py <work_dir>")
        sys.exit(1)

    work_dir = sys.argv[1]
    tmp_dir = os.path.join(work_dir, ".distill-tmp")
    os.makedirs(tmp_dir, exist_ok=True)

    total_count = 0
    for cn_dim, en_dim in DIM_FILE_MAP.items():
        md_path = os.path.join(work_dir, f"borrowable-{cn_dim}.md")
        if not os.path.exists(md_path):
            print(f"[SKIP] {md_path} 不存在")
            continue

        data = migrate_file(md_path, en_dim, work_dir)
        out_path = os.path.join(tmp_dir, f"{en_dim}.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        n = len(data["borrowable"])
        total_count += n
        print(f"[OK] {cn_dim}({en_dim}): {n} 条 → {out_path}")

    print(f"\n总计迁移: {total_count} 条 borrowable")
    print(f"输出目录: {tmp_dir}")

if __name__ == "__main__":
    main()
