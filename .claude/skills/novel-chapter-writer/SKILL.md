---
name: novel-chapter-writer
description: 逐章写作编排器，驱动 4 个独立子 Agent 协作完成章节。触发词：写第N章/继续写/写一章
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, Agent, Task, mcp__novel-db__get_chapter_context, mcp__novel-db__validate_chapter, mcp__novel-db__writing_finish, mcp__novel-db__skill_loader, mcp__novel-db__character_update, mcp__novel-db__character_increment, mcp__novel-db__character_snapshot_by_name, mcp__novel-db__relation_snapshot_by_name, mcp__novel-db__foreshadow_plant, mcp__novel-db__foreshadow_recall, mcp__novel-db__world_upsert, mcp__novel-db__character_create, mcp__novel-db__relation_create, mcp__novel-db__consistency_guard, mcp__memory__memory_store, mcp__memory__memory_search
depends_on: lorecraft, engines/anti-ai-quickref, engines/author-voice, engines/causality, agents/context-curator, agents/creative-director, agents/engine-coordinator, agents/text-generator
lifecycle: core
version: "1.1.0"
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

### 角色分工与失败处理

| 角色 | 执行者 | 职责 | 上下文 | 完整性检查 | 不通过时 |
|------|--------|------|--------|-----------|----------|
| 数据采集 | **编排器（你）** | 调 MCP 工具收集原始数据 | 主对话 | — | — |
| 信息整理 | **Agent 1** (search) | 清洗、压缩、结构化上下文 | 独立干净 | 上下文包含人物档案+伏笔清单+缺口标注 | 补充查询 MCP 后重新启动 Agent 1 |
| 创意决策 | **Agent 2** (general_purpose_task) | 场面设计、因果链、角色弧线、创建新实体（调 MCP） | 独立干净 | 创意蓝图含场面设计+因果链+角色行为弧线 | 指出缺失项，要求 Agent 2 补充 |
| 引擎统筹 | **Agent 3** (general_purpose_task) | 加载引擎文件、定制指令 | 独立干净 | 引擎指令包含反AI指令+硬约束+场面引擎 | 指出缺失项，要求 Agent 3 补充 |
| 正文生成 | **Agent 4** (general_purpose_task) | 逐场面写正文、自检 | 独立干净 | 正文长度达到卷均章节的 80–120%（常规章）或 120–180%（关键转折章）+ 含自检报告 | 反馈缺失项，要求 Agent 4 修复 |
| 校验存盘 | **编排器（你）** | validate + writing_finish + 写文件 | 主对话 | — | — |

**Agent 重试机制**：每个 Agent 步骤建议预留 1–3 次重试空间。重试次数取决于问题的严重程度——格式缺失可快速修复，创意偏差可能需要更多轮次。若同一 Agent 多次不通过（通常 2 次以上），编排器应降级处理：手动补全缺失部分后继续下一 Agent，并在 Memory 中记录 `bug: Agent{N}连续失败`，供后续流程优化参考。

### Agent 输出格式（编排器验证用）

每个 Agent 返回时，编排器需要验证以下字段的存在性和完整性——这是为了确保下游 Agent 获得足够的信息输入，避免信息断层导致创意偏离或正文质量下降：

| Agent | 必填字段 | 格式 |
|-------|---------|------|
| Agent 1 | `人物档案` `伏笔清单` `缺口标注` | 人物档案建议压缩到核心信息密度（单角色约占上下文包的 5–10%，保留动机、能力状态、关系张力等本章必需信息，细节可裁剪），伏笔含本章操作，缺口含缺失信息类型 |
| Agent 2 | `场面设计` `因果链` `角色行为弧线` `叙事节奏` `已创建实体` | 场面数量占本章叙事负荷的合理比例（常规章 2–4 个，根据章节复杂度调整；高密度转折章可达 5–6 个），因果链含前因→后果→角色选择，弧线含失控时刻，新实体已通过 MCP 创建并记录 ID |
| Agent 3 | `场面引擎指令` `反AI指令(F1-F6)` `硬约束清单` | 每场面有定制引擎指令，反AI指令具体到本章可执行项 |
| Agent 4 | `章节正文` `自检报告` | 正文长度约为卷均章节的 80–120%（常规章），关键转折章可放宽至 120–180%；纯净化无注释；自检报告含反AI逐项结果+硬约束逐条结果 |

编排器接收每个 Agent 输出后，对照上表逐字段检查。字段缺失会导致下游 Agent 信息不足，进而影响创意质量或正文完整性，因此需要按失败处理表启动重试或手动补全。

