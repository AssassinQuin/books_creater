import os
import re

CONSTRAINTS_FILE = os.environ.get(
    "CONSTRAINTS_FILE",
    os.path.join(
        os.environ.get(
            "NOVEL_PROJECT_ROOT",
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        ),
        ".claude", "skills", "writing-constraints.md"
    )
)


def _parse_constraints_md() -> dict:
    result = {
        "hard_pct": {},
        "hard_abs": {},
        "banned_patterns": [],
        "guidelines": {},
    }
    try:
        with open(CONSTRAINTS_FILE, "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        return result

    pct_pattern = re.compile(
        r'^\|\s*(\w[\w_]*)\s*\|\s*([^|]+)\s*\|\s*([\d.]+)\s*\|\s*([\d.]+)\s*\|\s*([^|]*)',
        re.MULTILINE
    )
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

    section_abs = re.search(r'## 硬约束（绝对值）\n(.*?)(?=\n## |\Z)', content, re.DOTALL)
    if section_abs:
        for m in re.finditer(
            r'^\|\s*(\w+)\s*\|\s*([^|]+)\s*\|\s*([\d.\-]*)\s*\|\s*([\d.\-]*)\s*\|\s*([^|]*)',
            section_abs.group(1), re.MULTILINE
        ):
            key = m.group(1).strip()
            if key in ("key", "---"):
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

    section_ban = re.search(r'## 违禁词\n(.*?)(?=\n## |\Z)', content, re.DOTALL)
    if section_ban:
        for m in re.finditer(r'^- \s*(.+)$', section_ban.group(1), re.MULTILINE):
            result["banned_patterns"].append(m.group(1).strip())

    section_guide = re.search(r'## 创作原则.*?\n(.*?)(?=\n## |\Z)', content, re.DOTALL)
    if section_guide:
        for m in re.finditer(
            r'^\|\s*([\w_]+)\s*\|\s*([^|]+)\s*\|\s*([^|]+)\s*\|\s*([^|]*)',
            section_guide.group(1), re.MULTILINE
        ):
            key = m.group(1).strip()
            if key in ("key", "---"):
                continue
            rule = m.group(3).strip() if m.group(2) and not m.group(2).startswith("铁律") and len(m.group(2)) > 5 else ""
            ref = m.group(4).strip() if m.group(4) else ""
            label = m.group(2).strip()
            if rule and len(rule) > 5:
                result["guidelines"][key] = {"label": label, "rule": rule, "ref": ref}
            else:
                ref = m.group(3).strip() if m.group(3) else ""
                result["guidelines"][key] = {"rule": label, "ref": ref}

    return result


_CONSTRAINTS_CACHE: dict = None


def _get_constraints() -> dict:
    global _CONSTRAINTS_CACHE
    if _CONSTRAINTS_CACHE is None:
        _CONSTRAINTS_CACHE = _parse_constraints_md()
    return _CONSTRAINTS_CACHE


def validate_chapter_text(text: str) -> dict:
    violations = []
    stats = {}
    c = _get_constraints()
    hard_pct = c.get("hard_pct", {})
    hard_abs = c.get("hard_abs", {})
    banned = c.get("banned_patterns", [])

    total_chars = len(re.sub(r'\s', '', text))
    paras = re.split(r'\n\s*\n', text)

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
            permille = count / total_chars * 1000
            rule = hard_pct[key]
            min_v, max_v = rule["min"], rule["max"]
            if permille < min_v or permille > max_v:
                violations.append(
                    f"{rule['label']}：{count}次({permille:.1f}‰)，需{min_v}-{max_v}‰"
                )

    stats["wave_count"] = len(re.findall(r'[～~]', text))

    ng = len(re.findall(r'不是[^，]*，[^。]*是', text))
    stats["negation_count"] = ng
    if "negation" in hard_abs and ng > hard_abs["negation"].get("max", 999):
        violations.append(f"{hard_abs['negation']['label']}：{ng}次，需≤{hard_abs['negation'].get('max',999)}次")

    if "word_count" in hard_abs and total_chars < hard_abs["word_count"].get("min", 0):
        violations.append(f"{hard_abs['word_count']['label']}：{total_chars}，需≥{hard_abs['word_count'].get('min',0)}字")
    stats["word_count"] = total_chars

    lp = sum(1 for p in paras if len(p.strip()) >= 180)
    stats["long_paragraphs"] = lp
    if "long_paragraphs" in hard_abs and lp < hard_abs["long_paragraphs"].get("min", 0):
        violations.append(f"{hard_abs['long_paragraphs']['label']}：{lp}个，需≥{hard_abs['long_paragraphs'].get('min',0)}个")

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

    db = len(re.findall(r'——[^—]', text))
    stats["dialogue_breaks"] = db
    if "dialogue_breaks" in hard_abs and db < hard_abs["dialogue_breaks"].get("min", 0):
        violations.append(f"{hard_abs['dialogue_breaks']['label']}：{db}次，需≥{hard_abs['dialogue_breaks'].get('min',0)}次")

    fb = [p for p in banned if p in text]
    stats["banned_patterns"] = fb
    if fb:
        violations.append(f"违禁词：{', '.join(fb)}")

    return {"violations": violations, "stats": stats, "passed": len(violations) == 0}


def _enrichment_level(current_words: int, min_words: int) -> str:
    if min_words <= 0 or current_words >= min_words:
        return ""
    deficit_pct = (min_words - current_words) / min_words * 100

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
            f"   - 找不出相关事件？说明你对大纲不够熟。再读一遍 `get_chapter_context` 返回的事件清单\n\n"
            f"加事件后重新调 `writing_finish`。不努力的话，有的是比你更能写的模型替你。"
        )
