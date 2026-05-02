---
name: novel-chapter-writer
description: 逐章写作引擎 — 上下文注入、多线交织、去AI味、一键状态更新。触发词：写第N章/继续写/写一章。
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, Agent, mcp__memory__memory_store, mcp__memory__memory_search, mcp__novel-db__novel_get, mcp__novel-db__chapter_list, mcp__novel-db__chapter_update, mcp__novel-db__writing_start, mcp__novel-db__writing_finish, mcp__novel-db__foreshadow_list, mcp__novel-db__foreshadow_plant, mcp__novel-db__foreshadow_recall, mcp__novel-db__character_list, mcp__novel-db__health_check, mcp__novel-db__dimension_query
---

# 逐章写作引擎

> 共享约定：读 `.claude/skills/novel-writer/references/shared-conventions.md`（含流程纪律）

## 强制流程

```
Step 1 注入上下文 → Step 2 📝写正文 → Step 3 🔒写作完成确认 → Step 4 存盘git commit
```

**Step 3 是不可跳过的强制步骤。** 即使写完正文后用户说了别的话，必须先完成 `writing_finish` 再回应。未完成 Step 3 视为流程中断，下次触发时检测并提醒。

---

## Step 1: 注入上下文

```
writing_start(novel_id, chapter_number)
→ 章节信息 + 前3章摘要 + 活跃人物 + 未回收伏笔 + 世界观 + 当前卷规划
```

---

## Step 2: 写正文（📝 可多次迭代）

读 `.claude/skills/novel-writer/references/writing-style.md` + `anti-ai-patterns.md`

### 场景类型策略（按 scene 的 emotion_type 切换）

读 `.claude/skills/novel-writer/references/scene-type-guide.md`

`writing_start` 注入上下文后，检查本章各 scene 的 `emotion_type`，按类型选择写作策略：

| emotion_type | 核心策略 | 占比规则 |
|---|---|---|
| dialogue | 潜台词+废话+抢话 | 对话≥60% |
| action | 短句密集+动词驱动 | 动作≥50%，对话≤20% |
| atmosphere | 五感铺陈+环境暗示情绪 | 环境≥40%，内心≥30% |
| psychology | 情绪分层+回忆碎片 | 内心独白≥40% |
| daily | 闲聊带设定+毛边细节 | 闲聊+侧面≥60% |
| montage | 多片段快切+强画面 | 每片段100-300字 |

如果 `emotion_type` 未指定，根据章节大纲关键词自动判断。同一章场景类型不超过2种。

### 去AI味要点

- 句式长短交替（不要每句15-20字）
- 省略过渡（不要每段"然而""于是""随后"）
- 对话有废话（真人说话有"嗯""啊""那个"）
- 场景有毛边（留点不规整的细节）
- 情绪克制（不要"震惊""难以置信""倒吸凉气"）

### 多线交织策略

1. 查当前卷 main_plotlines → 本章属于哪条线的节点
2. 查 `foreshadow_list` → 有计划在附近回收的伏笔吗？
3. 暗线埋设：非暗线章节用日常场景不经意带过
4. 配角出场：检查哪些核心配角最近5章没出场
5. 场景切换：同一章不超过2个

### 章节节奏

开头10%承接铺垫 → 发展40%核心推进 → 高潮30%最紧张 → 收尾20%钩子悬念

**爽点密度**：每3-5章一个（打脸/逆袭/获得/展示/复仇）

### 风格参考（如有语料库）

写前检查 Memory 中是否有 `shared,style-profile` 标签的语料。如有，写作时参考其句式长度、对话占比、描写密度特征。详见 `.claude/skills/novel-writer/references/corpus-style-guide.md`

---

## Step 3: 🔒写后状态更新（不可跳过）

> **这是最容易遗漏的步骤。正文写完后立即执行，不管用户接下来说什么。**

```
writing_finish(chapter_id, summary="章节概要",
  key_events=["事件1","事件2"],
  characters_involved=[人物id列表],
  new_foreshadows=[{description:"伏笔描述",importance:"medium"}],
  resolved_foreshadows=[伏笔id列表],
  ability_level="金丹中期", location="潜龙城",
  timeline_events=[{event_time:"午后", event_order:1, event_description:"XXX"}])
```

一步完成：摘要 + 状态 + 伏笔 + 维度 + 时间线。

完成后向用户确认：`"✓ 第{N}章状态已更新（摘要/伏笔/时间线/维度）"`

**然后**才能进入对话、修改、或下一章。

---

## 每10章：健康快检

```
foreshadow_list(status="planted") → 未回收伏笔
character_list → 长期未出场配角
dimension_query(dimension="ability") → 升级节奏
```

发现问题 → **暂停提醒用户**，建议调用 `/novel-doctor` 深入诊断。

---

## Step 4: 存盘

`novels/{小说名}/正文/第{NNN}章-{标题}.md` → `git commit -m "ch{N}: {标题}"`

---

## 流程中断恢复

触发时先检查：是否有上一章写完但未执行 `writing_finish` 的情况？
```
chapter_list → 最近一章状态是否为 written？
```
如果是 drafting → 提醒"上次第{N}章写完了但状态没更新，先补 writing_finish？"
