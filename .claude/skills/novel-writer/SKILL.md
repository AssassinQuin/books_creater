---
name: novel-writer
description: 百万字网文创作引擎 — 卷级循环工作流，结构化数据驱动，群像+明暗双线+去AI味。触发词：写小说/头脑风暴/建世界观/设计人物/规划卷/写第N章/继续写/审阅/上架/诊断/卡文/改设定/进度。
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, Agent, mcp__memory__memory_store, mcp__memory__memory_search, mcp__memory__memory_update, mcp__memory__memory_delete, mcp__memory__memory_list, mcp__memory__memory_graph, mcp__novel-db__novel_create, mcp__novel-db__novel_list, mcp__novel-db__novel_get, mcp__novel-db__novel_update, mcp__novel-db__world_upsert, mcp__novel-db__world_query, mcp__novel-db__world_delete, mcp__novel-db__character_create, mcp__novel-db__character_list, mcp__novel-db__character_get, mcp__novel-db__character_update, mcp__novel-db__relation_create, mcp__novel-db__relation_list, mcp__novel-db__volume_create, mcp__novel-db__volume_list, mcp__novel-db__volume_get, mcp__novel-db__volume_update, mcp__novel-db__chapter_plan, mcp__novel-db__chapter_list, mcp__novel-db__chapter_update, mcp__novel-db__chapter_save_summary, mcp__novel-db__chapter_get_context, mcp__novel-db__foreshadow_plant, mcp__novel-db__foreshadow_list, mcp__novel-db__foreshadow_recall, mcp__novel-db__timeline_add, mcp__novel-db__timeline_query, mcp__novel-db__scene_create, mcp__novel-db__scene_list, mcp__novel-db__dimension_log, mcp__novel-db__dimension_query, mcp__novel-db__db_search, mcp__novel-db__writing_start, mcp__novel-db__writing_finish, mcp__novel-db__health_check
---

# 百万字网文创作引擎

## 铁律（所有输出必须遵守）

1. **人物群像** — NPC有自己的生活，反派有自己的逻辑，配角有自己的故事线，不全围着主角转
2. **去AI味** — 禁止：不禁/缓缓/淡淡/微微/代价/反噬/寿命折损/精神崩溃。对话像真人，描写有画面
3. **日常即世界观** — 用摊贩大爷的闲聊、告示栏的排名、酒馆的物价展示世界，不空洞堆设定
4. **百万字是马拉松** — 卷级规划、配角轮换、伏笔回收节奏、升级衰减后的替代爽点，从第一天就设计
5. **明暗双线** — 每卷有明线（主角推进）和暗线（隐藏真相），暗线不一次揭完，分卷递进

## 意图路由

```
关键词                                                    → 进入
─────────────────────────────────────────────────────────────────────
"头脑风暴"/"灵感"/"我有个想法"                             → A1: 项目启动
"建世界观"/"世界观"/"设定"                                  → A2: 世界观建模
"设计人物"/"加个人物"/"人物卡"                              → A3: 人物设计
"规划卷"/"大纲"/"卷大纲"                                   → B1: 卷规划
"写第N章"/"继续写"/"写一章"                                → B2: 逐章写作
"审阅"/"检查"/"review"                                     → B3: 审阅
"上架"/"发布"/"番茄"/"起点"                                → C1: 平台上架
"诊断"/"卡文"/"疲劳"/"写不动"                              → C2: 健康诊断
"改设定"/"改人物"/"调整"                                   → C3: 级联更新
"进度"/"状态"/"status"                                     → D: 状态总览
"加素材"/"拆书"/"参考"                                     → D: 素材操作
无匹配 → novel_get + chapter_list 查进度，建议下一步

**冲突消歧**：B2写作中说"改设定"→ 暂停写作进入C3级联更新，更新完回到B2继续。同一消息匹配多个关键词→优先级：C3更新 > B2写作 > 其他。
```

## 数据分层

| 数据 | 存储 | 原因 |
|------|------|------|
| 世界观/人物/章节/伏笔/时间线/维度 | **novel-db** | 结构化查询，百万字规模 |
| 灵感碎片/写作经验/跨项目素材/AI味黑名单 | **Memory** | 非结构化创意 |
| 正文/设定文档/审阅报告 | **Git文件** | 人类可读可编辑 |

---

## A层: 项目基建（只跑一次）

### A1: 项目启动

触发: "头脑风暴"/"灵感"

1. 确认小说名，`novel_create` 创建项目
2. 读 `references/brainstorm-guide.md`，**一次只问一个问题**：
   - 画面感 → 主角特质 → 读者情绪(爽/虐/燃/感动/紧张) → 对立面 → 独特规则
   - 用户提到"群像"→ 追问每个核心角色的独立线和交汇点
