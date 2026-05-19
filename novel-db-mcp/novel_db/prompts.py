import json

from .db import query
from .constraints import _get_constraints


def _build_event_checklist(chapter: dict) -> str:
    outline = chapter.get("outline", "") or ""
    outline = outline.strip()
    if not outline:
        return "（大纲为空，请自行规划本章事件）"
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
    rows = query(
        "SELECT cq.*, ch.number as chapter_number FROM chapter_quality cq "
        "JOIN chapters ch ON cq.chapter_id = ch.id "
        "WHERE ch.novel_id = %s AND ch.number < %s "
        "ORDER BY ch.number DESC LIMIT %s",
        (novel_id, chapter_number, limit)
    )
    return [dict(r) for r in rows]


def _build_rules_prompt() -> str:
    c = _get_constraints()
    lines = []

    hard_pct = c.get("hard_pct", {})
    hard_abs = c.get("hard_abs", {})

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
        core_keys = ["刀锋技法", "质量方差", "废笔配额", "角色失控", "饱和度不均", "留白不点破", "节奏断层"]
        for key in core_keys:
            if key in guidelines:
                rule = guidelines[key]
                rule_text = rule.get("rule", "")
                label = rule.get("label", key)
                short = rule_text.split("。")[0] if "。" in rule_text else rule_text[:60]
                lines.append(f"▸ **{label}**: {short}")
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
                          vol: dict, quality_history: list,
                          echoes: list = None) -> str:
    lines = []
    cn = ch.get("number", "?")

    lines.append(f"# 第{cn}章 · 写作上下文")
    lines.append(f"\n**章节**: 第{cn}章「{ch.get('title','')}」 类型:{ch.get('chapter_type','normal')}")

    ch_type = ch.get("chapter_type", "normal")
    ch_title = ch.get("title", "")
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

    checklist = _build_event_checklist(dict(ch))
    lines.append(f"\n## 本章事件清单（写前确认序列，写中逐项勾选）\n{checklist}")

    if summaries:
        lines.append("\n## 前章回顾")
        for s in summaries:
            sn = s.get("chapter_number", s.get("chapter_id", "?"))
            sm = (s.get("summary", "") or "")[:120]
            lines.append(f"- Ch{sn}: {sm}{'…' if len(s.get('summary',''))>120 else ''}")
    else:
        lines.append("\n## 前章回顾\n（尚无前章）")

    if chars:
        lines.append("\n## 出场人物索引")
        for c in chars[:10]:
            role_label = {"protagonist": "主角", "ally": "同伴", "antagonist": "反派",
                          "mentor": "导师", "rival": "对手", "love_interest": "恋人"}.get(c.get("role",""), c.get("role",""))
            lines.append(f"- {c.get('name','?')}（{role_label}）")
        if len(chars) > 10:
            lines.append(f"  …还有{len(chars)-10}人")
        lines.append("\n**角色蒸馏详情**：`character_detail(novel_name, character_name)` 加载完整蒸馏卡（外观/性格/说话风格/能力/状态/关系/物品）")

    if foreshadows:
        lines.append(f"\n## 未回收伏笔（{len(foreshadows)}条）")
        for f in foreshadows[:5]:
            imp = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(f.get("importance",""), "")
            lines.append(f"- {imp} {f.get('description','')[:80]}")
        if len(foreshadows) > 5:
            lines.append(f"  …还有{len(foreshadows)-5}条")

    if echoes:
        lines.append(f"\n## 🔁 本章回响（{len(echoes)}处）")
        for e in echoes[:5]:
            rel = "（强相关）" if e.get("strong_related") else ""
            lines.append(f"- {e.get('source_event','')[:50]} ← Ch{e.get('source_ch','?')}{rel}")
        lines.append("⚠️ 融入世界呼吸/日常动作，不要独立段落。普通回响≤2次/卷。")

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

    lines.append(f"\n---\n{_build_rules_prompt()}")

    av_rows = query("SELECT data FROM world_settings WHERE category = 'author_voice' LIMIT 1", ())
    if av_rows:
        av_data = av_rows[0]["data"]
        if isinstance(av_data, dict) and "content" in av_data:
            av_text = av_data["content"]
            lines.append("\n## 🎨 作者DNA")
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

    lines.append("\n---\n📎 **按需加载（写中需要再调，不占上下文）**")
    lines.append("写人物→`character_detail(novel_name, character_name)`")
    lines.append("写场景→`engine_detail('action/dialogue/environment/item')`")
    lines.append("查世界观→`world_query(novel_id, category)`")
    lines.append("查创作原则→`rule_detail('{key}')`")
    lines.append("自查正文→`validate_chapter(text)` → 写后必调 `chapter_self_check(text)` → `writing_finish(..., self_check='passed')`")

    lines.append(f"\n---\n**写作完成后调 writing_finish(novel_name, chapter_number, chapter_text, summary, key_events, …) 存盘。硬约束由 MCP 自动校验，不通过不存盘。**")

    return "\n".join(lines)
