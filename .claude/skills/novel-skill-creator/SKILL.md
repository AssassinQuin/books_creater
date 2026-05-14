---
name: novel-skill-creator
description: 小说技能创建指南 — 创建新技能的标准化流程、模板和审查清单。触发词：创建技能/新建技能/加技能/add skill。
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
lifecycle: meta
---

# 小说技能创建指南

> **原则**: 小而美、可组合、渐进式披露。所有规则和数据在 MCP 中，不在 SKILL.md 中。

<what-to-do>

## 创建流程（3步）

1. **需求收集**: 确定技能名/触发词/核心功能/所用 MCP 工具
2. **草稿编写**: 按新模板（MCP 驱动架构）
3. **审查发布**: 通过审查清单后放入对应桶目录

</what-to-do>

<supporting-info>

## SKILL.md 模板（MCP 驱动版）

```markdown
---
name: {技能名}
description: {一句话能力描述}。触发词：{词1}/{词2}/{词3}
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, mcp__novel-db__writing_start, mcp__novel-db__validate_chapter, mcp__novel-db__writing_finish, ...
lifecycle: core | quality | experimental | deprecated
---

# {技能标题}

<what-to-do>
## 强制流程

```
{步骤1} → {步骤2} → 🔒{MCP工具名} → {步骤3}
```

规则由 MCP 管理，通过工具调用注入。SKILL.md 只描述流程和工具调用方式。

- 规则参考: `writing_start` 返回 `rules` 字段（硬约束/推荐/创作原则）
- 引擎参考: `engine_detail('type')`
- 详情钻取: `rule_detail('{key}')`
- 强制校验: `validate_chapter(text)` / `writing_finish(chapter_id, chapter_text, ...)`
</what-to-do>

<supporting-info>
## 具体步骤说明

{简要描述流程，引用 MCP 工具名代替"读 xxx.md"}
</supporting-info>
```

## 审查清单

创建新技能后逐项检查：

- [ ] **触发精确**: description 含 3-5 个触发词，格式"触发词：词1/词2/词3"
- [ ] **SKILL.md ≤ 80 行**: 不拆分支撑信息
- [ ] **what-to-do/supporting-info 分层**: 核心指令在 what-to-do
- [ ] **强制流程有检查点**: 关键步骤有 🔒 标记
- [ ] **引用 MCP 工具**: 不写"读 xxx.md"，写"调 `tool()`"
- [ ] **allowed-tools** 包含所有实际调用的 MCP 工具
- [ ] **无重复功能**: 与现有技能无重叠
- [ ] **lifecycle 标记正确**

## 桶分级

| 桶 | 用途 | 自动路由 | 示例 |
|----|------|---------|------|
| core | 核心创作流程 | 是 | novel-writer, novel-chapter-writer |
| quality | 质量保障 | 是 | novel-qa, novel-battle, novel-reviser |
| experimental | 实验性功能 | 否 | darwin-skill |
| deprecated | 已废弃 | 否 | — |

## 文件组织

- SKILL.md 只保留流程和 MCP 工具引用
- 参考文档保留在 `references/` 目录（按需读）
- 所有规则在 `server.py` 的 `ALL_RULES` 中
- 引擎内容在 `server.py` 的 `ENGINE_CONTENT` 或 `world_settings(category='engine_reference')`

</supporting-info>
