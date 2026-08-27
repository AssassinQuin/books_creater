"""Novel Writer MCP Server - FastMCP 3.x + PostgreSQL"""

import glob
import hashlib
import json
import os
import re
from typing import Any

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

import psycopg2
import psycopg2.extras
from fastmcp import FastMCP

PROJECT_ROOT = os.environ.get(
    "NOVEL_PROJECT_ROOT",
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql:///fcli"
)

mcp = FastMCP("novel-db", instructions="网文小说创作数据库 MCP，管理小说项目、世界观、人物、章节、伏笔、时间线等结构化数据。")


def get_conn():
    return psycopg2.connect(DATABASE_URL)


def query(sql: str, params: tuple = (), fetch: str = "all") -> Any:
    conn = get_conn()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(sql, params)
        if fetch == "none":
            result = None
        elif fetch == "one":
            result = cur.fetchone()
        elif fetch == "val":
            result = cur.fetchone()
            result = list(result.values())[0] if result else None
        else:
            result = cur.fetchall()
        conn.commit()
        return result
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


# ─── 约束从 Markdown 文件加载（regex 解析，用户编辑文件即可）───

CONSTRAINTS_FILE = os.environ.get(
    "CONSTRAINTS_FILE",
    os.path.join(PROJECT_ROOT, ".claude", "skills", "writing-constraints.md")
)


