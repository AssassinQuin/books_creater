---
name: novel-plan
description: 大纲规划（全书或单卷）。触发词：规划大纲/设计卷/全书框架/章节规划
allowed-tools: mcp__novel-db__*, Read, Write, Edit, Glob, Grep, Bash, Agent, Task
version: "2.0.0"
---

# 大纲规划

## 触发
用户说"规划大纲""设计卷""全书框架""章节规划"。

## 前置检查
- 项目已创建（novel-setup 完成）
- 世界观 ≥ 3 维度，角色 ≥ 2 个
- 不满足 → 提示用户先补齐，不自动跳转

## 模式选择（问用户）
1. **全书框架** — 每卷"做什么"，不设计具体事件
2. **单卷大纲** — 某卷每章"怎么做"

用户选哪个做哪个，不自动串联。

## 全书框架
1. 加载：`world_query` + `character_list` + `foreshadow_list` + 氛围 DNA
2. 设计框架（起承转合/卷功能/因果链/主线暗线）
3. 用户确认 → `volume_create` / `volume_update` + `foreshadow_plant`
4. 写入 `novels/{小说名}/设定/大纲/`

## 单卷大纲
1. 加载：`volume_get` + 全书框架 + 角色蒸馏卡 + 未回收伏笔 + 氛围 DNA
2. 设计事件架构（因果链/人物弧光/悬念锚点）→ 用户确认
3. 设计逐章大纲（场景/伏笔/声音适配）→ 用户确认
4. 三视角审查（读者/作者/人物并行）→ 修复 P0
5. `chapter_plan` + `scene_create` + `foreshadow_plant` + 新实体入库
6. 写入 `novels/{小说名}/设定/大纲/V{N}-{卷名}.md`

## 约束
从 `world_settings` / `writing_rules` / 氛围DNA 加载约束。高层覆盖低层。
- 每章 ≥ 3 个可辨识事件
- 因果链不可断
- 巧合计 ≤ 1 次/卷

## 完成后
问用户：设计其他卷 / 开始写正文 / 其他。