3. 每个回答 → `memory_store(tags="project:{名},idea")`
4. 结束输出：核心冲突(1-3选1) + 主线方向(2-3选1) + 建议品类(参考 `genre-profiles.md`)
5. 用户选定 → `novel_update(genre, status)` + `memory_store(tags="decision")`
6. `git commit -m "A1: 项目启动 - {小说名}"`

### A2: 世界观建模

触发: "建世界观" | 前置: A1完成

1. 读 `references/worldbuilding-template.md`
2. 引导逐维度建立，**一次一个维度**：种族→势力→地理→能力→经济→日常
3. 每维度完成 → `world_upsert(novel_id, category, name, data)` + 写文件
4. 全部完成 → 维度交叉验证（时间×空间、经济×势力、能力×种族）
5. `git commit -m "A2: 世界观完成 - {小说名}"`

### A3: 人物设计

触发: "设计人物" | 前置: A2完成

1. 读 `references/character-design.md`，召回 `world_query` 的设定
2. 引导设计：

   **主角**: 出身/外部目标/内部渴望/性格(用行为定义)/缺陷/习惯/底线/禁忌
   **核心配角**(至少3人): 各自目标、独立故事线、与主角利益冲突
   **反派**: 合理动机、自己逻辑、站他视角说得通
   **NPC**: 摊贩/酒馆老板/巡逻兵，用侧面描写丰富世界

3. 每人 → `character_create(...)` + `relation_create(...)` 建关系
4. **群像独立检查**（每人必答）：不出场时在做什么？有什么自己的目标？
5. `git commit -m "A3: 人物完成 - {小说名}"`

---

## B层: 卷级循环（每卷重复）

> **百万字的核心**：不是一次性跑完Phase 0→6，而是每卷都经过 B1规划→B2写作→B3审阅 的完整循环。

### B1: 卷规划

触发: "规划卷"/"大纲" | 前置: A层完成

1. 召回：`novel_get` + `world_query` + `character_list` + `relation_list` + 已有 `volume_list`
2. 如果是第一卷 → 先生成**全书总纲**（一页纸）：
   - 核心冲突 + 终极方向
   - 预计卷数（百万字≈500章/8-15卷）
   - 主角成长弧线关键节点
   - 明暗双线全局规划（暗线分几层揭示）
3. **逐卷规划**：
   ```
   volume_create(novel_id, number=N, title="卷名",
     main_plotlines=[
       {name:"主线", description:"...", purpose:"推进XXX"},
       {name:"暗线", description:"...", purpose:"揭示XXX的一角"},
       {name:"配角线", description:"...", purpose:"展示XXX的独立弧光"}
     ],
     notes="伏笔埋设计划/配角出场安排/升级节点/替代爽点")
   ```

   **每卷必定义**：
   - 主线推进程度 + 暗线揭示多少（不能一次揭完）
   - 重点出场配角(2-4人)及弧光
   - 升级节点（如有）或替代爽点（势力博弈/智斗/信息差/以弱胜强）
   - 伏笔计划：埋几条、回收几条旧伏笔
   - 卷尾状态：主角水平、世界格局变化

4. 卷确认后 → 章节场景清单：
   ```
   chapter_plan(novel_id, number=N, title, outline, chapter_type, volume_id)
   scene_create(chapter_id, scene_number, location, characters_involved,
                conflict, emotion_type, key_beats)
   ```
5. 跨卷伏笔：`foreshadow_plant(novel_id, description, planted_chapter_id, planned_recall_chapter, importance, related_characters)`
6. `git commit -m "B1: 第{N}卷规划完成"`

### B2: 逐章写作

触发: "写第N章"/"继续写"

#### 写前：一键注入上下文

```
writing_start(novel_id, chapter_number)
→ 章节信息 + 前3章摘要 + 活跃人物 + 未回收伏笔 + 世界观 + 当前卷规划
```
一步到位，不需要手动调多个工具。

#### 写时：规则+策略

读 `references/writing-style.md` + `references/anti-ai-patterns.md`

**去AI味要点**：
- 句式长短交替（不要每句15-20字）
- 省略过渡（不要每段"然而""于是""随后"）
- 对话有废话（真人说话有"嗯""啊""那个"）
- 场景有毛边（留点不规整的细节）
- 情绪克制（不要"震惊""难以置信""倒吸凉气"）

**多线交织策略**（每章按优先级安排）：
1. 查当前卷 main_plotlines → 本章属于哪条线的节点
2. 查 `foreshadow_list` → 有计划在附近回收的伏笔吗？
3. 暗线埋设：非暗线章节用日常场景不经意带过（路人闲聊/偶然线索/配角无意透露）
4. 配角出场：检查哪些核心配角最近5章没出场，安排出场或侧面提及
5. 场景切换：同一章不超过2个，切换用空行+时间/地点标注