## 阶段指令与引擎加载

**阶段指令**：`skill_loader("novel-chapter-writer", "phase", "b2-chapter")` — 编排器在 Step 2 启动前加载，注入当前上下文。

**引擎按需加载**：Agent 3 根据场面类型调用 `skill_loader` 加载对应引擎；Agent 4 写作前加载 `skill_loader("novel-chapter-writer", "engine", "anti-ai")`。

**叙事声音统一性**：建议所有场面加载 `skill_loader("novel-chapter-writer", "engine", "author-voice")` — 叙事声音指纹（视角/句式/比喻/信息投放/留白/词汇）。这是为了确保跨场次的作者声音一致性，避免不同 Agent 生成的场面出现语调断裂。若某场面有特殊声音需求（如回忆片段、书信体），可在此基础上叠加变体引擎。

| 场面类型 | 加载引擎 |
|---------|---------|
| **所有场面** | `skill_loader("novel-chapter-writer", "engine", "author-voice")` |
| 环境描写 | `skill_loader("novel-chapter-writer", "engine", "environment")` |
| 对话博弈 | `skill_loader("novel-chapter-writer", "engine", "dialogue")` |
| 动作/战斗 | `skill_loader("novel-chapter-writer", "engine", "action")` + `skill_loader("novel-chapter-writer", "engine", "battle")` + `skill_loader("novel-chapter-writer", "engine", "author-voice-battle")` |
| 情感高潮 | `skill_loader("novel-chapter-writer", "engine", "author-voice-emotion")` |
| 日常/世界呼吸 | `skill_loader("novel-chapter-writer", "engine", "author-voice-daily")` |
| 悬疑/揭秘 | `skill_loader("novel-chapter-writer", "engine", "author-voice-mystery")` |
| 物品使用 | `skill_loader("novel-chapter-writer", "engine", "item")` |
| 多人物互动 | `skill_loader("novel-chapter-writer", "engine", "scene-composition")` |
| 需要深化 | `skill_loader("novel-chapter-writer", "engine", "scene-deepening")` |
| 世界观元素 | `skill_loader("novel-chapter-writer", "engine", "world-element-registry")` |
| 读者视角审查 | `skill_loader("novel-chapter-writer", "engine", "reader-perspective-agent")` |
| 作者视角审查 | `skill_loader("novel-chapter-writer", "engine", "author-perspective-agent")` |
| 人物视角审查 | `skill_loader("novel-chapter-writer", "engine", "character-perspective-agent")` |

## 子 Agent 启动模板

Step 2-5 均使用 Task 工具启动子 Agent，统一结构如下：

```
subagent_type: {search | general_purpose_task}
description: {任务简述}
query: 你是 {Agent 角色} Agent。请读取 .claude/skills/novel-chapter-writer/agents/{agent-file}.md 了解你的完整职责和输出格式。

你的任务：{任务描述}

{输入数据}

要求：
1. {具体要求 1}
2. {具体要求 2}
...
N. 按 {agent-file}.md 中定义的输出格式产出结果
```

## Step 0: 断点检测 + 数据一致性校验

检查目标章节文件 `novels/{小说名}/正文/第{NNN}章-{标题}.md` 是否已存在：
- **文件存在且内容完整** → 提示「第 N 章已完成，是否写第 N+1 章？」
- **文件不存在** → 进入 Step 1
- **断点续传**：通过 Memory 搜索 `flow-state` 恢复上次中断位置

**数据一致性校验**：
```python
# 校验 DB 与文件一致性，不一致自动同步
consistency_guard(novel_name="NOVEL_NAME", auto_sync=True)
# 返回 synced_count > 0 时，提示用户哪些数据被同步了
```

> 为什么需要这一步：DB 是设定数据的唯一权威源，文件是人可读副本。若两者不一致，Agent 在读取设定时可能拿到过时信息，导致角色状态错误、伏笔重复回收或世界观冲突。自动同步确保所有 Agent 基于同一事实工作。

## Step 1: 编排器采集原始数据

### 1.1 加载卷级大纲

```python
# DB 是权威源，直接调 MCP 获取卷大纲
volume_get(novel_name="NOVEL_NAME", volume_number={卷号})
# 如 MCP 返回不完整（notes 为空），回退读文件：Read("novels/{小说名}/设定/大纲/V{卷号}-{卷名}.md")
# 提取本章信息：核心事件/参与角色/微事件/伏笔操作/声音适配标记
```

### 1.2 调用聚合 MCP（一次调用获取全部上下文）

