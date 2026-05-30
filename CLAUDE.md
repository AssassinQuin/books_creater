# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

百万字网文创作引擎 — AI-powered Chinese web novel writing system. Uses Claude Code skills + MCP for structured, long-form novel creation with anti-AI-writing patterns, ensemble casts, and dual-track plotting.

### Project Variables（项目变量）

> **所有 Skill 必须使用以下变量，禁止硬编码小说名。**

| 变量 | 解析逻辑 |
|------|---------|
| `NOVEL_NAME` | 从用户输入/上下文确定 |
| `NOVEL_DB_ID` | 通过 `novel_get(novel_name=NOVEL_NAME)` 查询 |
| `NOVEL_TOTAL_VOLUMES` | 由各小说项目自行定义 |

当前无活跃项目。创建新小说时通过 `novel-setup` skill 初始化。

## Domain Vocabulary

- **`NOVEL-CONTEXT.md`**（项目根目录）：所有核心术语的标准含义，技能处理术语时必须以此文件为准
- **`SENTENCE-PATTERNS.md`**（项目根目录）：反AI句式系统（标点多样性/信息投放/场景结构/否定句式/意象梯度/环境音效），所有章节写作必须遵守
- **`.claude/skills/lorecraft/references/term-map.md`**：灵能玄幻术语映射（数据→讯息/系统→阵法/信号→灵波等）。卷级大纲/章节正文/设定文件生成前加载，写后逐条检查术语合规

## Architecture

### Data Architecture

Three-layer data architecture:
- **novel-db MCP** (libsql): 结构化数据 — 世界观、角色、章节、伏笔、时间线。Server at `novel-db-mcp/server.py`，数据存储在 `data/novel.db`。~56 个 MCP 工具，全部按 name 操作（不需要 ID）
- **Memory MCP** (16 tools): 非结构化创意数据 — 灵感、写作经验、反AI模式黑名单。**需要先加载 memory skill 再调用**
- **Git files**: 人可读内容 — 小说正文、设定文档、审阅报告，存放于 `novels/{小说名}/`

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

### Chapter Writing: Direct Pipeline (v2)

章节写作采用 **编排器直调 MCP + 模型**（novel-write skill）：

```
novel-write
  │  Step 1: get_chapter_context (MCP) → 精简上下文包
  ↓
Step 2: 创意决策 → 用户确认蓝图
  ↓
Step 3: resolve_engines (MCP) → 引擎指令
  ↓
Step 4: 逐场面生成正文 + 自检
  ↓
Step 5: validate_chapter → writing_finish → 存盘
```

约束从 DB 加载（System < Genre < Novel < Volume < Chapter），氛围DNA自动包含在上下文包中。

### Skill System

#### Project Skills (`.claude/skills/`)

6 个核心 skill（v2 精简版，每个 <80 行）。用户直接说触发词即可调用，无需总路由器。

| Skill | 触发词 | 核心功能 | 约束来源 |
|-------|--------|----------|---------|
| **novel-setup** | 新建小说/建世界观/加设定/加物品 | 项目创建、世界观构建、氛围DNA | DB约束层级 |
| **novel-character** | 设计人物/加人物/改人物/人物卡 | 角色蒸馏7步、外观、对话设计 | DB约束层级 |
| **novel-plan** | 规划大纲/设计卷/全书框架/章节规划 | 全书框架 + 单卷大纲 | DB约束层级 |
| **novel-write** | 写第N章/继续写/写一章 | 单章正文生成 | DB约束层级 |
| **novel-review** | 审阅/检查/诊断/OOC/创意分析 | 5种审查模式（大纲/正文/设定/健康/创意） | DB约束层级 |
| **novel-fix** | 修复/润色/改文/去重 | 3种修复模式（修复/润色/术语修复） | DB约束层级 |

约束层级：System < Genre < Novel < Volume < Chapter，高层覆盖低层。氛围DNA通过 `world_upsert(category='core_setting')` 存DB，下游skill通过 `world_query` / `get_chapter_context` 自动获取。

#### 已废弃 Skills（请勿使用）

