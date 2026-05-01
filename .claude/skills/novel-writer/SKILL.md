---
name: novel-writer
description: 网文创作全流程 — 从碎片灵感到百万字长篇。自然语言触发，引导式工作流，novel-db MCP 管理结构化数据，Memory MCP 管理灵感素材。
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, Agent, mcp__memory__memory_store, mcp__memory__memory_search, mcp__memory__memory_update, mcp__memory__memory_delete, mcp__memory__memory_list, mcp__memory__memory_graph, mcp__novel-db__novel_create, mcp__novel-db__novel_list, mcp__novel-db__novel_get, mcp__novel-db__novel_update, mcp__novel-db__world_upsert, mcp__novel-db__world_query, mcp__novel-db__world_delete, mcp__novel-db__character_create, mcp__novel-db__character_list, mcp__novel-db__character_get, mcp__novel-db__character_update, mcp__novel-db__relation_create, mcp__novel-db__relation_list, mcp__novel-db__volume_create, mcp__novel-db__volume_list, mcp__novel-db__volume_get, mcp__novel-db__volume_update, mcp__novel-db__chapter_plan, mcp__novel-db__chapter_list, mcp__novel-db__chapter_update, mcp__novel-db__chapter_save_summary, mcp__novel-db__chapter_get_context, mcp__novel-db__foreshadow_plant, mcp__novel-db__foreshadow_list, mcp__novel-db__foreshadow_recall, mcp__novel-db__timeline_add, mcp__novel-db__timeline_query, mcp__novel-db__scene_create, mcp__novel-db__scene_list, mcp__novel-db__dimension_log, mcp__novel-db__dimension_query, mcp__novel-db__db_search
---

# 网文创作 Skill

> **本文件功能**: 网文创作全流程引导系统。用户直接聊天触发各阶段，AI 自动识别意图并执行对应工作流。

## 核心写作理念（铁律，所有阶段必须遵守）

1. **世界观严谨完整**: 种族、能力、势力、地区、货币、衣食住行——每个维度都有明确设定，不能模糊带过
2. **人物丰满多样**: 不全围着主角转。NPC 有自己的生活，反派有自己的逻辑，路人有自己的故事
3. **禁止 AI 味设定**: 不准加"使用能力的代价""反噬""寿命折损""精神崩溃"等廉价戏剧冲突
4. **日常要充实**: 路边摆摊大爷说"小伙子厉害啊，潜龙榜排第 37"，用侧面描写建立世界观，不要空洞设定堆砌
5. **全白话接地气**: 对话像真人说话，描写有画面感，拒绝文绉绉的 AI 腔
6. **百万字是马拉松不是短跑**: 卷级规划、配角轮换、伏笔回收节奏、升级衰减后的替代爽点，都要从第一天开始设计

## 意图路由

用户消息匹配以下关键词时，进入对应阶段。**一次只匹配一个阶段**。

```
关键词                                          → 阶段
───────────────────────────────────────────────────────────────
"头脑风暴"/"聊聊点子"/"我有个想法"/"灵感"          → Phase 0-1: 灵感收集+头脑风暴
"建世界观"/"设计世界"/"设定世界"/"世界观"           → Phase 2: 世界观建模
"设计人物"/"加个人物"/"人物卡"/"人物"              → Phase 2b: 人物设计
"规划卷"/"卷大纲"/"卷规划"                        → Phase 3: 卷+大纲生成
"生成大纲"/"做大纲"/"规划剧情"/"大纲"              → Phase 3: 卷+大纲生成
"写第N章"/"继续写"/"开始写"/"写一章"              → Phase 4: 逐章写作
"审阅"/"检查"/"review"/"找问题"                   → Phase 5: 审阅修改
"上架"/"发布"/"番茄适配"/"起点"                   → Phase 6: 平台上架
"改设定"/"修改世界观"/"改人物"/"调整"              → 更新模式: 级联更新
"项目状态"/"当前进度"/"status"/"进度"              → 状态总览
"加素材"/"拆书"/"参考"/"借鉴"/"找参考"            → 素材库操作
"诊断"/"疲劳"/"卡文"/"写不动了"                   → 健康度诊断
```

