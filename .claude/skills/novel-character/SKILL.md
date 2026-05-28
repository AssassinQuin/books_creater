---
name: novel-character
description: 人物设计/修改。触发词：设计人物/加人物/改人物/人物卡
allowed-tools: mcp__novel-db__*, Read, Write, Edit, Glob, Grep, Bash
version: "2.0.0"
---

# 人物设计/修改

## 触发
用户说"设计人物""加人物""改人物""人物卡"。

## 模式（问用户）
1. **新建** — 蒸馏7步创建完整角色
2. **修改** — 更新现有角色档案

## 新建流程
1. `world_query` + `character_list` → 避免重名
2. 蒸馏7步（萃取→深度→洋葱→矛盾→共情→定标→锻造），每步确认
3. 外观 + 对话设计 → 用户确认
4. `character_create` + `relation_create` → `sync_db_to_files`

## 修改流程
1. `character_detail` + `relation_list` → 评估影响范围
2. 用户确认修改内容
3. `character_update` + `relation_update` → `sync_db_to_files`

## 约束
从 `world_query` / `get_chapter_context` 加载约束。高层覆盖低层。
- 外观占档案 5%-15%，用具体特征不用形容词
- 对话设计覆盖 ≥3 种关系类型
- 术语遵循 term-map

## 完成后
问用户：继续设计人物 / 规划大纲 / 其他。