```
get_chapter_context(novel_name="NOVEL_NAME", chapter_number) → 全部写作上下文
```

**一次调用返回**：章节信息 + 卷级大纲 + 前3章摘要 + 全部角色深度信息（外观/性格/说话风格/能力/状态/关系）+ 未回收伏笔 + 活跃线索 + 世界观全分类数据 + 人物关系 + 时间线 + 质量历史 + 写作提示词（含规则+作者DNA）

**无需再单独调用**：~~writing_start~~ / ~~volume_get~~ / ~~foreshadow_list~~ / ~~character_detail~~ / ~~relation_list~~ / ~~world_query~~ / ~~timeline_query~~ — 全部已聚合。

**如 world_settings 某分类为空**：说明大纲阶段未同步到DB，编排器回退读取设定文件。

将所有数据保存到临时文件，传递给 Agent 1：

```python
# 编排器将聚合数据保存到临时文件（不注入 prompt，节省编排器上下文）
Write("novels/{小说名}/.tmp/ch{N}-raw-data.md", raw_data)
```

**raw_data 内容要求**：以下信息是 Agent 1 有效工作的基础，缺失任何一项都会导致上下文压缩失真：
- 本章核心事件（来自卷级事件大纲）
- 声音适配标记（来自卷级事件大纲）
- 涉及的世界元素定义（来自世界元素索引）
- 人物档案/伏笔/时间线（来自 MCP）

## Step 2: 启动 Agent 1 — Context Curator

使用 Task 工具启动 search 子 Agent：

```
subagent_type: search
description: 整理第N章上下文
query: 你是 Context Curator Agent。请读取 .claude/skills/novel-chapter-writer/agents/context-curator.md 了解你的完整职责和输出格式。

你的任务：接收以下原始数据，清洗、压缩、结构化，产出干净的上下文包。

原始数据文件：novels/{小说名}/.tmp/ch{N}-raw-data.md（请用 Read 工具读取）

要求：
1. 人物档案建议压缩到核心信息密度（单角色约占上下文包的 5–10%），优先保留本章需要的信息（动机、能力状态、关系张力），细节可裁剪
2. 标注每个人物的「本章动机」和每个伏笔的「本章操作」
3. 识别缺口：标注缺失的信息
4. 按 context-curator.md 中定义的输出格式产出上下文包
5. 不创作、不添加原始数据中不存在的信息
```

Agent 1 返回 → 编排器验证必填字段 → **保存到临时文件**：

```python
# 编排器验证后保存，不保留全文在上下文中
Write("novels/{小说名}/.tmp/ch{N}-context-package.md", context_package)
```

如果 Agent 1 标注了缺口，编排器补充查询 MCP 后更新临时文件。

## Step 3: 启动 Agent 2 — Creative Director

使用 Task 工具启动 general_purpose_task 子 Agent：

```
subagent_type: general_purpose_task
description: 设计第N章创意蓝图
query: 你是 Creative Director Agent。请读取 .claude/skills/novel-chapter-writer/agents/creative-director.md 了解你的完整职责和输出格式。

你的任务：基于上下文包，做出本章全部创意决策，产出创意蓝图。

上下文包文件：novels/{小说名}/.tmp/ch{N}-context-package.md（请用 Read 工具读取）

阶段指令（已加载）：
{phase_instruction}

引擎指令（编排器已通过 skill_loader 预加载并注入你的上下文）：
- 环境设计: engines/environment.md
- 对话设计: engines/dialogue.md
- 动作设计: engines/action.md
- 因果链: engines/causality.md

要求：
1. 确认事件因果链完整性
2. 将场面分配到章级起承转合四段中（常规章 2–4 个场面，高密度转折章可达 5–6 个）
3. 选择 1 种悬念未知类型作为本章锚点
4. 设计每个场面的密度/角色矩阵/微事件/伏笔操作/镜头序列
5. 设计叙事节奏（情绪曲线+节奏断层+刀锋技法），本章情绪峰值建议不低于上一章的 80%，关键转折章可突破上限
6. 设计每个出场角色的行为弧线（含失控时刻）
7. 识别需要新建的人物/地点/物品/势力/伏笔，直接调用 MCP 创建（见 creative-director.md 步骤 5）
8. 将创意蓝图保存到 novels/{小说名}/创意决策/Ch{N}-创意蓝图.md
9. 按 creative-director.md 中定义的输出格式产出创意蓝图（含已创建实体 ID）
```

Agent 2 返回 → 编排器验证必填字段 → **创意蓝图已由 Agent 2 保存到文件**，编排器只提取元数据（已创建实体ID、伏笔操作摘要）用于 Step 6。

