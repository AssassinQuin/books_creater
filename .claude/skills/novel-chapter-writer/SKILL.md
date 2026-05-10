---
name: novel-chapter-writer
description: 逐章写作引擎 — 上下文注入、多线交织、去AI味、一键状态更新。触发词：写第N章/继续写/写一章。
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, Agent, mcp__memory__memory_store, mcp__memory__memory_search, mcp__novel-db__novel_get, mcp__novel-db__chapter_list, mcp__novel-db__chapter_update, mcp__novel-db__writing_start, mcp__novel-db__writing_finish, mcp__novel-db__foreshadow_list, mcp__novel-db__foreshadow_plant, mcp__novel-db__foreshadow_recall, mcp__novel-db__character_list, mcp__novel-db__character_get, mcp__novel-db__character_update, mcp__novel-db__relation_list, mcp__novel-db__world_query, mcp__novel-db__world_upsert, mcp__novel-db__timeline_query, mcp__novel-db__volume_get, mcp__novel-db__health_check, mcp__novel-db__dimension_query
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

**跨大纲全量加载（强制）：**

调用 `writing_start` 后，补充查询全卷上下文：

```
1. world_query(category="faction") → 势力范围、当前势力关系
2. world_query(category="location") → 区域设定、本章涉及地点详情
3. world_query(category="ability") | world_query(category="economy") → 物品/资源体系
4. character_get(character_id) → 章节涉及人物最新状态(status含position/inventory/mental_state)
5. relation_list() → 人物关系网，判断对话立场/冲突来源
6. timeline_query(from_chapter=1, to_chapter=当前章) → 全卷时间线，避免矛盾
7. volume_get(volume_id) → 当前卷完整规划，理解本章在卷中位置
```

---

## Step 2: 写正文（📝 可多次迭代）

### 2.0 前置准备（强制）

```
读 设定/写作执行规范.md
```
**强制遵守以下规范：**
- 最低字数：3000字（不含标点）
- 内容依据：本章大纲为纲，世界观/人物状态为准
- 写作规范：详见`写作执行规范.md`中的去AI味/节奏/风格要求
- 检查清单：写前逐项检查，写后逐项确认

### 2.1 角色蒸馏（让人物活过来）

写前对章节涉及的人物进行状态分析：

```
for each character in characters_involved:
  1. 调用 character_get(character_id) → 获取最新状态
  2. 分析当前状态：
     - position: 人在哪？处于什么环境？
     - inventory: 手中有什么物？
     - mental_state: 当前情绪、认知、压力？
     - 最近经历: 前3章发生了什么影响他？
  3. 决定行为模式：
     - 说话风格：紧张/放松/愤怒/悲伤时的用词差异
     - 行动倾向：主动/被动/犹豫/果断
     - 对话立场：对其他人物的态度（敌对/盟友/暧昧）
```

**写作时动态检查：**
- 每句对话是否符合人物当前mental_state？
- 每个动作是否符合position和inventory设定？
- 如发现偏离，暂停并提醒用户确认是否更新角色状态或调整写作方向

### 2.2 设定冲突检测与整改

写作过程中持续检查，发现冲突立即处理：

**检测维度：**
| 冲突类型 | 检测方法 |
|-----------|---------|
| 世界观冲突 | 当前情节是否与`world_query`返回的设定矛盾？ |
| 人物冲突 | 人物行为是否与`character_get`返回的status/背景矛盾？ |
| 时间线冲突 | 是否与`timeline_query`返回的历史事件矛盾？ |
| 大纲冲突 | 是否偏离`writing_start`返回的outline逻辑？ |
| 前文冲突 | 是否与前3章摘要中的关键事实矛盾？ |

**发现冲突时（三选一）：**
1. **整改设定** → 调用`world_upsert`/`character_update`修改基础设定
2. **整改大纲** → 更新章节outline（需确认）
3. **重构正文** → 按修正后设定/大纲重写当前段落

**执行流程：**
- 暂停写作，明确列出冲突点
- 展示选项1/2/3给用户
- 用户选择后执行对应修复
- 修复后继续写作

### 2.3 写作执行

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

**字数约束（强制）：**
- 最低字数：3000字（不含标点）
- 目标字数：3500-4500字
- 检测：写完字数后，如<3000字，必须扩展而非拖沓

**节奏控制：**
- 开头10%承接铺垫 → 发展40%核心推进 → 高潮30%最紧张 → 收尾20%钩子悬念

**防拖沓原则（不要特异凑字数）：**
| 禁止方式 | 替代方案 |
|---------|---------|
| 用"于是""随后""接着"过渡 | 直接用动作/对话接续 |
| 无意义的心理描写长段 | 用具体行为展示情绪 |
| 重复相同动作描写 | 合并或用一次概括 |
| 用大量环境描写填充 | 用环境暗示情绪，不单独堆砌 |
| 章节末无实质推进 | 每段至少有一个推进点 |

**爽点密度**：每3-5章一个（打脸/逆袭/获得/展示/复仇）

### 风格参考（如有语料库）

写前检查 Memory 中是否有 `shared,style-profile` 标签的语料。如有，写作时参考其句式长度、对话占比、描写密度特征。详见 `.claude/skills/novel-writer/references/corpus-style-guide.md`

---

## Step 3: 🔒写后状态更新（不可跳过）

> **这是最容易遗漏的步骤。正文写完后立即执行，不管用户接下来说什么。**

### 3.1 角色档案增量更新

调用 `character_update` 更新本章发生变化的人物状态：

```
for each character in characters_involved:
  character_update(character_id,
    status={
      position: "人在哪？",
      inventory: ["手中有什么物？"],
      mental_state: "当前情绪/认知/压力？",
      recent_events: ["本章发生的关键事件"]
    })
```

**更新原则：**
- 只更新本章确实变化的状态字段
- 保留未变化字段为空（不覆盖）
- 添加recent_events时用增量方式（追加而非替换）

### 3.2 完整状态同步

```
writing_finish(chapter_id, summary="章节概要",
  key_events=["事件1","事件2"],
  characters_involved=[人物id列表],
  new_foreshadows=[{description:"伏笔描述",importance:"medium"}],
  resolved_foreshadows=[伏笔id列表],
  ability_level="金丹中期", location="潜龙城",
  timeline_events=[{event_time:"午后", event_order:1, event_description:"XXX"}])
```

一步完成：摘要 + 状态 + 伏笔 + 维度 + 时间线 + **角色增量更新**。

完成后向用户确认：`"✓ 第{N}章状态已更新（摘要/伏笔/时间线/维度/角色状态）"`

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
