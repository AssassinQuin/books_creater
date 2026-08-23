#!/usr/bin/env python3
"""清洗拆分《我师兄实在太稳健了》源文本。
1. 按 '序号.第N章' 标记行拆分为章节文件（章号=标记行第N章的N，内容顺序锚定）
2. 统一标题：去【求票】类尾标，格式 第NNN章 标题
3. 删除噪音：盗版水印/广告行/纯空白；感言运营章移入 感言/
4. 输出 清洗报告.md：章数/噪音统计/序号-章号漂移曲线/可疑标题错位窗口
用法: python3 split_clean.py
"""
import re, os, statistics

# 已验证的感言/运营章清单（2026-08-23 摘要级核验 + 补造代理逐源文确认）
KNOWN_ESSAY = {35, 51, 69, 91, 100, 107, 130, 177, 313, 368, 388, 393, 416, 443,
               480, 502, 568, 589, 648, 673, 707, 717, 736}

SRC = "/Users/ganjie/code/personal/bywork/books_creater/参考/我师兄实在太稳健了_utf8.txt"
SRC_END = "/Users/ganjie/code/personal/bywork/books_creater/参考/我师兄实在太稳健了_结局补全.txt"
OUT_DIR = "/Users/ganjie/code/personal/bywork/books_creater/拆文库/我师兄实在太稳健了/正文"
ESSAY_DIR = "/Users/ganjie/code/personal/bywork/books_creater/拆文库/我师兄实在太稳健了/感言"
REPORT = "/Users/ganjie/code/personal/bywork/books_creater/拆文库/我师兄实在太稳健了/清洗报告.md"

MARKER = re.compile(r'^(\d+)\.第(\d+)章\s*(.*)$')
NOISE = re.compile(r'人人小说网|最快更新|最新章节|无弹窗|首发|www\.|https?://|\.net|\.com|\.cc|手机用户|章节错误|点此报错|【?求?订阅】?$')
ESSAY_HINT = re.compile(r'求票|求推荐|求月票|求订阅|均订|上架|请假|感谢|感言|码字|更新时间|存稿|补更|加更计划| writer|作者君')

def clean_title(t):
    t = re.sub(r'【[^】]*】', '', t).strip()
    t = re.sub(r'\s+', ' ', t)
    return t

def clean_body(lines):
    kept, removed = [], 0
    for ln in lines:
        s = ln.strip()
        if not s:
            continue
        if NOISE.search(s) and len(s) < 60:  # 短行且含广告词才删，防误删正文
            removed += 1
            continue
        if s in ('　　，最快更新我师兄实在太稳健了最新章节！',):
            removed += 1
            continue
        kept.append(ln.rstrip())
    return kept, removed

def split(path):
    chapters, order = {}, []
    cur = None
    with open(path, encoding='utf-8') as f:
        for raw in f:
            m = MARKER.match(raw.strip())
            if m and len(raw.strip()) < 60:
                seq, num, title = int(m.group(1)), int(m.group(2)), clean_title(m.group(3))
                if num in chapters:
                    print(f"[WARN] 重复章号 {num}（序号{seq}），跳过后者")
                    continue
                cur = {'seq': seq, 'num': num, 'title': title, 'lines': []}
                chapters[num] = cur
                order.append(num)
            elif cur is not None:
                cur['lines'].append(raw.rstrip())
    return chapters, order

def main():
    os.makedirs(OUT_DIR, exist_ok=True); os.makedirs(ESSAY_DIR, exist_ok=True)
    chapters, order = split(SRC)
    n_essay, n_plot, total_noise, sizes = 0, 0, 0, []
    drift = []  # (章号, 序号-章号)
    essay_list, suspects = [], []
    for num in order:
        c = chapters[num]
        body, removed = clean_body(c['lines'])
        total_noise += removed
        text = '\n'.join(body).strip()
        sizes.append(len(text))
        drift.append((num, c['seq'] - num))
        is_essay = num in KNOWN_ESSAY or len(text) < 400 or (len(body) <= 12 and ESSAY_HINT.search(text))
        header = f"第{num}章 {c['title']}\n"
        if is_essay:
            n_essay += 1
            essay_list.append((num, c['title'], len(text)))
            with open(f"{ESSAY_DIR}/第{num:03d}章_{c['title'] or '无题'}.txt", 'w', encoding='utf-8') as f:
                f.write(header + '\n' + text + '\n')
        else:
            n_plot += 1
            with open(f"{OUT_DIR}/第{num:03d}章_{c['title'] or '无题'}.txt", 'w', encoding='utf-8') as f:
                f.write(header + '\n' + text + '\n')
    # 结局补全覆盖（起点官方759-761 = 本库760-762）
    end_over = []
    if os.path.exists(SRC_END):
        ech, eorder = split(SRC_END)
        for num in eorder:
            import glob
            for old in glob.glob(f"{OUT_DIR}/第{num:03d}章_*.txt"):
                os.remove(old)  # 覆盖前清除同章号旧文件，防标题差异产生双件
            c = ech[num]
            body, _ = clean_body(c['lines'])
            text = '\n'.join(body).strip()
            with open(f"{OUT_DIR}/第{num:03d}章_{c['title'] or '无题'}.txt", 'w', encoding='utf-8') as f:
                f.write(f"第{num}章 {c['title']}\n\n{text}\n")
            end_over.append(num)
    # 漂移变化点（可疑标题错位窗口起点）
    prev = None
    for num, d in drift:
        if prev is not None and abs(d - prev[1]) >= 2:
            suspects.append((prev[0], num, prev[1], d))
        prev = (num, d)
    with open(REPORT, 'w', encoding='utf-8') as f:
        f.write("# 清洗报告\n\n")
        f.write(f"- 源文件：{os.path.basename(SRC)}（{os.path.getsize(SRC)//1024}KB）\n")
        f.write(f"- 章节总数：{len(order)}（章号 {min(order)}-{max(order)}）\n")
        f.write(f"- 正文章：{n_plot} → 正文/（每章一文件，头部为统一标题行）\n")
        f.write(f"- 感言/运营章：{n_essay} → 感言/\n")
        f.write(f"- 删除噪音行：{total_noise}\n")
        f.write(f"- 章均字符：{statistics.mean(sizes):.0f}，中位数 {statistics.median(sizes):.0f}，最短 {min(sizes)}，最长 {max(sizes)}\n")
        if end_over:
            f.write(f"- 结局补全覆盖章号：{end_over}（真结局源：飘天文学）\n\n")
        f.write("## 感言章清单\n\n| 章号 | 标题 | 字符数 |\n|---|---|---|\n")
        for num, t, ln in essay_list:
            f.write(f"| {num} | {t} | {ln} |\n")
        f.write("\n## 序号-章号漂移突变点（标题错位窗口线索）\n\n| 前章 | 后章 | 前漂移 | 后漂移 |\n|---|---|---|---|\n")
        for a, b, da, db in suspects:
            f.write(f"| {a} | {b} | {da} | {db} |\n")
    print(f"完成：{len(order)} 章，正文 {n_plot}，感言 {n_essay}，噪音行 {total_noise}，漂移突变 {len(suspects)} 处")

if __name__ == '__main__':
    main()
