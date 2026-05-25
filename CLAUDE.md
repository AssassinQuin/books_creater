# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

百万字网文创作引擎 — AI-powered Chinese web novel writing system. Uses Claude Code skills + MCP for structured, long-form novel creation with anti-AI-writing patterns, ensemble casts, and dual-track plotting.

### Project Variables（项目变量）

> **所有 Skill 必须使用以下变量，禁止硬编码小说名。**

| 变量 | 当前值 | 解析逻辑 |
|------|--------|---------|
| `NOVEL_NAME` | `这次不一样了` | 优先从 CLAUDE.md 读取；若多项目则从用户输入/上下文确定 |
| `NOVEL_DB_ID` | 动态 | 通过 `novel_get(novel_name=NOVEL_NAME)` 查询，不同环境不同 |
| `NOVEL_TOTAL_VOLUMES` | `15` | 含尾声 |

Current project: **《这次不一样了》** — 14卷+尾声, 百万字级玄幻网文.

## Domain Vocabulary

- **`NOVEL-CONTEXT.md`**（项目根目录）：所有核心术语的标准含义，技能处理术语时必须以此文件为准
- **`SENTENCE-PATTERNS.md`**（项目根目录）：反AI句式系统（标点多样性/信息投放/场景结构/否定句式/意象梯度/环境音效），所有章节写作必须遵守
- **`.claude/skills/lorecraft/references/term-map.md`**：灵能玄幻术语映射（数据→讯息/系统→阵法/信号→灵波等）。卷级大纲/章节正文/设定文件生成前加载，写后逐条检查术语合规

## Architecture

### Data Architecture

Three-layer data architecture:
- **novel-db MCP** (libsql): 结构化数据 — 世界观、角色、章节、伏笔、时间线。Server at `novel-db-mcp/server.py`，数据存储在 `data/novel.db`。~56 个 MCP 工具，全部按 name 操作（不需要 ID）
- **Memory MCP** (16 tools): 非结构化创意数据 — 灵感、写作经验、反AI模式黑名单。**需要先加载 memory skill 再调用**
- **Git files**: 人可读内容 — 小说正文、设定文档、审阅报告，存放于 `novels/这次不一样了/`

#### 核心原则：DB 为权威源，MCP 为唯一操作方式

**禁止使用 Python/sqlite3 命令操作 DB**。所有数据读写通过 MCP 工具完成。

```
skill操作 → MCP工具 → DB（直接写入）→ sync_db_to_files() → 文件（人可读副本）
```

| 数据类型 | 权威源 | 写入规则 | 读取规则 |
|---------|--------|---------|---------|
| 世界观/地点/物品/能力 | **DB** | MCP写入，完事后 `sync_db_to_files()` | `world_query()` 优先；返回空时回退读文件 |
| 角色档案/关系 | **DB** | MCP写入，完事后 `sync_db_to_files()` | `character_detail()` 优先 |
| 伏笔 | **DB** | MCP写入，完事后 `sync_db_to_files()` | `foreshadow_list()` 优先 |
| 卷级大纲 | **DB** + 文件 | DB为主，文件同步 | `volume_get()` 获取摘要；返回空时回退读文件 |
| 章节正文 | **文件** | 先写文件，再调 `writing_finish` 写DB元数据 | `Read()` 文件获取正文 |
| 审计报告/创意蓝图 | **文件** | 只写文件 | 只读文件 |

#### 同步工具

| 工具 | 用途 |
|------|------|
| `sync_startup(novel_name)` | 启动时对比DB与文件差异，返回冲突报告 |
| `sync_db_to_files(novel_name, data_type?, overwrite?)` | DB→文件同步（可指定类型、强制覆盖） |
| `sync_files_to_db(novel_name)` | 文件→DB同步（卷级大纲notes回写） |

#### 文件结构规范

设定文件按标准模板书写，二级标题对应 DB 字段。模板权威源：`.claude/skills/templates/`。

| 实体类型 | 模板文件 | DB 表 |
|---------|---------|-------|
| 人物 | `templates/character.md` | `characters` |
| 世界观 | `templates/world-setting.md` | `world_settings` |
| 人物关系 | `templates/relation.md` | `character_relations` |
| 伏笔 | `templates/foreshadow.md` | `foreshadows` |
| 卷级大纲 | `templates/volume.md` | `volumes` |