**无匹配时**: 用 `novel_get` + `chapter_list` 查当前进度，建议下一步。

---

## 数据分层策略

| 数据类型 | 存储位置 | 原因 |
|----------|----------|------|
| 世界观/人物/章节/伏笔/时间线/维度变更 | **novel-db MCP** | 结构化查询，支撑百万字规模 |
| 灵感碎片/写作经验/跨项目素材 | **Memory MCP** | 非结构化创意内容 |
| 正文/设定文档/审阅报告 | **Git 文件** | 人类可读可编辑 |

---

## Phase 0-1: 灵感收集 + 头脑风暴

**触发**: 用户说"头脑风暴"/"我有个想法" 等关键词

**目标**: 从用户的碎片灵感中提炼核心冲突和主线方向

### 流程

1. 确认小说名（如果没有则询问）
2. 用 `novel_create` 创建项目，记录返回的 `novel_id`
3. 确保目录存在：`novels/{小说名}/`
4. **读取** `references/brainstorm-guide.md` 获取引导话术
5. 进入引导式对话，**一次只问一个问题**：

   **第 1 轮** — 画面感：
   > "你最兴奋的场景是什么？描述一下那个画面。哪怕只有一句话也行。"

   **第 2 轮** — 主角特质：
   > "主角最让你着迷的特质是什么？他/她是个什么样的人？"

   **第 3 轮** — 读者情绪：
   > "你希望读者读完最强烈的情绪是什么？爽？虐？燃？感动？"

   **第 4 轮** — 对立面：
   > "有没有一个你特别想写的对手/反派？他为什么跟主角作对？"

   **第 5 轮** — 独特规则：
   > "这个世界最不一样的规则是什么？什么是这里的人觉得理所当然，但读者会觉得'卧槽'的？"

   **后续轮** — 根据回答深入追问。如果用户提到"群像"/"多主角"→ 追问每个核心角色的独立故事线和交汇点

6. 每个回答**立即存入 Memory**（灵感碎片是非结构化创意）：
   ```
   memory_store(content="用户灵感：{精炼内容}", metadata={tags: "project:{小说名},idea"})
   ```

7. 头脑风暴结束时，**AI 整理输出**：
   - 识别出的核心冲突（1-3 个候选，让用户选）
   - 潜在主线方向（2-3 个方向供选择）
   - 亮点场景列表
   - 建议的小说类型（参考 `references/genre-profiles.md`）
   - **如果是群像文**：初步群像架构（核心角色数量、各自独立线、交汇设计）

8. 用户选定后，用 `novel_update` 更新 genre/status，**核心决策存 Memory**：
   ```
   memory_store(content="核心冲突：...", metadata={tags: "project:{小说名},decision"})
   ```

9. `git add . && git commit -m "Phase 0-1: 头脑风暴完成 - {小说名}"`

---

## Phase 2: 世界观建模

**触发**: 用户说"建世界观"/"设定世界" 等关键词

**前置检查**: 必须已完成 Phase 0-1（Memory 中有核心冲突）

### 流程

1. 从 Memory 召回核心冲突 + 所有灵感碎片
2. **读取** `references/worldbuilding-template.md`
3. 引导用户逐维度建立世界观（**一次一个维度**，不一次全问）：

   维度顺序：种族 → 势力 → 地理 → 能力等级 → 经济 → 日常生活

   每个维度的引导问题详见 `references/worldbuilding-template.md`

4. 每个维度完成后**立即写入 novel-db**：
   ```
   world_upsert(novel_id, category="{维度}", name="{子项名}", data={完整设定})
   ```
   同时写入文件 `novels/{小说名}/世界观/{维度}.md`

5. 所有维度完成后，**维度交叉验证**（详见 worldbuilding-template.md 底部清单）：
   - 时间×空间：移动时间合理？
   - 经济×势力：财力与行为匹配？
   - 能力×种族：各种族能力差异自洽？

6. `git add . && git commit -m "Phase 2: 世界观建模完成 - {小说名}"`

---

## Phase 2b: 人物设计

**触发**: 用户说"设计人物"/"加个人物" 等关键词

### 流程

