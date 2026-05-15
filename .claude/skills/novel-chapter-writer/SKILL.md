---
name: novel-chapter-writer
description: 逐章写作编排器，驱动 4 个独立子 Agent 协作完成章节。触发词：写第N章/继续写/写一章
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, Agent, Task, mcp__novel-db__writing_start, mcp__novel-db__validate_chapter, mcp__novel-db__writing_finish, mcp__novel-db__skill_loader, mcp__novel-db__character_detail, mcp__novel-db__event_checklist, mcp__novel-db__author_voice, mcp__novel-db__writing_spec, mcp__novel-db__character_get, mcp__novel-db__character_list, mcp__novel-db__relation_list, mcp__novel-db__foreshadow_list, mcp__novel-db__foreshadow_plant, mcp__novel-db__foreshadow_recall, mcp__novel-db__world_query, mcp__novel-db__world_upsert, mcp__novel-db__timeline_query, mcp__novel-db__volume_get, mcp__novel-db__chapter_list, mcp__memory__memory_store, mcp__memory__memory_search
lifecycle: core
---

# 逐章写作编排器（Multi-Agent Pipeline）

> **架构原则**：编排器负责 MCP 工具调用和数据流转，子 Agent 各司其职、上下文干净、互不污染。

<what-to-do>

## 流水线总览

```
Step 0 断点检测
  ↓
Step 1 编排器调 MCP 收集原始数据
  ↓
Step 2 启动 Agent 1: Context Curator → 产出干净的上下文包
  ↓
Step 3 启动 Agent 2: Creative Director → 产出创意蓝图（含新实体创建）+ 存档
  ↓  🔒 检查点 A: 确认创意蓝图（场面数量/因果链/角色弧线）
Step 4 启动 Agent 3: Engine Coordinator → 产出引擎指令包
  ↓
Step 5 启动 Agent 4: Text Generator → 产出章节正文
  ↓  🔒 检查点 B: 确认正文完整性（字数/场面覆盖/反AI自检）
Step 6 🔒 writing_finish + 存盘
```

### Agent 失败处理

每个 Agent 步骤最多重试 **2 次**。编排器在每次 Agent 返回后检查输出完整性：

| Agent | 完整性检查 | 不通过时 |
|-------|-----------|----------|
| Agent 1 | 上下文包含人物档案+伏笔清单+缺口标注 | 补充查询 MCP 后重新启动 Agent 1 |
| Agent 2 | 创意蓝图含场面设计+因果链+角色行为弧线 | 指出缺失项，要求 Agent 2 补充 |
| Agent 3 | 引擎指令包含反AI指令+硬约束+场面引擎 | 指出缺失项，要求 Agent 3 补充 |
| Agent 4 | 正文字数≥2500 + 含自检报告 | 反馈缺失项，要求 Agent 4 修复 |

若同一 Agent 连续 2 次不通过 → 编排器降级处理：手动补全缺失部分后继续下一 Agent，并在 Memory 中记录 `bug: Agent{N}连续失败`。

## Agent 输出格式（编排器验证用）

每个 Agent 返回时，编排器必须验证以下必填字段存在且非空：

| Agent | 必填字段 | 格式 |
|-------|---------|------|
| Agent 1 | `人物档案` `伏笔清单` `缺口标注` | 人物档案 ≤200字/人，伏笔含本章操作，缺口含缺失信息类型 |
| Agent 2 | `场面设计` `因果链` `角色行为弧线` `叙事节奏` `已创建实体` | 场面 2-4 个，因果链含前因→后果→角色选择，弧线含失控时刻，新实体已通过 MCP 创建并记录 ID |
| Agent 3 | `场面引擎指令` `反AI指令(F1-F6)` `硬约束清单` | 每场面有定制引擎指令，反AI指令具体到本章可执行项 |
| Agent 4 | `章节正文` `自检报告` | 正文 ≥2500 字，纯净化无注释；自检报告含反AI逐项结果+硬约束逐条结果 |

编排器接收每个 Agent 输出后，对照上表逐字段检查。任一必填字段缺失 → 按 Agent 失败处理表重试。

## 阶段指令加载

本章写作阶段指令：`skill_loader("novel-chapter-writer", "phase", "b2-chapter")`

编排器在 Step 2 启动前加载阶段指令，注入当前上下文。

## 引擎按需加载

Agent 3 根据场面类型，按需调用 `skill_loader` 加载引擎：

