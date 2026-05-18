---
name: novel-skill-creator
description: 小说技能创建指南 — 创建新技能的标准化流程、模板和审查清单。触发词：创建技能/新建技能/加技能/add skill。
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
lifecycle: meta
depends_on: CLAUDE.md
version: "1.2.0"
---

# 小说技能创建指南

> **原则**: 小而美、可组合、渐进式披露。所有规则和数据在 MCP 中，不在 SKILL.md 中。

<what-to-do>

## 创建流程（4步）

1. **需求收集**: 确定技能名/触发词/核心功能/所用 MCP 工具
2. **冲突检测**: 检查与现有技能的重叠（见下方冲突检测清单）
3. **草稿编写**: 按新模板（MCP 驱动架构）
4. **🔒 审查确认**: 通过审查清单后展示草稿给用户确认，用户说OK后才放入对应桶目录

### 冲突检测清单（新技能创建前必检）

- [ ] 触发词是否与已有 skill 重叠？（检查 `.claude/skills/*/SKILL.md` 的 `description` 字段）
- [ ] 核心功能是否与已有 skill 重复？（比对 what-to-do 的主要步骤）
- [ ] 如果重叠度 >50%：建议扩展现有 skill 而非创建新 skill
- [ ] 如果互补但有关联：添加 `depends_on` 声明

</what-to-do>

<supporting-info>

## SKILL.md 模板（MCP 驱动版）

```markdown
---
name: {技能名}
description: {一句话能力描述}。触发词：{词1}/{词2}/{词3}
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, mcp__novel-db__get_chapter_context, ...
lifecycle: core | quality | experimental | deprecated
---

# {技能标题}

<what-to-do>
## 强制流程

```
{步骤1} → {步骤2} → 🔒{MCP工具名} → {步骤3}
```

规则由 MCP 管理，通过工具调用注入。SKILL.md 只描述流程和工具调用方式。

- 规则参考: `get_chapter_context` 返回 `rules` 字段（硬约束/推荐/创作原则）
- 引擎参考: `skill_loader('type')`
- 详情钻取: `rule_detail('{key}')`
- 强制校验: `validate_chapter(text)` / `writing_finish(chapter_id, chapter_text, ...)`
</what-to-do>
```

## 审查清单

- [ ] **触发精确**: description 含 3-5 个触发词，格式"触发词：词1/词2/词3"
- [ ] **what-to-do/supporting-info 分层**: 核心指令在 what-to-do，`<what-to-do>` 核心流程 ≤200 行，总文件含 supporting-info 不限
- [ ] **强制流程有检查点**: 关键步骤有 🔒 标记
- [ ] **引用 MCP 工具**: 不写"读 xxx.md"，写"调 `tool()`"
- [ ] **allowed-tools** 包含所有实际调用的 MCP 工具
- [ ] **无重复功能**: 与现有技能无重叠
- [ ] **lifecycle 标记正确**
- [ ] **version 字段**: 遵循 semver（如 "1.0.0"）

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

## 失败处理

- **创建失败**（SKILL.md 写入错误）：删除已创建的文件和 agents/ 目录
- **审查不通过**：保留 SKILL.md 草稿，标注问题清单，用户确认后修复
- **技能废弃**：将 lifecycle 改为 `deprecated`，添加迁移说明指向替代技能（参考 novel-ability-designer 废弃格式）
- **冲突发现**：创建冲突检测报告，建议合并或重命名

## 示例：创建 novel-battle skill（历史参考）

1. **需求收集**："需要一个专门设计战斗场景的 skill"
2. **冲突检测**：novel-chapter-writer 的 engines/battle.md 已覆盖战斗描写，但缺少独立战斗设计流程 → 可创建
3. **草稿编写**：按模板填写 SKILL.md（触发词：战斗设计/打斗/对战）
4. **审查发布**：frontmatter 完整 ✓ / 流程清晰 ✓ / 边界条件 ✗（缺少多角色战斗的边界） → 补充后发布
5. **集成**：在 novel-writer 路由表添加 "战斗设计" → novel-battle

</supporting-info>
