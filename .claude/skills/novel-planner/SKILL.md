---
name: novel-planner
description: 小说卷规划，含全书总纲、逐卷环境先行设计、章节场景清单和跨卷伏笔。触发词：规划卷/大纲/卷大纲
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, mcp__novel-db__novel_get, mcp__novel-db__world_query, mcp__novel-db__world_upsert, mcp__novel-db__character_list, mcp__novel-db__character_get, mcp__novel-db__relation_list, mcp__novel-db__volume_create, mcp__novel-db__volume_list, mcp__novel-db__volume_get, mcp__novel-db__volume_update, mcp__novel-db__chapter_plan, mcp__novel-db__scene_create, mcp__novel-db__scene_list, mcp__novel-db__foreshadow_plant, mcp__novel-db__foreshadow_list, mcp__novel-db__engine_detail, mcp__novel-db__rule_detail
lifecycle: core
---

# 小说卷规划

<what-to-do>

## 强制流程

```
召回(novel_get+world_query+character_list+volume_list) →
全书总纲(首卷) → 🔒确认 →
逐卷规划(环境先行: engine_detail('environment')) → 🔒确认 →
章节场景(chapter_plan+scene_create) → 跨卷伏笔(foreshadow_plant) → git commit
```

每卷规划完必须 🔒确认 才能进入场景创建。

</what-to-do>

<supporting-info>

## 全书总纲（首卷必做）
- 核心冲突 + 终极方向 + 预计卷数(8-15)
- 主角成长弧线关键节点
- 明暗双线全局规划
- 🔒用户确认后才继续

## 逐卷规划
```
volume_create(novel_id, number=N, title="卷名",
  main_plotlines=[{name, description, purpose}, ...],
  notes="伏笔计划/配角安排/升级节点/替代爽点")
```

每卷必含：主线推进 + 暗线揭示 + 配角弧光 + 升级/爽点 + 伏笔计划

**环境先行**: 识别本卷主要场景(2-5个) → `engine_detail('environment')` 查看5要素 → `world_upsert(category='location')` → 再规划事件

**因果逻辑**: `engine_detail('causality')` 查看因果大纲法 → 每事件必须有前因后果

## 章节场景清单
```
chapter_plan(novel_id, number, title, outline, chapter_type, volume_id)
scene_create(chapter_id, scene_number, location, conflict, emotion_type, ...)
```
场景快照(≤200字): 地点 | 时间 | 人物 | 物品 | 目标 | 感官细节

## 跨卷伏笔
`foreshadow_plant(novel_id, description, planned_recall_chapter, importance, tags)`

## 大纲验证
三Agent审查 → P0必须修复 → 🔒通过后进入场景

参考 `references/outline-review-checklist.md`（审阅报告用）

</supporting-info>