| 场面类型 | 加载引擎 |
|---------|---------|
| 环境描写 | `skill_loader("novel-chapter-writer", "engine", "environment")` |
| 对话博弈 | `skill_loader("novel-chapter-writer", "engine", "dialogue")` |
| 动作/战斗 | `skill_loader("novel-chapter-writer", "engine", "action")` |
| 物品使用 | `skill_loader("novel-chapter-writer", "engine", "item")` |
| 多人物互动 | `skill_loader("novel-chapter-writer", "engine", "scene-composition")` |
| 需要深化 | `skill_loader("novel-chapter-writer", "engine", "scene-deepening")` |

Agent 4 写作前加载：`skill_loader("novel-chapter-writer", "engine", "anti-ai")`

## 角色分工

| 角色 | 谁做 | 职责 | 上下文 |
|------|------|------|--------|
| 数据采集 | **编排器（你）** | 调 MCP 工具收集原始数据 | 主对话 |
| 信息整理 | **Agent 1** (search) | 清洗、压缩、结构化上下文 | 独立干净 |
| 创意决策 | **Agent 2** (general_purpose_task) | 场面设计、因果链、角色弧线、创建新实体（调 MCP） | 独立干净 |
| 引擎统筹 | **Agent 3** (general_purpose_task) | 加载引擎文件、定制指令 | 独立干净 |
| 正文生成 | **Agent 4** (general_purpose_task) | 逐场面写正文、自检 | 独立干净 |
| 校验存盘 | **编排器（你）** | validate + writing_finish + 写文件 | 主对话 |

## Step 0: 断点检测

检查目标章节文件 `novels/{小说名}/正文/第{NNN}章-{标题}.md` 是否已存在：
- **文件存在且内容完整** → 提示「第 N 章已完成，是否写第 N+1 章？」
- **文件不存在** → 进入 Step 1
- **断点续传**：通过 Memory 搜索 `flow-state` 恢复上次中断位置

## Step 1: 编排器采集原始数据

调用 MCP 工具，收集以下原始数据：

```
writing_start(novel_id, chapter_number) → writing_prompt
volume_get(volume_id) → 卷级规划
character_detail(id) → 每个出场人物的深度信息
relation_list(novel_id) → 人物关系
foreshadow_list(novel_id, status="planted") → 未回收伏笔
world_query(novel_id, category="location") → 场景地点
world_query(novel_id, category="faction") → 势力信息
timeline_query(novel_id, from_chapter=N-3) → 时间线
```

将所有原始数据整理为一段完整文本（raw_data），传递给 Agent 1。

## Step 2: 启动 Agent 1 — Context Curator

使用 Task 工具启动 search 子 Agent：

```
subagent_type: search
description: 整理第N章上下文
query: 你是 Context Curator Agent。请读取 .claude/skills/novel-chapter-writer/agents/context-curator.md 了解你的完整职责和输出格式。

你的任务：接收以下原始数据，清洗、压缩、结构化，产出干净的上下文包。

原始数据：
{raw_data}

要求：
1. 人物档案压缩到 200 字以内，只保留本章需要的信息
2. 标注每个人物的「本章动机」和每个伏笔的「本章操作」
3. 识别缺口：标注缺失的信息
4. 按 context-curator.md 中定义的输出格式产出上下文包
5. 不创作、不添加原始数据中不存在的信息
```

Agent 1 返回 → **上下文包**（context_package）

如果 Agent 1 标注了缺口，编排器补充查询 MCP 后更新上下文包。

## Step 3: 启动 Agent 2 — Creative Director

使用 Task 工具启动 general_purpose_task 子 Agent：

```
subagent_type: general_purpose_task
description: 设计第N章创意蓝图
query: 你是 Creative Director Agent。请读取 .claude/skills/novel-chapter-writer/agents/creative-director.md 了解你的完整职责和输出格式。

你的任务：基于上下文包，做出本章全部创意决策，产出创意蓝图。

上下文包：
{context_package}

阶段指令（已加载）：
{phase_instruction}

引擎指令（按需加载）：
- 环境设计: `skill_loader("novel-chapter-writer", "engine", "environment")`
- 对话设计: `skill_loader("novel-chapter-writer", "engine", "dialogue")`
- 动作设计: `skill_loader("novel-chapter-writer", "engine", "action")`
- 因果链: `skill_loader("novel-chapter-writer", "engine", "causality")`

要求：
1. 确认事件因果链完整性
2. 将 2-4 个场面分配到章级起承转合四段中
3. 选择 1 种悬念未知类型作为本章锚点
4. 设计每个场面的密度/角色矩阵/微事件/伏笔操作/镜头序列
5. 设计叙事节奏（情绪曲线+节奏断层+刀锋技法），本章情绪峰值 ≥ 上一章
6. 设计每个出场角色的行为弧线（含失控时刻）
7. 识别需要新建的人物/地点/物品/势力/伏笔，直接调用 MCP 创建（见 creative-director.md 步骤 5）
8. 将创意蓝图保存到 novels/{小说名}/创意决策/Ch{N}-创意蓝图.md
9. 按 creative-director.md 中定义的输出格式产出创意蓝图（含已创建实体 ID）
```

