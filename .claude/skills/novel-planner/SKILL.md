---
name: novel-planner
description: 小说卷规划 — 全书总纲、逐卷规划、环境先行事件设计、章节场景清单、跨卷伏笔埋设。触发词：规划卷/大纲/卷大纲/全书大纲。
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, mcp__novel-db__novel_get, mcp__novel-db__world_query, mcp__novel-db__character_list, mcp__novel-db__character_get, mcp__novel-db__relation_list, mcp__novel-db__volume_create, mcp__novel-db__volume_list, mcp__novel-db__volume_get, mcp__novel-db__volume_update, mcp__novel-db__chapter_plan, mcp__novel-db__scene_create, mcp__novel-db__scene_list, mcp__novel-db__foreshadow_plant, mcp__novel-db__foreshadow_list, mcp__novel-db__world_upsert
---

# 小说卷规划

> 共享约定：读 `.claude/skills/novel-writer/references/shared-conventions.md`
> 环境引擎：读 `.claude/skills/novel-writer/references/engine-environment.md`
> 快照引擎：读 `.claude/skills/novel-writer/references/engine-snapshot.md`

## 强制流程

```
B1: 召回数据 → 全书总纲(首卷) → 🔒确认 → 逐卷规划(环境先行) → 🔒卷确认 → 章节场景(含快照) → 跨卷伏笔 → commit
```

每卷规划完必须 🔒确认 才能进入章节场景创建。用户说"改"→ 回退修改。

---

## B1: 卷规划

触发: "规划卷"/"大纲" | 前置: A层完成

1. 召回：`novel_get` + `world_query` + `character_list` + `relation_list` + 已有 `volume_list`
2. 如果是第一卷 → 先生成**全书总纲**（一页纸）：
   - 核心冲突 + 终极方向
   - 预计卷数（百万字≈500章/8-15卷）
   - 主角成长弧线关键节点
   - 明暗双线全局规划（暗线分几层揭示）
   - 🔒**用户确认总纲**后才继续
3. **逐卷规划**（环境先行）：
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

### 环境先行设计（每卷必做）

在规划事件前，先设计该卷涉及的**核心环境**：

1. 识别本卷主要场景地点（2-5个）
2. 每个地点按 `engine-environment.md` 的5要素建立档案：
   - 空间结构 / 灵能维度 / 感官层 / 时间维度 / 情绪映射
3. 存入 `world_upsert(category="location", name="{地点名}", data={环境档案})`
4. 环境设计完成后，再规划该环境中发生的事件

**大事件多环境切换**：
```
事件: {事件名}
├── 环境1: {地点A} ({事件阶段1})
├── 环境2: {地点B} ({事件阶段2})
├── 环境3: {地点C} ({事件阶段3})
└── 环境间过渡: {怎么从A到B到C}
```
每个环境独立建档案，过渡段标注时间和距离。

4. **大纲验证（强制）**：每卷规划完成后，启动 `outline-review-checklist.md` 三Agent审查：
   - Agent A: 因果链 + 叙事结构（开篇钩子/因果链完整性/场景过渡/节奏）
   - Agent B: 角色动机 + 行为逻辑（关键动作动机/并行线/特别检查项）
   - Agent C: 商业性 + 信息密度（爽点/弃文风险/伏笔管理）
   - 生成大纲审查报告，标记P0-P3问题
   - **P0问题必须修复后才能继续**

   🔒**大纲审查通过后确认**才进入章节场景。

4. 卷确认后 → 章节场景清单（含快照）：
   ```
   chapter_plan(novel_id, number=N, title, outline, chapter_type, volume_id)
   scene_create(chapter_id, scene_number, location, characters_involved,
                conflict, emotion_type, key_beats)
   ```

   **场景快照**（每章创建场景时同步生成，参照 `engine-snapshot.md`）：
   ```
   场景快照（≤200字速记）:
   地点: {参照world_query的地点档案}
   时间: {时段+天气}
   人物: {出场人物+当前位置+身体状态}
   物品: {关键物品+状态}
   目的: {这章的人物目标}
   环境: {感官基线的1-2个关键细节}
   ```

   代表性地点写入 `world_upsert(category="location")`，后续正文写作时直接加载。

5. 跨卷伏笔：`foreshadow_plant(novel_id, description, planted_chapter_id, planned_recall_chapter, importance, related_characters)`
6. `git commit -m "B1: 第{N}卷规划完成"`

完成后建议：`/novel-chapter-writer` 开始逐章写作。

---

## 大纲更新

触发: 用户在写作过程中想修改某卷规划

1. `volume_get(volume_id)` 读取当前规划
2. 修改 → `volume_update(volume_id, ...)`
3. 如果改了已写章节的大纲 → 检查 `chapter_list(volume_id)` 标注受影响章节，提醒用户
4. `git commit -m "更新: 第{N}卷大纲调整"`

---

## 断点续传

触发时先检查 `memory_search(query="flow-state", tags=["project:{名},flow-state"])`
有记录 → "上次我们在{步骤}暂停了，从那里继续？"
