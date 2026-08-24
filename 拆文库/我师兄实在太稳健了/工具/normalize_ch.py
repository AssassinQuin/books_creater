#!/usr/bin/env python3
"""归一化重拆《我师兄实在太稳健了》→ chapters/ch_NNN.txt
源：正文/ + 感言/（split_clean.py 已清洗成果，含结局补全覆盖）
1. 合并两库按章号补全 1..765 完整序列（感言章并入，目录中标记类型）
2. 归一化：首行统一「第N章 标题」；每段一行；去全角缩进/空行/行尾空白；残留噪音行兜底过滤
3. 输出 ch_%03d.txt + 目录.md（章号/标题/类型/字数 + 缺章/异常显性报告）
用法: python3 normalize_ch.py
"""
import re, os, glob

ROOT = "/Users/ganjie/code/personal/bywork/books_creater/拆文库/我师兄实在太稳健了"
SRC_DIRS = [("正文", "正文"), ("感言", "感言")]  # 先正文：重复章号时首见优先并报警
OUT_DIR = os.path.join(ROOT, "chapters")
TOC = os.path.join(OUT_DIR, "目录.md")

FNAME = re.compile(r'^第(\d{1,4})章(?:_(.*))?\.txt$')
HEADER = re.compile(r'^第\d+章\s*(.*)$')
NOISE = re.compile(r'人人小说网|最快更新|最新章节|无弹窗|首发|www\.|https?://|\.net|\.com|\.cc|手机用户|章节错误|点此报错')
TITLE_TAIL = re.compile(r'【[^】]*】')  # 标题内残留【求票】类尾标


def normalize_title(t):
    t = TITLE_TAIL.sub('', t or '').strip()
    return re.sub(r'\s+', ' ', t)


def normalize_body(text):
    out, noise = [], 0
    for ln in text.splitlines():
        s = ln.strip()  # 去全角/半角缩进与行尾空白
        if not s:
            continue
        if NOISE.search(s) and len(s) < 60:  # 短行且含广告词才删，防误删正文
            noise += 1
            continue
        out.append(s)
    return out, noise


def main():
    chapters, problems = {}, []
    for dname, ctype in SRC_DIRS:
        for path in sorted(glob.glob(os.path.join(ROOT, dname, '*.txt'))):
            base = os.path.basename(path)
            m = FNAME.match(base)
            if not m:
                problems.append(f"文件名不合规: {dname}/{base}")
                continue
            num = int(m.group(1))
            with open(path, encoding='utf-8') as f:
                raw = f.read()
            first, _, rest = raw.partition('\n')
            hm = HEADER.match(first.strip())
            title_file = normalize_title(m.group(2))
            title_head = normalize_title(hm.group(1)) if hm else ''
            title = title_head or title_file
            if title_head and title_file and title_head != title_file:
                problems.append(f"第{num}章标题不一致: 文件名[{title_file}] vs 首行[{title_head}]，取首行")
            if num in chapters:
                # 双库同存（已验证内容一致）：实为「正文+末尾感言」混合章
                chapters[num]['type'] = '正文(含感言尾)'
                problems.append(f"重复章号 {num}: {chapters[num]['from']} 与 {path}，取先见，标记混合章")
                continue
            chapters[num] = {'title': title, 'type': ctype, 'from': path, 'rest': rest}

    nums = sorted(chapters)
    if not nums:
        raise SystemExit("未发现任何源章节，终止")
    lo, hi = nums[0], nums[-1]
    missing = [n for n in range(lo, hi + 1) if n not in chapters]

    os.makedirs(OUT_DIR, exist_ok=True)
    for old in glob.glob(os.path.join(OUT_DIR, 'ch_*.txt')):  # 清理上次运行残留
        os.remove(old)

    total_chars, n_essay, n_plot, n_hybrid, total_noise, rows = 0, 0, 0, 0, 0, []
    for n in nums:
        c = chapters[n]
        body, noise = normalize_body(c['rest'])
        total_noise += noise
        text = '\n'.join(body)
        chars = len(text.replace('\n', ''))
        total_chars += chars
        if c['type'] == '感言':
            n_essay += 1
        elif c['type'] == '正文(含感言尾)':
            n_hybrid += 1
        else:
            n_plot += 1
        with open(os.path.join(OUT_DIR, f'ch_{n:03d}.txt'), 'w', encoding='utf-8') as f:
            f.write(f"第{n}章 {c['title']}\n\n{text}\n")
        rows.append((n, c['title'], c['type'], chars))

    with open(TOC, 'w', encoding='utf-8') as f:
        f.write("# 我师兄实在太稳健了 · 归一化章节目录\n\n")
        f.write("- 源：正文/ + 感言/（工具/split_clean.py 清洗成果 + 结局补全覆盖）\n")
        f.write(f"- 输出：chapters/ch_{lo:03d}.txt – ch_{hi:03d}.txt，共 {len(rows)} 章"
                f"（正文 {n_plot} + 正文含感言尾 {n_hybrid} + 感言 {n_essay}）\n")
        f.write("- 归一化：每段一行、去缩进/空行/广告噪音行；首行统一「第N章 标题」\n")
        f.write(f"- 总字数 {total_chars}，删除噪音行 {total_noise}\n")
        if missing:
            f.write(f"- ⚠️ 缺章 {len(missing)} 个：{missing}\n")
        if problems:
            f.write(f"- ⚠️ 异常 {len(problems)} 条（详见运行输出）\n")
        f.write("\n| 文件 | 章号 | 标题 | 类型 | 字数 |\n|---|---|---|---|---|\n")
        for n, t, ty, ch in rows:
            f.write(f"| ch_{n:03d}.txt | {n} | {t or '无题'} | {ty} | {ch} |\n")

    print(f"章数 {len(rows)}（正文{n_plot}/混合{n_hybrid}/感言{n_essay}）范围 {lo}-{hi} "
          f"缺章 {missing if missing else '无'} 噪音行 {total_noise} 总字数 {total_chars}")
    if problems:
        print(f"⚠️ 异常 {len(problems)} 条：")
        for p in problems:
            print('  -', p)


if __name__ == '__main__':
    main()