def _parse_constraints_md() -> dict:
    """解析 writing-constraints.md，返回结构化的约束字典。"""
    result = {
        "hard_pct": {},      # 百分比密度约束
        "hard_abs": {},       # 绝对值硬约束（含原推荐约束，已升级为强制）
        "banned_patterns": [], # 违禁词
        "guidelines": {},     # 创作原则
    }
    try:
        with open(CONSTRAINTS_FILE, "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        return result

    # ── 硬约束（百分比）── 表格格式: | key | 标签 | min‰ | max‰ | 说明 |
    pct_pattern = re.compile(
        r'^\|\s*(\w[\w_]*)\s*\|\s*([^|]+)\s*\|\s*([\d.]+)\s*\|\s*([\d.]+)\s*\|\s*([^|]*)',
        re.MULTILINE
    )
    # 找到 "## 硬约束（百分比密度）" 和下一个 "##" 之间的表格行
    section_pct = re.search(r'## 硬约束（百分比密度）\n(.*?)(?=\n## |\Z)', content, re.DOTALL)
    if section_pct:
        for m in pct_pattern.finditer(section_pct.group(1)):
            key = m.group(1).strip()
            if key in ("key", "---"):
                continue
            label = m.group(2).strip()
            min_v = float(m.group(3))
            max_v = float(m.group(4))
            result["hard_pct"][key] = {"label": label, "min": min_v, "max": max_v}

    # ── 硬约束（绝对值）── | key | 标签 | min | max | 说明 |
    section_abs = re.search(r'## 硬约束（绝对值）\n(.*?)(?=\n## |\Z)', content, re.DOTALL)
    if section_abs:
        for m in re.finditer(
            r'^\|\s*(\w+)\s*\|\s*([^|]+)\s*\|\s*([\d.\-]*)\s*\|\s*([\d.\-]*)\s*\|\s*([^|]*)',
            section_abs.group(1), re.MULTILINE
        ):
            key = m.group(1).strip()
            if key in ("key", "---"):  # 跳过表头
                continue
            label = m.group(2).strip()
            min_v = m.group(3).strip()
            max_v = m.group(4).strip()
            entry = {"label": label}
            if min_v and min_v != '-':
                entry["min"] = float(min_v)
            if max_v and max_v != '-':
                entry["max"] = float(max_v)
            result["hard_abs"][key] = entry

    # ── 违禁词 ──
    section_ban = re.search(r'## 违禁词\n(.*?)(?=\n## |\Z)', content, re.DOTALL)
    if section_ban:
        for m in re.finditer(r'^- \s*(.+)$', section_ban.group(1), re.MULTILINE):
            result["banned_patterns"].append(m.group(1).strip())

    # ── 创作原则(7条核心+4条补充) ──
    section_guide = re.search(r'## 创作原则.*?\n(.*?)(?=\n## |\Z)', content, re.DOTALL)
    if section_guide:
        for m in re.finditer(
            r'^\|\s*([\w_]+)\s*\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|\s*([^|]*)',
            section_guide.group(1), re.MULTILINE
        ):
            key = m.group(1).strip()
            if key in ("key", "---"):
                continue
            # Format 1: has label column (7 core)
            # Format 2: no label column (4 supplementary)
            rule = m.group(3).strip() if m.group(2) and not m.group(2).startswith("铁律") and len(m.group(2)) > 5 else ""
            ref = m.group(4).strip() if m.group(4) else ""
            label = m.group(2).strip()
            if rule and len(rule) > 5:
                result["guidelines"][key] = {"label": label, "rule": rule, "ref": ref}
            else:
                # Supplementary: label field is actually the rule
                ref = m.group(3).strip() if m.group(3) else ""
                result["guidelines"][key] = {"rule": label, "ref": ref}

    return result


# 内存缓存（文件变更后重启 MCP 即可刷新）
_CONSTRAINTS_CACHE: dict = None


def _get_constraints() -> dict:
    """获取约束（带缓存）。"""
    global _CONSTRAINTS_CACHE
    if _CONSTRAINTS_CACHE is None:
        _CONSTRAINTS_CACHE = _parse_constraints_md()
    return _CONSTRAINTS_CACHE


def validate_chapter_text(text: str) -> dict:
    """对正文逐项检查。约束从 writing-constraints.md 文件加载（regex 解析）。"""
    violations = []
    stats = {}
    c = _get_constraints()
    hard_pct = c.get("hard_pct", {})
    hard_abs = c.get("hard_abs", {})
    banned = c.get("banned_patterns", [])

    total_chars = len(re.sub(r'\s', '', text))  # 去空白后的中文字符数
    paras = re.split(r'\n\s*\n', text)

    # ── 百分比密度检查（基于总字数的千分比‰）──
    punct_checks = {
        "em_dash": (r'——', "em_dash_count"),
        "ellipsis": (r'……', "ellipsis_count"),
        "semicolon": (r'；', "semicolon_count"),
        "exclamation": (r'！', "exclamation_count"),
    }
    for key, (pattern, stat_key) in punct_checks.items():
        count = len(re.findall(pattern, text))
        stats[stat_key] = count
        if key in hard_pct and total_chars > 0:
            permille = count / total_chars * 1000  # 千分比
            rule = hard_pct[key]
            min_v, max_v = rule["min"], rule["max"]
            if permille < min_v or permille > max_v:
                violations.append(
                    f"{rule['label']}：{count}次({permille:.1f}‰)，需{min_v}-{max_v}‰"
                )

    # 波浪号 — 仅统计
    stats["wave_count"] = len(re.findall(r'[～~]', text))

    # ── 绝对值硬约束（含原推荐约束，已升级为强制）──
    # 否定句式
    ng = len(re.findall(r'不是[^，]*，[^。]*是', text))
    stats["negation_count"] = ng
    if "negation" in hard_abs and ng > hard_abs["negation"].get("max", 999):
        violations.append(f"{hard_abs['negation']['label']}：{ng}次，需≤{hard_abs['negation'].get('max',999)}次")

    # 字数
    if "word_count" in hard_abs and total_chars < hard_abs["word_count"].get("min", 0):
        violations.append(f"{hard_abs['word_count']['label']}：{total_chars}，需≥{hard_abs['word_count'].get('min',0)}字")
    stats["word_count"] = total_chars

    # 长段落
    lp = sum(1 for p in paras if len(p.strip()) >= 180)
    stats["long_paragraphs"] = lp
    if "long_paragraphs" in hard_abs and lp < hard_abs["long_paragraphs"].get("min", 0):
        violations.append(f"{hard_abs['long_paragraphs']['label']}：{lp}个，需≥{hard_abs['long_paragraphs'].get('min',0)}个")

    # 每段标点多样性
    punct_types_list = []
    for p in paras:
        if not p.strip():
            continue
        types = set()
        for ch, name in [('。', '句'), ('，', '逗'), ('——', '破'), ('……', '省'),
                          ('；', '分'), ('！', '叹'), ('？', '问'), ('：', '冒'), ('、', '顿')]:
            if ch in p:
                types.add(name)
        punct_types_list.append(len(types))
    avg_pt = sum(punct_types_list) / len(punct_types_list) if punct_types_list else 0
    stats["avg_punct_types_per_para"] = round(avg_pt, 2)
    if "avg_punct_types" in hard_abs and avg_pt < hard_abs["avg_punct_types"].get("min", 0):
        violations.append(f"{hard_abs['avg_punct_types']['label']}：{avg_pt:.1f}，需≥{hard_abs['avg_punct_types'].get('min',0)}")

    # 对话打断
    db = len(re.findall(r'——[^—]', text))
    stats["dialogue_breaks"] = db
    if "dialogue_breaks" in hard_abs and db < hard_abs["dialogue_breaks"].get("min", 0):
        violations.append(f"{hard_abs['dialogue_breaks']['label']}：{db}次，需≥{hard_abs['dialogue_breaks'].get('min',0)}次")

    # ── 违禁词（硬拦截）──
    fb = [p for p in banned if p in text]
    stats["banned_patterns"] = fb
    if fb:
        violations.append(f"违禁词：{', '.join(fb)}")

    return {"violations": violations, "stats": stats, "passed": len(violations) == 0}


def _enrichment_level(current_words: int, min_words: int) -> str:
    """字数不足时返回 PUA 风格充实指引（L1→L2→L3 逐级加压）。"""
    if min_words <= 0 or current_words >= min_words:
        return ""
    deficit_pct = (min_words - current_words) / min_words * 100
    
    # ── L1: 温和失望（引擎丰富） ──
    if deficit_pct < 20:
        return (
            f"## 🔶 L1 — 引擎丰富（距目标 {deficit_pct:.0f}%）\n"
            f"字数 {current_words}，需 ≥{min_words}。\n\n"
            f"**你的借口**：「内容差不多了，字数差一点而已」\n"
            f"**反击**：你差20%不到就敢交？引擎摆在那你不用，让我怎么给你打绩效？\n\n"
            f"**强制动作——必须从以下选至少1个，不准跳过：**\n"
            f"1. `engine_detail('environment')` → 场景缺了哪一感？补上\n"
            f"2. `engine_detail('action')` → 动作链缺反馈拍？加上\n"
            f"3. `engine_detail('dialogue')` → 对话太平？加弦外之音/打断/停顿\n"
            f"4. `engine_detail('item')` → 物品只出现没用？给个展示场景\n"
            f"选完后重新调 `writing_finish`。不准磨洋工（同一段扩三遍不算干事）。"
        )
    
    # ── L2: 灵魂拷问（场景深化） ──
    elif deficit_pct < 50:
        return (
            f"## 🔶 L2 — 场景深化（距目标 {deficit_pct:.0f}%）\n"
            f"字数 {current_words}，需 ≥{min_words}。\n\n"
            f"**你的借口**：「信息密度高，不需要更多描写」\n"
            f"**反击**：验证了吗？调 `engine_detail` 检查了吗？你做的事情价值点在哪？\n\n"
            f"**灵魂拷问—强制回答并执行：**\n"
            f"1. 你这个场景的**底层逻辑**是什么？前因后果展开过吗？→ 因果链展开\n"
            f"2. 你的**顶层设计**在哪？子冲突在哪？→ `engine_detail('scene')` 追加 Yes-but/No-and\n"
            f"3. 你的**差异化**在哪？这段 Telling 能不能改成 Showing？→ 必须改1段\n\n"
            f"禁止扩描写注水——必须加动作/对话/冲突。今天最好的表现是明天最低的要求。"
        )
    
    # ── L3: 361 考核（加事件） ──
    else:
        return (
            f"## 🔴 L3 — 加事件（距目标 {deficit_pct:.0f}%）\n"
            f"字数 {current_words}，需 ≥{min_words}。\n\n"
            f"**你的借口**：「内容已经够了，很紧凑了」\n"
            f"**反击**：字数低于 {int(min_words)} 字谈什么紧凑？大纲里的事件你用完了吗？\n\n"
            f"**强制动作——以下两条选1条执行：**\n"
            f"1. `event_checklist(chapter_id)` → 找未使用的事件追加\n"
            f"2. 加微事件（日常碎片/路人互动/环境异常信号），150-300字\n"
            f"   - 必须与主线/暗线/人物弧线之一相关\n"
            f"   - 找不出相关事件？说明你对大纲不够熟。再读一遍 `writing_start` 返回的事件清单\n\n"
            f"加事件后重新调 `writing_finish`。不努力的话，有的是比你更能写的模型替你。"
        )


# ─── Engine Reference Content ────────────────────────────

# 引擎内容不硬编码，全部存储在 world_settings(category='engine_reference') 中。
# 模型用 seed_engine_data(novel_id, engine_type, content) 添加/修改。


def _build_event_checklist(chapter: dict) -> str:
    """从大纲文本解析事件清单。支持按换行/->/→/|/；分割。"""
    outline = chapter.get("outline", "") or ""
    outline = outline.strip()
    if not outline:
        return "（大纲为空，请自行规划本章事件）"
    # 先按换行分割
    raw = outline.replace("->", "\n").replace("→", "\n").replace("|", "\n").replace("；", "\n")
    lines = [l.strip() for l in raw.split("\n") if l.strip() and len(l.strip()) > 0]
    if not lines:
        return "（大纲无事件明细，请自行规划）"
    checklist = []
    for i, evt in enumerate(lines[:15], 1):
        checklist.append(f"  [ ] E{i}: {evt}")
    if len(lines) > 15:
        checklist.append(f"  …还有{len(lines)-15}个事件")
    return "\n".join(checklist)


def _build_character_detail_card(char: dict, relations: list = None) -> str:
    """构建角色蒸馏卡片（供 character_detail 工具用）。"""
    lines = []
    lines.append(f"### {char.get('name', '?')}（{char.get('role', '?')}）")
    if char.get("appearance"):
        lines.append(f"外观：{char['appearance'][:100]}")
    if char.get("personality"):
        lines.append(f"性格：{char['personality'][:100]}")
    if char.get("speech_style"):
        lines.append(f"说话风格：{char['speech_style']}")
    if char.get("catchphrase"):
        lines.append(f"口头禅：{char['catchphrase']}")
    if char.get("ability_level"):
        lines.append(f"能力等级：{char['ability_level']}")
    status = char.get("status", "")
    if status and status != "{}":
        lines.append(f"当前状态：{status}")
    if char.get("background"):
        lines.append(f"背景：{char['background'][:150]}")
    if char.get("goals"):
        lines.append(f"目标：{char['goals'][:100]}")
    if char.get("weaknesses"):
        lines.append(f"弱点：{char['weaknesses'][:100]}")
    if char.get("arc_notes"):
        lines.append(f"人物弧线：{char['arc_notes'][:100]}")
    if relations:
        lines.append("关系：")
        for r in relations:
            other = r.get("to_name") if r.get("from_character_id") != char.get("id") else r.get("from_name")
            lines.append(f"  - {r.get('relation_type')}: {other} {r.get('description','')[:50]}")
    return "\n".join(lines)


def _get_quality_history(novel_id: int, chapter_number: int, limit: int = 3) -> list:
    """获取前N章的质量历史。"""
    rows = query(
        "SELECT cq.*, ch.number as chapter_number FROM chapter_quality cq "
        "JOIN chapters ch ON cq.chapter_id = ch.id "
        "WHERE ch.novel_id = %s AND ch.number < %s "
        "ORDER BY ch.number DESC LIMIT %s",
        (novel_id, chapter_number, limit)
    )
    return [dict(r) for r in rows]


def _build_rules_prompt() -> str:
    """组装规则提示词（从 writing-constraints.md 加载）。"""
    c = _get_constraints()
    lines = []

    hard_pct = c.get("hard_pct", {})
    hard_abs = c.get("hard_abs", {})

    # 合并硬约束展示
    if hard_pct or hard_abs:
        lines.append("## 🔴 硬约束（MCP 自动校验，不通过拒绝存盘）")
        for key, rule in hard_pct.items():
            lines.append(f"- {rule.get('label',key)}：{rule.get('min',0)}-{rule.get('max',999)}‰")
        for key, rule in hard_abs.items():
            if "min" in rule and "max" in rule:
                lines.append(f"- {rule.get('label',key)}：{rule['min']}-{rule['max']}")
            elif "min" in rule:
                lines.append(f"- {rule.get('label',key)}：≥{rule['min']}")
            elif "max" in rule:
                lines.append(f"- {rule.get('label',key)}：≤{rule['max']}")

    guidelines = c.get("guidelines", {})
    if guidelines:
        lines.append("\n## 📋 写中强制遵守（必须做到，写后自检）")
        lines.append("")
        # 7条核心创作原则——直接展示在prompt中，不藏
        core_keys = ["刀锋技法", "质量方差", "废笔配额", "角色失控", "饱和度不均", "留白不点破", "节奏断层"]
        for key in core_keys:
            if key in guidelines:
                rule = guidelines[key]
                rule_text = rule.get("rule", "")
                label = rule.get("label", key)
                # 精简：只显示第一句核心要求
                short = rule_text.split("。")[0] if "。" in rule_text else rule_text[:60]
                lines.append(f"▸ **{label}**: {short}")
        # 其余原则通过 rule_detail 按需查看
        other_keys = [k for k in guidelines.keys() if k not in core_keys]
        if other_keys:
            lines.append("**更多创作原则**（`rule_detail('{key}')` 查看）：")
            for key in other_keys[:5]:
                lines.append(f"- {key}")
            if len(other_keys) > 5:
                lines.append(f"- …还有{len(other_keys)-5}条")

    return "\n".join(lines)


def _build_writing_prompt(ch: dict, summaries: list, chars: list,
                          foreshadows: list, world_index: list,
                          vol: dict, quality_history: list) -> str:
    """组装完整写作提示词（渐进披露：常驻信息+按需钻取工具指引）。"""
    lines = []
    cn = ch.get("number", "?")

    # ═══════════════ 常驻信息（写在 prompt 里） ═══════════════

    lines.append(f"# 第{cn}章 · 写作上下文")
    lines.append(f"\n**章节**: 第{cn}章「{ch.get('title','')}」 类型:{ch.get('chapter_type','normal')}")

    # ── 场景快照（写前锁定锚点） ──
    ch_type = ch.get("chapter_type", "normal")
    ch_title = ch.get("title", "")
    # 从世界设置中找第一个场地作为默认
    default_loc = ""
    for w in world_index:
        if w.get("category") in ("location", "location_detail"):
            default_loc = w.get("name", "")
            break
    lines.append("\n## 📍 场景快照")
    lines.append(f"**地点**: {default_loc or '待定'} | **时间**: D{ch.get('number',0)} | **关键物品**: F1残片 | **本章目标**: {ch.get('outline','')[:60]}…")
    lines.append("**感官基调**: 待写时确定（视觉主导/听觉主导/触觉主导）")
    outline = ch.get('outline', '') or ''
    if outline:
        lines.append(f"**大纲**: {outline[:200]}{'…' if len(outline)>200 else ''}")

    # ── 事件清单（从大纲解析） ──
    checklist = _build_event_checklist(dict(ch))
    lines.append(f"\n## 本章事件清单（写前确认序列，写中逐项勾选）\n{checklist}")

    # ── 前3章摘要 ──
    if summaries:
        lines.append("\n## 前章回顾")
        for s in summaries:
            sn = s.get("chapter_number", s.get("chapter_id", "?"))
            sm = (s.get("summary", "") or "")[:120]
            lines.append(f"- Ch{sn}: {sm}{'…' if len(s.get('summary',''))>120 else ''}")
    else:
        lines.append("\n## 前章回顾\n（尚无前章）")

    # ── 出场人物索引（精简）──
    if chars:
        lines.append("\n## 出场人物索引")
        for c in chars[:10]:
            role_label = {"protagonist": "主角", "ally": "同伴", "antagonist": "反派",
                          "mentor": "导师", "rival": "对手", "love_interest": "恋人"}.get(c.get("role",""), c.get("role",""))
            lines.append(f"- {c.get('name','?')}（{role_label}）")
        if len(chars) > 10:
            lines.append(f"  …还有{len(chars)-10}人")
        lines.append("\n**角色蒸馏详情**：`character_detail(novel_name, character_name)` 加载完整蒸馏卡（外观/性格/说话风格/能力/状态/关系/物品）")

    # ── 未回收伏笔索引 ──
    if foreshadows:
        lines.append(f"\n## 未回收伏笔（{len(foreshadows)}条）")
        for f in foreshadows[:5]:
            imp = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(f.get("importance",""), "")
            lines.append(f"- {imp} {f.get('description','')[:80]}")
        if len(foreshadows) > 5:
            lines.append(f"  …还有{len(foreshadows)-5}条")

    # ── 质量趋势 ──
    if quality_history:
        lines.append("\n## 质量趋势")
        for q in quality_history:
            qn = q.get("chapter_number", "?")
            qp = "✅" if q.get("passed") else "❌"
            lines.append(f"- Ch{qn} {qp} 破折号:{q.get('em_dash_count','?')} 省略号:{q.get('ellipsis_count','?')} 字数:{q.get('word_count','?')} 否定:{q.get('negation_count','?')}")
        last = quality_history[0]
        ed = last.get("em_dash_count", 0)
        if isinstance(ed, int) and ed < 8:
            lines.append(f"⚠️ 连续破折号不足，本章注意增加到8-12")

    # ═══════════════ 规则 ═══════════════
    lines.append(f"\n---\n{_build_rules_prompt()}")

    # ═══════════════ 作者声音 ═══════════════
    av_rows = query("SELECT data FROM world_settings WHERE category = 'author_voice' LIMIT 1", ())
    if av_rows:
        av_data = av_rows[0]["data"]
        if isinstance(av_data, dict) and "content" in av_data:
            av_text = av_data["content"]
            lines.append("\n## 🎨 作者DNA")
            # 精简提取：每个维度只取精髓一句
            dims = {
                "## 偏执": "兄妹张力·废墟秩序",
                "## 审美": "旧的/破的/补过的→好看，看小处不看大景",
                "## 动作与场面": "升格慢镜头·短句加速长句拉慢·感官齐上",
                "## 比喻": "身体感受＞文学形容，禁安全牌比喻",
                "## 留白": "不总结不解释不升华，动作先上解释延后",
                "## 疯劲": "情绪高潮不喘气地接，写了太过不留",
                "## 世界呼吸": "静止的世界里角色有自己的瞬间"
            }
            for dim, essence in dims.items():
                if dim in av_text:
                    lines.append(f"▸ {essence}")
    lines.append("（完整版: `author_voice(novel_id)`）")

    # ═══════════════ 按需钻取工具指引 ═══════════════
    lines.append("\n---\n📎 **按需加载（写中需要再调，不占上下文）**")
    lines.append("写人物→`character_detail(novel_name, character_name)`")
    lines.append("写场景→`engine_detail('action/dialogue/environment/item')`")
    lines.append("查世界观→`world_query(novel_id, category)`")
    lines.append("查创作原则→`rule_detail('{key}')`")
    lines.append("自查正文→`validate_chapter(text)` → 写后必调 `chapter_self_check(text)` → `writing_finish(..., self_check='passed')`")

    # ── 结尾 ──
    lines.append(f"\n---\n**写作完成后调 writing_finish(novel_name, chapter_number, chapter_text, summary, key_events, …) 存盘。硬约束由 MCP 自动校验，不通过不存盘。**")

    return "\n".join(lines)


# ─── Novel CRUD ──────────────────────────────────────────

@mcp.tool
def novel_create(name: str, genre: str = "", target_platform: str = "",
                 notes: str = "") -> str:
    """创建小说项目"""
    try:
        r = query(
            "INSERT INTO novels (name, genre, target_platform, notes, status) "
            "VALUES (%s, %s, %s, %s, 'brainstorming') RETURNING id",
            (name, genre, target_platform, notes), fetch="one"
        )
        return json.dumps({"ok": True, "id": r["id"], "name": name}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)


@mcp.tool
def novel_list() -> str:
    """列出所有小说项目"""
    rows = query("SELECT id, name, genre, status, current_chapter, target_platform FROM novels ORDER BY updated_at DESC")
    return json.dumps([dict(r) for r in rows], ensure_ascii=False, default=str)


@mcp.tool
def novel_get(novel_name: str) -> str:
    """获取小说项目详情
      novel_name: 小说名称
    """
    novel_id = _resolve_novel_id(novel_name)

    r = query("SELECT * FROM novels WHERE id = %s", (novel_id,), fetch="one")
    return json.dumps(dict(r) if r else {"error": "not found"}, ensure_ascii=False, default=str)


@mcp.tool
def novel_update(novel_name: str, genre: str = "", target_platform: str = "",
                 status: str = "", current_chapter: int = 0,
                 notes: str = "") -> str:
    """更新小说项目。传入需要修改的字段，空值/零值会被忽略
      novel_name: 小说名称
    """
    novel_id = _resolve_novel_id(novel_name)

    fields = {}
    if genre: fields["genre"] = genre
    if target_platform: fields["target_platform"] = target_platform
    if status: fields["status"] = status
    if current_chapter: fields["current_chapter"] = current_chapter
    if notes: fields["notes"] = notes
    if not fields:
        return json.dumps({"ok": False, "error": "no valid fields"}, ensure_ascii=False)
    sets = [f"{k} = %s" for k in fields]
    vals = list(fields.values()) + [novel_id]
    query(f"UPDATE novels SET {', '.join(sets)}, updated_at = NOW() WHERE id = %s", tuple(vals), fetch="none")
    return json.dumps({"ok": True}, ensure_ascii=False)


# ─── World Settings ──────────────────────────────────────

@mcp.tool
def world_upsert(novel_name: str, category: str, name: str, data: dict,
                  keys: str = "", secondary_keys: str = "", tags: str = "",
                  related_ids: str = "", volume_range: str = "", writing_guide: str = "",
                  lorebook_id: str = "", priority: int = 30, is_constant: bool = False) -> str:
    """新增或更新世界观设定。category: race/faction/location/ability/economy/daily_life/history
    keys/secondary_keys/tags/related_ids: JSON字符串数组，解析后存入TEXT[]列
    volume_range: 卷范围字符串，writing_guide: 写作指导，lorebook_id: Lorebook ID
    priority: 优先级(默认30)，is_constant: 是否常驻
      novel_name: 小说名称
    """
    novel_id = _resolve_novel_id(novel_name)

    data_json = json.dumps(data, ensure_ascii=False)

    extra_cols = []
    extra_vals_insert = []
    extra_vals_update = []

    if keys:
        parsed_keys = json.loads(keys)
        extra_cols.append("keys")
        extra_vals_insert.append(parsed_keys)
        extra_vals_update.append(parsed_keys)
    if secondary_keys:
        parsed_skeys = json.loads(secondary_keys)
        extra_cols.append("secondary_keys")
        extra_vals_insert.append(parsed_skeys)
        extra_vals_update.append(parsed_skeys)
    if tags:
        parsed_tags = json.loads(tags)
        extra_cols.append("tags")
        extra_vals_insert.append(parsed_tags)
        extra_vals_update.append(parsed_tags)
    if related_ids:
        parsed_rids = json.loads(related_ids)
        extra_cols.append("related_ids")
        extra_vals_insert.append(parsed_rids)
        extra_vals_update.append(parsed_rids)
    if volume_range:
        extra_cols.append("volume_range")
        extra_vals_insert.append(volume_range)
        extra_vals_update.append(volume_range)
    if writing_guide:
        extra_cols.append("writing_guide")
        extra_vals_insert.append(writing_guide)
        extra_vals_update.append(writing_guide)
    if lorebook_id:
        extra_cols.append("lorebook_id")
        extra_vals_insert.append(lorebook_id)
        extra_vals_update.append(lorebook_id)
    if priority != 30:
        extra_cols.append("priority")
        extra_vals_insert.append(priority)
        extra_vals_update.append(priority)
    if is_constant:
        extra_cols.append("is_constant")
        extra_vals_insert.append(is_constant)
        extra_vals_update.append(is_constant)

    if extra_cols:
        col_str = ", ".join(extra_cols)
        insert_placeholders = ", ".join(["%s"] * len(extra_cols))
        update_sets = ", ".join([f"{c} = %s" for c in extra_cols])
        query(
            f"INSERT INTO world_settings (novel_id, category, name, data, {col_str}) "
            f"VALUES (%s, %s, %s, %s, {insert_placeholders}) "
            f"ON CONFLICT (novel_id, category, name) DO UPDATE SET data = %s, {update_sets}, updated_at = NOW()",
            (novel_id, category, name, data_json, *extra_vals_insert, data_json, *extra_vals_update),
            fetch="none"
        )
    else:
        query(
            "INSERT INTO world_settings (novel_id, category, name, data) "
            "VALUES (%s, %s, %s, %s) "
            "ON CONFLICT (novel_id, category, name) DO UPDATE SET data = %s, updated_at = NOW()",
            (novel_id, category, name, data_json, data_json),
            fetch="none"
        )
    _record_db_hash(novel_id, "world", f"{category}:{name}", data_json)
    return json.dumps({"ok": True, "category": category, "name": name}, ensure_ascii=False)


@mcp.tool
def world_query(novel_name: str, category: str = "", name: str = "") -> str:
    """查询世界观设定。category 和 name 可选，为空返回全部
      novel_name: 小说名称
    """
    novel_id = _resolve_novel_id(novel_name)
    if category and name:
        rows = query("SELECT * FROM world_settings WHERE novel_id = %s AND category = %s AND name = %s",
                     (novel_id, category, name))
    elif category:
        rows = query("SELECT * FROM world_settings WHERE novel_id = %s AND category = %s",
                     (novel_id, category))
    else:
        rows = query("SELECT * FROM world_settings WHERE novel_id = %s ORDER BY category, name",
                     (novel_id,))
    return json.dumps([dict(r) for r in rows], ensure_ascii=False, default=str)
@mcp.tool
def world_delete(novel_name: str, category: str, name: str) -> str:
    """删除世界观设定
      novel_name: 小说名称
    """
    novel_id = _resolve_novel_id(novel_name)

    query("DELETE FROM world_settings WHERE novel_id = %s AND category = %s AND name = %s",
          (novel_id, category, name), fetch="none")
    return json.dumps({"ok": True}, ensure_ascii=False)


# ─── Volume CRUD ──────────────────────────────────────────

@mcp.tool
def volume_create(novel_name: str, number: int, title: str = "",
                  main_plotlines: list = None, notes: str = "") -> str:
    """创建卷。main_plotlines: [{name, description, purpose}]
      novel_name: 小说名称
    """
    novel_id = _resolve_novel_id(novel_name)

    mp = json.dumps(main_plotlines or [], ensure_ascii=False)
    r = query(
        "INSERT INTO volumes (novel_id, number, title, main_plotlines, notes) "
        "VALUES (%s, %s, %s, %s, %s) ON CONFLICT (novel_id, number) "
        "DO UPDATE SET title = %s, main_plotlines = %s, notes = %s, updated_at = NOW() "
        "RETURNING id",
        (novel_id, number, title, mp, notes, title, mp, notes), fetch="one"
    )
    return json.dumps({"ok": True, "id": r["id"], "number": number}, ensure_ascii=False)


@mcp.tool
def volume_list(novel_name: str) -> str:
    """列出小说所有卷
      novel_name: 小说名称
    """
    novel_id = _resolve_novel_id(novel_name)

    rows = query(
        "SELECT v.*, "
        "(SELECT COUNT(*) FROM chapters WHERE volume_id = v.id) as chapter_count "
        "FROM volumes v WHERE v.novel_id = %s ORDER BY v.number",
        (novel_id,)
    )
    return json.dumps([dict(r) for r in rows], ensure_ascii=False, default=str)


def _volume_get_by_id(volume_id: int) -> str:
    v = query("SELECT * FROM volumes WHERE id = %s", (volume_id,), fetch="one")
    if not v:
        return json.dumps({"error": "not found"}, ensure_ascii=False)
    chapters = query(
        "SELECT id, number, title, status, chapter_type FROM chapters "
        "WHERE volume_id = %s ORDER BY number", (volume_id,)
    )
    result = dict(v)
    result["chapters"] = [dict(c) for c in chapters]
    return json.dumps(result, ensure_ascii=False, default=str)


def _volume_update_by_id(volume_id: int, title: str = "",
                  main_plotlines: list = None, notes: str = "") -> str:
    fields = {}
    if title: fields["title"] = title
    if main_plotlines is not None:
        fields["main_plotlines"] = json.dumps(main_plotlines, ensure_ascii=False)
    if notes: fields["notes"] = notes
    if not fields:
        return json.dumps({"ok": False, "error": "no valid fields"}, ensure_ascii=False)
    sets = [f"{k} = %s" for k in fields]
    vals = list(fields.values()) + [volume_id]
    query(f"UPDATE volumes SET {', '.join(sets)}, updated_at = NOW() WHERE id = %s", tuple(vals), fetch="none")
    return json.dumps({"ok": True}, ensure_ascii=False)


# ─── Character CRUD ──────────────────────────────────────

@mcp.tool
def character_create(novel_name: str, name: str, role: str = "npc",
                     faction_id: int = None, race: str = "", ability_level: str = "",
                     appearance: str = "", personality: str = "", background: str = "",
                     goals: str = "", weaknesses: str = "", speech_style: str = "",
                     catchphrase: str = "", arc_notes: str = "",
                     first_appearance_chapter: int = None,
                     appearance_detail: str = "", decision_engine: str = "",
                     voice_fingerprint: str = "", ability_system: str = "",
                     behavior_pattern: str = "", current_snapshot: str = "",
                     growth_trajectory: str = "") -> str:
    """创建人物。role: protagonist/ally/antagonist/mentor/rival/love_interest/npc
    appearance_detail/decision_engine/voice_fingerprint/ability_system/behavior_pattern/current_snapshot/growth_trajectory: JSON字符串
      novel_name: 小说名称
    """
    novel_id = _resolve_novel_id(novel_name)

    _json_fields = {}
    if appearance_detail:
        _json_fields["appearance_detail"] = json.loads(appearance_detail)
    if decision_engine:
        _json_fields["decision_engine"] = json.loads(decision_engine)
    if voice_fingerprint:
        _json_fields["voice_fingerprint"] = json.loads(voice_fingerprint)
    if ability_system:
        _json_fields["ability_system"] = json.loads(ability_system)
    if behavior_pattern:
        _json_fields["behavior_pattern"] = json.loads(behavior_pattern)
    if current_snapshot:
        _json_fields["current_snapshot"] = json.loads(current_snapshot)
    if growth_trajectory:
        _json_fields["growth_trajectory"] = json.loads(growth_trajectory)

    base_cols = ("novel_id, name, role, faction_id, race, ability_level, "
                 "appearance, personality, background, goals, weaknesses, speech_style, catchphrase, "
                 "arc_notes, first_appearance_chapter")
    base_vals = (novel_id, name, role, faction_id, race, ability_level, appearance,
                 personality, background, goals, weaknesses, speech_style, catchphrase,
                 arc_notes, first_appearance_chapter)

    if _json_fields:
        extra_cols = ", ".join(_json_fields.keys())
        extra_vals = list(_json_fields.values())
        all_cols = f"{base_cols}, {extra_cols}"
        all_vals = base_vals + tuple(extra_vals)
    else:
        all_cols = base_cols
        all_vals = base_vals

    placeholders = ",".join(["%s"] * len(all_vals))
    r = query(
        f"INSERT INTO characters ({all_cols}) VALUES ({placeholders}) RETURNING id",
        all_vals, fetch="one"
    )
    _record_db_hash(novel_id, "character", name, json.dumps({"name": name, "role": role, "race": race, "appearance": appearance}, ensure_ascii=False))
    return json.dumps({"ok": True, "id": r["id"], "name": name}, ensure_ascii=False)


def _character_update_by_id(character_id: int, name: str = "", role: str = "", faction_id: int = 0,
                     race: str = "", ability_level: str = "", status: str = "",
                     appearance: str = "", personality: str = "", background: str = "",
                     goals: str = "", weaknesses: str = "", speech_style: str = "",
                     catchphrase: str = "", arc_notes: str = "", is_active: bool = True,
                     _status_json: str = "",
                     appearance_detail: str = "", decision_engine: str = "",
                     voice_fingerprint: str = "", ability_system: str = "",
                     behavior_pattern: str = "", current_snapshot: str = "",
                     growth_trajectory: str = "") -> str:
    fields = {}
    if name: fields["name"] = name
    if role: fields["role"] = role
    if faction_id: fields["faction_id"] = faction_id
    if race: fields["race"] = race
    if ability_level: fields["ability_level"] = ability_level
    if status: fields["status"] = status
    if _status_json: fields["status"] = _status_json
    if appearance: fields["appearance"] = appearance
    if personality: fields["personality"] = personality
    if background: fields["background"] = background
    if goals: fields["goals"] = goals
    if weaknesses: fields["weaknesses"] = weaknesses
    if speech_style: fields["speech_style"] = speech_style
    if catchphrase: fields["catchphrase"] = catchphrase
    if arc_notes: fields["arc_notes"] = arc_notes
    if not is_active: fields["is_active"] = False
    if appearance_detail: fields["appearance_detail"] = json.loads(appearance_detail)
    if decision_engine: fields["decision_engine"] = json.loads(decision_engine)
    if voice_fingerprint: fields["voice_fingerprint"] = json.loads(voice_fingerprint)
    if ability_system: fields["ability_system"] = json.loads(ability_system)
    if behavior_pattern: fields["behavior_pattern"] = json.loads(behavior_pattern)
    if current_snapshot: fields["current_snapshot"] = json.loads(current_snapshot)
    if growth_trajectory: fields["growth_trajectory"] = json.loads(growth_trajectory)
    if not fields:
        return json.dumps({"ok": False, "error": "no valid fields"}, ensure_ascii=False)
    sets = [f"{k} = %s" for k in fields]
    vals = list(fields.values()) + [character_id]
    query(f"UPDATE characters SET {', '.join(sets)}, updated_at = NOW() WHERE id = %s", tuple(vals), fetch="none")
    char = query("SELECT novel_id, name FROM characters WHERE id = %s", (character_id,), fetch="one")
    if char:
        _record_db_hash(char["novel_id"], "character", char["name"], json.dumps(fields, ensure_ascii=False))
    return json.dumps({"ok": True}, ensure_ascii=False)


@mcp.tool
def character_list(novel_name: str, role: str = "") -> str:
    """列出小说人物。role 可选过滤
      novel_name: 小说名称
    """
    novel_id = _resolve_novel_id(novel_name)
    if role:
        rows = query("SELECT * FROM characters WHERE novel_id = %s AND role = %s AND is_active = TRUE ORDER BY role, name",
                     (novel_id, role))
    else:
        rows = query("SELECT * FROM characters WHERE novel_id = %s AND is_active = TRUE ORDER BY role, name",
                     (novel_id,))
    return json.dumps([dict(r) for r in rows], ensure_ascii=False, default=str)
def _character_get_by_id(character_id: int) -> str:
    r = query("SELECT * FROM characters WHERE id = %s", (character_id,), fetch="one")
    return json.dumps(dict(r) if r else {"error": "not found"}, ensure_ascii=False, default=str)


# ─── Character Relations ─────────────────────────────────

def _relation_create_by_id(novel_name: str, from_character_id: int, to_character_id: int,
                    relation_type: str, description: str = "",
                    chapter_established: int = None, intensity: int = 5) -> str:
    novel_id = _resolve_novel_id(novel_name)

    r = query(
        "INSERT INTO character_relations (novel_id, from_character_id, to_character_id, "
        "relation_type, description, chapter_established, intensity) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id",
        (novel_id, from_character_id, to_character_id, relation_type,
         description, chapter_established, intensity), fetch="one"
    )
    return json.dumps({"ok": True, "id": r["id"]}, ensure_ascii=False)


@mcp.tool
def relation_list(novel_name: str) -> str:
    """列出小说的所有人物关系
      novel_name: 小说名称
    """
    novel_id = _resolve_novel_id(novel_name)

    rows = query(
        "SELECT cr.*, c1.name as from_name, c2.name as to_name "
        "FROM character_relations cr "
        "JOIN characters c1 ON cr.from_character_id = c1.id "
        "JOIN characters c2 ON cr.to_character_id = c2.id "
        "WHERE cr.novel_id = %s ORDER BY cr.relation_type",
        (novel_id,)
    )
    return json.dumps([dict(r) for r in rows], ensure_ascii=False, default=str)


# ─── Chapter Management ──────────────────────────────────

@mcp.tool
def chapter_plan(novel_name: str, number: int, title: str = "",
                 outline: str = "", chapter_type: str = "normal",
                 volume_id: int = None) -> str:
    """规划章节。chapter_type: normal/transition/climax/filler/daily
      novel_name: 小说名称
    """
    novel_id = _resolve_novel_id(novel_name)

    r = query(
        "INSERT INTO chapters (novel_id, number, title, outline, chapter_type, volume_id) "
        "VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT (novel_id, number) "
        "DO UPDATE SET title = %s, outline = %s, chapter_type = %s, volume_id = %s, updated_at = NOW() "
        "RETURNING id",
        (novel_id, number, title, outline, chapter_type, volume_id,
         title, outline, chapter_type, volume_id), fetch="one"
    )
    return json.dumps({"ok": True, "id": r["id"], "number": number}, ensure_ascii=False)


@mcp.tool
def chapter_list(novel_name: str, status: str = "") -> str:
    """列出章节。status 可选过滤: planned/drafting/written/reviewed/published
      novel_name: 小说名称
    """
    novel_id = _resolve_novel_id(novel_name)
    if status:
        rows = query("SELECT * FROM chapters WHERE novel_id = %s AND status = %s ORDER BY number",
                     (novel_id, status))
    else:
        rows = query("SELECT * FROM chapters WHERE novel_id = %s ORDER BY number", (novel_id,))
    return json.dumps([dict(r) for r in rows], ensure_ascii=False, default=str)
def _chapter_update_by_id(chapter_id: int, title: str = "", status: str = "",
                   outline: str = "", chapter_type: str = "",
                   volume_id: int = None) -> str:
    fields = {}
    if title: fields["title"] = title
    if status: fields["status"] = status
    if outline: fields["outline"] = outline
    if chapter_type: fields["chapter_type"] = chapter_type
    if volume_id is not None: fields["volume_id"] = volume_id
    if not fields:
        return json.dumps({"ok": False, "error": "no valid fields"}, ensure_ascii=False)
    sets = [f"{k} = %s" for k in fields]
    vals = list(fields.values()) + [chapter_id]
    query(f"UPDATE chapters SET {', '.join(sets)}, updated_at = NOW() WHERE id = %s", tuple(vals), fetch="none")
    return json.dumps({"ok": True}, ensure_ascii=False)


@mcp.tool
def chapter_save_summary(novel_name: str, chapter_number: int, summary: str,
                         key_events: list = None, characters_involved: list = None,
                         new_foreshadows: list = None, resolved_foreshadows: list = None,
                         dimension_snapshot: dict = None) -> str:
    """保存章节摘要。每章写完后调用
      novel_name: 小说名称
      chapter_number: 章节序号
    """
    chapter_id = _resolve_chapter_id(novel_name, chapter_number)
    ke = json.dumps(key_events or [], ensure_ascii=False)
    ds = json.dumps(dimension_snapshot or {}, ensure_ascii=False)
    ci = characters_involved or []
    nf = new_foreshadows or []
    rf = resolved_foreshadows or []
    query(
        "INSERT INTO chapter_summaries (chapter_id, summary, key_events, characters_involved, "
        "new_foreshadows, resolved_foreshadows, dimension_snapshot) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s) "
        "ON CONFLICT (chapter_id) DO UPDATE SET "
        "summary = %s, key_events = %s, characters_involved = %s, "
        "new_foreshadows = %s, resolved_foreshadows = %s, dimension_snapshot = %s",
        (chapter_id, summary, ke, ci, nf, rf, ds,
         summary, ke, ci, nf, rf, ds),
        fetch="none"
    )
    return json.dumps({"ok": True}, ensure_ascii=False)


@mcp.tool
def chapter_get_context(novel_name: str, chapter_number: int) -> str:
    """获取写作上下文：前N章摘要 + 人物状态 + 未回收伏笔 + 世界观 + 章节大纲
      novel_name: 小说名称
    """
    novel_id = _resolve_novel_id(novel_name)

    result = {}

    ch = query("SELECT * FROM chapters WHERE novel_id = %s AND number = %s",
               (novel_id, chapter_number), fetch="one")
    if not ch:
        return json.dumps({"error": f"chapter {chapter_number} not found"}, ensure_ascii=False)
    result["chapter"] = dict(ch)

    prev = query(
        "SELECT cs.summary, cs.dimension_snapshot FROM chapter_summaries cs "
        "JOIN chapters c ON cs.chapter_id = c.id "
        "WHERE c.novel_id = %s AND c.number < %s ORDER BY c.number DESC LIMIT 3",
        (novel_id, chapter_number)
    )
    result["recent_summaries"] = [dict(r) for r in prev]

    chars = query("SELECT id, name, role, ability_level, status FROM characters "
                  "WHERE novel_id = %s AND is_active = TRUE", (novel_id,))
    result["active_characters"] = [dict(r) for r in chars]

    foreshadows = query(
        "SELECT id, description, planted_chapter_id FROM foreshadows "
        "WHERE novel_id = %s AND status = 'planted'", (novel_id,))
    result["unresolved_foreshadows"] = [dict(r) for r in foreshadows]

    world = query("SELECT category, name, data FROM world_settings WHERE novel_id = %s", (novel_id,))
    result["world_settings"] = [dict(r) for r in world]

    return json.dumps(result, ensure_ascii=False, default=str)


# ─── Foreshadow ──────────────────────────────────────────

@mcp.tool
def foreshadow_plant(novel_name: str, description: str,
                     planted_chapter_id: int = None,
                     planned_recall_chapter: int = None,
                     importance: str = "medium",
                     related_characters: list = None,
                     tags: list = None) -> str:
    """埋设伏笔
      novel_name: 小说名称
    """
    novel_id = _resolve_novel_id(novel_name)

    r = query(
        "INSERT INTO foreshadows (novel_id, description, planted_chapter_id, "
        "planned_recall_chapter, importance, related_characters, tags) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id",
        (novel_id, description, planted_chapter_id, planned_recall_chapter,
         importance, related_characters or [], tags or []), fetch="one"
    )
    _record_db_hash(novel_id, "foreshadow", str(r["id"]), json.dumps({"description": description, "importance": importance}, ensure_ascii=False))
    return json.dumps({"ok": True, "id": r["id"]}, ensure_ascii=False)


@mcp.tool
def foreshadow_recall(novel_name: str, foreshadow_id: int, actual_recall_chapter_id: int) -> str:
    """回收伏笔。
      novel_name: 小说名称（验证归属）
      foreshadow_id: 伏笔ID
      actual_recall_chapter_id: 实际回收章节ID
    """
    novel_id = _resolve_novel_id(novel_name)
    fs = query("SELECT id FROM foreshadows WHERE id=%s AND novel_id=%s", (foreshadow_id, novel_id), fetch="one")
    if not fs:
        return json.dumps({"error": f"伏笔 {foreshadow_id} 不存在或不属于该小说"}, ensure_ascii=False)
    query(
        "UPDATE foreshadows SET status = 'recalled', actual_recall_chapter_id = %s, updated_at = NOW() "
        "WHERE id = %s", (actual_recall_chapter_id, foreshadow_id),
        fetch="none"
    )
    return json.dumps({"ok": True}, ensure_ascii=False)


@mcp.tool
def foreshadow_list(novel_name: str, status: str = "") -> str:
    """列出伏笔。status 可选: planted/recalled/abandoned
      novel_name: 小说名称
    """
    novel_id = _resolve_novel_id(novel_name)

    if status:
        rows = query("SELECT * FROM foreshadows WHERE novel_id = %s AND status = %s ORDER BY id",
                     (novel_id, status))
    else:
        rows = query("SELECT * FROM foreshadows WHERE novel_id = %s ORDER BY id", (novel_id,))
    return json.dumps([dict(r) for r in rows], ensure_ascii=False, default=str)


# ─── Timeline ────────────────────────────────────────────

@mcp.tool
def timeline_add(novel_name: str, chapter_id: int, event_time: str,
                 event_order: int, event_description: str,
                 characters_involved: list = None,
                 location_id: int = None,
                 significance: str = "normal") -> str:
    """添加时间线事件
      novel_name: 小说名称
    """
    novel_id = _resolve_novel_id(novel_name)

    r = query(
        "INSERT INTO timeline_events (novel_id, chapter_id, event_time, event_order, "
        "event_description, characters_involved, location_id, significance) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id",
        (novel_id, chapter_id, event_time, event_order, event_description,
         characters_involved or [], location_id, significance), fetch="one"
    )
    return json.dumps({"ok": True, "id": r["id"]}, ensure_ascii=False)


@mcp.tool
def timeline_query(novel_name: str, from_chapter: int = 0, to_chapter: int = 99999) -> str:
    """查询时间线事件，可按章节范围过滤
      novel_name: 小说名称
    """
    novel_id = _resolve_novel_id(novel_name)
    rows = query(
        "SELECT te.*, c.number as chapter_number FROM timeline_events te "
        "JOIN chapters c ON te.chapter_id = c.id "
        "WHERE te.novel_id = %s AND c.number BETWEEN %s AND %s "
        "ORDER BY te.event_order",
        (novel_id, from_chapter, to_chapter)
    )
    return json.dumps([dict(r) for r in rows], ensure_ascii=False, default=str)
# ─── Scene Outlines ──────────────────────────────────────
@mcp.tool
def scene_create(novel_name: str, chapter_number: int, scene_number: int,
                 location: str = "", characters_involved: list = None,
                 conflict: str = "", emotion_type: str = "",
                 key_beats: list = None, notes: str = "") -> str:
    """创建场景大纲
      novel_name: 小说名称
      chapter_number: 章节序号
    """
    chapter_id = _resolve_chapter_id(novel_name, chapter_number)
    kb = json.dumps(key_beats or [], ensure_ascii=False)
    ci = characters_involved or []
    query(
        "INSERT INTO scene_outlines (chapter_id, scene_number, location, characters_involved, "
        "conflict, emotion_type, key_beats, notes) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s) "
        "ON CONFLICT (chapter_id, scene_number) DO UPDATE SET "
        "location = %s, characters_involved = %s, conflict = %s, emotion_type = %s, "
        "key_beats = %s, notes = %s",
        (chapter_id, scene_number, location, ci,
         conflict, emotion_type, kb, notes,
         location, ci, conflict, emotion_type, kb, notes),
        fetch="none"
    )
    return json.dumps({"ok": True}, ensure_ascii=False)


@mcp.tool
def scene_list(novel_name: str, chapter_number: int) -> str:
    """列出章节的场景大纲
      novel_name: 小说名称
      chapter_number: 章节序号
    """
    chapter_id = _resolve_chapter_id(novel_name, chapter_number)
    rows = query("SELECT * FROM scene_outlines WHERE chapter_id = %s ORDER BY scene_number",
                 (chapter_id,))
    return json.dumps([dict(r) for r in rows], ensure_ascii=False, default=str)


# ─── Dimension Changes ───────────────────────────────────

@mcp.tool
def dimension_log(novel_name: str, chapter_id: int, dimension: str,
                  change_type: str, entity_name: str,
                  before_value: dict = None, after_value: dict = None,
                  description: str = "") -> str:
    """记录维度变更。dimension: time/space/ability/economy/character_status
      novel_name: 小说名称
    """
    novel_id = _resolve_novel_id(novel_name)

    bv = json.dumps(before_value or {}, ensure_ascii=False)
    av = json.dumps(after_value or {}, ensure_ascii=False)
    query(
        "INSERT INTO dimension_changes (novel_id, chapter_id, dimension, change_type, "
        "entity_name, before_value, after_value, description) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
        (novel_id, chapter_id, dimension, change_type, entity_name, bv, av, description),
        fetch="none"
    )
    return json.dumps({"ok": True}, ensure_ascii=False)


@mcp.tool
def dimension_query(novel_name: str, dimension: str = "", from_chapter: int = 0,
                    to_chapter: int = 99999) -> str:
    """查询维度变更记录
      novel_name: 小说名称
    """
    novel_id = _resolve_novel_id(novel_name)

    sql = (
        "SELECT dc.*, c.number as chapter_number FROM dimension_changes dc "
        "JOIN chapters c ON dc.chapter_id = c.id "
        "WHERE dc.novel_id = %s AND c.number BETWEEN %s AND %s"
    )
    params: list = [novel_id, from_chapter, to_chapter]
    if dimension:
        sql += " AND dc.dimension = %s"
        params.append(dimension)
    sql += " ORDER BY c.number, dc.id"
    rows = query(sql, tuple(params))
    return json.dumps([dict(r) for r in rows], ensure_ascii=False, default=str)


# ─── Search ──────────────────────────────────────────────

@mcp.tool
def db_search(novel_name: str, keyword: str) -> str:
    """在小说所有数据中搜索关键词（世界观/人物/章节/伏笔/时间线）
      novel_name: 小说名称
    """
    novel_id = _resolve_novel_id(novel_name)
    result: dict = {}
    kw = f"%{keyword}%"
    world = query(
        "SELECT category, name, data FROM world_settings "
        "WHERE novel_id = %s AND (name ILIKE %s OR data::text ILIKE %s)",
        (novel_id, kw, kw)
    )
    if world:
        result["world_settings"] = [dict(r) for r in world]
    chars = query(
        "SELECT id, name, role, personality FROM characters "
        "WHERE novel_id = %s AND is_active = TRUE AND "
        "(name ILIKE %s OR personality ILIKE %s OR background ILIKE %s OR goals ILIKE %s)",
        (novel_id, kw, kw, kw, kw)
    )
    if chars:
        result["characters"] = [dict(r) for r in chars]
    chapters = query(
        "SELECT number, title, outline FROM chapters "
        "WHERE novel_id = %s AND (title ILIKE %s OR outline ILIKE %s)",
        (novel_id, kw, kw)
    )
    if chapters:
        result["chapters"] = [dict(r) for r in chapters]
    foreshadows = query(
        "SELECT id, description, status FROM foreshadows "
        "WHERE novel_id = %s AND description ILIKE %s",
        (novel_id, kw)
    )
    if foreshadows:
        result["foreshadows"] = [dict(r) for r in foreshadows]
    return json.dumps(result, ensure_ascii=False, default=str)
# ─── Composite Orchestration Tools ────────────────────────
@mcp.tool
def writing_start(novel_name: str, chapter_number: int) -> str:
    """写章前一键注入上下文：章节信息+前3章摘要+活跃人物索引+未回收伏笔+当前卷规划+硬约束+质量历史。
      novel_name: 小说名称
    """
    novel_id = _resolve_novel_id(novel_name)

    result = {}

    ch = query("SELECT * FROM chapters WHERE novel_id = %s AND number = %s",
               (novel_id, chapter_number), fetch="one")
    if not ch:
        return json.dumps({"error": f"chapter {chapter_number} not found"}, ensure_ascii=False)
    result["chapter"] = dict(ch)

    prev = query(
        "SELECT cs.summary, cs.dimension_snapshot FROM chapter_summaries cs "
        "JOIN chapters c ON cs.chapter_id = c.id "
        "WHERE c.novel_id = %s AND c.number < %s ORDER BY c.number DESC LIMIT 3",
        (novel_id, chapter_number)
    )
    result["recent_summaries"] = [dict(r) for r in prev]

    chars = query("SELECT id, name, role FROM characters "
                  "WHERE novel_id = %s AND is_active = TRUE", (novel_id,))
    result["active_characters"] = [dict(r) for r in chars]

    foreshadows = query(
        "SELECT id, description, planted_chapter_id, importance FROM foreshadows "
        "WHERE novel_id = %s AND status = 'planted' ORDER BY id", (novel_id,))
    result["unresolved_foreshadows"] = [dict(r) for r in foreshadows]

    world = query("SELECT category, name FROM world_settings WHERE novel_id = %s", (novel_id,))
    result["world_settings_index"] = [dict(r) for r in world]

    if ch.get("volume_id"):
        vol = query("SELECT * FROM volumes WHERE id = %s", (ch["volume_id"],), fetch="one")
        if vol:
            result["current_volume"] = dict(vol)

    # ── 质量历史 ──
    quality_history = _get_quality_history(novel_id, chapter_number)
    result["quality_history"] = quality_history

    # ── 全部规则（从 writing-constraints.md 加载）──
    # ── 组装完整写作提示词（规则已内嵌在 writing_prompt 中，不再单独返回 rules 字段）

    # ── 组装完整写作提示词（渐进披露）──
    result["writing_prompt"] = _build_writing_prompt(
        ch=result["chapter"],
        summaries=result["recent_summaries"],
        chars=result["active_characters"],
        foreshadows=result["unresolved_foreshadows"],
        world_index=result["world_settings_index"],
        vol=result.get("current_volume", {}),
        quality_history=quality_history,
    )

    return json.dumps(result, ensure_ascii=False, default=str)


@mcp.tool
def rule_detail(rule_key: str) -> str:
    """查看某条创作原则的完整说明。从 writing-constraints.md 加载。"""
    c = _get_constraints()
    guidelines = c.get("guidelines", {})
    rule = guidelines.get(rule_key)
    if not rule:
        return json.dumps({"error": f"rule '{rule_key}' not found. 编辑 writing-constraints.md 添加"},
                           ensure_ascii=False)
    return json.dumps({"key": rule_key, "rule": rule.get("rule",""), "ref": rule.get("ref","")},
                       ensure_ascii=False)


def _character_detail_by_id(character_id: int, chapter_number: int = None) -> str:
    char = query("SELECT * FROM characters WHERE id = %s", (character_id,), fetch="one")
    if not char:
        return json.dumps({"error": "character not found"}, ensure_ascii=False)

    result = dict(char)

    rels = query(
        "SELECT cr.relation_type, cr.description, cr.intensity, cr.status, "
        "c1.name as from_name, c2.name as to_name "
        "FROM character_relations cr "
        "JOIN characters c1 ON cr.from_character_id = c1.id "
        "JOIN characters c2 ON cr.to_character_id = c2.id "
        "WHERE cr.novel_id = %s AND (c1.id = %s OR c2.id = %s)",
        (char["novel_id"], character_id, character_id)
    )
    result["relations"] = [dict(r) for r in rels]

    if chapter_number:
        snap = query(
            "SELECT css.* FROM character_state_snapshots css "
            "JOIN chapters c ON css.chapter_id = c.id "
            "WHERE css.character_id = %s AND c.number <= %s "
            "ORDER BY c.number DESC LIMIT 1",
            (character_id, chapter_number), fetch="one"
        )
        if snap:
            result["snapshot"] = dict(snap)
    else:
        snap = query(
            "SELECT css.*, c.number as chapter_number FROM character_state_snapshots css "
            "JOIN chapters c ON css.chapter_id = c.id "
            "WHERE css.character_id = %s ORDER BY c.number DESC LIMIT 1",
            (character_id,), fetch="one"
        )
        if snap:
            result["snapshot"] = dict(snap)

    return json.dumps(result, ensure_ascii=False, default=str)


@mcp.tool
def record_new_content(novel_name: str, content_type: str, name: str = "",
                        data: str = "", file_path: str = "") -> str:
    """记录写作中新出现的设定/物品/地点/NPC到DB。
    content_type: 'setting'|'item'|'location'|'npc'|'faction'
    name: 名称。为空时返回该类型的模板结构供填写
    data: JSON字符串，按模板字段填写。先调 record_new_content(novel_name="这次不一样了", 'item') 查看模板

    用法:
      # 查看模板
      record_new_content(novel_name="这次不一样了", 'item')
      # 保存数据
      record_new_content(novel_name="这次不一样了", 'item', '灵能短刀', '{"appearance":"...", "function":"..."}')
      novel_name: 小说名称
    """
    novel_id = _resolve_novel_id(novel_name)

    valid_types = ["setting", "item", "location", "npc", "faction"]
    if content_type not in valid_types:
        return json.dumps({"error": f"type must be one of {valid_types}"}, ensure_ascii=False)

    # 如无 name，返回模板
    if not name:
        tmpl = query(
            "SELECT data FROM world_settings WHERE novel_id = %s AND category = 'template' AND name = %s",
            (novel_id, content_type), fetch="one"
        )
        if tmpl:
            return json.dumps({
                "template": tmpl["data"],
                "usage": f"填写后调 record_new_content(novel_name, '{content_type}', name, json_data)"
            }, ensure_ascii=False)
        return json.dumps({"template": f"no template for {content_type}, use generic description"}, ensure_ascii=False)

    # 解析 data
    parsed_data = {}
    if data:
        try:
            parsed_data = json.loads(data)
        except json.JSONDecodeError as e:
            return json.dumps({"error": f"invalid JSON data: {str(e)}"}, ensure_ascii=False)

    cat_map = {
        "setting": "core_setting",
        "item": "ability",
        "location": "location",
        "faction": "faction",
    }

    if content_type == "npc":
        # 写入 characters 表
        existing = query(
            "SELECT id FROM characters WHERE novel_id = %s AND name = %s",
            (novel_id, name), fetch="one"
        )
        if existing:
            return json.dumps({"ok": True, "action": "already_exists", "id": existing["id"], "name": name}, ensure_ascii=False)
        desc = parsed_data.get("背景", parsed_data.get("notes", "")) if parsed_data else ""
        r = query(
            "INSERT INTO characters (novel_id, name, role, appearance, personality, speech_style, background, status) "
            "VALUES (%s, %s, 'npc', %s, %s, %s, %s, %s) RETURNING id",
            (novel_id, name,
             parsed_data.get("外观", {}).get("服饰", "") if isinstance(parsed_data.get("外观"), dict) else str(parsed_data.get("外观", "")),
             str(parsed_data.get("性格", {}).get("核心特质", "") if isinstance(parsed_data.get("性格"), dict) else parsed_data.get("性格", "")),
             str(parsed_data.get("性格", {}).get("说话风格", "") if isinstance(parsed_data.get("性格"), dict) else ""),
             str(parsed_data.get("背景", {}).get("出身", "") if isinstance(parsed_data.get("背景"), dict) else desc),
             json.dumps(parsed_data.get("当前状态", {}), ensure_ascii=False) if isinstance(parsed_data.get("当前状态"), dict) else "{}"),
            fetch="one"
        )
        char_id = r["id"] if r else None
        # 同时存完整数据到 world_settings
        if parsed_data:
            query("""INSERT INTO world_settings (novel_id, category, name, data) VALUES (%s, 'character_detail', %s, %s)
                     ON CONFLICT (novel_id, category, name) DO UPDATE SET data = %s""",
                  (novel_id, f"npc_{name}", json.dumps(parsed_data, ensure_ascii=False),
                   json.dumps(parsed_data, ensure_ascii=False)), fetch="none")
        return json.dumps({"ok": True, "action": "created", "id": char_id, "type": "npc", "name": name}, ensure_ascii=False)
    else:
        # 写入 world_settings
        cat = cat_map.get(content_type, "core_setting")
        store_data = parsed_data if parsed_data else {"content": data or name, "source": "chapter_writing"}
        # 添加名称到数据中
        if isinstance(store_data, dict):
            store_data["_name"] = name
        query(
            "INSERT INTO world_settings (novel_id, category, name, data) "
            "VALUES (%s, %s, %s, %s) ON CONFLICT (novel_id, category, name) DO UPDATE SET data = %s",
            (novel_id, cat, name, json.dumps(store_data, ensure_ascii=False),
             json.dumps(store_data, ensure_ascii=False)), fetch="none"
        )
        return json.dumps({"ok": True, "action": "saved", "type": content_type, "category": cat, "name": name}, ensure_ascii=False)


@mcp.tool
def event_checklist(novel_name: str, chapter_number: int) -> str:
    """获取本章事件清单+检查表。基于大纲自动解析，写前确认事件序列，写中逐项勾选。
      novel_name: 小说名称
      chapter_number: 章节序号
    """
    novel_id = _resolve_novel_id(novel_name)
    ch = query("SELECT * FROM chapters WHERE novel_id = %s AND number = %s",
               (novel_id, chapter_number), fetch="one")
    if not ch:
        return json.dumps({"error": "chapter not found"}, ensure_ascii=False)

    checklist = _build_event_checklist(dict(ch))

    result = {
        "chapter_id": ch["id"],
        "chapter_title": ch.get("title", ""),
        "chapter_number": ch.get("number", 0),
        "chapter_type": ch.get("chapter_type", "normal"),
        "full_outline": ch.get("outline", ""),
        "event_checklist": checklist,
        "usage": "写前确认事件序列→写中每完成一个勾选[✅]→写后确认全部覆盖→调writing_finish"
    }
    return json.dumps(result, ensure_ascii=False)


@mcp.tool
def seed_engine_data(novel_name: str, engine_type: str = "", content: str = "") -> str:
    """写入或更新引擎参考内容到 DB。engine_type: scene/action/dialogue/environment/item/snapshot/ability/causality。
    模型可从 skill 文件中读取内容后调此工具写入。content 为空则返回当前内容供参考。
      novel_name: 小说名称
    """
    novel_id = _resolve_novel_id(novel_name)

    if not engine_type:
        # 列出当前所有
        rows = query(
            "SELECT name, data FROM world_settings WHERE novel_id = %s AND category = 'engine_reference'",
            (novel_id,)
        )
        result = {}
        for r in rows:
            d = r["data"]
            result[r["name"]] = d.get("content","")[:100] if isinstance(d, dict) else ""
        return json.dumps({"engines": result, "count": len(result)}, ensure_ascii=False)

    if not content:
        # 读取当前内容
        row = query(
            "SELECT data FROM world_settings WHERE novel_id = %s AND category = 'engine_reference' AND name = %s",
            (novel_id, engine_type), fetch="one"
        )
        if row:
            d = row["data"]
            return json.dumps({"engine": engine_type, "content": d.get("content","") if isinstance(d, dict) else d}, ensure_ascii=False)
        return json.dumps({"engine": engine_type, "content": None}, ensure_ascii=False)

    query(
        "INSERT INTO world_settings (novel_id, category, name, data) "
        "VALUES (%s, 'engine_reference', %s, %s) "
        "ON CONFLICT (novel_id, category, name) DO UPDATE SET data = %s, updated_at = NOW()",
        (novel_id, engine_type, json.dumps({"content": content}), json.dumps({"content": content})),
        fetch="none"
    )
    return json.dumps({"ok": True, "engine_type": engine_type, "content_length": len(content)}, ensure_ascii=False)


@mcp.tool
def engine_detail(engine_type: str, novel_name: str) -> str:
    """加载写作引擎参考。从 world_settings 读取，模型可自定义覆盖。
      novel_name: 小说名称
    """
    novel_id = _resolve_novel_id(novel_name)

    # 优先读本小说
    row = query(
        "SELECT data FROM world_settings WHERE novel_id = %s AND category = 'engine_reference' AND name = %s",
        (novel_id, engine_type), fetch="one"
    )
    if row:
        data = row["data"]
        if isinstance(data, dict) and "content" in data:
            return json.dumps({"engine": engine_type, "content": data["content"], "source": "db"}, ensure_ascii=False)

    # 全局兜底
    row = query(
        "SELECT data FROM world_settings WHERE novel_id = %s AND category = 'engine_reference' AND name = %s",
        (0, engine_type), fetch="one"
    )
    if row:
        data = row["data"]
        if isinstance(data, dict) and "content" in data:
            return json.dumps({"engine": engine_type, "content": data["content"], "source": "global"}, ensure_ascii=False)

    return json.dumps({"error": f"engine '{engine_type}' not found. 用 seed_engine_data(novel_name, '{engine_type}', content=...) 添加"}, ensure_ascii=False)


_SYNC_LOREBOOK_BASE = "/Users/ganjie/code/personal/bywork/books_creater/novels"


@mcp.tool
def sync_lorebook(novel_name: str) -> str:
    """从 设定/世界观/ 目录下的 MD 文件同步数据到 DB。
    解析 ## category: name 格式，upsert 到 world_settings 表。
    每次写作前调一次，确保 DB 与文件一致。"""
    novel_dir = os.path.join(_SYNC_LOREBOOK_BASE, novel_name, "设定", "世界观")
    if not os.path.isdir(novel_dir):
        return json.dumps({"error": f"novel dir not found: {novel_dir}"}, ensure_ascii=False)

    novel = query("SELECT id FROM novels WHERE name = %s", (novel_name,), fetch="one")
    if not novel:
        return json.dumps({"error": f"novel '{novel_name}' not found in DB"}, ensure_ascii=False)
    novel_id = novel["id"]

    changes = {}
    md_files = sorted(
        f for f in os.listdir(novel_dir)
        if f.endswith(".md") and not f.startswith("_")
    )

    for fname in md_files:
        fpath = os.path.join(novel_dir, fname)
        with open(fpath, "r", encoding="utf-8") as f:
            text = f.read()

        parts = re.split(r"^## (.+)$", text, flags=re.MULTILINE)
        if len(parts) < 3:
            continue

        for i in range(1, len(parts), 2):
            header = parts[i].strip()
            body = parts[i + 1].strip()

            m = re.match(r"^(\w+):\s+(.+)$", header)
            if not m:
                continue

            category = m.group(1)
            name = m.group(2)

            meta = {}
            content_lines = []
            in_meta = True

            for line in body.split("\n"):
                if in_meta and line.startswith("- **"):
                    fm = re.match(r"^- \*\*(\w+)\*\*:\s*(.+)$", line)
                    if fm:
                        key = fm.group(1)
                        val_str = fm.group(2).strip()
                        try:
                            val = json.loads(val_str)
                        except (json.JSONDecodeError, ValueError):
                            val = val_str
                        meta[key] = val
                    else:
                        in_meta = False
                        content_lines.append(line)
                elif in_meta and line.strip() == "":
                    in_meta = False
                else:
                    in_meta = False
                    content_lines.append(line)

            content = "\n".join(content_lines).strip()
            content = re.sub(r"^---\s*$", "", content, flags=re.MULTILINE).strip()

            data = dict(meta)
            data["content"] = content
            data_json = json.dumps(data, ensure_ascii=False)

            keys_val = meta.get("keys", [])
            if isinstance(keys_val, str):
                keys_val = [k.strip() for k in keys_val.split(",")]
            secondary_keys_val = meta.get("secondary_keys", [])
            if isinstance(secondary_keys_val, str):
                secondary_keys_val = [k.strip() for k in secondary_keys_val.split(",")]
            tags_val = meta.get("tags", [])
            if isinstance(tags_val, str):
                tags_val = [k.strip() for k in tags_val.split(",")]
            related_val = meta.get("related", [])
            if isinstance(related_val, str):
                related_val = [k.strip() for k in related_val.split(",")]
            volume_range = meta.get("volume_range", "")
            if not isinstance(volume_range, str):
                volume_range = str(volume_range)
            priority = meta.get("priority", 30)
            if isinstance(priority, str):
                try:
                    priority = int(priority)
                except ValueError:
                    priority = 30
            is_constant = meta.get("is_constant", False)
            if isinstance(is_constant, str):
                is_constant = is_constant.lower() in ("true", "1", "yes")

            try:
                query(
                    "INSERT INTO world_settings (novel_id, category, name, data, keys, secondary_keys, tags, related_ids, volume_range, priority, is_constant) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) "
                    "ON CONFLICT (novel_id, category, name) DO UPDATE SET "
                    "data = EXCLUDED.data, keys = EXCLUDED.keys, secondary_keys = EXCLUDED.secondary_keys, "
                    "tags = EXCLUDED.tags, related_ids = EXCLUDED.related_ids, volume_range = EXCLUDED.volume_range, "
                    "priority = EXCLUDED.priority, is_constant = EXCLUDED.is_constant, updated_at = NOW()",
                    (novel_id, category, name, data_json,
                     keys_val if keys_val else None,
                     secondary_keys_val if secondary_keys_val else None,
                     tags_val if tags_val else None,
                     related_val if related_val else None,
                     volume_range or None,
                     priority if priority != 30 else None,
                     is_constant or None),
                    fetch="none"
                )
                _record_db_hash(novel_id, "world", f"{category}:{name}", data_json)
                cat_key = category
                changes[cat_key] = changes.get(cat_key, 0) + 1
            except Exception as e:
                pass

    return json.dumps({"ok": True, "novel_id": novel_id, "changes": changes}, ensure_ascii=False)

@mcp.tool
def author_voice(novel_name: str) -> str:
    """加载本小说的作者声音维度。存储在 world_settings(category='author_voice') 中。
      novel_name: 小说名称
    """
    novel_id = _resolve_novel_id(novel_name)

    rows = query(
        "SELECT name, data FROM world_settings WHERE novel_id = %s AND category = 'author_voice'",
        (novel_id,)
    )
    if rows:
        result = {"voices": [dict(r) for r in rows]}
    else:
        # 兜底：项目中默认的作者声音定义
        result = {"voices": [
            {"name": "审美偏执", "content": "用旧了的东西好看。管壁锈痕、工具磨损、棉衣补丁——天然会注意这些"},
            {"name": "比喻体系", "content": "身体感受＞文学形容。用'牙齿磕牙齿'代替'刺骨'，禁安全牌比喻"},
            {"name": "不点破留白", "content": "叙事默认不总结不解释不升华。动作先上，解释延后"},
            {"name": "细节集中", "content": "一个场景只给1个核心特写，其他全部模糊带过"},
            {"name": "疯劲密度", "content": "情绪高潮时事件不喘气地接。写完觉得'会不会太过'——留着，是对的"},
            {"name": "世界呼吸", "content": "冰冷静止的世界里，角色有自己的瞬间——踩石头走平衡、哼跑调的曲子"}
        ], "note": "默认声音，可通过 world_upsert(category='author_voice') 覆盖"}
    return json.dumps(result, ensure_ascii=False)


@mcp.tool
def writing_spec(novel_name: str) -> str:
    """加载本小说的写作执行规范。存储在 world_settings(category='writing_spec') 中。
      novel_name: 小说名称
    """
    novel_id = _resolve_novel_id(novel_name)

    rows = query(
        "SELECT name, data FROM world_settings WHERE novel_id = %s AND category = 'writing_spec'",
        (novel_id,)
    )
    if rows:
        specs = [dict(r) for r in rows]
        return json.dumps({"specs": specs}, ensure_ascii=False)
    return json.dumps({"specs": [], "note": "未设置写作规范。用 world_upsert(category='writing_spec') 添加"}, ensure_ascii=False)


@mcp.tool
def chapter_self_check(chapter_text: str, self_report: str = "") -> str:
    """写后自检工具。12项语义检查（刀锋技法/质量方差/废笔配额/角色失控/饱和度不均/留白不点破/节奏断层/AI指纹/叙事意识/人物鲜活/世界观植入/NPC出场）。
    
    用法：
      1. chapter_self_check(chapter_text) → 返回12项检查表
      2. 逐项检查后，调 chapter_self_check(chapter_text, '{"结果": {...}}')
      3. writing_finish 需要传 self_check='passed' 才能存盘
    """
    CHECKLIST = {
        "刀锋技法": {
            "标准": "至少1种:沉默暴击/暴力插入/不回头/尺度崩塌/反高潮/情绪断层/悬而未决。使用后禁解释/升华/自我剖析。",
            "结果": "待检查",
            "说明": ""
        },
        "质量方差": {
            "标准": "2-3个粗糙段/章(无感官/无比喻/纯动作)，相邻段落质量差≥20分。连续精写≤3段。",
            "结果": "待检查",
            "说明": ""
        },
        "废笔配额": {
            "标准": "≥3种废笔/章(角色废话/环境废笔/生活碎片/假伏笔/跑题对话)，真废笔和废线按需使用。",
            "结果": "待检查",
            "说明": ""
        },
        "角色失控": {
            "标准": "1+次/章角色'不对'(说蠢话/情绪过头/跑题/不理性决定)，不是OOC。",
            "结果": "待检查",
            "说明": ""
        },
        "饱和度不均": {
            "标准": "主角超饱和，NPC极简(1个特征反复用)，路人透明。不撒匀。",
            "结果": "待检查",
            "说明": ""
        },
        "留白不点破": {
            "标准": "禁金句总结/升华。主题通过人物行为传达，不用叙事者评论。不解释情感。",
            "结果": "待检查",
            "说明": ""
        },
        "节奏断层": {
            "标准": "1+处/章节奏真的断了(突然加速/停滞/切走/时间塌缩)。",
            "结果": "待检查",
            "说明": ""
        },
        "AI指纹": {
            "标准": "FP-1句号切割法/FP-2解释式展示/FP-3结构对称/FP-4否定转折模式化。≤1处。",
            "结果": "待检查",
            "说明": ""
        },
        "叙事意识": {
            "标准": "焦点(主角>NPC>路人) / 爆炸点(大纲事件章必炸) / 真废笔+废线穿插。",
            "结果": "待检查",
            "说明": ""
        },
        "人物鲜活": {
            "标准": "微动作/微表情代替直白情绪词('紧张'→手指敲桌面)。禁'不舍''难过''留恋'。",
            "结果": "待检查",
            "说明": ""
        },
        "世界观植入": {
            "标准": "≥3个元素自然融入(通过动作/对话/环境展现，非科普)。",
            "结果": "待检查",
            "说明": ""
        },
        "NPC出场": {
            "标准": "≥2个有动机的NPC出现(不止当工具人，有独立的行为逻辑)。",
            "结果": "待检查",
            "说明": ""
        }
    }

    if not self_report:
        # 返回检查表
        return json.dumps({
            "checklist": CHECKLIST,
            "instruction": "逐项检查后，调 chapter_self_check(text, '{\"结果\":{\"刀锋技法\":\"✅\",\"质量方差\":\"⚠\",...}}')",
            "禁止存盘": "12项全部标注✅或⚠后方可调writing_finish(self_check='passed')"
        }, ensure_ascii=False)

    # 解析自检报告
    try:
        report = json.loads(self_report)
    except json.JSONDecodeError:
        return json.dumps({"error": "无效JSON格式"}, ensure_ascii=False)

    results = report.get("结果", report.get("results", {}))
    if not results:
        return json.dumps({"error": "缺少‘结果’字段"}, ensure_ascii=False)

    # 统计
    passed = 0
    failed = 0
    detail = []
    for key, item in CHECKLIST.items():
        r = results.get(key, "待检查")
        desc = results.get(f"{key}_说明", "")
        if r == "✅":
            passed += 1
        elif r == "⚠":
            passed += 1  # 部分达标也算可以通过
        else:
            failed += 1
        detail.append(f"{key}: {r}" + (f" - {desc}" if desc else ""))

    ok = failed == 0
    return json.dumps({
        "self_check_passed": ok,
        "summary": f"✅ {passed}项通过 / ❌ {failed}项不通过",
        "detail": detail,
        "提示": "通过后调 writing_finish(self_check='passed') 存盘" if ok else "修复后重新调 chapter_self_check"
    }, ensure_ascii=False)


@mcp.tool
def validate_chapter(chapter_text: str) -> str:
    """校验正文是否满足硬约束。返回 violations + stats + enrichment（字数不足时的充实指引）。约束从 writing-constraints.md 加载。"""
    result = validate_chapter_text(chapter_text)
    stats = result.get("stats", {})
    wc = stats.get("word_count", 0)
    c = _get_constraints()
    hard_abs = c.get("hard_abs", {})
    min_words = hard_abs.get("word_count", {}).get("min", 0)
    if wc < min_words:
        result["enrichment"] = _enrichment_level(wc, min_words)
    return json.dumps(result, ensure_ascii=False)


@mcp.tool
def writing_finish(novel_name: str, chapter_number: int, summary: str, chapter_text: str,
                   key_events: list = None, characters_involved: list = None,
                   new_foreshadows: list = None, resolved_foreshadows: list = None,
                   ability_level: str = "", location: str = "",
                   timeline_events: list = None,
                   self_check: str = "") -> str:
    """写章后一键更新所有状态：先校验正文→再自检→通过后存摘要+维度+伏笔+时间线。校验或自检不通过会拒绝存盘。
    self_check: 必须传'passed'，表示 chapter_self_check 已完成并全部通过。"""
    novel_id = _resolve_novel_id(novel_name)
    ch = query("SELECT id, novel_id, number FROM chapters WHERE novel_id=%s AND number=%s", (novel_id, chapter_number), fetch="one")
    if not ch:
        return json.dumps({"error": f"章节 {chapter_number} 不存在"}, ensure_ascii=False)
    chapter_id = ch["id"]

    validation = validate_chapter_text(chapter_text)
    if not validation["passed"]:
        err = {
            "ok": False,
            "error": "硬约束校验不通过，拒绝存盘",
            "violations": validation["violations"],
            "stats": validation["stats"],
        }
        # 字数不足时追加充实指引（L1/L2/L3）
        stats = validation["stats"]
        wc = stats.get("word_count", 0)
        c = _get_constraints()
        hard_abs = c.get("hard_abs", {})
        min_words = hard_abs.get("word_count", {}).get("min", 0)
        if wc < min_words:
            err["enrichment"] = _enrichment_level(wc, min_words)
        return json.dumps(err, ensure_ascii=False)

    # ❗ 自检拦截
    if self_check != "passed":
        return json.dumps({
            "ok": False,
            "error": "自检未完成，拒绝存盘",
            "hint": "调 chapter_self_check(chapter_text) → 逐项检查 → 修复 → 再调 writing_finish(self_check='passed')"
        }, ensure_ascii=False)

    ke = json.dumps(key_events or [], ensure_ascii=False)
    ds = {}
    if ability_level:
        ds["ability"] = ability_level
    if location:
        ds["location"] = location
    ds_json = json.dumps(ds, ensure_ascii=False)
    ci = characters_involved or []
    nf = new_foreshadows or []
    rf = resolved_foreshadows or []

    # 1. 保存章节摘要
    query(
        "INSERT INTO chapter_summaries (chapter_id, summary, key_events, characters_involved, "
        "new_foreshadows, resolved_foreshadows, dimension_snapshot) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s) "
        "ON CONFLICT (chapter_id) DO UPDATE SET "
        "summary = %s, key_events = %s, characters_involved = %s, "
        "new_foreshadows = %s, resolved_foreshadows = %s, dimension_snapshot = %s",
        (chapter_id, summary, ke, ci, nf, rf, ds_json,
         summary, ke, ci, nf, rf, ds_json),
        fetch="none"
    )

    # 2. 更新章节状态
    query("UPDATE chapters SET status = 'written', updated_at = NOW() WHERE id = %s", (chapter_id,), fetch="none")

    # 3. 回收伏笔
    for fid in (rf or []):
        query("UPDATE foreshadows SET status = 'recalled', actual_recall_chapter_id = %s, "
               "updated_at = NOW() WHERE id = %s", (chapter_id, fid), fetch="none")

    # 4. 维度变更
    if ability_level:
        query(
            "INSERT INTO dimension_changes (novel_id, chapter_id, dimension, change_type, "
            "entity_name, after_value, description) VALUES (%s,%s,'ability','update','主角',%s,'等级变更')",
            (ch["novel_id"], chapter_id, json.dumps({"level": ability_level})),
            fetch="none"
        )
    if location:
        query(
            "INSERT INTO dimension_changes (novel_id, chapter_id, dimension, change_type, "
            "entity_name, after_value, description) VALUES (%s,%s,'space','move','主角',%s,'位置变更')",
            (ch["novel_id"], chapter_id, json.dumps({"location": location})),
            fetch="none"
        )

    # 5. 时间线事件
    for evt in (timeline_events or []):
        if isinstance(evt, dict) and evt.get("event_description"):
            query(
                "INSERT INTO timeline_events (novel_id, chapter_id, event_time, event_order, "
                "event_description, characters_involved) VALUES (%s,%s,%s,%s,%s,%s)",
                (ch["novel_id"], chapter_id,
                 evt.get("event_time", ""), evt.get("event_order", 0),
                 evt["event_description"], evt.get("characters_involved", [])),
                fetch="none"
            )

    # 6. 存储质量数据
    stats = validation["stats"]
    query(
        "INSERT INTO chapter_quality (chapter_id, novel_id, "
        "em_dash_count, ellipsis_count, semicolon_count, exclamation_count, wave_count, "
        "negation_count, word_count, long_paragraphs, avg_punct_types_per_para, "
        "dialogue_breaks, banned_patterns, violations, passed) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
        "ON CONFLICT (chapter_id) DO UPDATE SET "
        "em_dash_count=%s, ellipsis_count=%s, semicolon_count=%s, exclamation_count=%s, wave_count=%s, "
        "negation_count=%s, word_count=%s, long_paragraphs=%s, avg_punct_types_per_para=%s, "
        "dialogue_breaks=%s, banned_patterns=%s, violations=%s, passed=%s",
        (chapter_id, ch["novel_id"],
         stats["em_dash_count"], stats["ellipsis_count"], stats["semicolon_count"],
         stats["exclamation_count"], stats["wave_count"],
         stats["negation_count"], stats["word_count"], stats["long_paragraphs"],
         stats["avg_punct_types_per_para"], stats["dialogue_breaks"],
         stats["banned_patterns"], json.dumps(validation["violations"]), validation["passed"],
         # ON CONFLICT update values
         stats["em_dash_count"], stats["ellipsis_count"], stats["semicolon_count"],
         stats["exclamation_count"], stats["wave_count"],
         stats["negation_count"], stats["word_count"], stats["long_paragraphs"],
         stats["avg_punct_types_per_para"], stats["dialogue_breaks"],
         stats["banned_patterns"], json.dumps(validation["violations"]), validation["passed"]),
        fetch="none"
    )

    return json.dumps({
        "ok": True,
        "updated": ["summary", "status", "foreshadows", "dimensions", "timeline", "quality"],
        "quality": {"passed": True, "stats": stats},
        "warnings": validation.get("warnings", []),
        "post_save_checklist": {
            "新地点": "本章是否出现了新地点？→ record_new_content(novel_name, 'location', '地名', json_data)",
            "新NPC": "本章是否出现了新NPC？→ record_new_content(novel_name, 'npc', '人名', json_data)",
            "新物品": "本章是否出现了新物品？→ record_new_content(novel_name, 'item', '物品名', json_data)",
            "新设定": "本章是否有新增世界观设定？→ record_new_content(novel_name, 'setting', '设定名', json_data)",
            "新伏笔": "本章是否埋了新伏笔？→ foreshadow_plant(novel_name=\"这次不一样了\", '描述', importance, tags)",
            "角色变化": "本章是否有角色状态变化？→ character_update(novel_name, character_name, status=...)",
            "线索追踪": "本章是否有新线索出现？→ 记录到设定/大纲/线索追踪.md"
        }
    }, ensure_ascii=False)


@mcp.tool
def health_check(novel_name: str) -> str:
    """一键健康诊断：伏笔积压+配角活跃+升级节奏+日常密度+暗线推进+卷完成度
      novel_name: 小说名称
    """
    novel_id = _resolve_novel_id(novel_name)

    result = {}

    # 基本信息
    novel = query("SELECT * FROM novels WHERE id = %s", (novel_id,), fetch="one")
    if not novel:
        return json.dumps({"error": "novel not found"}, ensure_ascii=False)

    chapters = query("SELECT id, number, status, chapter_type, volume_id FROM chapters "
                     "WHERE novel_id = %s ORDER BY number", (novel_id,))
    total_chapters = len(chapters)
    written = [c for c in chapters if c["status"] == "written"]
    result["progress"] = {"total": total_chapters, "written": len(written)}

    # 伏笔积压
    planted = query("SELECT id, description, planted_chapter_id, importance FROM foreshadows "
                    "WHERE novel_id = %s AND status = 'planted' ORDER BY id", (novel_id,))
    recalled = query("SELECT COUNT(*) as cnt FROM foreshadows "
                     "WHERE novel_id = %s AND status = 'recalled'", (novel_id,), fetch="val")
    total_foreshadows = len(planted) + (recalled or 0)
    recall_rate = (recalled or 0) / total_foreshadows if total_foreshadows > 0 else 1.0

    planted_list = [dict(f) for f in planted]
    if written:
        latest_num = max(c["number"] for c in written)
        for f in planted_list:
            planted_ch = query("SELECT number FROM chapters WHERE id = %s",
                              (f["planted_chapter_id"],), fetch="one")
            if planted_ch:
                f["age_chapters"] = latest_num - planted_ch["number"]
    result["foreshadow"] = {
        "planted": len(planted), "recalled": recalled or 0,
        "recall_rate": round(recall_rate, 2),
        "oldest_planted": max((f.get("age_chapters", 0) for f in planted_list), default=0),
        "warning": recall_rate < 0.5 and len(planted) > 0
    }

    # 配角活跃
    chars = query("SELECT id, name, role FROM characters "
                  "WHERE novel_id = %s AND is_active = TRUE AND role != 'protagonist'", (novel_id,))
    core_chars = [c for c in chars if c["role"] in ("ally", "rival", "mentor", "love_interest")]
    char_activity = []
    for cc in core_chars:
        recent = query(
            "SELECT cs.chapter_id FROM chapter_summaries cs "
            "JOIN chapters ch ON cs.chapter_id = ch.id "
            "WHERE ch.novel_id = %s AND %s = ANY(cs.characters_involved) "
            "ORDER BY ch.number DESC LIMIT 1",
            (novel_id, cc["id"])
        )
        last_ch = None
        if recent and written:
            ch_num = query("SELECT number FROM chapters WHERE id = %s",
                           (recent[0]["chapter_id"],), fetch="val")
            if ch_num:
                last_ch = ch_num
                latest_num = max(c["number"] for c in written)
                gap = latest_num - ch_num
            else:
                gap = None
        else:
            gap = None
        char_activity.append({"name": cc["name"], "role": cc["role"],
                              "last_chapter": last_ch, "gap": gap,
                              "warning": gap is not None and gap > 10})
    result["character_activity"] = char_activity

    # 升级节奏
    ability_changes = query(
        "SELECT dc.after_value, c.number FROM dimension_changes dc "
        "JOIN chapters c ON dc.chapter_id = c.id "
        "WHERE dc.novel_id = %s AND dc.dimension = 'ability' ORDER BY c.number",
        (novel_id,)
    )
    result["ability_progression"] = [dict(r) for r in ability_changes]

    # 卷完成度
    volumes = query(
        "SELECT v.*, "
        "(SELECT COUNT(*) FROM chapters WHERE volume_id = v.id AND status = 'written') as written_count, "
        "(SELECT COUNT(*) FROM chapters WHERE volume_id = v.id) as total_count "
        "FROM volumes v WHERE v.novel_id = %s ORDER BY v.number",
        (novel_id,)
    )
    result["volumes"] = [dict(v) for v in volumes]

    # 综合诊断
    warnings = []
    if result["foreshadow"]["warning"]:
        warnings.append(f"伏笔积压：回收率仅{recall_rate:.0%}，最老伏笔已过{result['foreshadow']['oldest_planted']}章")
    inactive = [c for c in char_activity if c.get("warning")]
    if inactive:
        warnings.append(f"配角遗忘：{', '.join(c['name'] for c in inactive)}超过10章未出场")
    if len(ability_changes) == 0 and total_chapters > 20:
        warnings.append("未记录任何能力等级变更，建议在writing_finish中传入ability_level")
    result["warnings"] = warnings
    result["healthy"] = len(warnings) == 0

    return json.dumps(result, ensure_ascii=False, default=str)



# ─── Skill Loader ────────────────────────────────────────

_SKILL_BASE_PATH = "/Users/ganjie/code/personal/bywork/books_creater/.claude/skills"

# 单次会话内缓存
_SKILL_LOADER_CACHE: dict = {}


def _resolve_skill_path(skill: str, level: str, resource: str, project: str = None) -> list:
    """按优先级生成待查找路径列表（从高到低）。"""
    paths = []
    # 1. 项目专属覆盖
    if project:
        paths.append(os.path.join(_SKILL_BASE_PATH, skill, "overrides", project, f"{level}s", f"{resource}.md"))
    # 2. skill 专属
    paths.append(os.path.join(_SKILL_BASE_PATH, skill, f"{level}s", f"{resource}.md"))
    # 3. 全局共享
    paths.append(os.path.join(_SKILL_BASE_PATH, f"{level}s", f"{resource}.md"))
    return paths


def _load_skill_file(skill: str, level: str, resource: str, project: str = None) -> dict:
    """按三级优先级加载文件，返回 {"content": str, "path": str, "source": str} 或 {"error": str, "paths_checked": list}。"""
    paths = _resolve_skill_path(skill, level, resource, project)
    checked = []

    for p in paths:
        checked.append(p)
        if not os.path.exists(p):
            continue
        if not os.path.isfile(p):
            continue
        # 权限检查（可读）
        if not os.access(p, os.R_OK):
            return {"error": "PERMISSION_DENIED", "path": p}
        try:
            with open(p, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            return {"error": "PERMISSION_DENIED", "path": p, "detail": str(e)}
        if not content.strip():
            return {"error": "EMPTY_FILE", "path": p}

        # 确定 source 标签
        if project and p.startswith(os.path.join(_SKILL_BASE_PATH, skill, "overrides", project)):
            source = f"project:{project}"
        elif p.startswith(os.path.join(_SKILL_BASE_PATH, skill)):
            source = f"skill:{skill}"
        else:
            source = "global"

        return {"content": content, "path": p, "source": source}

    return {"error": "NOT_FOUND", "paths_checked": checked}


@mcp.tool
def skill_loader(skill: str, level: str, resource: str, project: str = "") -> str:
    """渐进式加载协议：按需加载 skill 子文件。三级优先级：project overrides > skill专属 > 全局共享。

    参数:
      skill: skill名称，如 "novel-planner"
      level: 加载层级，如 "phase" | "engine" | "example" | "agent"
      resource: 资源名，如 "b1-volume" | "environment" | "dialogue"
      project: 项目专属覆盖名，如 "这次不一样了"（可选）

    用法示例:
      skill_loader("novel-planner", "phase", "b1-volume")
      skill_loader("novel-chapter-writer", "engine", "environment", "这次不一样了")
      skill_loader("novel-chapter-writer", "example", "dialogue")
      skill_loader("novel-planner", "agent", "event-architect")
    """
    cache_key = f"{skill}:{level}:{resource}:{project or ''}"

    # 检查缓存
    if cache_key in _SKILL_LOADER_CACHE:
        cached = _SKILL_LOADER_CACHE[cache_key]
        return json.dumps({
            "content": cached["content"],
            "path": cached["path"],
            "source": cached["source"],
            "cached": True
        }, ensure_ascii=False)

    result = _load_skill_file(skill, level, resource, project if project else None)

    if "error" in result:
        return json.dumps(result, ensure_ascii=False)

    # 写入缓存
    _SKILL_LOADER_CACHE[cache_key] = {
        "content": result["content"],
        "path": result["path"],
        "source": result["source"]
    }

    return json.dumps({
        "content": result["content"],
        "path": result["path"],
        "source": result["source"],
        "cached": False
    }, ensure_ascii=False)
# ─── Sync Tools ──────────────────────────────────

_NOVELS_BASE = os.path.join(PROJECT_ROOT, "novels")


def _ensure_data_hashes_table():
    query("""
        CREATE TABLE IF NOT EXISTS data_hashes (
            id SERIAL PRIMARY KEY,
            novel_id INTEGER NOT NULL,
            data_type TEXT NOT NULL,
            data_key TEXT NOT NULL,
            db_hash TEXT NOT NULL DEFAULT '',
            file_hash TEXT NOT NULL DEFAULT '',
            db_updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
            file_updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
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




def _resolve_novel_id(novel_name_or_id) -> int:
    """接受 novel_name(str) 或 novel_id(int)，返回 novel_id。"""
    if isinstance(novel_name_or_id, int):
        return novel_name_or_id
    try:
        nid = int(novel_name_or_id)
        return nid
    except (ValueError, TypeError):
        pass
    r = query("SELECT id FROM novels WHERE name = %s", (novel_name_or_id,), fetch="one")
    if not r:
        raise ValueError(f"小说 '{novel_name_or_id}' 不存在于数据库中")
    return r["id"]

def _resolve_chapter_id(novel_name: str, chapter_number: int) -> int:
    novel_id = _resolve_novel_id(novel_name)
    r = query("SELECT id FROM chapters WHERE novel_id = %s AND number = %s",
              (novel_id, chapter_number), fetch="one")
    if not r:
        raise ValueError(f"章节 {chapter_number} 不存在于小说 '{novel_name}' 中")
    return r["id"]

def _get_novel_name(novel_id: int) -> str:
    r = query("SELECT name FROM novels WHERE id = %s", (novel_id,), fetch="one")
    return r["name"] if r else ""


def _sync_world_to_file(novel_id: int, novel_name: str, category: str, name: str, data: dict):
    """将 DB 中的世界观条目同步到 MD 文件（新模板格式：## category: name）"""
    base = os.path.join(_NOVELS_BASE, novel_name, "设定", "世界观")
    os.makedirs(base, exist_ok=True)

    category_file_map = {
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
    target_file = category_file_map.get(category, f"{category}.md")
    fpath = os.path.join(base, target_file)

    meta = {k: v for k, v in data.items() if k != "content"}
    lines = [f"\n## {category}: {name}\n"]
    for key, val in meta.items():
        if isinstance(val, (list, dict)):
            val_str = json.dumps(val, ensure_ascii=False)
        else:
            val_str = str(val)
        lines.append(f"- **{key}**: {val_str}")
    if data.get("content"):
        lines.append("")
        lines.append(data["content"])
    entry_text = "\n".join(lines) + "\n"

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
    base = os.path.join(_NOVELS_BASE, novel_name, "设定", "人物")
    os.makedirs(base, exist_ok=True)
    fpath = os.path.join(base, f"{char['name']}.md")
    lines = [f"# {char['name']}\n"]
    for k, v in char.items():
        if k in ("id", "novel_id", "created_at", "updated_at"):
            continue
        if v and v != "{}" and v != "[]" and v != "":
            lines.append(f"- **{k}**: {v}")
    content = "\n".join(lines) + "\n"
    with open(fpath, "w", encoding="utf-8") as f:
        f.write(content)
    _record_file_hash(novel_id, "character", char["name"], content)


def _sync_foreshadow_to_file(novel_id: int, novel_name: str, fs: dict):
    base = os.path.join(_NOVELS_BASE, novel_name, "设定", "大纲")
    os.makedirs(base, exist_ok=True)
    fpath = os.path.join(base, "伏笔清单.md")
    entry = f"- [{fs['status']}] {fs['description']} (id:{fs['id']}"
    if fs.get("planned_recall_chapter"):
        entry += f", 计划回收:Ch{fs['planned_recall_chapter']}"
    entry += ")\n"
    if os.path.exists(fpath):
        with open(fpath, "r", encoding="utf-8") as f:
            content = f.read()
        marker = f"(id:{fs['id']}"
        if marker in content:
            start = content.index(marker)
            line_start = content.rfind("\n- ", 0, start) + 1
            line_end = content.find("\n", start)
            content = content[:line_start] + entry + content[line_end:]
        else:
            content += entry
    else:
        content = f"# 伏笔清单\n{entry}"
    with open(fpath, "w", encoding="utf-8") as f:
        f.write(content)
    _record_file_hash(novel_id, "foreshadow", str(fs["id"]), content)


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


@mcp.tool
def sync_startup(novel_name: str, data_type: str = "") -> str:
    """启动时双向对比DB与文件状态，检测冲突，返回差异报告供用户确认。
    新数据流：skill→DB直接操作，文件为可选副本。启动时对比两端，冲突默认以DB为准。
    参数:
      novel_name: 小说名称
      data_type: 校验范围，空=全部，可选: world/character/foreshadow/volume/chapter
    返回:
      差异报告，含: db_only(DB有文件无), file_only(文件有DB无), conflict(两端都有但不同)
      每个冲突项标记默认解决方案(以DB为准)
    用法:
      sync_startup(novel_name="这次不一样了")
      sync_startup(novel_name="这次不一样了", data_type="world")
    """
    novel_id = _resolve_novel_id(novel_name)
    _ensure_data_hashes_table()
    results = {
        "db_only": [],
        "file_only": [],
        "conflict": [],
        "consistent": [],
        "summary": {}
    }
    types_to_check = [data_type] if data_type else ["world", "character", "foreshadow", "volume"]

    if "world" in types_to_check:
        db_rows = query(
            "SELECT category, name, data, updated_at FROM world_settings WHERE novel_id = %s",
            (novel_id,)
        )
        db_map = {}
        for row in db_rows:
            key = f"{row['category']}:{row['name']}"
            db_map[key] = row
            db_hash = _compute_hash(_db_row_to_hashable(dict(row)))
            file_path = os.path.join(
                _NOVELS_BASE, novel_name, "设定", "世界观",
                {"core_setting": "核心设定.md", "bestiary": "异灵图鉴.md",
                 "ability": "能力体系.md", "item": "物品装备.md",
                 "economy": "经济体系.md", "daily_life": "日常生活.md",
                 "history": "历史事件.md", "location": "地图.md",
                 "faction": "势力.md", "race": "种族.md"}.get(row["category"], f"{row['category']}.md")
            )
            if os.path.exists(file_path):
                with open(file_path, "r", encoding="utf-8") as f:
                    file_content = f.read()
                marker = f"## {row['category']}: {row['name']}"
                if marker in file_content:
                    file_hash = _compute_hash(file_content)
                    if db_hash != file_hash:
                        results["conflict"].append({
                            "type": "world", "key": key,
                            "db_updated": str(row.get("updated_at", "")),
                            "resolution": "DB→file"
                        })
                    else:
                        results["consistent"].append({"type": "world", "key": key})
                else:
                    results["db_only"].append({"type": "world", "key": key, "note": "DB有但文件中无对应章节"})
            else:
                results["db_only"].append({"type": "world", "key": key, "note": "文件不存在"})
            _record_db_hash(novel_id, "world", key, db_hash)

    if "character" in types_to_check:
        db_rows = query(
            "SELECT id, name, role, race, ability_level, appearance, personality, "
            "speech_style, background, goals, weaknesses, catchphrase, arc_notes, status, updated_at "
            "FROM characters WHERE novel_id = %s AND is_active = TRUE",
            (novel_id,)
        )
        for row in db_rows:
            key = row["name"]
            db_hash = _compute_hash(_db_row_to_hashable(dict(row)))
            file_path = os.path.join(_NOVELS_BASE, novel_name, "设定", "人物", f"{key}.md")
            if os.path.exists(file_path):
                with open(file_path, "r", encoding="utf-8") as f:
                    file_content = f.read()
                file_hash = _compute_hash(file_content)
                if db_hash != file_hash:
                    results["conflict"].append({
                        "type": "character", "key": key,
                        "db_updated": str(row.get("updated_at", "")),
                        "resolution": "DB→file"
                    })
                else:
                    results["consistent"].append({"type": "character", "key": key})
            else:
                results["db_only"].append({"type": "character", "key": key, "note": "文件不存在"})
            _record_db_hash(novel_id, "character", key, db_hash)

    if "foreshadow" in types_to_check:
        db_rows = query(
            "SELECT id, description, status, importance, planned_recall_chapter, updated_at "
            "FROM foreshadows WHERE novel_id = %s",
            (novel_id,)
        )
        for row in db_rows:
            key = str(row["id"])
            db_hash = _compute_hash(_db_row_to_hashable(dict(row)))
            _record_db_hash(novel_id, "foreshadow", key, db_hash)
            results["consistent"].append({"type": "foreshadow", "key": key, "desc": row["description"][:40]})

    if "volume" in types_to_check:
        outline_dir = os.path.join(_NOVELS_BASE, novel_name, "设定", "大纲")
        if os.path.isdir(outline_dir):
            for fname in sorted(os.listdir(outline_dir)):
                if not fname.endswith(".md") or fname in ("伏笔清单.md", "附录.md", "兄妹心结-渐进弧线.md"):
                    continue
                fpath = os.path.join(outline_dir, fname)
                with open(fpath, "r", encoding="utf-8") as f:
                    content = f.read()
                file_hash = _compute_hash(content)
                key = fname.replace(".md", "")
                _record_file_hash(novel_id, "volume", key, content)
                vol_match = re.match(r"V(\d+)", fname)
                if vol_match:
                    vol_num = int(vol_match.group(1))
                    vol = query(
                        "SELECT id, notes, updated_at FROM volumes WHERE novel_id = %s AND number = %s",
                        (novel_id, vol_num), fetch="one"
                    )
                    if vol:
                        db_hash = _compute_hash(str(vol.get("notes", "")))
                        if db_hash != file_hash:
                            results["conflict"].append({
                                "type": "volume", "key": key,
                                "db_updated": str(vol.get("updated_at", "")),
                                "resolution": "file→DB"
                            })
                        else:
                            results["consistent"].append({"type": "volume", "key": key})
                    else:
                        results["file_only"].append({"type": "volume", "key": key, "note": "DB中无此卷记录"})
                else:
                    results["file_only"].append({"type": "volume", "key": key, "note": "非标准卷号"})

    results["summary"] = {
        "novel_id": novel_id,
        "novel_name": novel_name,
        "total_checked": len(results["consistent"]) + len(results["conflict"]) + len(results["db_only"]) + len(results["file_only"]),
        "consistent": len(results["consistent"]),
        "conflict": len(results["conflict"]),
        "db_only": len(results["db_only"]),
        "file_only": len(results["file_only"]),
    }
    return json.dumps(results, ensure_ascii=False, default=str)


@mcp.tool
def sync_db_to_files(novel_name: str, data_type: str = "", overwrite: bool = False) -> str:
    """将DB数据同步到文件（用户主动触发）。skill操作只写DB，用户选择何时同步到文件。
    参数:
      novel_name: 小说名称
      data_type: 同步范围，空=全部，可选: world/character/foreshadow/volume/chapter
      overwrite: True=强制覆盖所有文件，False=只同步有差异的
    用法:
      sync_db_to_files(novel_name="这次不一样了")                    # 同步全部有差异的
      sync_db_to_files(novel_name="这次不一样了", data_type="world")  # 只同步世界观
      sync_db_to_files(novel_name="这次不一样了", overwrite=True)     # 强制全量覆盖
    """
    novel_id = _resolve_novel_id(novel_name)
    results = {"synced": [], "skipped": [], "errors": []}
    types_to_sync = [data_type] if data_type else ["world", "character", "foreshadow", "volume"]

    if "world" in types_to_sync:
        rows = query(
            "SELECT category, name, data FROM world_settings WHERE novel_id = %s",
            (novel_id,)
        )
        for row in rows:
            key = f"{row['category']}:{row['name']}"
            try:
                _sync_world_to_file(novel_id, novel_name, row["category"], row["name"], row["data"])
                results["synced"].append({"type": "world", "key": key, "direction": "DB→file"})
            except Exception as e:
                results["errors"].append({"type": "world", "key": key, "error": str(e)})

    if "character" in types_to_sync:
        rows = query(
            "SELECT id, name, role, race, ability_level, appearance, personality, "
            "speech_style, background, goals, weaknesses, catchphrase, arc_notes, status "
            "FROM characters WHERE novel_id = %s AND is_active = TRUE",
            (novel_id,)
        )
        for row in rows:
            try:
                _sync_character_to_file(novel_id, novel_name, dict(row))
                results["synced"].append({"type": "character", "key": row["name"], "direction": "DB→file"})
            except Exception as e:
                results["errors"].append({"type": "character", "key": row["name"], "error": str(e)})

    if "foreshadow" in types_to_sync:
        rows = query(
            "SELECT id, description, status, importance, planned_recall_chapter FROM foreshadows WHERE novel_id = %s",
            (novel_id,)
        )
        for row in rows:
            try:
                _sync_foreshadow_to_file(novel_id, novel_name, dict(row))
                results["synced"].append({"type": "foreshadow", "key": str(row["id"]), "direction": "DB→file"})
            except Exception as e:
                results["errors"].append({"type": "foreshadow", "key": str(row["id"]), "error": str(e)})

    if "volume" in types_to_sync:
        outline_dir = os.path.join(_NOVELS_BASE, novel_name, "设定", "大纲")
        if os.path.isdir(outline_dir):
            for fname in sorted(os.listdir(outline_dir)):
                if not fname.endswith(".md"):
                    continue
                fpath = os.path.join(outline_dir, fname)
                vol_match = re.match(r"V(\d+)", fname)
                if vol_match:
                    vol_num = int(vol_match.group(1))
                    vol = query(
                        "SELECT id FROM volumes WHERE novel_id = %s AND number = %s",
                        (novel_id, vol_num), fetch="one"
                    )
                    if vol:
                        with open(fpath, "r", encoding="utf-8") as f:
                            content = f.read()
                        query(
                            "UPDATE volumes SET notes = %s, updated_at = NOW() WHERE id = %s",
                            (content[:2000], vol["id"]), fetch="none"
                        )
                        results["synced"].append({"type": "volume", "key": fname.replace(".md", ""), "direction": "file→DB"})

    summary = {
        "novel_id": novel_id,
        "novel_name": novel_name,
        "synced_count": len(results["synced"]),
        "skipped_count": len(results["skipped"]),
        "error_count": len(results["errors"]),
        "synced": results["synced"],
        "errors": results["errors"],
    }
    return json.dumps(summary, ensure_ascii=False, default=str)



# ─── Character State Snapshot & Plot Thread Tools ───────────
def _character_snapshot_by_id(character_id: int, chapter_id: int,
                       location: str = "", arc_phase: str = "",
                       emotional_state: str = "", physical_state: str = "",
                       ability_snapshot: str = "[]", inventory_snapshot: str = "[]",
                       knowledge_snapshot: str = "{}", notes: str = "") -> str:
    query(
        "INSERT INTO character_state_snapshots "
        "(character_id, chapter_id, location, arc_phase, emotional_state, physical_state, "
        "ability_snapshot, inventory_snapshot, knowledge_snapshot, notes) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s::jsonb, %s) "
        "ON CONFLICT (character_id, chapter_id) DO UPDATE SET "
        "location=%s, arc_phase=%s, emotional_state=%s, physical_state=%s, "
        "ability_snapshot=%s::jsonb, inventory_snapshot=%s::jsonb, knowledge_snapshot=%s::jsonb, notes=%s",
        (character_id, chapter_id, location, arc_phase, emotional_state, physical_state,
         ability_snapshot, inventory_snapshot, knowledge_snapshot, notes,
         location, arc_phase, emotional_state, physical_state,
         ability_snapshot, inventory_snapshot, knowledge_snapshot, notes),
        fetch="none"
    )
    return json.dumps({"ok": True, "character_id": character_id, "chapter_id": chapter_id}, ensure_ascii=False)


def _character_get_state_by_id(character_id: int, chapter_id: int = 0) -> str:
    if chapter_id == 0:
        r = query(
            "SELECT css.*, c.number as chapter_number FROM character_state_snapshots css "
            "JOIN chapters c ON css.chapter_id = c.id "
            "WHERE css.character_id = %s ORDER BY c.number DESC LIMIT 1",
            (character_id,), fetch="one"
        )
    else:
        r = query(
            "SELECT * FROM character_state_snapshots "
            "WHERE character_id = %s AND chapter_id = %s",
            (character_id, chapter_id), fetch="one"
        )
    if not r:
        char = query("SELECT name FROM characters WHERE id = %s", (character_id,), fetch="one")
        name = char["name"] if char else "Unknown"
        return json.dumps({"error": f"No snapshot for {name}", "character_id": character_id}, ensure_ascii=False)
    return json.dumps(dict(r), ensure_ascii=False, default=str)


def _relation_snapshot_by_id(relation_id: int, chapter_id: int,
                      intensity: int = 5, status: str = "active",
                      notes: str = "") -> str:
    query(
        "INSERT INTO relation_state_snapshots "
        "(relation_id, chapter_id, intensity, status, notes) "
        "VALUES (%s, %s, %s, %s, %s) "
        "ON CONFLICT (relation_id, chapter_id) DO UPDATE SET "
        "intensity=%s, status=%s, notes=%s",
        (relation_id, chapter_id, intensity, status, notes,
         intensity, status, notes),
        fetch="none"
    )
    return json.dumps({"ok": True, "relation_id": relation_id, "chapter_id": chapter_id}, ensure_ascii=False)


def _relation_get_state_by_id(relation_id: int, chapter_id: int = 0) -> str:
    if chapter_id == 0:
        r = query(
            "SELECT rss.*, c.number as chapter_number FROM relation_state_snapshots rss "
            "JOIN chapters c ON rss.chapter_id = c.id "
            "WHERE rss.relation_id = %s ORDER BY c.number DESC LIMIT 1",
            (relation_id,), fetch="one"
        )
    else:
        r = query(
            "SELECT * FROM relation_state_snapshots "
            "WHERE relation_id = %s AND chapter_id = %s",
            (relation_id, chapter_id), fetch="one"
        )
    if not r:
        return json.dumps({"error": "No snapshot", "relation_id": relation_id}, ensure_ascii=False)
    return json.dumps(dict(r), ensure_ascii=False, default=str)


@mcp.tool
def plot_thread_create(novel_name: str, name: str,
                        thread_type: str = "mainline",
                        description: str = "",
                        start_chapter_id: int = 0,
                        volume_scope: str = "[]",
                        related_characters: str = "[]",
                        related_foreshadows: str = "[]") -> str:
    """创建线索/暗线。thread_type: mainline/subplot/darkline/mystery/clue

    参数:
      novel_name: 小说名称
      name: 线索名称
      thread_type: mainline/subplot/darkline/mystery/clue
      description: 描述
      start_chapter_id: 起始章节ID
      volume_scope: 涉及卷号(JSON数组)
      related_characters: 关联角色(JSON数组)
      related_foreshadows: 关联伏笔ID(JSON数组)
    """
    novel_id = _resolve_novel_id(novel_name)

    r = query(
        "INSERT INTO plot_threads "
        "(novel_id, name, thread_type, description, start_chapter_id, "
        "volume_scope, related_characters, related_foreshadows) "
        "VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s::jsonb) "
        "ON CONFLICT (novel_id, name) DO UPDATE SET "
        "thread_type=%s, description=%s, start_chapter_id=%s, "
        "volume_scope=%s::jsonb, related_characters=%s::jsonb, related_foreshadows=%s::jsonb, updated_at=NOW() "
        "RETURNING id",
        (novel_id, name, thread_type, description, start_chapter_id or None,
         volume_scope, related_characters, related_foreshadows,
         thread_type, description, start_chapter_id or None,
         volume_scope, related_characters, related_foreshadows),
        fetch="one"
    )
    return json.dumps({"ok": True, "id": r["id"], "name": name}, ensure_ascii=False)


@mcp.tool
def plot_thread_list(novel_name: str, thread_type: str = "") -> str:
    """列出线索/暗线。thread_type可选过滤。
      novel_name: 小说名称
    """
    novel_id = _resolve_novel_id(novel_name)
    if thread_type:
        rows = query(
            "SELECT * FROM plot_threads WHERE novel_id = %s AND thread_type = %s ORDER BY id",
            (novel_id, thread_type)
        )
    else:
        rows = query("SELECT * FROM plot_threads WHERE novel_id = %s ORDER BY id", (novel_id,))
    return json.dumps([dict(r) for r in rows], ensure_ascii=False, default=str)
@mcp.tool
def plot_thread_update(novel_name: str, thread_id: int, status: str = "",
                       end_chapter_number: int = 0,
                       progress_notes: str = "[]") -> str:
    """更新线索/暗线状态。每卷结束时调用。

    参数:
      novel_name: 小说名称
      thread_id: 线索ID
      status: active/resolved/dormant/abandoned
      end_chapter_number: 结束章节序号
      progress_notes: 进展备注(JSON数组，追加)
    """
    novel_id = _resolve_novel_id(novel_name)
    t = query("SELECT id FROM plot_threads WHERE id = %s AND novel_id = %s",
              (thread_id, novel_id), fetch="one")
    if not t:
        return json.dumps({"ok": False, "error": f"thread {thread_id} not found in novel '{novel_name}'"}, ensure_ascii=False)
    sets = []
    vals = []
    if status:
        sets.append("status = %s")
        vals.append(status)
    if end_chapter_number:
        end_chapter_id = _resolve_chapter_id(novel_name, end_chapter_number)
        sets.append("end_chapter_id = %s")
        vals.append(end_chapter_id)
    if progress_notes and progress_notes != "[]":
        sets.append("progress_notes = progress_notes || %s::jsonb")
        vals.append(progress_notes)
    if not sets:
        return json.dumps({"ok": False, "error": "Nothing to update"}, ensure_ascii=False)
    sets.append("updated_at = NOW()")
    vals.append(thread_id)
    query(f"UPDATE plot_threads SET {', '.join(sets)} WHERE id = %s", tuple(vals), fetch="none")
    return json.dumps({"ok": True, "thread_id": thread_id}, ensure_ascii=False)


@mcp.tool
def character_get(novel_name: str, character_name: str) -> str:
    """按角色名获取人物详情（无需ID）。
      novel_name: 小说名称
      character_name: 角色名
    """
    novel_id = _resolve_novel_id(novel_name)
    char = query("SELECT id FROM characters WHERE novel_id=%s AND name=%s", (novel_id, character_name), fetch="one")
    if not char:
        return json.dumps({"error": f"角色 '{character_name}' 不存在"}, ensure_ascii=False)
    return _character_get_by_id(char["id"])


@mcp.tool
def character_detail(novel_name: str, character_name: str, chapter_number: int = None) -> str:
    """按角色名获取角色蒸馏卡片（无需ID）。
      novel_name: 小说名称
      character_name: 角色名
      chapter_number: 章节序号（可选，用于获取该章状态快照）
    """
    novel_id = _resolve_novel_id(novel_name)
    char = query("SELECT id FROM characters WHERE novel_id=%s AND name=%s", (novel_id, character_name), fetch="one")
    if not char:
        return json.dumps({"error": f"角色 '{character_name}' 不存在"}, ensure_ascii=False)
    return _character_detail_by_id(char["id"], chapter_number)


@mcp.tool
def character_update(novel_name: str, character_name: str, name: str = "", role: str = "", faction_id: int = 0,
                             race: str = "", ability_level: str = "", status: str = "",
                             appearance: str = "", personality: str = "", background: str = "",
                             goals: str = "", weaknesses: str = "", speech_style: str = "",
                             catchphrase: str = "", arc_notes: str = "", is_active: bool = True,
                             _status_json: str = "",
                             appearance_detail: str = "", decision_engine: str = "",
                             voice_fingerprint: str = "", ability_system: str = "",
                             behavior_pattern: str = "", current_snapshot: str = "",
                             growth_trajectory: str = "") -> str:
    """按角色名更新人物信息（无需ID）。传入需要修改的字段，空值/零值会被忽略。
      novel_name: 小说名称
      character_name: 角色名
    """
    novel_id = _resolve_novel_id(novel_name)
    char = query("SELECT id FROM characters WHERE novel_id=%s AND name=%s", (novel_id, character_name), fetch="one")
    if not char:
        return json.dumps({"error": f"角色 '{character_name}' 不存在"}, ensure_ascii=False)
    return _character_update_by_id(char["id"], name, role, faction_id, race, ability_level, status,
                            appearance, personality, background, goals, weaknesses, speech_style,
                            catchphrase, arc_notes, is_active, _status_json,
                            appearance_detail, decision_engine, voice_fingerprint, ability_system,
                            behavior_pattern, current_snapshot, growth_trajectory)


@mcp.tool
def volume_get(novel_name: str, number: int) -> str:
    """按卷号获取卷详情（无需volume_id）。
      novel_name: 小说名称
      number: 卷号（如1, 2, 3）
    """
    novel_id = _resolve_novel_id(novel_name)
    vol = query("SELECT id FROM volumes WHERE novel_id=%s AND number=%s", (novel_id, number), fetch="one")
    if not vol:
        return json.dumps({"error": f"卷 {number} 不存在"}, ensure_ascii=False)
    return _volume_get_by_id(vol["id"])


@mcp.tool
def volume_update(novel_name: str, number: int, title: str = "",
                            main_plotlines: list = None, notes: str = "") -> str:
    """按卷号更新卷信息（无需volume_id）。传入需要修改的字段，空值会被忽略。
      novel_name: 小说名称
      number: 卷号
    """
    novel_id = _resolve_novel_id(novel_name)
    vol = query("SELECT id FROM volumes WHERE novel_id=%s AND number=%s", (novel_id, number), fetch="one")
    if not vol:
        return json.dumps({"error": f"卷 {number} 不存在"}, ensure_ascii=False)
    return _volume_update_by_id(vol["id"], title, main_plotlines, notes)


@mcp.tool
def relation_create(novel_name: str, from_name: str, to_name: str,
                            relation_type: str, description: str = "",
                            chapter_established: int = None, intensity: int = 5) -> str:
    """按角色名创建人物关系（无需角色ID）。
      novel_name: 小说名称
      from_name: 关系发起方角色名
      to_name: 关系接受方角色名
      relation_type: ally/enemy/mentor/lover/family/rival/subordinate
      description: 关系描述
      chapter_established: 建立章节ID
      intensity: 关系强度(1-10)
    """
    novel_id = _resolve_novel_id(novel_name)
    from_char = query("SELECT id FROM characters WHERE novel_id=%s AND name=%s", (novel_id, from_name), fetch="one")
    if not from_char:
        return json.dumps({"error": f"角色 '{from_name}' 不存在"}, ensure_ascii=False)
    to_char = query("SELECT id FROM characters WHERE novel_id=%s AND name=%s", (novel_id, to_name), fetch="one")
    if not to_char:
        return json.dumps({"error": f"角色 '{to_name}' 不存在"}, ensure_ascii=False)
    return _relation_create_by_id(novel_name, from_char["id"], to_char["id"], relation_type, description, chapter_established, intensity)


@mcp.tool
def character_snapshot(novel_name: str, character_name: str, chapter_number: int,
                                location: str = "", arc_phase: str = "",
                                emotional_state: str = "", physical_state: str = "",
                                ability_snapshot: str = "[]", inventory_snapshot: str = "[]",
                                knowledge_snapshot: str = "{}", notes: str = "") -> str:
    """按角色名+章节号保存快照（无需查ID）。每章写完后调用。

    参数:
      novel_name: 小说名称
      character_name: 角色名
      chapter_number: 章节序号（如1, 2, 15）
      location: 当前位置
      arc_phase: 弧线阶段
      emotional_state: 情绪状态
      physical_state: 身体状态
      ability_snapshot: 能力快照(JSON)
      inventory_snapshot: 物品快照(JSON)
      knowledge_snapshot: 知识快照(JSON)
      notes: 备注
    """
    novel_id = _resolve_novel_id(novel_name)

    char = query("SELECT id FROM characters WHERE novel_id=%s AND name=%s", (novel_id, character_name), fetch="one")
    if not char:
        return json.dumps({"error": f"角色 '{character_name}' 不存在"}, ensure_ascii=False)
    ch = query("SELECT id FROM chapters WHERE novel_id=%s AND number=%s", (novel_id, chapter_number), fetch="one")
    if not ch:
        return json.dumps({"error": f"章节 {chapter_number} 不存在"}, ensure_ascii=False)
    return _character_snapshot_by_id(char["id"], ch["id"], location, arc_phase, emotional_state,
                             physical_state, ability_snapshot, inventory_snapshot, knowledge_snapshot, notes)


@mcp.tool
def character_get_latest(novel_name: str, character_name: str) -> str:
    """获取角色最新状态快照（按名称查询，无需ID）。

    参数:
      novel_name: 小说名称
      character_name: 角色名
    """
    novel_id = _resolve_novel_id(novel_name)

    char = query("SELECT id FROM characters WHERE novel_id=%s AND name=%s", (novel_id, character_name), fetch="one")
    if not char:
        return json.dumps({"error": f"角色 '{character_name}' 不存在"}, ensure_ascii=False)
    r = query(
        "SELECT css.*, c.number as chapter_number FROM character_state_snapshots css "
        "JOIN chapters c ON css.chapter_id = c.id "
        "WHERE css.character_id = %s ORDER BY c.number DESC LIMIT 1",
        (char["id"],), fetch="one"
    )
    if not r:
        return json.dumps({"error": f"'{character_name}' 暂无快照", "character_name": character_name}, ensure_ascii=False)
    result = dict(r)
    result["character_name"] = character_name
    return json.dumps(result, ensure_ascii=False, default=str)


@mcp.tool
def relation_snapshot(novel_name: str, from_name: str, to_name: str, chapter_number: int,
                              intensity: int = 5, status: str = "active", notes: str = "") -> str:
    """按角色名保存关系快照（无需查ID）。关系变化时调用。

    参数:
      novel_name: 小说名称
      from_name: 关系发起方角色名
      to_name: 关系接受方角色名
      chapter_number: 章节序号
      intensity: 关系强度(1-10)
      status: 关系状态(active/broken/evolved/hidden)
      notes: 备注
    """
    novel_id = _resolve_novel_id(novel_name)

    rel = query(
        "SELECT cr.id FROM character_relations cr "
        "JOIN characters c1 ON cr.from_character_id=c1.id "
        "JOIN characters c2 ON cr.to_character_id=c2.id "
        "WHERE cr.novel_id=%s AND c1.name=%s AND c2.name=%s",
        (novel_id, from_name, to_name), fetch="one"
    )
    if not rel:
        return json.dumps({"error": f"关系 '{from_name}'→'{to_name}' 不存在"}, ensure_ascii=False)
    ch = query("SELECT id FROM chapters WHERE novel_id=%s AND number=%s", (novel_id, chapter_number), fetch="one")
    if not ch:
        return json.dumps({"error": f"章节 {chapter_number} 不存在"}, ensure_ascii=False)
    return _relation_snapshot_by_id(rel["id"], ch["id"], intensity, status, notes)


@mcp.tool
def get_chapter_context(novel_name: str, chapter_number: int) -> str:
    """获取写某章所需的全部上下文（聚合查询，一次调用替代10+单独调用）。
    返回:
    - 章节信息 + 卷级大纲 + 前N章摘要
    - 出场角色深度信息（外观/性格/说话风格/能力/状态/关系）
    - 未回收伏笔 + 活跃线索
    - 世界观全分类数据（location/faction/ability/economy/daily_life/race/history）
    - 人物关系
    - 时间线（前3章）
    - 质量历史
    - 写作提示词（含规则+作者DNA）
    参数:
      novel_name: 小说名称
      chapter_number: 章节序号
    """
    novel_id = _resolve_novel_id(novel_name)
    result = {"chapter_number": chapter_number}
    ch = query("SELECT * FROM chapters WHERE novel_id=%s AND number=%s", (novel_id, chapter_number), fetch="one")
    if not ch:
        return json.dumps({"error": f"章节 {chapter_number} 不存在"}, ensure_ascii=False)
    result["chapter"] = dict(ch)
    if ch.get("volume_id"):
        vol = query("SELECT * FROM volumes WHERE id=%s", (ch["volume_id"],), fetch="one")
        if vol:
            result["volume"] = {"number": vol["number"], "title": vol["title"], "main_plotlines": vol["main_plotlines"], "notes": vol.get("notes", "")}
    prev_summaries = query(
        "SELECT cs.*, c.number FROM chapter_summaries cs "
        "JOIN chapters c ON cs.chapter_id=c.id "
        "WHERE c.novel_id=%s AND c.number < %s ORDER BY c.number DESC LIMIT 3",
        (novel_id, chapter_number)
    )
    result["prev_summaries"] = [dict(r) for r in prev_summaries]
    foreshadows = query(
        "SELECT * FROM foreshadows WHERE novel_id=%s AND status='planted' ORDER BY importance, id",
        (novel_id,)
    )
    result["unresolved_foreshadows"] = [dict(r) for r in foreshadows]
    threads = query("SELECT * FROM plot_threads WHERE novel_id=%s AND status='active'", (novel_id,))
    result["active_threads"] = [dict(r) for r in threads]
    all_chars = query("SELECT * FROM characters WHERE novel_id=%s AND is_active=TRUE", (novel_id,))
    char_details = []
    for c in all_chars:
        cd = dict(c)
        rels = query(
            "SELECT cr.relation_type, cr.description, cr.intensity, cr.status, "
            "c1.name as from_name, c2.name as to_name "
            "FROM character_relations cr "
            "JOIN characters c1 ON cr.from_character_id=c1.id "
            "JOIN characters c2 ON cr.to_character_id=c2.id "
            "WHERE cr.novel_id=%s AND (c1.id=%s OR c2.id=%s)",
            (novel_id, c["id"], c["id"])
        )
        cd["relations"] = [dict(r) for r in rels]
        snap = query(
            "SELECT css.* FROM character_state_snapshots css "
            "JOIN chapters ch2 ON css.chapter_id=ch2.id "
            "WHERE css.character_id=%s ORDER BY ch2.number DESC LIMIT 1",
            (c["id"],), fetch="one"
        )
        if snap:
            cd["latest_snapshot"] = dict(snap)
        char_details.append(cd)
    result["character_details"] = char_details
    relations = query(
        "SELECT cr.relation_type, cr.description, cr.intensity, cr.status, "
        "c1.name as from_name, c2.name as to_name "
        "FROM character_relations cr "
        "JOIN characters c1 ON cr.from_character_id=c1.id "
        "JOIN characters c2 ON cr.to_character_id=c2.id "
        "WHERE cr.novel_id=%s",
        (novel_id,)
    )
    result["relations"] = [dict(r) for r in relations]
    world_categories = ["location", "faction", "ability", "economy", "daily_life", "race", "history"]
    world_data = {}
    for cat in world_categories:
        rows = query("SELECT name, data FROM world_settings WHERE novel_id=%s AND category=%s", (novel_id, cat))
        if rows:
            world_data[cat] = [{**dict(r)} for r in rows]
    result["world_settings"] = world_data
    timeline = query(
        "SELECT te.*, c.number as chapter_number FROM timeline_events te "
        "JOIN chapters c ON te.chapter_id=c.id "
        "WHERE c.novel_id=%s AND c.number >= %s ORDER BY c.number",
        (novel_id, max(1, chapter_number - 3))
    )
    result["timeline"] = [dict(r) for r in timeline]
    quality_history = _get_quality_history(novel_id, chapter_number)
    result["quality_history"] = quality_history
    result["writing_prompt"] = _build_writing_prompt(
        ch=dict(ch),
        summaries=[dict(r) for r in prev_summaries],
        chars=[{"id": c["id"], "name": c["name"], "role": c["role"]} for c in all_chars],
        foreshadows=[dict(r) for r in foreshadows],
        world_index=[{"category": cat, "name": w["name"]} for cat, items in world_data.items() for w in items],
        vol=result.get("volume", {}),
        quality_history=quality_history,
    )
    return json.dumps(result, ensure_ascii=False, default=str)
@mcp.tool
def foreshadow_abandon(novel_name: str, foreshadow_id: int, reason: str = "") -> str:
    """放弃伏笔（不可逆）。百万字长篇中必然有放弃的伏笔。

    参数:
      novel_name: 小说名称
      foreshadow_id: 伏笔ID
      reason: 放弃原因
    """
    novel_id = _resolve_novel_id(novel_name)

    fs = query("SELECT id FROM foreshadows WHERE id=%s AND novel_id=%s", (foreshadow_id, novel_id), fetch="one")
    if not fs:
        return json.dumps({"error": f"伏笔 {foreshadow_id} 不存在"}, ensure_ascii=False)
    query("UPDATE foreshadows SET status='abandoned', updated_at=NOW() WHERE id=%s", (foreshadow_id,), fetch="none")
    _record_db_hash(novel_id, "foreshadow", str(foreshadow_id), "abandoned")
    return json.dumps({"ok": True, "foreshadow_id": foreshadow_id, "status": "abandoned", "reason": reason}, ensure_ascii=False)


@mcp.tool
def relation_update(novel_name: str, from_name: str, to_name: str,
                    relation_type: str = "", description: str = "",
                    intensity: int = 0, status: str = "") -> str:
    """更新人物关系（增量型）。关系类型/强度/描述/状态均可变更。

    参数:
      novel_name: 小说名称
      from_name: 关系发起方角色名
      to_name: 关系接受方角色名
      relation_type: 新关系类型（空=不变）
      description: 新描述（空=不变）
      intensity: 新强度（0=不变）
      status: 新状态（active/broken/evolved/hidden，空=不变）
    """
    novel_id = _resolve_novel_id(novel_name)

    rel = query(
        "SELECT cr.id, cr.intensity as cur_intensity FROM character_relations cr "
        "JOIN characters c1 ON cr.from_character_id=c1.id "
        "JOIN characters c2 ON cr.to_character_id=c2.id "
        "WHERE cr.novel_id=%s AND c1.name=%s AND c2.name=%s",
        (novel_id, from_name, to_name), fetch="one"
    )
    if not rel:
        return json.dumps({"error": f"关系 '{from_name}'→'{to_name}' 不存在"}, ensure_ascii=False)
    sets = []
    vals = []
    if relation_type:
        sets.append("relation_type = %s")
        vals.append(relation_type)
    if description:
        sets.append("description = %s")
        vals.append(description)
    if intensity > 0:
        old_i = rel["cur_intensity"]
        sets.append("intensity = %s")
        vals.append(intensity)
        sets.append("intensity_change_log = COALESCE(intensity_change_log, '[]'::jsonb) || %s::jsonb")
        vals.append(json.dumps([{"from": old_i, "to": intensity}]))
    if status:
        sets.append("status = %s")
        vals.append(status)
    if not sets:
        return json.dumps({"ok": False, "error": "Nothing to update"}, ensure_ascii=False)
    vals.append(rel["id"])
    query(f"UPDATE character_relations SET {', '.join(sets)} WHERE id = %s", tuple(vals), fetch="none")
    return json.dumps({"ok": True, "from": from_name, "to": to_name}, ensure_ascii=False)


@mcp.tool
def chapter_update_metadata(novel_name: str, chapter_number: int,
                            summary: str = "", key_events: str = "[]",
                            characters_involved: str = "[]",
                            new_foreshadows: str = "[]",
                            resolved_foreshadows: str = "[]") -> str:
    """更新章节元数据（不重新校验正文）。修订后同步DB用。

    参数:
      novel_name: 小说名称
      chapter_number: 章节序号
      summary: 章节摘要
      key_events: 关键事件(JSON数组)
      characters_involved: 参与角色(JSON数组)
      new_foreshadows: 新埋伏笔(JSON数组)
      resolved_foreshadows: 已回收伏笔(JSON数组)
    """
    novel_id = _resolve_novel_id(novel_name)

    ch = query("SELECT id FROM chapters WHERE novel_id=%s AND number=%s", (novel_id, chapter_number), fetch="one")
    if not ch:
        return json.dumps({"error": f"章节 {chapter_number} 不存在"}, ensure_ascii=False)
    existing = query("SELECT chapter_id FROM chapter_summaries WHERE chapter_id=%s", (ch["id"],), fetch="one")
    if existing:
        sets = []
        vals = []
        if summary:
            sets.append("summary = %s")
            vals.append(summary)
        if key_events != "[]":
            sets.append("key_events = %s::jsonb")
            vals.append(key_events)
        if characters_involved != "[]":
            sets.append("characters_involved = %s::jsonb")
            vals.append(characters_involved)
        if new_foreshadows != "[]":
            sets.append("new_foreshadows = %s::jsonb")
            vals.append(new_foreshadows)
        if resolved_foreshadows != "[]":
            sets.append("resolved_foreshadows = %s::jsonb")
            vals.append(resolved_foreshadows)
        if sets:
            vals.append(ch["id"])
            query(f"UPDATE chapter_summaries SET {', '.join(sets)} WHERE chapter_id = %s", tuple(vals), fetch="none")
    else:
        query(
            "INSERT INTO chapter_summaries (chapter_id, summary, key_events, characters_involved, new_foreshadows, resolved_foreshadows) "
            "VALUES (%s, %s, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb)",
            (ch["id"], summary, key_events, characters_involved, new_foreshadows, resolved_foreshadows),
            fetch="none"
        )
    return json.dumps({"ok": True, "chapter_number": chapter_number}, ensure_ascii=False)


@mcp.tool
def chapter_plan_batch(novel_name: str, chapters_json: str = "[]") -> str:
    """批量规划章节（卷级大纲用，一次创建15-20章）。

    参数:
      novel_name: 小说名称
      chapters_json: 章节数组JSON，每项: {"number": 1, "title": "标题", "outline": "大纲", "chapter_type": "normal", "volume_number": 1}
    """
    novel_id = _resolve_novel_id(novel_name)

    chapters = json.loads(chapters_json)
    results = []
    for ch in chapters:
        vol = query("SELECT id FROM volumes WHERE novel_id=%s AND number=%s", (novel_id, ch.get("volume_number", 1)), fetch="one")
        vol_id = vol["id"] if vol else None
        r = query(
            "INSERT INTO chapters (novel_id, number, title, outline, chapter_type, volume_id) "
            "VALUES (%s, %s, %s, %s, %s, %s) "
            "ON CONFLICT (novel_id, number) DO UPDATE SET title=%s, outline=%s, chapter_type=%s, volume_id=%s, updated_at=NOW() "
            "RETURNING id",
            (novel_id, ch["number"], ch.get("title", ""), ch.get("outline", ""), ch.get("chapter_type", "normal"), vol_id,
             ch.get("title", ""), ch.get("outline", ""), ch.get("chapter_type", "normal"), vol_id),
            fetch="one"
        )
        results.append({"number": ch["number"], "id": r["id"]})
    return json.dumps({"ok": True, "created": len(results), "chapters": results}, ensure_ascii=False)


@mcp.tool
def character_increment(novel_name: str, character_name: str,
                        location: str = "", arc_phase: str = "",
                        emotional_state: str = "", physical_state: str = "",
                        ability_add: str = "", inventory_add: str = "",
                        knowledge_add: str = "",
                        snapshot_update: str = "",
                        growth_add: str = "") -> str:
    """角色增量更新（只追加，不覆盖档案）。适用于正文写作中角色状态变化。

    参数:
      novel_name: 小说名称
      character_name: 角色名
      location: 新位置（空=不变）
      arc_phase: 新弧线阶段（空=不变）
      emotional_state: 新情绪（空=不变）
      physical_state: 新身体状态（空=不变）
      ability_add: 新增能力(JSON字符串, 追加到ability_progression)
      inventory_add: 新增物品(JSON字符串, 追加到inventory)
      knowledge_add: 新增知识(JSON字符串, 合并到knowledge_state)
      snapshot_update: 当前快照更新(JSON字符串, 合并到current_snapshot)
      growth_add: 成长轨迹追加(JSON字符串, 追加到growth_trajectory数组)
    """
    novel_id = _resolve_novel_id(novel_name)

    char = query("SELECT id, current_location, current_arc_phase, emotional_state, physical_state, "
                 "ability_progression, inventory, knowledge_state, current_snapshot, growth_trajectory "
                 "FROM characters WHERE novel_id=%s AND name=%s", (novel_id, character_name), fetch="one")
    if not char:
        return json.dumps({"error": f"角色 '{character_name}' 不存在"}, ensure_ascii=False)
    sets = []
    vals = []
    if location:
        sets.append("current_location = %s")
        vals.append(location)
    if arc_phase:
        sets.append("current_arc_phase = %s")
        vals.append(arc_phase)
    if emotional_state:
        sets.append("emotional_state = %s")
        vals.append(emotional_state)
    if physical_state:
        sets.append("physical_state = %s")
        vals.append(physical_state)
    if ability_add:
        sets.append("ability_progression = COALESCE(ability_progression, '[]'::jsonb) || %s::jsonb")
        vals.append(ability_add)
    if inventory_add:
        sets.append("inventory = COALESCE(inventory, '[]'::jsonb) || %s::jsonb")
        vals.append(inventory_add)
    if knowledge_add:
        sets.append("knowledge_state = COALESCE(knowledge_state, '{}'::jsonb) || %s::jsonb")
        vals.append(knowledge_add)
    if snapshot_update:
        sets.append("current_snapshot = COALESCE(current_snapshot, '{}'::jsonb) || %s::jsonb")
        vals.append(snapshot_update)
    if growth_add:
        sets.append("growth_trajectory = COALESCE(growth_trajectory, '[]'::jsonb) || %s::jsonb")
        vals.append(growth_add)
    if not sets:
        return json.dumps({"ok": False, "error": "Nothing to update"}, ensure_ascii=False)
    sets.append("updated_at = NOW()")
    vals.append(char["id"])
    query(f"UPDATE characters SET {', '.join(sets)} WHERE id = %s", tuple(vals), fetch="none")
    return json.dumps({"ok": True, "character_name": character_name, "updated_fields": [s.split("=")[0].strip() for s in sets[:-1]]}, ensure_ascii=False)


@mcp.tool
def world_deactivate(novel_name: str, category: str, name: str, reason: str = "") -> str:
    """世界观元素停用（不可逆型：地点毁灭、势力解散、物品消耗等）。
    参数:
      novel_name: 小说名称
      category: 类别(location/faction/ability/economy等)
      name: 元素名称
      reason: 停用原因
    """
    novel_id = _resolve_novel_id(novel_name)
    ws = query("SELECT id, data FROM world_settings WHERE novel_id=%s AND category=%s AND name=%s",
               (novel_id, category, name), fetch="one")
    if not ws:
        return json.dumps({"error": f"世界元素 '{category}:{name}' 不存在"}, ensure_ascii=False)
    data = ws["data"] if isinstance(ws["data"], dict) else {}
    data["_deactivated"] = True
    data["_deactivation_reason"] = reason
    query("UPDATE world_settings SET status='inactive', data=%s, updated_at=NOW() WHERE id=%s",
          (json.dumps(data, ensure_ascii=False), ws["id"]), fetch="none")
    return json.dumps({"ok": True, "category": category, "name": name, "status": "inactive", "reason": reason}, ensure_ascii=False)


if __name__ == "__main__":
    mcp.run()