**章节节奏**：开头10%承接铺垫 → 发展40%核心推进 → 高潮30%最紧张 → 收尾20%钩子悬念
**爽点密度**：每3-5章一个（打脸/逆袭/获得/展示/复仇）

#### 写后：一键更新所有状态（每章必做）

```
writing_finish(chapter_id, summary="章节概要",
  key_events=["事件1","事件2"],
  characters_involved=[人物id列表],
  new_foreshadows=[{description:"伏笔描述",importance:"medium"}],
  resolved_foreshadows=[伏笔id列表],
  ability_level="金丹中期", location="潜龙城",
  timeline_events=[{event_time:"午后", event_order:1, event_description:"XXX"}])
```
一步完成：摘要保存 + 章节状态更新 + 伏笔回收 + 维度变更(ability/space) + 时间线记录。不需要分别调5个工具。

#### 每10章：自动健康快检

```
foreshadow_list(status="planted") → 未回收伏笔数和最老章距
character_list → 检查谁长期没出场
dimension_query(dimension="ability") → 升级节奏是否合理
```
如果发现问题 → **暂停提醒用户**（不自动改，等人确认）

#### 输出

`novels/{小说名}/正文/第{NNN}章-{标题}.md` → `git commit -m "ch{N}: {标题}"`

### B3: 审阅

触发: "审阅"/"检查"

1. 读 `references/review-checklist.md`
2. 用 `db_search`/`foreshadow_list`/`dimension_query` 获取数据
3. 3个Agent并行：
   - **A-逻辑**: `timeline_query`+`dimension_query` 检查时间/空间/能力一致性，`foreshadow_list(status="planted")` 查超30章未回收伏笔标黄
   - **B-人设**: `character_list` 对照人设检查OOC，AI味检测（对照 `anti-ai-patterns.md` 高频词黑名单+Memory中的 `shared,anti-ai-pattern` 新发现模式）
   - **C-合规+竞争力**: 平台合规（参考 `platform-rules.md`），爽点密度（每3-5章检查），钩子有效性，侧面描写充实度
4. 汇总 → `novels/{小说名}/审阅报告/` → 问题分级：致命(必须改)/严重(建议改)/轻微(可选)

---

## C层: 运维（按需触发）

### C1: 平台上架

触发: "上架" | 读 `references/platform-rules.md` → 合规检查 + 降AI率 + 排版适配

### C2: 健康诊断

触发: "诊断"/"卡文"/"疲劳"

**一键诊断**：
```
health_check(novel_id)
→ 进度 + 伏笔积压(回收率/最老章距) + 配角活跃(出场间隔>10章标黄) + 升级曲线 + 卷完成度 + 警告列表
```

**健康指标**：

| 指标 | 健康 | 异常 |
|------|------|------|
| 伏笔积压 | 未回收<40% | >50%且最老>30章 |
| 配角活跃 | 核心配角5章内提及 | >10章无提及 |
| 升级节奏 | 符合genre建议 | 40章无升级且无替代爽点 |
| 日常密度 | 5-8章有日常 | 连续10章纯战斗 |
| 暗线推进 | 15-20章有新进展 | >30章无新线索 |

**破局方案**：
- **升级衰减**：切爽点类型（升级碾压→势力博弈/智斗/信息差/以弱胜强），引新体系（炼丹/阵法/灵兽）
- **配角遗忘**：信息差回归（他在暗处做了什么？），独立线与主线交汇，侧面描写维持存在
- **伏笔膨胀**：批量回收（选3-5条重要伏笔2-3章内回收），长线伏笔延后新卷，果断放弃不重要的

### C3: 级联更新

触发: "改设定"
1. 改对应数据（`world_upsert`/`character_update`）
2. `db_search(novel_id, keyword)` 找受影响内容
3. 列出受影响章节 → 询问用户哪些需要改

---

## D层: 查询

### 状态总览

触发: "进度"/"状态"

```
novel_get + volume_list + chapter_list + foreshadow_list + character_list
→ 项目名/阶段/卷进度/章节数/人物数/伏笔回收率/最近章节
```

### 素材操作

触发: "加素材"/"拆书"
- 内容 → `memory_store(tags="shared,material")`
- 拆书 → `memory_store(tags="shared,analysis")`
- 新AI味 → `memory_store(tags="shared,anti-ai-pattern")`

---

## Memory 数据模型

| type | tags |
|------|------|
| 灵感碎片 | project:{名},idea |
| 核心决策 | project:{名},decision |
| 写作经验 | project:{名},learning |
| AI味黑名单 | shared,anti-ai-pattern |
| 通用素材 | shared,material |
| 拆书笔记 | shared,analysis |

## Git 规范

`A1/A2/A3/B1/B3: {描述}` | `ch{N}: {标题}` | `更新: {描述}`
