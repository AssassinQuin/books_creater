#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""提取转生史莱姆 EPUB 正文为纯文本（去 HTML 标签 + 解码实体），按卷落盘。"""
import zipfile, re, os, html
from pathlib import Path

BASE = Path("/Users/ganjie/code/personal/bywork/books_creater")
WORK = BASE / "拆文库/转生史莱姆/_原著正文"
WORK.mkdir(parents=True, exist_ok=True)

GROUPS = [
    BASE / "伏瀬 - 關於我轉生變成史萊姆這檔事（01-13卷）台版繁中EPUB",
    BASE / "伏瀬 - 關於我轉生變成史萊姆這檔事（14-20卷）繁体中文EPUB",
]

TAG_RE = re.compile(r'<[^>]+>')

def clean(raw: str) -> str:
    text = TAG_RE.sub('', raw)
    text = html.unescape(text)
    # 压掉多余空白行，但保留换行
    lines = [ln.strip() for ln in text.splitlines()]
    return '\n'.join(ln for ln in lines if ln)

total = 0
results = []
for g in GROUPS:
    if not g.exists():
        print(f"[WARN] 目录不存在: {g}")
        continue
    for epub in sorted(g.glob("*.epub")):
        m = re.search(r'(\d+(?:\.\d+)?)', epub.stem)
        if not m:
            continue
        vol = m.group(1)
        out = WORK / f"V{vol}.txt"
        parts = []
        with zipfile.ZipFile(epub) as z:
            names = sorted(n for n in z.namelist()
                           if n.startswith('OEBPS/Text/') and n.endswith('.xhtml'))
            for fn in names:
                raw = z.read(fn).decode('utf-8', errors='ignore')
                parts.append(f"\n=== {os.path.basename(fn)} ===\n{clean(raw)}")
        out.write_text(''.join(parts), encoding='utf-8')
        chars = len(out.read_text(encoding='utf-8'))
        total += chars
        results.append((vol, chars, out.name))

print("=== 提取结果 ===")
for vol, chars, name in sorted(results, key=lambda x: float(x[0])):
    print(f"卷{vol:>5}: {chars:>8} 字符  {name}")
print(f"\n共 {len(results)} 个文件，总计 {total} 字符（约 {total//10000} 万字）")