## Step 4: 启动 Agent 3 — Engine Coordinator

使用 Task 工具启动 general_purpose_task 子 Agent：

```
subagent_type: general_purpose_task
description: 为第N章加载引擎指令
query: 你是 Engine Coordinator Agent。请读取 .claude/skills/novel-chapter-writer/agents/engine-coordinator.md 了解你的完整职责和输出格式。

你的任务：基于创意蓝图，判断场面类型，加载对应引擎文件，产出引擎指令包。

创意蓝图文件：novels/{小说名}/创意决策/Ch{N}-创意蓝图.md（请用 Read 工具读取）

你需要读取的文件（使用 Read 工具）：
- .claude/skills/engines/anti-ai-quickref.md（反AI指纹速查卡，替代全量SENTENCE-PATTERNS.md）
- .claude/skills/engines/writing-style.md
- .claude/skills/lorecraft/references/term-map.md（🔒 术语规范——写前必读，写作全程使用有文化根脉的灵能术语，避免现代术语侵入世界观）
- 根据场面类型，按 engine-coordinator.md 的步骤 2 加载对应引擎文件

注意：writing-constraints.md 的规则已由编排器通过 get_chapter_context 注入，无需重复读取。

要求：
1. 判定每个场面的主导类型
2. 加载对应的引擎参考文件
3. 提取反 AI 指纹指令（F1-F6 具体到本章）
4. 提取硬约束检查清单（转化为可执行指令）
5. 为每个场面生成定制化的引擎指令
6. 在引擎指令包中加入术语规范（引用 `term-map.md` 的需规避术语清单），提示 Agent 4 写后逐项自检
7. 按 engine-coordinator.md 中定义的输出格式产出引擎指令包
```

Agent 3 返回 → 编排器验证必填字段 → **保存到临时文件**：

```python
Write("novels/{小说名}/.tmp/ch{N}-engine-package.md", engine_package)
```

## Step 5: 启动 Agent 4 — Text Generator

使用 Task 工具启动 general_purpose_task 子 Agent：

```
subagent_type: general_purpose_task
description: 生成第N章正文
query: 你是 Text Generator Agent。请读取 .claude/skills/novel-chapter-writer/agents/text-generator.md 了解你的完整职责和输出格式。

你的任务：基于创意蓝图和引擎指令包，逐场面生成章节正文。

创意蓝图文件：novels/{小说名}/创意决策/Ch{N}-创意蓝图.md（请用 Read 工具读取）
引擎指令包文件：novels/{小说名}/.tmp/ch{N}-engine-package.md（请用 Read 工具读取）

要求：
1. 写前确认信息就绪度（角色矩阵/感官分配/反AI指令/硬约束/微事件/伏笔）——信息缺口会导致场面干瘪或角色行为失准
2. 按起承转合四段逐场面生成正文（搭建场景快照→建立镜头→主体→收束）
3. 每段篇幅占比建议范围：起 10–15% / 承 40–50% / 转 20–25% / 合 10–15%（根据情节需要可±5% 调整，如快节奏战斗章可压缩"起"至 5%）
4. 每完成一个场面，对照反 AI 指纹指令逐项自检
5. 全文通读后，对照硬约束清单逐条自检
6. **术语合规检查**：对照 `term-map.md` 需规避术语清单逐项检查，确保全文无现代术语违规（如数据/系统/信号/参数/权限等）。术语违规会破坏世界观沉浸感，且难以在后续修订中批量修正
7. 正文部分纯净化，不含注释、统计、审计备注——这些非正文内容会污染最终交付物，增加后期清理成本
8. 按 text-generator.md 中定义的输出格式产出正文+自检报告
```

Agent 4 返回 → **章节正文**（chapter_text）+ **自检报告**

## Step 6: 🔒 存盘 + 移交审计

> **生成与审计分离原则**：本章只负责生成正文，不执行审计。审计由 novel-qa 独立进行。

### 6.1 调用 writing_finish

```
writing_finish(
  chapter_id,
  chapter_text,
  summary={Agent 4 自检报告中的摘要},
  key_events={创意蓝图中的事件清单},
  characters_involved={创意蓝图中出场角色 ID 列表},
  new_foreshadows={创意蓝图中新种的伏笔},
  resolved_foreshadows={创意蓝图中回收的伏笔},
  self_check='passed'
)
```

> 注意：此处 `self_check` 是 Agent 4 的自检报告，不是 novel-qa 的独立审计。

### 6.1.1 更新角色状态快照（强制）

