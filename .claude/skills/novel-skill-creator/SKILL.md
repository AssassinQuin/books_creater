---
name: novel-skill-creator
description: 小说技能创建指南 — 创建新技能的标准化流程、模板和审查清单。触发词：创建技能/新建技能/加技能/add skill。
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
lifecycle: meta
---

# 小说技能创建指南

> **用途**: 当需要为 books_creater 系统添加新技能时，按本指南执行。
> **原则**: 小而美、可组合、渐进式披露。

<what-to-do>
## 创建流程（3步）

1. **需求收集**: 确定技能名称、触发词、核心功能、与现有技能的关系
2. **草稿编写**: 按 SKILL.md 模板 + frontmatter 规范编写
3. **审查发布**: 通过审查清单后放入对应桶目录

每个步骤必须完成才能进入下一步。
</what-to-do>

<supporting-info>

## SKILL.md 模板

```markdown
---
name: {技能名}
description: {一句话能力描述}。触发词：{词1}/{词2}/{词3}。
allowed-tools: {工具列表}
lifecycle: core | quality | experimental | deprecated
---

# {技能标题}

> 共享约定：读 `references/shared-conventions.md`

<what-to-do>
## 强制流程

```
{步骤1} → {步骤2} → 🔒{检查点} → {步骤3}
```
</what-to-do>

<supporting-info>
## 详细步骤说明

{每个步骤的详细指令...}
</supporting-info>
```

## Frontmatter 规范

| 字段 | 必填 | 格式 | 限制 |
|------|------|------|------|
| name | 是 | kebab-case | ≤30字符 |
| description | 是 | 一句话能力 + "触发词：" + 3-5个关键词 | ≤512字符 |
| allowed-tools | 是 | 逗号分隔 | 仅列出实际使用的工具 |
| lifecycle | 是 | core/quality/experimental/deprecated | 见桶分级定义 |

### description 写法

```
{能力一句话描述}。触发词：{词1}/{词2}/{词3}。
```

**好例子**:
- "逐章写作引擎，驱动从大纲到成文的完整流程。触发词：写第N章/继续写/写一章"
- "小说全链路质量保障，含审阅、诊断和级联更新。触发词：审阅/检查/诊断/改设定/OOC"

**坏例子**:
- "这个skill用来写章节，包含引擎驱动、事件体系、场景搭建、人物鲜活、世界观植入、NPC互动、分支事件、增量同步"（太长，包含实现细节）
- "写作"（太短，无触发词）

## 拆分阈值

| 条件 | 操作 |
|------|------|
| SKILL.md ≤ 100行 | 无需拆分 |
| SKILL.md 100-200行 | 考虑拆分支撑信息到独立 .md 文件 |
| SKILL.md > 200行 | 必须拆分。核心流程留在 SKILL.md，详细指令移到子文档 |

### 拆分原则

- **SKILL.md** 只保留: frontmatter + 核心流程（Step 概览）+ 强制检查点 + 子文档引用
- **子文档** 命名: 大写 + 短横线（如 `WRITING-CORE.md`, `EVENT-SYSTEM.md`）
- **子文档位置**: 与 SKILL.md 同目录
- **引用方式**: 在 SKILL.md 中用 `> 读 {子文档名} — {一句话说明}` 引用

## 桶分级（lifecycle）

| 桶 | 用途 | 自动路由 | 示例 |
|----|------|---------|------|
| core | 核心创作流程 | 是 | novel-writer, novel-chapter-writer |
| quality | 质量保障 | 是 | novel-qa, novel-battle, novel-reviser |
| experimental | 实验性功能 | 否 | darwin-skill, 新原型 |
| deprecated | 已废弃 | 否 | 被替代的旧版技能 |

## 审查清单

创建新技能后，逐项检查：

- [ ] **触发精确**: description 包含 3-5 个触发词，格式为"触发词：词1/词2/词3"
- [ ] **SKILL.md ≤ 100行**: 或已拆分支撑信息到子文档
- [ ] **what-to-do/supporting-info 分层**: 核心指令在 what-to-do 标签中
- [ ] **强制流程有检查点**: 关键步骤有 🔒 标记
- [ ] **术语一致**: 使用 NOVEL-CONTEXT.md 中的标准术语
- [ ] **引擎引用正确**: 引用 `references/engine-*.md` 时路径正确
- [ ] **lifecycle 标记**: frontmatter 中包含正确的生命周期标记
- [ ] **无重复功能**: 与现有技能无功能重叠（如有，考虑合并或拆分边界）
- [ ] **allowed-tools 最小化**: 只列出实际使用的工具

## 参考文档组织规范

- 通用参考文档放 `novel-writer/references/`
- 技能专属参考文档放 `{技能目录}/` 下
- 引用路径使用相对路径: `references/{文件名}.md`

</supporting-info>
