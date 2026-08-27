---
name: novel-planner
description: 小说卷规划 — 全书总纲、逐卷规划、章节场景清单、跨卷伏笔埋设。触发词：规划卷/大纲/卷大纲/全书大纲。
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, mcp__novel-db__novel_get, mcp__novel-db__world_query, mcp__novel-db__character_list, mcp__novel-db__character_get, mcp__novel-db__relation_list, mcp__novel-db__volume_create, mcp__novel-db__volume_list, mcp__novel-db__volume_get, mcp__novel-db__volume_update, mcp__novel-db__chapter_plan, mcp__novel-db__scene_create, mcp__novel-db__scene_list, mcp__novel-db__foreshadow_plant, mcp__novel-db__foreshadow_list
---

# 小说卷规划

> 共享约定：读 `.claude/skills/novel-writer/references/shared-conventions.md`

## 强制流程

```
B1: 召回数据 → 全书总纲(首卷) → 🔒确认 → 逐卷规划 → 🔒卷确认 → 章节场景 → 跨卷伏笔 → commit
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

   🔒**每卷规划后确认**才进入章节场景。

4. 卷确认后 → 章节场景清单：
   ```
   chapter_plan(novel_id, number=N, title, outline, chapter_type, volume_id)
   scene_create(chapter_id, scene_number, location, characters_involved,
                conflict, emotion_type, key_beats)
   ```
   - 先 `chapter_plan` 创建章节，拿到 `chapter_id`
   - 再 `scene_create` 为每章创建场景

5. 跨卷伏笔：`foreshadow_plant(novel_id, description, planted_chapter_id, planned_recall_chapter, importance, related_characters)`
   - `planted_chapter_id`: 用当前卷的某章 id（已有）
   - `planned_recall_chapter`: 用章节号（非id），写作时再绑定实际 id
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