### Chapter Writing: Multi-Agent Pipeline

章节写作采用 **4 子 Agent 流水线**：

```
编排器 (novel-chapter-writer)
  │  Step 1: 调 MCP 收集原始数据
  ↓
Agent 1: Context Curator     → 清洗、压缩、结构化 → 上下文包
  ↓
Agent 2: Creative Director   → 场面设计、因果链、角色弧线、创建新实体 → 创意蓝图
  ↓
Agent 3: Engine Coordinator  → 加载引擎、定制指令 → 引擎指令包
  ↓
Agent 4: Text Generator      → 逐场面写正文、自检 → 章节正文
  ↓
编排器: validate_chapter → writing_finish → 存盘
```

| Agent | 指令文件 | 职责 |
|-------|---------|------|
| Context Curator | `novel-chapter-writer/agents/context-curator.md` | 清洗压缩原始数据，产出上下文包 |
| Creative Director | `novel-chapter-writer/agents/creative-director.md` | 场面设计+因果链+创建新实体，存档创意蓝图 |
| Engine Coordinator | `novel-chapter-writer/agents/engine-coordinator.md` | 加载引擎文件，为每个场面定制指令 |
| Text Generator | `novel-chapter-writer/agents/text-generator.md` | 逐场面生成正文+反AI自检+硬约束自检 |

Agent 2 直接调 MCP 创建新人物/地点/物品/势力/伏笔，无需编排器中转。编排器负责数据采集、校验和存盘。

### Skill System

#### 三层技能架构（SkillX 启发）

Skill 按**规划/功能/原子**三层组织，模型每次只加载当前 Step 需要的约束和方法：

| 层级 | 载体 | 职责 | 加载时机 |
|------|------|------|---------|
| **规划技能** | SKILL.md `<what-to-do>` | "先做什么后做什么"+硬约束+检查点 | skill 触发时 |
| **功能技能** | `agents/*.md` + `shared/*.md` | "如何完成子任务"+工具组合+共享协议 | 执行对应 Step 时 |
| **原子技能** | `engines/*.md` + MCP 工具 | "某个约束/工具怎么用"+参数+失败模式 | 按需加载 |

原子技能三级加载策略：
- **Tier 0（铁律层）**：writing-constraints + anti-ai + anti-ai-patterns + causality — 始终注入
- **Tier 1（基础层）**：writing-style + author-voice + world-element-registry — skill 触发时加载
- **Tier 2（按需层）**：其余 32 个引擎 — 执行对应 Step 时按需加载

#### 共享协议层（`.claude/skills/shared/`）

跨 skill 重复的功能技能，提取为共享模块：

| 协议 | 用途 | 被 skill 引用 |
|------|------|-------------|
| `engine-loading-protocol.md` | 引擎加载→验证→失败处理 | planner/planner-volume/chapter-writer |
| `db-save-protocol.md` | MCP调用→结果校验→错误中止 | planner/planner-volume/chapter-writer |
| `checkpoint-protocol.md` | 展示→确认→修改循环 | planner/planner-volume/chapter-writer |
| `three-perspective-protocol.md` | 三视角审查+红蓝对抗 | planner/planner-volume/qa |
| `consistency-protocol.md` | consistency_guard 调用规范 | planner-volume/chapter-writer |

#### Project Skills (`.claude/skills/`)

| Skill | 触发词 | 核心功能 | 强制检查点 |
|-------|--------|----------|-----------|
| **novel-writer** | 写小说/帮我写/上架/进度 | 总路由器，分发到子技能 | 冲突消歧按 C3>B2 |
| **novel-setup** | 头脑风暴/灵感/建世界观/设定 | 项目初始化、世界观构建 | 🔒 世界观确认后才能进入人物 |
| **novel-character** | 设计人物/加人物/人物卡 | 角色蒸馏7步、外观模板、关系差异化 | 🔒 蒸馏7步+外观+对话完整 |
| **novel-planner** | 规划卷/大纲 | 全书总纲、逐卷环境先行设计 | 🔒 每卷确认后才能进入场景 |
| **novel-planner-volume** | 卷大纲/章节规划/事件设计 | 卷级章节设计（场景+事件+支线） | 🔒 场景清单确认后才能进入正文 |
| **novel-chapter-writer** | 写第N章/继续写/写一章 | Multi-Agent Pipeline 编排器 | 🔒 writing_finish 不可跳过 |
| **novel-creative-analyze** | 创意分析/评好/惊喜度/创意评估 | 创意质量评估（惊喜度/情感/节奏） | 🔒 评分卡确认 |
| **novel-qa** | 审阅/检查/诊断/OOC | 三视角审查+AI指纹检测 | 🔒 P0/P1问题必须修复 |
| **novel-reviser** | 修复/去重/修文/润色 | 文本修订、润色 | - |

