---
name: novel-setup
description: 小说项目基建，含头脑风暴、世界观建模和物品档案管理。触发词：头脑风暴/建世界观/设定/加物品
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, Agent, mcp__novel-db__novel_create, mcp__novel-db__novel_list, mcp__novel-db__novel_get, mcp__novel-db__novel_update, mcp__novel-db__world_upsert, mcp__novel-db__world_query, mcp__novel-db__world_delete, mcp__novel-db__engine_detail, mcp__novel-db__rule_detail
lifecycle: core
---

# 小说项目基建

<what-to-do>

## 强制流程

```
A1: novel_create + 头脑风暴 → 🔒输出决策卡 → git commit
A2: world_query(已有) → world_upsert(逐维度) → 🔒交叉验证 → git commit
物品: world_query(查重) → engine_detail('item') → world_upsert(category='ability'/'economy')
```

所有 `world_upsert` 后必须 🔒 用户确认。

</what-to-do>

<supporting-info>

## A1: 项目启动
触发："头脑风暴"/"灵感"

1. 确认小说名，`novel_create` 创建
2. 逐问深挖：画面→主角→情绪→对立面→独特规则，每次只问一个
3. 每次回答存 `memory_store(tags="project:{名},idea")`
4. 🔒 输出决策卡（核心冲突/主线方向/读者情绪/亮点场景/品类节奏）
5. 用户选定 → `novel_update(genre, status)` + `memory_store` + git commit

创作决策做 ADR：`docs/decisions/ADR-TEMPLATE.md`

## A2: 世界观建模
触发："建世界观" | 前置：项目已创建

1. `world_query(novel_id)` 查已有维度
2. 引导模式（默认）：先确立双锚点（危机锚+变量锚）→ 核心稀缺资源 → 世界观刑具化 → 涟漪效应 → 逐维度展开
3. 快速模式：基于品类模板一次生成8维度
4. 每维度完成 → `world_upsert(novel_id, category, name, data={...})` → 🔒确认
5. 🔒交叉验证：锚点稳固/稀缺真实/涟漪完整/价值一致性和跨维度检查

**参考**: `engine_detail('causality')` 查看因果逻辑法；`references/worldbuilding-template.md`

## 物品档案
触发："加物品" | 新物品首次出现时

1. `world_query(name='{物品名}')` 确认不重复
2. `engine_detail('item')` 查看文章生命周期模板
3. `world_upsert(category='ability'/'economy', name='{物品名}', data={完整档案})`
4. 🔒确认档案完整性

## 断点续传
`memory_search(query="flow-state", tags=["project:{名},flow-state"])`

</supporting-info>
