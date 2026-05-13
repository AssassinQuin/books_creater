# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

百万字网文创作引擎 — AI-powered Chinese web novel writing system. Uses Claude Code skills + MCP (Model Context Protocol) for structured, long-form novel creation with anti-AI-writing patterns, ensemble casts, and dual-track plotting.

Current project: **《这次不一样了》** — 14卷+尾声, 百万字级玄幻网文. Novel DB id: 1.

## Domain Vocabulary

**`NOVEL-CONTEXT.md`**（项目根目录）定义了所有核心术语的标准含义。所有技能处理术语时必须以此文件为准。

**`SENTENCE-PATTERNS.md`**（项目根目录）定义了反AI句式系统——标点多样性引擎、信息投放节奏、场景结构随机组合、否定句式管理、意象梯度系统、环境音效轮换库。所有章节写作必须遵守其中的反AI指纹消除规则。

## Architecture

Three-layer data architecture:
- **novel-db MCP** (PostgreSQL): Structured data — world-building, characters, chapters, foreshadowing, timelines, dimensions. Server at `/Users/ganjie/skills/novel-db-mcp/server.py`, connects to `postgresql://localhost:5432/fcli`
- **Memory MCP** (16 tools): Unstructured creative data — inspiration, writing experience, cross-project materials, anti-AI pattern blacklist. **必须先加载 memory skill 再调用任何 memory_memory_* 工具**。详见 [Memory Skill](#memory-integration)
- **Git files**: Human-readable content — novel text, setting docs, review reports in `novels/{小说名}/`

### Skill System

Skills follow **progressive disclosure** design — each SKILL.md contains core flow in `<what-to-do>` and detailed instructions in `<supporting-info>`. Sub-documents are loaded on demand.

#### External Skills Repository

`/home/z/my-project/skills/` 目录包含通用 skill 仓库（`https://github.com/AssassinQuin/skills.git`）。以下写作相关 skill 已同步加载：

| Skill | 路径 | 用途 | 何时使用 |
|-------|------|------|----------|
| **web-novel-writer** | `skills/web-novel-writer/SKILL.md` | 高质量网文正文写作引擎（多视角叙事+电影级画面感+严密逻辑体系） | B2章节写作时参考 |
| **novel-framework** | `skills/novel-framework/SKILL.md` | 百万字级框架设计系统（9大Agent：世界观/时空/人物/关系/能力/物品/故事/线索/逻辑校验） | A2建世界观、A3人物设计、B1大纲规划 |
| **storytelling** | `skills/storytelling/SKILL.md` | 故事创作方法论（三幕剧/英雄旅程/角色冰山模型/对话技巧/世界观建构） | 创作方法论参考 |
| **prose-craft** | `skills/prose-craft/SKILL.md` | 散文质量引擎（Voice发现/Styleguide选择/句子节奏/段落构建/强开篇强收尾） | 写作质量提升、文风调整 |
| **memory** | `skills/memory/SKILL.md` | 持久化记忆管理（16个MCP工具、标签体系、跨Skill API） | 任何需要存储/检索记忆时 |
| **mcp-builder** | `skills/mcp-builder/SKILL.md` | MCP服务开发指南（Python FastMCP / TypeScript SDK） | 构建新的MCP服务时 |

**注意**：这些外部 skill 不替代本项目已有的 skill 系统，而是作为**补充参考**。项目内 skill（novel-writer/novel-setup/novel-character/novel-planner/novel-chapter-writer/novel-qa/novel-battle/novel-reviser）仍然是核心工作流。

#### Skill Lifecycle (Bucket System)

| Bucket | Purpose | Skills | Auto-routed |
|--------|---------|--------|-------------|
| **core** | Core creation flow | novel-writer, novel-setup, novel-character, novel-planner, novel-chapter-writer | Yes |
| **quality** | Quality assurance | novel-qa, novel-battle, novel-reviser | Yes |
| **experimental** | Experimental features | darwin-skill | No |
| **deprecated** | Deprecated | (empty) | No |
| **meta** | Meta-tools | novel-skill-creator | No |

Each skill has a `lifecycle` field in YAML frontmatter indicating its bucket.

#### Decision Records

Important creative decisions are recorded as ADRs in `docs/decisions/`. See `docs/decisions/ADR-TEMPLATE.md` for format. Decisions must pass the three-condition gate (irreversible + non-obvious + real tradeoff).

## Workflow Phases

| Phase | Purpose | Trigger Keywords |
|-------|---------|-----------------|
| A1 | Project bootstrap | "头脑风暴"/"灵感" |
| A2 | World-building | "建世界观"/"设定" |
| A3 | Character design | "设计人物"/"人物卡" |
| B1 | Volume planning | "规划卷"/"大纲" |
| B2 | Chapter writing | "写第N章"/"继续写" |
| B3 | Review | "审阅"/"检查" |
| C1 | Platform publishing | "上架"/"发布" |
| C2 | Health diagnosis | "诊断"/"卡文" |
| C3 | Cascade updates | "改设定"/"调整" |
| D | Status/materials | "进度"/"加素材" |

Priority on conflict: C3 > B2 > others.

## Key Orchestration Tools

- `writing_start(novel_id, chapter_number)` — one-shot context injection before writing (chapter info + last 3 summaries + active characters + unrecycled foreshadowing + world settings + current volume plan)
- `writing_finish(chapter_id, ...)` — one-shot state update after writing (summary + events + foreshadowing + timeline + dimensions)
- `health_check(novel_id)` — one-shot diagnosis (foreshadowing backlog + side character activity + upgrade pacing + daily scene density + hidden plot progress + volume completion)

## File Organization Rules

- **反AI系统 (`SENTENCE-PATTERNS.md`)**: 反AI句式系统，包含6大引擎（标点多样性/信息投放节奏/场景结构随机组合/否定句式管理/意象梯度/环境音效轮换）。写作前必读，写作后逐项检查。与 writing-style.md 同级。
- **设定文件**: 详情内容写在 `角色深化.md` / `世界观.md` / `地图.md` / `线索追踪.md` 等
- **大纲中使用指针**: 引用详情时写 `→见角色深化·关系成长路径` 而不是复制内容
- **灵感库 (`设定/灵感库/`)**: 只放调研、头脑风暴、可复用方法论. 不放审计报告
- **审阅报告 (`审阅报告/`)**: 审计发现、问题清单、修复方案
- **决策记录 (`docs/decisions/`)**: 不可逆的创作决策（ADR格式）
- **单源维护**: 同一内容(伏笔/线索/关系/设定)只在主文件描述完整, 其他文件用指针引用
- **写作执行规范** (`设定/写作执行规范.md`): **最高优先级**，每章必须严格遵守字数要求、内容依据、写作规范、检查清单。违反规范必须重写。详见文件内容。

## Current Project Status (2026-05-10)

- 14卷+尾声大纲完成, Phase3验证通过(综合90/100)
- 10维度达尔文评估→R1-R5女娲修复→Phase3验证全流程完成
- 审阅报告存于 `审阅报告/大纲审查-Phase2修复-2026-05-09/`
- novel-db数据库已同步(15卷/15章/21伏笔/4时间线事件)
- 残留4条P3轻微问题(不影响正文): 鸦成长中间节点/F8伏笔/V3爽感/V4练习场
- 下一步: 正文生成(B2), 从V1开始

## Anti-AI Writing System (Critical)

AI-generated novel text has detectable fingerprints. The `SENTENCE-PATTERNS.md` system addresses 6 identified fingerprints:

| Fingerprint | Problem | Solution |
|-------------|---------|----------|
| F1 Period-cutting | Overuse of periods to create short "breathing" sentences | Punctuation diversity engine: require 3+ punctuation types per paragraph, 8-15 em-dashes per chapter |
| F2 Explain-after-introduce | Every setting immediately followed by explanation | 3-layer info delivery: introduce via action → demonstrate via conflict → explain when needed |
| F3 Symmetrical structure | Every scene follows identical template | Scene structure randomizer: 6 entry types × 8 body types × 6 closing types, no two adjacent scenes identical |
| F4 Negation-pattern excess | "Not X, but Y" overused (15+ times in 25 chapters) | Hard cap: ≤1/chapter, ≤5/book. 8 negation alternatives provided |
| F5 Image overfrequency | Same imagery repeated without variation | Imagery gradient system + replacement library |
| F6 Environment white-noise | Same ambient sounds repeated 30+ times | Rotation library, ≤2 same-type sounds per chapter |

All skill files must reference SENTENCE-PATTERNS.md and enforce its rules in generated content.

---

## Git Commit Convention

```
A1/A2/A3/B1/B3: {description}    # milestone commits
ch{N}: {标题}                      # chapter commits
更新: {description}                # other changes
```

## Content Output

Novel text goes to `novels/{小说名}/正文/第{NNN}章-{标题}.md`.

## MCP Configuration

Configured in `.mcp.json`. The `novel-db` MCP server is a Python process that must have PostgreSQL running locally on port 5432 with database `fcli`.

## Memory Integration

### 概述

Memory MCP 提供 16 个工具，用于跨会话持久化知识管理。**必须先加载 memory skill 才能调用**，禁止直接调用 `memory_memory_*` 工具。

### 标签体系

| Scope | 别名 | 含义 | 示例 |
|-------|------|------|------|
| 项目专属 | `project` | 仅当前项目可见，存储时自动追加 `project:books_creater` | 写作决策、项目规范 |
| 共享 | `shared` | 跨项目复用的技术知识 | 写作方法论、反AI模式 |
| 全局 | `global` | 用户偏好，所有项目可用 | 语言偏好、工具配置 |
| 会话 | `session` | 临时会话状态 | 待办、中间状态 |

| Type | 含义 |
|------|------|
| `decision` | 架构/技术选型决策 |
| `convention` | 编码/写作规范、命名规则 |
| `preference` | 用户偏好 |
| `learning` | 经验教训、洞察 |
| `context` | 项目状态、事实信息 |
| `bug` | 已知问题及修复 |
| `reference` | 文档参考 |
| `pattern` | 可复用的代码/写作模式 |

### 本项目 Memory 使用场景

| 场景 | Scope | Type | 示例 |
|------|-------|------|------|
| 保存写作决策 | `project` | `decision` | "V3章末不回收F8伏笔，推迟到V5" |
| 保存反AI模式 | `shared` | `pattern` | "否定句式消解8种写法" |
| 保存灵感/方法论 | `project` | `reference` | "低智商犯罪-蒸馏写作手法" |
| 保存人物行为记录 | `project` | `context` | "沈野V2CH30获得共振卡" |
| 保存用户偏好 | `global` | `preference` | "每章正文3000-5000字" |
| 会话结束批量提取 | 自动 | 自动 | `memory_harvest(sessions=1)` |

### Memory 工具速查

**核心CRUD**：`memory_store` / `memory_search` / `memory_list` / `memory_update` / `memory_delete`
**批量操作**：`memory_cleanup` / `memory_ingest` / `memory_harvest` / `memory_store_session`
**质量管理**：`memory_health` / `memory_stats` / `memory_quality`
**图与冲突**：`memory_conflicts` / `memory_resolve` / `memory_graph`

**完整参数参考**：`/home/z/my-project/skills/memory/references/mcp-tools.md`