> **novel-qa vs novel-creative-analyze**：qa 找错（OOC/因果断裂/术语违规），creative-analyze 评好（惊喜度/情感冲击/节奏）。先过 qa（无P0），再过 creative-analyze（提升质量）。

#### External Skills (`/home/z/my-project/skills/`)

| Skill | 用途 | 何时使用 |
|-------|------|----------|
| **web-novel-writer** | 网文正文写作引擎 | B2章节写作 |
| **novel-framework** | 百万字框架设计 | A2世界观/A3人物/B1大纲 |
| **storytelling** | 故事创作方法论 | 对话设计、人物描写 |
| **prose-craft** | 散文质量引擎 | 文风调整 |
| **memory** | 持久化记忆管理（16个MCP工具） | 存储检索记忆时 |

外部 skill 为**补充参考**，项目内 skill 是核心工作流。

#### Skill Lifecycle

| Bucket | Skills | Auto-routed |
|--------|--------|-------------|
| **core** | novel-writer, novel-setup, novel-character, novel-planner, novel-planner-volume, novel-chapter-writer, novel-creative-analyze | Yes |
| **quality** | novel-qa, novel-reviser | Yes |
| **experimental** | darwin-skill | No |
| **meta** | novel-skill-creator | No |

## Workflow Phases

| Phase | Purpose | Trigger Keywords |
|-------|---------|-----------------|
| A1 | Project bootstrap | "头脑风暴"/"灵感" |
| A2 | World-building | "建世界观"/"设定" |
| A3 | Character design | "设计人物"/"人物卡" |
| B1 | Volume planning | "规划卷"/"大纲"/"卷大纲"/"章节规划" |
| B2 | Chapter writing | "写第N章"/"继续写" |
| B3 | Review | "审阅"/"检查" |
| C1 | Platform publishing | "上架"/"发布" |
| C2 | Health diagnosis | "诊断"/"卡文" |
| C3 | Cascade updates | "改设定"/"调整" |
| D | Status/materials | "进度"/"加素材" |

Priority on conflict: C3 > B2 > others. 阶段指令文件位于 `.claude/skills/phases/`。

## Key Orchestration Tools

### 写作流程

| 工具 | 用途 | 调用时机 |
|------|------|----------|
| `get_chapter_context(novel_name, chapter_number, load_mode)` | 聚合上下文（章节+卷大纲+前3章摘要+角色+伏笔+世界观+关系+时间线+质量历史）。load_mode: smart/volume/targeted/full | 编排器 Step 1 必调 |
| `validate_chapter(chapter_text)` | 写后硬约束校验（标点/否定句式/字数/创作原则） | 编排器 Step 6 强制 |
| `writing_finish(novel_name, chapter_number, ...)` | 写作后状态更新（摘要+事件+伏笔+时间线+维度） | 编排器 Step 6 强制 |
| `health_check(novel_name)` | 健康诊断（伏笔积压/配角活跃/暗线推进/卷完成度） | C2 诊断时 |

### 数据 CRUD

| 工具 | 用途 |
|------|------|
| `foreshadow_update(novel_name, foreshadow_id, ...)` | 伏笔部分更新 |
| `character_batch_detail(novel_name, character_names)` | 批量获取角色详情 |
| `scene_update` / `scene_delete` | 场景更新/删除 |
| `timeline_update` / `timeline_delete` | 时间线更新/删除 |
| `distillation_evolve` / `distillation_get` / `distillation_timeline` / `distillation_compare` | 角色蒸馏演化记录与查询 |

### 写作引擎（`.claude/skills/engines/`）

