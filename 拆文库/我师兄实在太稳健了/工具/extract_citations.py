#!/usr/bin/env python3
"""提取 大纲.md + 卷纲_第NN卷.md 中的「章号引用」清单，供正文核验。
引用形态：裸数字或区间（448 / 92-99 / 第47章），后随事件上下文。
输出：工具/引用清单.json（结构化）+ 控制台统计。
用法：python3 extract_citations.py [--all]  # 默认跳过卷八（尾段另案处理），--all 含卷八
"""
import re, os, json, sys

ROOT = "/Users/ganjie/code/personal/bywork/books_creater/拆文库/我师兄实在太稳健了"
OUT = os.path.join(ROOT, "工具", "引用清单.json")

CIT = re.compile(
    r'(?P<di>第\s*)?(?P<s>\d{1,3})'
    r'(?:\s*[-–—~]\s*(?P<e>\d{1,3}))?'
    r'(?P<zh>\s*章)?'
)
# 非章位数字的上下文信号（紧跟其后的字符若为这些，多半是量词/编号而非章号+事件）
NON_EVENT = re.compile(r'^[\s|:：,，、]*([%％万字年卷批次条幕阶段L]|个|次|位|名|段|份|套|章总|章 ≈)')
CTX = re.compile(r'\s*章?\s*[:：,，、]?\s*\|?\s*(.{0,28})')


def extract(path):
    """返回 [(line_no, start, end|None, context, raw_line_prefix)]"""
    out = []
    with open(path, encoding='utf-8') as f:
        for i, line in enumerate(f, 1):
            if line.startswith('#'):
                continue
            for m in CIT.finditer(line):
                s = int(m.group('s'))
                e = int(m.group('e')) if m.group('e') else None
                if not (1 <= s <= 765):
                    continue
                if e is not None and not (1 <= e <= 765 and e > s and e - s <= 120):
                    e = None  # 异常区间按单点处理
                cm = CTX.match(line, m.end())
                ctx = (cm.group(1).strip(' |')) if cm else ''
                # 收录条件：带「第/章」标记，或后随汉字事件词；纯数字+量词/空上下文丢弃
                marked = bool(m.group('di')) or bool(m.group('zh'))
                has_cjk = bool(re.match(r'^[一-鿿]', ctx))
                if not (marked or has_cjk):
                    continue
                if NON_EVENT.match(ctx):
                    continue
                out.append({'line': i, 'start': s, 'end': e, 'ctx': ctx,
                            'kind': '第N章' if m.group('di') else ('N章' if m.group('zh') else ('range' if e else 'bare')),
                            'src': line.strip()[:60]})
    return out


STOP_PROBE = {'日常', '大战', '高潮', '事件', '剧情', '单元', '篇', '上下', '上下半场',
              '双段', '定情', '副本', '篇章', '上半场', '下半场', '线', '线开', '收束',
              '视角', '切片', '开卷', '卷末', '卷尾', '章位', '蓄力', '善后', '引爆'}
CH_DIR = os.path.join(ROOT, 'chapters')


def ch_path(n):
    return os.path.join(CH_DIR, f'ch_{n:03d}.txt')


def probes(ctx):
    """从事件上下文提取探针词：CJK 连续段≥2字，去停用词，取最长 3 个"""
    runs = [r for r in re.split(r'[^一-鿿]+', ctx) if len(r) >= 2 and r not in STOP_PROBE]
    runs.sort(key=len, reverse=True)
    return runs[:3]


def screen(result):
    """初筛：探针词命中 ch_start（±1）判 auto_ok，否则 suspect。尾段(≥746，含重复区)整体 suspect。"""
    cache = {}
    for cits in result.values():
        for c in cits:
            ps = probes(c['ctx'])
            c['probes'] = ps
            n = c['start']
            if n >= 746:  # 尾段另案（结构仲裁中）
                c['screen'] = 'tail'
                continue
            if not ps:
                c['screen'] = 'suspect'  # 无可用探针（如表格首列区间，事件在隔壁列被截）
                continue
            hit = False
            for d in (0, -1, 1):
                p = ch_path(n + d)
                if p not in cache:
                    cache[p] = open(p, encoding='utf-8').read() if os.path.exists(p) else ''
                strong = [x for x in ps if len(x) >= 3]
                pool = strong or ps
                if any(x in cache[p] for x in pool):
                    hit = True
                    c['hit_at'] = n + d
                    break
            c['screen'] = 'ok' if hit else 'suspect'


def main():
    include_all = '--all' in sys.argv
    files = [('大纲.md', os.path.join(ROOT, '写作目录/大纲/大纲.md'))]
    for v in range(1, 9):
        files.append((f'卷纲_第0{v}卷', os.path.join(ROOT, f'写作目录/大纲/卷纲_第0{v}卷.md')))
    result, stats = {}, {}
    for name, path in files:
        if not include_all and name == '卷纲_第08卷':
            continue  # 尾段另案（结构仲裁中），含 651-762 引用一并处理
        cits = extract(path)
        # 去重：同文件同(起点,上下文前8字)
        seen, dedup = set(), []
        for c in cits:
            key = (c['start'], c['ctx'][:8])
            if key in seen:
                continue
            seen.add(key)
            dedup.append(c)
        result[name] = dedup
        stats[name] = len(dedup)
    screen(result)
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
    total = sum(stats.values())
    ok = sum(1 for cits in result.values() for c in cits if c['screen'] == 'ok')
    sus = sum(1 for cits in result.values() for c in cits if c['screen'] == 'suspect')
    tail = sum(1 for cits in result.values() for c in cits if c['screen'] == 'tail')
    print(f"引用总数（去重后）{total} → {OUT}")
    print(f"初筛：auto_ok {ok} | suspect {sus} | tail另案 {tail}")
    for k, v in stats.items():
        s = sum(1 for c in result[k] if c['screen'] == 'suspect')
        print(f"  {k}: {v} (suspect {s})")


if __name__ == '__main__':
    main()