每章写完后，必须用 `character_increment` 增量更新出场角色的状态：

```python
for character in involved_characters:
    character_increment(
        novel_name="NOVEL_NAME",
        character_name=character.name,
        snapshot_update=json.dumps({
            "identity": character.new_identity,
            "ability": character.new_ability_state,
            "goal": character.new_goal,
            "knows": character.new_knowledge,
            "doesnt_know": character.new_unknowns,
            "relationships": character.relationship_changes
        }),
        growth_add=json.dumps({
            "volume": current_volume,
            "chapter": chapter_number,
            "changes": character.changes_this_chapter,
            "trigger": character.trigger_event
        })
    )
```

### 6.1.2 保存角色快照到独立表（新增——供 get_chapter_context 消费）

`character_increment` 写入 `characters.current_snapshot`（可变），但 `get_chapter_context` 和 `character_detail` 从 `character_state_snapshots` 表读取。必须同时写入快照表，下游才能读到数据：

```python
for character in involved_characters:
    character_snapshot_by_name(
        novel_name="NOVEL_NAME",
        character_name=character.name,
        chapter_number=chapter_number,
        location=character.current_location,
        arc_phase=character.arc_phase,
        emotional_state=character.emotional_state,
        physical_state=character.physical_state,
        ability_snapshot=json.dumps(character.ability_state),
        inventory_snapshot=json.dumps(character.inventory),
        knowledge_snapshot=json.dumps(character.knowledge_state),
        notes=character.snapshot_notes
    )
```

### 6.1.3 保存关系快照（新增——关系状态可追溯）

Creative Director 在创意蓝图中设计了关系变化。每章写完后，对有显著变化的角色关系调用快照：

```python
for relation_change in blueprint.relationship_changes:
    relation_snapshot_by_name(
        novel_name="NOVEL_NAME",
        from_name=relation_change.from_name,
        to_name=relation_change.to_name,
        chapter_number=chapter_number,
        intensity=relation_change.new_intensity,
        status=relation_change.new_status,  # active/broken/evolved/hidden
        notes=relation_change.description
    )
```

### 6.2 存盘

正文写入 `novels/{小说名}/正文/第{NNN}章-{标题}.md`。

**正文纯净化**：正文文件应只包含叙事内容。注释、统计、审计备注等非正文内容会污染最终交付物，增加后期清理成本，因此不应写入正文文件。只写入 Agent 4 输出的正文部分（分隔线 `---` 之前的内容）。

### 6.3 自动一致性同步（MCP 级 — 替代手动文件同步）

Agent 2 在创意决策中可能通过 MCP 创建了新实体（DB 已有），编排器无需手动遍历写入文件——由 `consistency_guard` 自动完成：

```python
# 一致性守卫自动检测 DB hash 变更 → 同步到文件
# DB-authoritative 数据（world/character/foreshadow）：DB 有变→自动写入文件
# 无需手动遍历 blueprint.new_characters 等——MCP 自动处理
consistency_guard(novel_name="NOVEL_NAME", auto_sync=True)
```

**原理**：Agent 2 通过 `character_create` / `world_upsert` / `foreshadow_plant` 写入 DB 时，`consistency_guard` 自动计算并存储了 DB 记录的 hash。重新调用时检测到 hash 变更，按权威源规则自动同步到文件。一个调用覆盖所有实体类型，无需逐个遍历。

**🔒 不可跳过此步骤**：跳过会导致设定文件与 DB 不一致，后续 Agent 读取时可能基于过时信息工作，引发角色状态错误或伏笔冲突。

### 6.4 清理临时文件

```python
# 删除本章临时文件（保留创意蓝图在 创意决策/ 目录）
import shutil
shutil.rmtree("novels/{小说名}/.tmp/", ignore_errors=True)
```

### 6.5 移交审计

生成完成后，提示用户：
```
第{NNN}章生成完成。是否进行独立审计？
- 输入"审计" → 触发 novel-qa 进行15维度扫描
- 输入"继续" → 进入下一章写作
```

审计由 novel-qa 独立执行，不阻塞写作流程。

## 子 Agent 指令文件

每个 Agent 的详细指令见：
- `.claude/skills/novel-chapter-writer/agents/context-curator.md` — Agent 1 完整职责
- `.claude/skills/novel-chapter-writer/agents/creative-director.md` — Agent 2 完整职责
- `.claude/skills/novel-chapter-writer/agents/engine-coordinator.md` — Agent 3 完整职责
- `.claude/skills/novel-chapter-writer/agents/text-generator.md` — Agent 4 完整职责

</what-to-do>