| 类别 | 文件 | 用途 |
|------|------|------|
| 场景 | `scene-composition.md` / `scene-deepening.md` / `scene-type.md` | 场景结构+深化+类型 |
| 描写 | `environment.md` / `dialogue.md` / `action.md` / `item.md` | 环境/对话/动作/物品 |
| 战斗 | `battle.md` / `ability.md` | 战斗设计+能力系统 |
| 叙事 | `causality.md` / `spiral-structure.md` / `plot-density.md` / `relationship.md` | 因果链+螺旋结构+情节密度+关系 |
| 反AI | `anti-ai.md` / `anti-ai-patterns.md` / `anti-ai-quickref.md` | 反AI指纹消除（quickref为写作时速查卡） |
| 声音 | `author-voice.md` + `author-voice-{emotion,daily,battle,mystery}.md` | 作者声音三层架构 |
| 审查 | `three-perspective.md` + `reader/author/character-perspective-agent.md` | 三视角审查 |
| 其他 | `snapshot.md` / `loading.md` / `writing-style.md` / `corpus-style.md` / `worldbuilding.md` / `world-element-registry.md` | 快照/加载/风格/世界观 |

## Shared Conventions (铁律)

> 详见 `.claude/skills/novel-writer/references/shared-conventions.md`

1. **人物群像** — NPC有自己的生活，反派有自己的逻辑，配角有自己的故事线
2. **去AI味** — 用通感/升格/环境衬托/荒诞笑点+温暖+暴力来写。避免不禁/缓缓/淡淡/微微/代价/反噬等AI味词
3. **日常即世界观** — 用摊贩闲聊、告示栏排名、酒馆物价展示世界
4. **百万字是马拉松** — 卷级规划、配角轮换、伏笔回收节奏、升级衰减后的替代爽点
5. **明暗双线** — 每卷有明线+暗线，暗线分卷递进
6. **因果链不可断** — 每个关键事件必须有充分前因
7. **开篇必须有钩子** — 前三章必须有冲突/悬念/异常信号
8. **角色不能为剧情变笨** — 不能靠"没注意到""没发现"来推动情节

### 流程纪律

- **步骤不可跳过** — 每个 skill 按编号步骤执行
- **🔒 关键检查点必须确认** — 用户说"OK"/"继续"才能下一步
- **断点续传** — 每次触发先检查 Memory 中的 `flow-state`
- **写后必存** — `writing_finish` 不可跳过

## Mandatory Enforcement (强制铁律)

**最高优先级规则，覆盖所有 skill 中的推荐/建议/可选措辞。**

### 规则 1: 全部强制

- `engines/writing-constraints.md` 中所有约束**全部强制**，不通过则拒绝存盘
- `validate_chapter` 将所有约束作为 violations 返回，有 violations 必须修复后才能存盘

### 规则 2: 审计强制

- `validate_chapter()` 每章必须调用
- `writing_finish` 的 `self_check='passed'` 是强制参数
- P0 **立即修复** → P1 **本轮内修复** → P2 **下一轮前修复**
- C3 级联更新需扫描全部影响范围并统一修复

### 规则 3: 字数不足强制充实

触发 `word_count` violation 时，`enrichment` 字段返回三层加压指令，**必须**执行：

```
L1 引擎丰富（<20%）   → 强制选1个 engine_detail 展开
L2 场景深化（20-50%） → 因果链/Telling→Showing/子冲突三选强制
L3 加事件（>50%）     → 强制从大纲找事件或加微事件
```

每次被 reject 后必须比上次更努力（更多引擎/更多段落/引入新内容）。违反 = 流程违规，需重做。

## File Organization

### 设定目录结构（`novels/这次不一样了/设定/`）

```
设定/
├── README.md                    ← 总索引
├── 人物/                        ← 角色档案（28个，DB同步）
├── 世界观/
│   ├── 核心设定/                ← 世界观核心规则（24个文件）
│   ├── 能力/                    ← 能力体系（含角色专属能力+物品）
│   ├── 地点/                    ← 地理设定（17个文件）
│   ├── 异灵/                    ← 异灵图鉴（按等级分组）
│   ├── 物品/                    ← 物品装备（按用途分组）
│   ├── 势力/                    ← 势力（按关系分组）
│   └── 经济体系/日常生活/历史事件/种族/建筑/文化/植物/术语规范
├── 大纲/                        ← 全书概览 + 伏笔清单 + 15卷大纲 + 支线总图
├── 锁定/                        ← 不可变更设定（7个文件）
├── 参考/                        ← 角色快速参考卡/能力方案/镜像设计/受伤追踪
├── 写作/                        ← 写作执行规范 + 作者声音
└── 灵感库/                      ← 调研、头脑风暴、可复用方法论
```