novel-writer（路由器，不再需要）/ novel-planner-volume（合并入 novel-plan）/ novel-chapter-writer（合并入 novel-write）/ novel-qa（合并入 novel-review）/ novel-creative-analyze（合并入 novel-review）/ novel-reviser（合并入 novel-fix）/ novel-ability-designer（合并入 abilitycraft）

#### External Skills

| Skill | 用途 | 何时使用 |
|-------|------|----------|
| **abilitycraft** | 能力设计+命名 | 觉醒者角色能力设计 |
| **lorecraft** | 术语映射+命名 | 术语合规检查 |
| **memory** | 持久化记忆管理（16个MCP工具） | 存储检索记忆时 |

#### Skill Lifecycle

| Bucket | Skills | Auto-routed |
|--------|--------|-------------|
| **core** | novel-setup, novel-character, novel-plan, novel-write | Yes |
| **quality** | novel-review, novel-fix | Yes |
| **deprecated** | novel-writer, novel-planner-volume, novel-chapter-writer, novel-qa, novel-creative-analyze, novel-reviser, novel-ability-designer | No |

## Workflow Phases

| Phase | Purpose | Trigger Keywords → Skill |
|-------|---------|------------------------|
| A | 项目创建+世界观+人物 | "新建小说"/"建世界观"/"设计人物" → novel-setup / novel-character |
| B | 大纲+正文 | "规划大纲"/"设计卷"/"写第N章" → novel-plan / novel-write |
| C | 审查+修复 | "审阅"/"检查"/"诊断"/"修复"/"润色" → novel-review / novel-fix |

用户自己选择当前做什么，skill 不自动串联。每个 skill 完成后问用户下一步。

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

- `writing-constraints.md` 中所有约束**全部强制**，不通过则拒绝存盘
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

### 设定目录结构（`novels/{小说名}/设定/`）

每部小说根据题材自行组织，通用结构参考：

```
设定/
├── README.md                    ← 总索引
├── 人物/                        ← 角色档案（DB同步）
├── 世界观/                      ← 按题材自行分类
├── 大纲/                        ← 全书概览 + 卷大纲 + 支线图
├── 锁定/                        ← 不可变更设定
├── 参考/                        ← 快速参考卡/追踪表
├── 写作/                        ← 写作执行规范 + 作者声音
└── 灵感库/                      ← 调研、头脑风暴、可复用方法论
```

### 其他规则

- **大纲中使用指针**: 引用详情时写指针而非复制
- **审阅报告**: 存放于 `审阅报告/` 目录
- **决策记录**: `docs/decisions/`（ADR格式）
- **单源维护**: 同一内容只在主文件完整描述，其他用指针引用
- **正文输出**: `novels/{小说名}/正文/第{NNN}章-{标题}.md`

## Current Project Status

**活跃项目：这次不一样**（灵气复苏/暗黑修仙 | 起点）

- 状态：`worldbuilding`（世界观构建中）
- 已完成：核心基调（5轴+行为映射+氛围DNA）、能力体系（灵/境界/灵纹/异兽/灵晶阵法）、7个势力（渊守/明堂/猎庭/溯源/祭灵/北庭/余烬）
- 待完成：地理/经济/日常/人物/卷级大纲
- 明堂为最终靶子——灵晶阵法抽灵→灵晶加速修炼→灵衰是代价
- NOVEL_NAME 变量值：`这次不一样`

## Anti-AI Writing System

`SENTENCE-PATTERNS.md` 应对 AI 写作指纹（通用，适用于所有小说）：

| 指纹 | 问题 | 解决方案 |
|------|------|---------|
| F1 句号切割 | 短句呼吸感过度 | 标点多样性引擎 |
| F2 即释即解 | 设定引入后立刻解释 | 三层信息投放 |
| F3 对称结构 | 场景模板雷同 | 场景结构随机组合 |
| F4 否定泛滥 | "不是X，而是Y"过多 | 硬上限+替代写法 |
| F5 意象重复 | 同一意象无变化 | 意象梯度系统 |
| F6 环境白噪 | 同一描写重复过多 | 轮换库 |

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