1. **读取** `references/character-design.md`
2. 从 novel-db 召回世界观：`world_query(novel_id)`
3. 引导设计人物（关注维度详见 character-design.md）：

   **主角** — 出身/外部目标/内部渴望/性格/缺陷/习惯/底线/禁忌
   **核心配角**（至少3人）— 各自目标、与主角关系、独立故事线
   **反派** — 合理动机、自己的逻辑、站在他视角说得通
   **NPC/路人** — 用侧面描写丰富世界观

4. 每个人物**写入 novel-db**：
   ```
   character_create(novel_id, name, role, race, ability_level, personality,
                    appearance, background, goals, weaknesses, speech_style,
                    catchphrase, arc_notes)
   ```

5. 用 `relation_create` 建立人物关系：
   ```
   relation_create(novel_id, from_id, to_id, relation_type, description, intensity)
   ```

6. **群像独立检查**（每个核心配角必须答上）：
   - 不出场时在做什么？
   - 有什么与主角无关的目标？
   - 和主角有利益冲突吗？

7. 写入文件 `novels/{小说名}/人物/{角色名}.md`

8. `git add . && git commit -m "Phase 2b: 人物设计完成 - {小说名}"`

---

## Phase 3: 卷规划 + 大纲生成

**触发**: 用户说"生成大纲"/"做大纲"/"规划卷" 等关键词

**前置**: Phase 0-2 必须完成

### 流程

1. 从 novel-db 召回：`novel_get` + `world_query` + `character_list` + `relation_list`

2. 生成**全书总纲**（一页纸）：
   - 核心冲突 + 终极对决方向
   - 预计卷数（每卷 30-80 章，百万字约 500 章 / 8-15 卷）
   - 主角成长弧线（从起点到终点的关键转变节点）
   - **明暗双线**：明线（主角视角推进）+ 暗线（隐藏的真相/阴谋/历史）

3. 引导用户确认/修改总纲

4. **逐卷规划**（这是百万字的核心）：
   ```
   volume_create(novel_id, number=N, title="卷名",
                 main_plotlines=[
                   {name: "主线", description: "本卷主线剧情", purpose: "推进XXX"},
                   {name: "暗线", description: "本卷暗线进展", purpose: "铺垫XXX"},
                   {name: "配角线", description: "本卷重点配角", purpose: "展示XXX"}
                 ],
                 notes="伏笔埋设计划、配角出场安排、升级节点")
   ```

   **每卷必须定义**：
   - 本卷主线推进到什么程度
   - 本卷暗线揭示多少（暗线不能一次揭完，要分卷递进）
   - 本卷重点出场的配角（2-4人）和他们的弧光
   - 本卷升级节点（如有）或替代爽点
   - 伏笔计划：本卷埋几条、回收几条旧伏笔
   - 本卷结尾状态：主角到什么水平、世界格局什么变化

5. 卷确认后，在每卷内生成**章节场景清单**：
   ```
   chapter_plan(novel_id, number=N, title="章名", outline="场景概述",
                chapter_type="normal/climax/transition/daily", volume_id=卷id)
   ```
   关键章节用 `scene_create` 细化：
   ```
   scene_create(chapter_id, scene_number, location, characters_involved,
                conflict, emotion_type, key_beats)
   ```

6. **伏笔全局规划**（跨卷）：
   ```
   foreshadow_plant(novel_id, description, planted_chapter_id,
                    planned_recall_chapter, importance, related_characters)
   ```

7. 写入文件 `novels/{小说名}/大纲/`

8. `git add . && git commit -m "Phase 3: 卷规划+大纲完成 - {小说名}"`

---

## Phase 4: 逐章写作

**触发**: 用户说"写第N章"/"继续写" 等关键词

### 上下文自动注入（写每章前执行）

**用 novel-db 的 chapter_get_context 一次获取所有上下文**：
```
chapter_get_context(novel_id, chapter_number)
→ 返回：章节信息 + 前3章摘要 + 活跃人物 + 未回收伏笔 + 世界观设定
```

补充查询（如果需要）：
```
foreshadow_list(novel_id, status="planted")  // 完整伏笔列表
volume_get(volume_id)                         // 当前卷信息+主线规划
```

