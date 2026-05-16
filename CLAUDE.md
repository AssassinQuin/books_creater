# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

百万字网文创作引擎 — AI-powered Chinese web novel writing system. Uses Claude Code skills + MCP (Model Context Protocol) for structured, long-form novel creation with anti-AI-writing patterns, ensemble casts, and dual-track plotting.

Current project: **《这次不一样了》** — 14卷+尾声, 百万字级玄幻网文. Novel DB id: 1.

## Domain Vocabulary

**`NOVEL-CONTEXT.md`**（项目根目录）定义了所有核心术语的标准含义。所有技能处理术语时必须以此文件为准。

**`SENTENCE-PATTERNS.md`**（项目根目录）定义了反AI句式系统——标点多样性引擎、信息投放节奏、场景结构随机组合、否定句式管理、意象梯度系统、环境音效轮换库。所有章节写作必须遵守其中的反AI指纹消除规则。

## Architecture

### Data Architecture

Three-layer data architecture:
- **novel-db MCP** (PostgreSQL): Structured data — world-building, characters, chapters, foreshadowing, timelines, dimensions. Server at `/Users/ganjie/skills/novel-db-mcp/server.py`, connects to `postgresql://localhost:5432/fcli`
- **Memory MCP** (16 tools): Unstructured creative data — inspiration, writing experience, cross-project materials, anti-AI pattern blacklist. **必须先加载 memory skill 再调用任何 memory_memory_* 工具**。详见 [Memory Skill](#memory-integration)
- **Git files**: Human-readable content — novel text, setting docs, review reports in `novels/{小说名}/`

#### 数据一致性铁律：DB优先，文件为副本

**核心原则**：同一数据在 DB 和文件中可能同时存在，但权威源只有一个。所有读取必须从权威源获取。

| 数据类型 | 权威源 | 文件角色 | 写入规则 | 读取规则 |
|---------|--------|---------|---------|---------|
| 世界观/地点/物品/能力 | **DB** (`world_query`) | 人可读副本 (`设定/世界观.md` / `地图.md` / `物品.md`) | 先写 DB，再写文件 | `world_query()` 优先；返回空时回退读文件 |
| 角色档案/关系 | **DB** (`character_detail` / `relation_list`) | 人可读副本 (`设定/人物/{名}.md` / `角色总览.md`) | 先写 DB，再写文件 | `character_detail()` 优先 |
| 伏笔 | **DB** (`foreshadow_list`) | 人可读副本 (`设定/大纲/` 中伏笔清单) | 先写 DB，再写文件 | `foreshadow_list()` 优先 |
| 卷级大纲（叙事内容） | **文件** (`设定/大纲/V{N}-{卷名}.md`) | 权威源 | 先写文件，再写 DB 摘要 | `Read()` 文件获取完整大纲；`volume_get()` 获取摘要 |
| 章节规划（逐章大纲） | **文件** (`设定/大纲/V{N}-{卷名}.md`) | 权威源 | 先写文件，再写 DB 摘要 | `Read()` 文件获取完整大纲；`chapter_list()` 获取摘要 |
| 章节正文 | **文件** (`正文/第{NNN}章-{标题}.md`) | 权威源 | 先写文件，再调 `writing_finish` 写 DB 元数据 | `Read()` 文件获取正文 |
| 审计报告 | **文件** (`审阅报告/`) | 唯一源 | 只写文件 | 只读文件 |
| 创意蓝图 | **文件** (`创意决策/Ch{N}-创意蓝图.md`) | 唯一源 | 只写文件（新实体 ID 记录在蓝图中） | 只读文件 |

**双写执行顺序**：
1. **DB 权威的数据**：`world_upsert` / `character_create` / `foreshadow_plant` → 确认成功 → 写文件
2. **文件权威的数据**：`Write()` 文件 → 确认成功 → `volume_update` / `chapter_plan` / `writing_finish` 写 DB 摘要

**禁止**：
- 只写文件不写 DB（下游 skill 读 DB 会读到旧数据）
- 只写 DB 不写文件（人无法审阅、git 无法追踪）
- 修改一方后不同步另一方（数据漂移）

**新增实体同步规则**（novel-chapter-writer Agent 2 创建的新实体）：
- Agent 2 通过 MCP 直接创建新实体（character_create / world_upsert / foreshadow_plant）→ DB 已有
- 编排器在 Step 6 存盘时，**必须将 Agent 2 创建的新实体同步写入设定文件**（`世界观.md` / `地图.md` / `物品.md` / `角色总览.md`）
- 当前 SKILL.md Step 6 缺少此同步步骤，需补充

**修订同步规则**（novel-reviser 修改正文后）：
- 修订只改文件（Edit），不直接改 DB
- 如果修订改变了角色状态/世界观/伏笔状态，编排器**必须**调 `character_update` / `world_upsert` / `foreshadow_recall` 同步 DB
- 当前 novel-reviser SKILL.md 缺少 DB 同步步骤，需补充

**自动一致性守卫**（`consistency_guard` MCP 工具）：
- 每次写入 DB 时（`world_upsert` / `character_create` / `character_update` / `foreshadow_plant` / `foreshadow_recall`），自动计算并存储 DB 记录的 hash
- 每次启动 skill 流程时（novel-chapter-writer Step 0 / novel-planner-volume Step 0），调用 `consistency_guard(novel_id, auto_sync=True)` 校验
- 检测到 DB hash 变更 → 自动同步到文件（DB 权威数据）
- 检测到文件 hash 变更 → 自动同步到 DB（文件权威数据）
- 无需消耗 token 做手动同步，MCP 自动执行

#### 文件结构规范：MD 标题 = DB 字段映射

所有设定文件必须按标准结构书写，**二级标题对应 DB 字段**，`consistency_guard` 解析标题即可批量更新，无需理解内容。

**模板权威源**：`.claude/skills/templates/` 目录，每个实体类型一个模板文件。所有 skill 创建/修改实体时必须遵守对应模板。

| 实体类型 | 模板文件 | DB 表 | 权威源 |
|---------|---------|-------|--------|
| 人物 | `templates/character.md` | `characters` | DB |
| 世界观 | `templates/world-setting.md` | `world_settings` | DB |
| 人物关系 | `templates/relation.md` | `character_relations` | DB |
| 伏笔 | `templates/foreshadow.md` | `foreshadows` | DB |
| 卷级大纲 | `templates/volume.md` | `volumes` | 文件 |
| 章节 | `templates/chapter.md` | `chapters` | 文件 |

**规则**：
- 文件中的 `## category: name` 格式对应 DB 的 `world_settings(category, name)`
- 文件中的 `- **field**: value` 格式对应 DB 表的字段
- `consistency_guard` 解析标题行即可定位 DB 记录，无需全文解析
- 新增数据必须同时满足文件结构和 DB schema
- 新增维度时：先在模板文件中追加定义 → DB 加列 → MCP 工具加参数 → skill 更新

### Chapter Writing: Multi-Agent Pipeline

章节写作采用 **4 子 Agent 流水线**，每个 Agent 上下文干净、职责单一：

```
编排器 (novel-chapter-writer)
  │  Step 1: 调 MCP 收集原始数据
  ↓
Agent 1: Context Curator     → 清洗、压缩、结构化 → 上下文包
  ↓
Agent 2: Creative Director   → 场面设计、因果链、角色弧线、创建新实体 → 创意蓝图 + 存档
  ↓
Agent 3: Engine Coordinator  → 加载引擎、定制指令 → 引擎指令包
  ↓
Agent 4: Text Generator      → 逐场面写正文、自检 → 章节正文
  ↓
编排器: validate_chapter → writing_finish → 存盘
```

| 角色 | 执行者 | 上下文 | 工具权限 |
|------|--------|--------|---------|
| 数据采集 | 编排器（主对话） | 主对话 | MCP 全部 |
| 信息整理 | Agent 1 (search) | 独立干净 | Read |
| 创意决策 | Agent 2 (general_purpose_task) | 独立干净 | Read, Write, mcp__memory__*, mcp__novel-db__character_create, mcp__novel-db__relation_create, mcp__novel-db__world_upsert, mcp__novel-db__foreshadow_plant |
| 引擎统筹 | Agent 3 (general_purpose_task) | 独立干净 | Read（加载引擎文件） |
| 正文生成 | Agent 4 (general_purpose_task) | 独立干净 | Read（参考引擎指令） |
| 校验存盘 | 编排器（主对话） | 主对话 | MCP 全部 |

**设计原则**：每个 Agent 只看到它需要的上下文，互不污染。Agent 2 直接调 MCP 创建新人物/地点/物品/势力/伏笔——无需编排器中转。编排器负责数据采集、校验和存盘。

### Skill System

Skills follow **progressive disclosure** design — each SKILL.md contains core flow in `<what-to-do>` and detailed instructions in `<supporting-info>`. Sub-documents are loaded on demand.

#### Project Skills (`.claude/skills/`)

| Skill | 触发词 | 核心功能 | 强制检查点 |
|-------|--------|----------|-----------|
| **novel-writer** | 写小说/帮我写/上架/进度 | 总路由器，分发到子技能，处理上架和状态查询 | 冲突消歧按 C3>B2 优先级 |
| **novel-setup** | 头脑风暴/灵感/建世界观/设定 | 项目初始化、世界观构建、物品设计 | 🔒 世界观确认后才能进入人物 |
| **novel-character** | 设计人物/加人物/人物卡 | 角色蒸馏7步、强制外观模板、关系差异化对话 | 🔒 蒸馏7步+外观+对话完整才能存入 |
| **novel-planner** | 规划卷/大纲 | 全书总纲、逐卷环境先行设计 | 🔒 每卷规划完必须确认才能进入场景 |
| **novel-planner-volume** | 卷大纲/章节规划/事件设计 | 卷级章节设计（场景清单+事件编排+支线体系），含独立agents目录 | 🔒 场景清单确认后才能进入正文 |
| **novel-chapter-writer** | 写第N章/继续写/写一章 | Multi-Agent Pipeline 编排器，驱动 4 子 Agent 协作（Context Curator → Creative Director → Engine Coordinator → Text Generator） | 🔒 Step6 writing_finish 不可跳过 |
| **novel-qa** | 审阅/检查/诊断/改设定/OOC | 全链路质量保障，三视角审查（读者/作者/人物）+AI指纹检测 | 🔒 P0/P1问题必须修复 |
| **novel-reviser** | 修复/去重/批量改/修文/润色 | 文本修订、润色 | - |

#### External Skills Repository

`/home/z/my-project/skills/` 目录包含通用 skill 仓库（`https://github.com/AssassinQuin/skills.git`）。以下写作相关 skill 已同步加载：

| Skill | 路径 | 用途 | 何时使用 |
|-------|------|------|----------|
| **web-novel-writer** | `skills/web-novel-writer/SKILL.md` | 网文正文写作引擎（多视角叙事+电影级画面感+**环境先行设计**+**事件场面搭建**+**正文加载协议**+**快照增量更新**+升级战斗系统） | B2章节写作时参考 |
| **novel-framework** | `skills/novel-framework/SKILL.md` | 百万字框架设计（9大Agent+**人物外观描写库**+**声音指纹**+**能力全链路**+**物品全链路**+**历史纵深设计**+**存储架构指南**+**战斗定位**） | A2建世界观、A3人物设计、B1大纲规划 |
| **storytelling** | `skills/storytelling/SKILL.md` | 故事创作方法论（三幕剧/英雄旅程+**人物对话引擎**+**弦外之音**+**环境暗示**+**通感**+**微表情**+**网文描写原则**） | 创作方法论参考、对话设计、人物描写 |
| **prose-craft** | `skills/prose-craft/SKILL.md` | 散文质量引擎（Voice发现/Styleguide选择/句子节奏/段落构建/强开篇强收尾） | 写作质量提升、文风调整 |
| **memory** | `skills/memory/SKILL.md` | 持久化记忆管理（16个MCP工具、标签体系、跨Skill API） | 任何需要存储/检索记忆时 |
| **mcp-builder** | `skills/mcp-builder/SKILL.md` | MCP服务开发指南（Python FastMCP / TypeScript SDK） | 构建新的MCP服务时 |

**注意**：外部 skill 作为**补充参考**。项目内 skill 是核心工作流。

#### Skill Lifecycle (Bucket System)

| Bucket | Purpose | Skills | Auto-routed |
|--------|---------|--------|-------------|
| **core** | Core creation flow | novel-writer, novel-setup, novel-character, novel-planner, novel-planner-volume, novel-chapter-writer | Yes |
| **quality** | Quality assurance | novel-qa, novel-reviser | Yes |
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
| B1 | Volume planning | "规划卷"/"大纲"/"卷大纲"/"章节规划"/"事件设计" |
| B2 | Chapter writing | "写第N章"/"继续写" — Multi-Agent Pipeline（编排器+4子Agent） |
| B3 | Review | "审阅"/"检查" |
| C1 | Platform publishing | "上架"/"发布" |
| C2 | Health diagnosis | "诊断"/"卡文" |
| C3 | Cascade updates | "改设定"/"调整" |
| D | Status/materials | "进度"/"加素材" |

Priority on conflict: C3 > B2 > others.

## Key Orchestration Tools

| 工具 | 用途 | 调用时机 |
|------|------|----------|
| `writing_start(novel_id, chapter_number)` | 写作前上下文注入（章节信息+前3章摘要+活跃人物+未回收伏笔+世界观+当前卷规划） | 编排器 Step 1 必调 |
| `character_detail(id)` | 单个角色深度信息（外观+性格+说话风格+能力+状态+关系+物品） | 编排器 Step 1 批量收集 |
| `validate_chapter(chapter_text)` | 写后硬约束校验（标点密度/否定句式/字数/创作原则） | 编排器 Step 6 强制 |
| `writing_finish(chapter_id, ...)` | 写作后状态更新（摘要+事件+伏笔+时间线+维度） | 编排器 Step 6 强制，不可跳过 |
| `health_check(novel_id)` | 健康诊断（伏笔积压/配角活跃/升级节奏/日常密度/暗线推进/卷完成度） | C2 诊断时 |

### Multi-Agent Pipeline 子 Agent 指令

| Agent | 指令文件 | 职责 |
|-------|---------|------|
| Agent 1: Context Curator | `.claude/skills/novel-chapter-writer/agents/context-curator.md` | 清洗压缩原始数据，产出干净上下文包 |
| Agent 2: Creative Director | `.claude/skills/novel-chapter-writer/agents/creative-director.md` | 场面设计+因果链+角色弧线+伏笔操作+创建新实体（人物/地点/物品/势力），存档创意蓝图 |
| Agent 3: Engine Coordinator | `.claude/skills/novel-chapter-writer/agents/engine-coordinator.md` | 加载引擎文件，为每个场面定制引擎指令 |
| Agent 4: Text Generator | `.claude/skills/novel-chapter-writer/agents/text-generator.md` | 逐场面生成正文+反AI指纹自检+硬约束自检 |

### 写作引擎参考文档

引擎文件位于 `.claude/skills/engines/`，按场景类型按需加载：

| 引擎 | 文件 | 用途 |
|------|------|------|
| 环境描写 | `environment.md` | 环境5要素+感官描写 |
| 对话系统 | `dialogue.md` | 差异化对话+弦外之音 |
| 动作链 | `action.md` | 动作链5拍+空间感知 |
| 物品系统 | `item.md` | 物品全生命周期 |
| 战斗系统 | `battle.md` | 战斗场景设计（从skill迁入engine） |
| 场景合成 | `scene-composition.md` / `scene-deepening.md` / `scene-type.md` | 场景结构+深化+类型分类 |
| 人物关系 | `relationship.md` | 关系动态+对话风格 |
| 能力系统 | `ability.md` | 能力全链路 |
| 因果链 | `causality.md` | 因果逻辑校验 |
| 快照 | `snapshot.md` | 场景/事件/人物快照 |
| 加载协议 | `loading.md` | 三级上下文加载协议 |
| 反AI | `anti-ai.md` / `anti-ai-patterns.md` / `anti-ai-quickref.md` | 反AI指纹消除（quickref为写作时速查卡，替代全量SENTENCE-PATTERNS.md） |
| 作者声音 | `author-voice.md` + 5个变体 | 作者声音三层架构（情感/日常/战斗/悬疑/视角） |
| 三视角审查 | `three-perspective.md` + 3个agent文件 | 读者/作者/人物三视角剧情审查 |
| 写作风格 | `writing-style.md` / `corpus-style.md` | 文体规范+语料风格 |
| 世界观 | `worldbuilding.md` / `world-element-registry.md` | 世界观构建+元素注册 |

> 所有引擎文件统一存放于 `.claude/skills/engines/`。references/ 目录仅保留非引擎参考材料（模板/示例/词库）。

### 作者声音系统

作者声音采用**三层架构**，存储在 `设定/作者声音.md`：
- **引擎层** (`engines/author-voice.md`): 通用作者声音框架
- **项目层** (`设定/作者声音.md`): 项目专属声音定制
- **变体层** (`engines/author-voice-{emotion,daily,battle,mystery}.md`): 按场景类型的情绪变体

### 三视角审查系统

审查由三个独立 Agent 执行，各自持有不同视角标准：
- **读者视角** (`engines/reader-perspective-agent.md`): 追读体验、悬念节奏、信息投放
- **作者视角** (`engines/author-perspective-agent.md`): 结构完整性、因果链、伏笔管理
- **人物视角** (`engines/character-perspective-agent.md`): 角色一致性、动机合理性、OOC检测

### 阶段指令文件

`.claude/skills/phases/` 目录包含各工作阶段的指令文件：

| 文件 | 阶段 | 用途 |
|------|------|------|
| `a1-brainstorm.md` | A1 | 头脑风暴 |
| `a2-worldbuilding.md` | A2 | 世界观构建 |
| `a3-character.md` | A3 | 人物设计 |
| `b1-volume.md` | B1 | 全书大纲规划 |
| `b2-chapter.md` | B2 | 章节写作 |
| `c2-diagnose.md` | C2 | 健康诊断 |
| `c3-update.md` | C3 | 级联更新 |

## Shared Conventions (铁律)

> 所有小说创作 skill 共用，见 `.claude/skills/novel-writer/references/shared-conventions.md`

1. **人物群像** — NPC有自己的生活，反派有自己的逻辑，配角有自己的故事线，不全围着主角转
2. **去AI味** — 禁止：不禁/缓缓/淡淡/微微/代价/反噬/寿命折损/精神崩溃。对话像真人，描写有画面
3. **日常即世界观** — 用摊贩大爷的闲聊、告示栏的排名、酒馆的物价展示世界，不空洞堆设定
4. **百万字是马拉松** — 卷级规划、配角轮换、伏笔回收节奏、升级衰减后的替代爽点，从第一天就设计
5. **明暗双线** — 每卷有明线（主角推进）和暗线（隐藏真相），暗线不一次揭完，分卷递进
6. **因果链不可断** — 每个关键事件必须有充分前因。"因为剧情需要"不是答案
7. **开篇必须有钩子** — 前三章必须有冲突/悬念/异常信号。纯日常白开水开头=弃文
8. **角色不能为剧情变笨** — 不能靠角色"没注意到""没发现""没问"来推动情节

### 流程纪律

- **步骤不可跳过** — 每个 skill 有编号步骤，必须按序执行
- **Multi-Agent Pipeline** — 章节写作由 4 个独立子 Agent 协作完成，每个 Agent 上下文干净、职责单一，编排器负责 MCP 调用和数据流转
- **🔒 关键检查点必须确认** — 执行后必须向用户确认，用户说"OK"/"继续"才能下一步
- **断点续传** — 每次触发先检查 Memory 中的 `flow-state`，有记录则恢复而非从头开始
- **写后必存** — `writing_finish` 是不可跳过的步骤

## Mandatory Enforcement (强制铁律)

**这是最高优先级规则，覆盖所有 skill 文件中的推荐/建议/可选措辞。**

### 规则 1: 全部强制，没有推荐

- `writing-constraints.md` 中所有约束（硬约束百分比、硬约束绝对值、创作原则）**全部强制**
- 不再有"推荐遵守"或"写中自觉"——全部是"**硬约束，不通过拒绝存盘**"
- MCP `validate_chapter` 将所有约束作为 violations 返回，`writing_finish` 检测到 violations 拒绝存盘
- "7条核心—写中强制检查"和"4条补充—必须执行"**必须逐条执行，不可跳过**

### 规则 2: 审计强制，不可跳过

- `validate_chapter()` 是写后的**强制**步骤，每章必须调用
- `writing_finish` 的 `self_check='passed'` 是**强制**参数，不自检通过禁止存盘
- 审阅发现的 P0/P1 问题**必须修复**后才能继续下一章
- C3 级联更新**必须**执行 `db_search` 扫描全部影响范围，不允许局修

### 规则 3: 内容充实激励引擎（字数不足时强制触发）

字数不足触发 `validate_chapter.violations` 中 `word_count` 时，`writing_finish` 和 `validate_chapter` 自动返回 `enrichment` 字段（PUA 风格三层加压），**必须**按其强制动作执行：

```
L1 引擎丰富（<20%）   → 温和失望 + 抗合理化反击 + 强制选1个 engine_detail 展开
L2 场景深化（20-50%） → 灵魂拷问 + 因果链/Telling→Showing/子冲突三选强制
L3 加事件（>50%）     → 361考核 + 强制从大纲找事件或加微事件
```

**不准说**：「字数够了」「内容很紧凑了」「信息密度高不需要更多」
**不准磨洋工**：同一段扩三遍不算干事，必须加**新内容**（动作/对话/冲突/事件）
**不准跳过**：`writing_finish` 返回 `enrichment` 字段后必须充实到字数达标，不准原样重调

每次调用 `writing_finish` 被 reject 后，AI 必须比上一次更努力：上次只用1个引擎？这次至少用2个。上次只改了一段？这次改两段。

违反上述任意规则 = 流程违规，必须重做。

## File Organization Rules

- **反AI系统 (`SENTENCE-PATTERNS.md`)**: 反AI句式系统，包含6大引擎（标点多样性/信息投放节奏/场景结构随机组合/否定句式管理/意象梯度/环境音效轮换）。写作前必读，写作后逐项检查。与 writing-style.md 同级。
- **设定文件**: 详情内容写在 `角色深化.md` / `世界观.md` / `地图.md` / `线索追踪.md` 等
- **大纲中使用指针**: 引用详情时写 `→见角色深化·关系成长路径` 而不是复制内容
- **灵感库 (`设定/灵感库/`)**: 只放调研、头脑风暴、可复用方法论. 不放审计报告
- **审阅报告 (`审阅报告/`)**: 审计发现、问题清单、修复方案
- **决策记录 (`docs/decisions/`)**: 不可逆的创作决策（ADR格式）
- **单源维护**: 同一内容(伏笔/线索/关系/设定)只在主文件描述完整, 其他文件用指针引用
- **写作执行规范** (`设定/写作执行规范.md`): **最高优先级**，每章必须严格遵守字数要求、内容依据、写作规范、检查清单。违反规范必须重写。详见文件内容。

## Current Project Status (2026-05-15)

- 14卷+尾声大纲完成, Phase3验证通过(综合90/100)
- 达尔文v3.2审计完成(2026-05-14), 含5层验证(L1故事逻辑~L5叙事动力)
- V1 Ch001-009深度审计完成, 存于 `审阅报告/V1Ch001-009深度审计/`
- 多轮审阅完成: 冲突检测、锁定设定校验、因果逻辑审计、三视角审查
- 正文碎片V01-V14已完成(卷级碎片, 存于 `正文碎片/`)
- novel-db当前未同步数据，正文生成前需先 `sync_lorebook`
- 架构变更: novel-battle迁入engines、新增novel-planner-volume skill、作者声音系统、三视角审查、阶段指令文件(phases/)
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
