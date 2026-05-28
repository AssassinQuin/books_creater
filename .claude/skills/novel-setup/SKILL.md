---
name: novel-setup
description: 项目创建与世界观构建。触发词：新建小说/建世界观/加设定/加物品
allowed-tools: mcp__novel-db__*, Read, Write, Edit, Glob, Grep, Bash
version: "2.0.0"
---

# 项目创建与世界观构建

## 触发
用户说"新建小说""建世界观""加设定""加物品"。

## 项目创建
1. `novel_create(novel_name)` 建项目
2. 逐问深挖（画面/主角/情绪/对立面/独特规则，每次只问一个）
3. 用户确认决策卡 → `novel_update(status="worldbuilding")`

## 世界氛围 DNA（逐步确认，不一次性生成）
决策卡确认后，逐步与用户确认：
1. 问用户：你的世界什么感觉？（时代/温度/参考作品）
2. 提取氛围标签 → 用户确认 → `world_upsert(category='core_setting', name='世界氛围DNA')`
3. 生成 1-2 个感官锚点 → 用户确认 → 更新 DB
4. 写 1 个参考片段（100-200字）→ 用户确认 → 再写下一个（共 2-3 个）
5. 生成禁忌清单 + 词汇色彩 → 用户确认 → 更新 DB
6. 汇总写入 `novels/{小说名}/设定/写作/world-atmosphere.md`

氛围 DNA 存 DB：`world_upsert(category='core_setting', name='世界氛围DNA', priority=100, is_constant=1)`。下游 skill 通过 `world_query` / `get_chapter_context` 自动获取。

## 世界观维度
逐维度展开，每维度用户确认后才继续：
种族 → 势力 → 地理 → 能力 → 经济 → 日常 → 历史 → 物品

每维度：`world_upsert` → 用户确认 → 下一维度。

## 交叉验证
全部维度完成后跑 6 项验证：
锚点稳固 / 稀缺真实 / 涟漪完整 / 价值一致 / 术语合规 / 氛围一致

## 品类规则注入
根据小说品类，`writing_rule_upsert` 注入品类默认约束（category='genre'）。这些规则可被小说级规则覆盖。

## 约束
从 `world_settings` 和 `writing_rules` 加载当前小说的约束。高层覆盖低层，不硬编码。

## 完成后
问用户：设计人物 / 规划大纲 / 其他。