### 写作规则（写入时实时检查）

- **读取** `references/writing-style.md` 和 `references/anti-ai-patterns.md`
- 对话必须像真人说话，白话为主
- 场景描写有画面感，不是空洞设定堆砌
- 用侧面描写丰富日常（路人视角/榜单/传闻/物价/街景）
- 禁止 AI 味高频词（"不禁""缓缓""淡淡""微微"）
- 禁止"代价""反噬""寿命折损"等套路
- 章末必须有钩子

### 多线交织写作策略

写每章时按以下优先级安排内容：

1. **检查当前卷的 main_plotlines**：本章属于哪条线的推进节点？
2. **检查伏笔状态**：`foreshadow_list(status="planted")` 中有计划在附近章节回收的吗？
3. **暗线埋设**：如果不是专门的暗线章节，用日常场景不经意地带过（路人闲聊、偶然发现的线索、配角无意间透露的信息）
4. **配角出场节奏**：检查哪些核心配角最近 5 章没出场了，考虑在本章安排出场或侧面提及
5. **场景切换**：同一章内不超过 2 个场景切换。切换时用空行+时间/地点标注

### 写作后状态更新（每章写完执行）

```
1. chapter_save_summary(chapter_id, summary, key_events, characters_involved,
                        new_foreshadows, resolved_foreshadows, dimension_snapshot)
2. 如有人物状态变更: character_update(character_id, ...)
3. 如有时间线事件: timeline_add(novel_id, chapter_id, event_time, event_order, description)
4. 如有能力/空间变更: dimension_log(novel_id, chapter_id, dimension, change_type, ...)
5. chapter_update(chapter_id, status="written")
```

### 输出

写入文件 `novels/{小说名}/正文/第{NNN}章-{标题}.md`

`git add . && git commit -m "ch{N}: {章节标题}"`

---

## Phase 5: 审阅修改

**触发**: 用户说"审阅"/"检查" 等关键词

### 流程

1. **读取** `references/review-checklist.md`
2. 用 `db_search(novel_id, keyword)` 和 `foreshadow_list` 等工具获取数据
3. 并行派 **3 个 Agent**：

   **Agent A — 逻辑+维度**:
   - `dimension_query(novel_id)` 检查能力/空间/时间一致性
   - `timeline_query(novel_id, from_chapter, to_chapter)` 检查时间线
   - `foreshadow_list(novel_id, status="planted")` 检查伏笔遗漏（超30章未回收标黄）

   **Agent B — 人设+文字**:
   - `character_list(novel_id)` 对照人设检查 OOC
   - AI 味检测（对照 anti-ai-patterns.md + Memory 中的黑名单）

   **Agent C — 合规+竞争力**:
   - 平台合规检查（参考 `references/platform-rules.md`）
   - 爽点密度、钩子有效性、差异化评估

4. 汇总 → 生成 `novels/{小说名}/审阅报告/第{N}次审阅.md`
5. 问题分级：致命/严重/轻微
6. `git add . && git commit -m "Phase 5: 审阅报告 - {范围}"`

---

## Phase 6: 平台上架

**触发**: 用户说"上架"/"番茄适配" 等关键词

1. **读取** `references/platform-rules.md`
2. 按目标平台检查合规性
3. 降 AI 率建议
4. 排版适配建议
5. 输出上架检查报告

---

## 健康度诊断（长篇专项）

**触发**: 用户说"诊断"/"疲劳"/"卡文" 等关键词

### 自动化诊断流程

用 novel-db 结构化查询，**5分钟出诊断报告**：

```
1. novel_get(novel_id) → 当前进度
2. chapter_list(novel_id) → 章节数量和状态分布
3. foreshadow_list(novel_id, status="planted") → 未回收伏笔（按章距排序）
4. character_list(novel_id) → 检查哪些角色长期没出场
5. dimension_query(novel_id, dimension="ability") → 升级节奏曲线
6. volume_list(novel_id) → 各卷完成度
```

### 诊断报告内容