Agent 2 返回 → **创意蓝图**（creative_blueprint）

## Step 4: 启动 Agent 3 — Engine Coordinator

使用 Task 工具启动 general_purpose_task 子 Agent：

```
subagent_type: general_purpose_task
description: 为第N章加载引擎指令
query: 你是 Engine Coordinator Agent。请读取 .claude/skills/novel-chapter-writer/agents/engine-coordinator.md 了解你的完整职责和输出格式。

你的任务：基于创意蓝图，判断场面类型，加载对应引擎文件，产出引擎指令包。

创意蓝图：
{creative_blueprint}

你需要读取的文件（使用 Read 工具）：
- SENTENCE-PATTERNS.md（项目根目录）
- .claude/skills/writing-constraints.md
- .claude/skills/novel-writer/references/writing-style.md
- 根据场面类型，按 engine-coordinator.md 的步骤 2 加载对应引擎文件

要求：
1. 判定每个场面的主导类型
2. 加载对应的引擎参考文件
3. 提取反 AI 指纹指令（F1-F6 具体到本章）
4. 提取硬约束检查清单（转化为可执行指令）
5. 为每个场面生成定制化的引擎指令
6. 按 engine-coordinator.md 中定义的输出格式产出引擎指令包
```

Agent 3 返回 → **引擎指令包**（engine_package）

## Step 5: 启动 Agent 4 — Text Generator

使用 Task 工具启动 general_purpose_task 子 Agent：

```
subagent_type: general_purpose_task
description: 生成第N章正文
query: 你是 Text Generator Agent。请读取 .claude/skills/novel-chapter-writer/agents/text-generator.md 了解你的完整职责和输出格式。

你的任务：基于创意蓝图和引擎指令包，逐场面生成章节正文。

创意蓝图：
{creative_blueprint}

引擎指令包：
{engine_package}

要求：
1. 写前确认所有信息就绪（角色矩阵/感官分配/反AI指令/硬约束/微事件/伏笔）
2. 按起承转合四段逐场面生成正文（搭建场景快照→建立镜头→主体→收束）
3. 确保每段字数占比：起 10-15% / 承 40-50% / 转 20-25% / 合 10-15%
4. 每完成一个场面，对照反 AI 指纹指令逐项自检
5. 全文通读后，对照硬约束清单逐条自检
6. 正文部分纯净化，不含注释、统计、审计备注
7. 按 text-generator.md 中定义的输出格式产出正文+自检报告
```

Agent 4 返回 → **章节正文**（chapter_text）+ **自检报告**

## Step 6: 🔒 校验 + 存盘

### 6.1 调用 MCP validate_chapter

```
validate_chapter(chapter_text)
```

若返回 violations → 将 violations 反馈给 Agent 4 修复，或编排器自行修复。
若返回 enrichment → 按 L1/L2/L3 阶梯充实后重新调用。

### 6.2 调用 writing_finish

```
writing_finish(
  chapter_id,
  chapter_text,
  summary={Agent 4 自检报告中的摘要},
  key_events={创意蓝图中的事件清单},
  characters_involved={创意蓝图中出场角色 ID 列表},
  foreshadow_operations={创意蓝图中的伏笔操作},
  self_check='passed'
)
```

若返回 enrichment → 必须充实后重新调用。每次 reject 后必须比上次更努力。

### 6.3 存盘

正文写入 `novels/{小说名}/正文/第{NNN}章-{标题}.md`。

**正文纯净化**：正文文件禁止包含注释、统计、审计备注等非正文内容。只写入 Agent 4 输出的正文部分（分隔线 `---` 之前的内容）。

## 子 Agent 指令文件

每个 Agent 的详细指令见：
- `.claude/skills/novel-chapter-writer/agents/context-curator.md` — Agent 1 完整职责
- `.claude/skills/novel-chapter-writer/agents/creative-director.md` — Agent 2 完整职责
- `.claude/skills/novel-chapter-writer/agents/engine-coordinator.md` — Agent 3 完整职责
- `.claude/skills/novel-chapter-writer/agents/text-generator.md` — Agent 4 完整职责

</what-to-do>