### 其他规则

- **大纲中使用指针**: 引用详情时写 `→见角色深化·关系成长路径` 而非复制
- **审阅报告**: 存放于 `审阅报告/` 目录
- **决策记录**: `docs/decisions/`（ADR格式，需通过三条件门控）
- **单源维护**: 同一内容只在主文件完整描述，其他用指针引用
- **写作执行规范** (`设定/写作/写作执行规范.md`): **最高优先级**，违反需重写
- **正文输出**: `novels/{小说名}/正文/第{NNN}章-{标题}.md`

## Current Project Status (2026-05-20)

- 15卷（含尾声）大纲完成，Phase3 验证通过（综合90/100）
- V1 Ch001-009 深度审计完成
- 多轮审阅完成：冲突检测、锁定设定校验、因果逻辑审计、三视角审查
- 正文碎片 V01-V14 已完成（存于 `正文碎片/`）
- 创意蓝图 Ch1-8 已完成（存于 `创意决策/`）
- DB 数据：28角色、200+世界观条、53伏笔、15卷大纲
- 设定目录已完成重组（人物/世界观/大纲/锁定/参考/写作 分层）
- Skill 体系重构完成：三层架构（规划/功能/原子）+ shared/ 共享协议层 + novel-creative-analyze 新增
- 下一步：正文生成（B2），从 V1 开始

## Anti-AI Writing System (Critical)

`SENTENCE-PATTERNS.md` 应对 6 种 AI 写作指纹：

| 指纹 | 问题 | 解决方案 |
|------|------|---------|
| F1 句号切割 | 短句呼吸感过度 | 标点多样性引擎：每段3+种标点，每章8-15个破折号 |
| F2 即释即解 | 设定引入后立刻解释 | 三层信息投放：动作引入→冲突展示→需要时解释 |
| F3 对称结构 | 场景模板雷同 | 场景结构随机组合器：6×8×6，相邻场景不重复 |
| F4 否定泛滥 | "不是X，而是Y"过多 | 硬上限：≤1/章，≤5/书，提供8种替代写法 |
| F5 意象重复 | 同一意象无变化 | 意象梯度系统+替换库 |
| F6 环境白噪 | 同一环境音重复30+次 | 轮换库，≤2同类型/章 |

## Platform & Command Rules

**执行任何命令前必须先确认当前操作系统平台。** 本项目运行在 Windows 上，所有 shell 命令必须使用 PowerShell 语法，禁止使用 bash/zsh 语法（如 `&&`、`export`、`source`、`cat`、`rm -rf` 等）。如果需要跨平台兼容，使用 Python 脚本而非 shell 命令。Sub-agent 同样受此规则约束——在 task description 中明确标注"Windows PowerShell 环境"。

## Git Commit Convention

```
A1/A2/A3/B1/B3: {description}    # milestone commits
ch{N}: {标题}                      # chapter commits
更新: {description}                # other changes
```

## MCP Configuration

Configured in `.mcp.json`. `novel-db` MCP server at `novel-db-mcp/server.py`，**libsql** 后端，DB 文件 `data/novel.db`。~56 tools，按 name 操作（不需要 ID）。

## Memory Integration

Memory MCP 提供 16 个工具用于跨会话持久化知识管理。**需要先加载 memory skill 再调用**。

标签体系：`project`（项目专属）/ `shared`（跨项目）/ `global`（全局偏好）/ `session`（临时状态）。类型：decision / convention / preference / learning / context / bug / reference / pattern。

核心CRUD：`memory_store` / `memory_search` / `memory_list` / `memory_update` / `memory_delete`
批量操作：`memory_cleanup` / `memory_ingest` / `memory_harvest` / `memory_store_session`
质量管理：`memory_health` / `memory_stats` / `memory_quality`
图与冲突：`memory_conflicts` / `memory_resolve` / `memory_graph`

完整参数参考：`skills/memory/references/mcp-tools.md`