| 指标 | 健康标准 | 异常信号 |
|------|---------|---------|
| 伏笔积压 | 未回收 < 总埋设的40% | 超50%且最老伏笔超过30章 |
| 配角活跃度 | 核心配角5章内至少提及1次 | 超过10章无任何提及 |
| 升级节奏 | 符合genre-profiles建议 | 连续40章无升级且无替代爽点 |
| 日常密度 | 每5-8章有日常场景 | 连续10章纯战斗/纯推进 |
| 暗线推进 | 每15-20章有暗线新进展 | 暗线超30章无新线索 |
| 卷转换 | 新卷开头3章内有视角刷新 | 卷与卷之间无差异化 |

### 常见疲劳破局方案

**升级衰减**（元婴后升级变慢）：
- 切换爽点类型：从"升级碾压"转为"势力博弈""智斗""信息差""以弱胜强"
- 引入新体系（如炼丹/阵法/灵兽），给出新的成长曲线
- 主角暂时失去优势（被人算计/环境限制），制造新的紧张感

**配角遗忘**（核心配角200章没出场）：
- 安排"配角回归"事件：用信息差制造惊喜（他在暗处做了什么？）
- 让配角的独立故事线与主线交汇
- 用侧面描写维持存在感（传闻/书信/其他角色的回忆）

**伏笔膨胀**（埋太多收不回来）：
- 批量回收：选3-5条重要性高的伏笔，在2-3章内集中回收
- 部分伏笔转为长线（标注 `importance="high"`, 延后到新卷回收）
- 果断放弃不重要的（`foreshadow_recall` 标记为 recalled 或直接在笔记中标注放弃）

---

## 更新模式: 级联更新

**触发**: 用户说"改设定"/"改人物" 等关键词

### 流程

1. 确认改什么（世界观/人物/力量体系/...）
2. 修改 novel-db 对应数据：
   - 世界观：`world_upsert` / `world_delete`
   - 人物：`character_update`
   - 关系：`relation_create` / `relation_update`
3. 用 `db_search(novel_id, keyword)` 找到所有受影响的内容
4. 检查大纲中哪些章节受影响 → 标记
5. 检查已写正文中哪些章节受影响 → 列出
6. **询问用户**: 哪些已写章节需要回头改？
7. `git add . && git commit -m "更新: {修改内容描述}"`

---

## 素材库操作

**触发**: 用户说"加素材"/"拆书"/"借鉴" 等关键词

1. 用户提供内容 → `memory_store(content, tags=["shared","material"])`
2. 参考某类小说 → 搜索相关作品分析
3. 拆书笔记 → `memory_store(content, tags=["shared","analysis"])`
4. 写作中发现新 AI 味模式 → `memory_store(content, tags=["shared","anti-ai-pattern"])`

---

## 状态总览

**触发**: 用户说"项目状态"/"进度" 等关键词

### 自动化查询

```
1. novel_get(novel_id) → 基本信息
2. volume_list(novel_id) → 各卷概览
3. chapter_list(novel_id) → 章节统计
4. foreshadow_list(novel_id) → 伏笔统计（按status分组计数）
5. character_list(novel_id) → 人物统计
```

### 输出格式

```
项目: {小说名} ({genre})
阶段: Phase {N} - {阶段名}
卷: {已完卷数}/{总卷数} | 最新卷: {卷名}
章节: 已写 {M} 章
人物: {N} 个角色 ({主角/配角/反派/NPC分布})
伏笔: {planted}埋 / {recalled}回收 / 未回收率{X%}
最近: 第{N}章 - {标题}
```

---

## Memory 数据模型（仅灵感/素材/经验）

| type | 内容 | tags 格式 |
|------|------|-----------|
| `idea` | 灵感碎片 | project:{名},idea |
| `decision` | 核心决策 | project:{名},decision |
| `learning` | 写作经验 | project:{名},learning |
| `anti-ai-pattern` | AI味黑名单 | shared,anti-ai-pattern |
| `material` | 通用素材 | shared,material |
| `analysis` | 拆书笔记 | shared,analysis |

## Git 规范

- 每个阶段完成 → commit
- 每章写完 → commit
- 每次改设定 → commit
- 格式: `Phase N: {描述}` 或 `ch{N}: {标题}` 或 `更新: {描述}`
