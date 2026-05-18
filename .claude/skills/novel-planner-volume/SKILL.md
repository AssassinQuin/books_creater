---
name: novel-planner-volume
description: 卷级大纲设计。把握小说脉络——事件架构+因果链+人物弧光+伏笔节奏。不做细节注册，留给正文写作阶段。触发词：设计卷/卷大纲/章节规划/事件设计
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, Agent, Task, mcp__novel-db__*
lifecycle: core
---

# 卷级大纲设计

> 设计"每章发生什么"——事件架构+因果链+人物弧光+伏笔节奏。**把握脉络，不追求细节**。世界元素注册、感官5要素、微事件多样性等留给正文写作阶段(novel-chapter-writer)。
> 可选输入：novel-planner 输出的卷级目标卡（非必需）。如存在则作为卷设计约束，不存在则自主设计。

<what-to-do>

## 强制流程

### 全量模式（首次/大改）

```
Step 0: 增量检测 → 加载框架+数据采集 → 🔒引擎验证
  ↓
Step 1: Agent — 事件架构师 → 因果链+人物弧光+悬念锚点
  ↓  🔒检查点A: 确认事件架构 + 新实体确认
Step 2: Agent — 章节设计师 → 逐章大纲+伏笔节奏+声音适配
  ↓  🔒检查点A2: 确认逐章大纲（用户修改→完善→确认）
Step 3: 卷级验证 → 三视角审查(读者/作者/人物，3Agent并行)
  ↓  🔒检查点B: 确认验证通过(P0必须修复)
Step 4: 保存(DB+文件+审计报告) → git commit
```

### 增量扩展模式（用户修改/扩展特定章节）

当用户对已生成大纲提出**局部修改**（如"Ch001加一个异灵追击场景""Ch003时间线不对"）时，**不重跑全流程**，走以下捷径：

```
Step 0: 定位影响范围
  ↓  读取现有逐章大纲，确定用户要改的章节
  ↓  检查因果链影响：改动是否波及邻章？
Step 1: 只修改目标章节
  ↓  编排器直接修改指定章节的场景/事件
  ↓  如需新增伏笔/角色，编排器调MCP创建
Step 2: 邻章校验
  ↓  检查修改后的章节与前后章的因果链/时间线是否连贯
  ↓  如有断裂，扩展修复范围
Step 2.5: 轻量级 P0+术语审查（强制——不可跳过）
  ↓  编排器对修改章+邻章执行 P0 检查 + 🔒术语扫描（见下方检查清单）
  ↓  发现 P0 或术语违规 → 修复后重新检查，直到全部通过
  ↓  无问题 → 用户确认 → 继续
Step 3: 保存 → git commit
```

**Step 2.5 P0 检查清单**（增量模式下必须全部通过，否则阻断保存）：
- [ ] **角色OOC检测**：修改章中每个出场角色的行为/对话是否符合其角色蒸馏卡（character_detail）
- [ ] **因果链断裂检测**：修改引入的事件是否与前后章因果链连贯？是否有"因为剧情需要"式的无前因事件？
- [ ] **时间线连续性**：修改章与前后章的时间戳是否递增、无跳跃？
- [ ] **新实体一致性**：新增的角色/地点/物品是否已调MCP注册（character_create/world_upsert）？
- [ ] **🔒术语扫描**：修改章中是否出现 term-map 禁止术语（数据/系统/信号/参数/权限/终端/频率等）？

**不可跳过 Step 2.5**。即使只是"加一句对话"，也必须执行 P0+术语检查。增量模式可以跳过完整三视角审查，但**不能跳过 P0+术语门控**。

**触发条件**：用户说"改Ch{N}""扩展Ch{N}""Ch{N}加个场景"等局部修改指令。
**不触发**：用户说"重新生成""重做大纲"→走全量模式。

## 编排器职责

只负责：**增量检测 + MCP调用 + Agent启动 + 检查点确认 + 保存**。不直接设计事件。

## Step 0: 增量检测与数据采集

### 0.0 数据一致性校验（强制）

```python
# 校验 DB 与文件一致性，不一致自动同步
consistency_guard(novel_name="NOVEL_NAME", auto_sync=True)
# 返回 synced_count > 0 时，提示用户哪些数据被同步了
```

### 0.1 增量检测（核心优化）

```python
# 检查是否存在上次的审计报告
audit_report = "novels/{小说名}/审阅报告/V{N}-卷级审计.md"

if audit_report exists:
    # 计算自上次审计以来的变更量
    git_diff = git diff --stat <last_audit_commit> -- "novels/{小说名}/设定/大纲/V{N}-*.md"
    changed_ratio = changed_lines / total_lines

    if changed_ratio < 0.3:
        mode = "增量审计"
        # 只审查变更的章节 + 前后各1章（因果链影响）
        scope = "变更章节及其邻章"
    else:
        mode = "全量审计"
        scope = "全部章节"
else:
    mode = "全量审计"
    scope = "全部章节"

# 展示给用户
print(f"审计模式: {mode} | 范围: {scope}")
```

**增量审计规则**：
- 变更比例低于三分之一：只审变更章+邻章，复用上次未变更部分的审查结果
- 变更比例达到或超过三分之一，或新增卷：全量审计
- 上次审计报告不存在：全量审计
- **强制全量触发**：用户明确要求、卷目标/核心设定变更、新增/删除整章

### 0.2 加载全书框架
```python
# 读取 novel-planner 输出（按需加载，不全读）
Read("novels/{小说名}/设定/全书大纲.md")          # 全书骨架
# 如有分文件则读取，否则从全书大纲提取
Read("novels/{小说名}/设定/大纲/跨卷因果链.md")    # 跨卷因果
```

### 0.3 加载本卷数据
```python
# 本卷大纲（核心输入）
Read("novels/{小说名}/设定/大纲/V{N}-{卷名}.md")

# 角色与伏笔（轻量）
character_list(novel_name="NOVEL_NAME")
foreshadow_list(novel_name="NOVEL_NAME", status='planted')

# 世界观（DB权威源，一次调用获取全部）
world_query(novel_name="NOVEL_NAME")
```

### 0.4 引擎加载（按步骤分批）

编排器在启动对应 Agent 时通过 `skill_loader` 传入引擎内容，**不预加载全部到编排器上下文**。

```
Step 1 (事件架构师) 需要：
  skill_loader("novel-planner-volume", "engine", "causality")
  skill_loader("novel-planner-volume", "engine", "relationship")

Step 2 (章节设计师) 需要：
  skill_loader("novel-planner-volume", "engine", "scene-type")
  skill_loader("novel-planner-volume", "engine", "scene-composition")
  skill_loader("novel-planner-volume", "engine", "author-voice")
  skill_loader("novel-planner-volume", "engine", "author-voice-emotion")
  skill_loader("novel-planner-volume", "engine", "author-voice-daily")
  skill_loader("novel-planner-volume", "engine", "author-voice-battle")
  skill_loader("novel-planner-volume", "engine", "author-voice-mystery")
  skill_loader("novel-planner-volume", "engine", "anti-ai-quickref")

Step 3 (三视角审查) 需要：
  skill_loader("novel-planner-volume", "engine", "reader-perspective-agent")
  skill_loader("novel-planner-volume", "engine", "author-perspective-agent")
  skill_loader("novel-planner-volume", "engine", "character-perspective-agent")

共享（Step 1/2 都需要）：
  skill_loader("novel-planner-volume", "agent", "shared-constraints")

🔒 术语规范（全程强制——所有 Agent 写前必读、写后自检）：
  Read(".claude/skills/lorecraft/SKILL.md")
  Read(".claude/skills/lorecraft/references/term-map.md")
  Read(".claude/skills/lorecraft/references/quickref.md")

🔒 世界元素索引（全程强制——Agent 1/2 输入必须包含）：
  Read(".claude/skills/engines/world-element-registry.md")
```

### 🔒 0.5 引擎加载验证（强制——防止静默丢弃）

编排器完成 Step 0.4 的所有加载后，**必须**在启动任何 Agent 之前执行以下验证：

```python
# 编排器在 Step 0.5 最后执行：
loaded_resources = {
    # Step 1 引擎
    "Step1-因果链(causality)": causality_loaded,
    "Step1-关系(relationship)": relationship_loaded,
    # Step 2 引擎
    "Step2-场景类型(scene-type)": scene_type_loaded,
    "Step2-场面合成(scene-composition)": scene_composition_loaded,
    "Step2-作者声音(author-voice)": author_voice_loaded,
    "Step2-作者声音-情感(author-voice-emotion)": author_voice_emotion_loaded,
    "Step2-作者声音-日常(author-voice-daily)": author_voice_daily_loaded,
    "Step2-作者声音-战斗(author-voice-battle)": author_voice_battle_loaded,
    "Step2-作者声音-悬疑(author-voice-mystery)": author_voice_mystery_loaded,
    "Step2-反AI速查(anti-ai-quickref)": anti_ai_loaded,
    # Step 3 引擎
    "Step3-读者视角(reader-perspective)": reader_loaded,
    "Step3-作者视角(author-perspective)": author_loaded,
    "Step3-人物视角(character-perspective)": character_loaded,
    # 共享
    "共享约束(shared-constraints)": shared_loaded,
    # 🔒 术语规范四件套（强制）
    "术语引擎(lorecraft-SKILL)": lorecraft_loaded,
    "术语映射(term-map)": term_map_loaded,
    "术语速查(quickref)": quickref_loaded,
    "世界元素索引(world-element-registry)": world_element_registry_loaded,
}

failed = [k for k, v in loaded_resources.items() if not v]
if failed:
    print(f"⚠️ 以下资源加载失败（可能被上下文截断）：{failed}")
    print("加载失败的资源不可跳过。请缩短其他内容或分批处理。")
    # 阻断：不允许启动 Agent
    return
else:
    print(f"✅ 全部 {len(loaded_resources)} 个资源加载成功")
    # 展示清单给用户确认
```

**为什么不应该在资源加载失败后仍启动 Agent**：Agent 依赖引擎文件中的方法论和约束来产出符合规范的内容。如果引擎加载失败，Agent 会在缺失关键约束的情况下工作，导致产出质量不可控，后续需要大量返工。如果上下文不足，编排器应提示用户并等待调整，而非静默跳过。

**世界观加载原则**：大纲设计必须基于已有世界观。世界观是创作的边界，不是建议。

### 0.6 加载上次审计报告（增量模式）
```python
if mode == "增量审计":
    Read(audit_report)
    # 从报告中提取：已通过的检查项、已标记的问题、上次验证状态

    # 🔒 强制检查：上次审计中是否有未修复的 P1/P2
    unresolved_p1 = [p for p in report.problems if p.level == "P1" and p.status != "✅已修"]
    unresolved_p2 = [p for p in report.problems if p.level == "P2" and p.status != "✅已修"]
    if unresolved_p1 or unresolved_p2:
        # 展示未修复问题给用户，要求确认是否继续
        print(f"⚠️ 上次审计有 {len(unresolved_p1)} 个P1 + {len(unresolved_p2)} 个P2未修复")
        print("未修复的问题不允许复用其审查结果，将在本轮重新审查。")
        # 将涉及未修复问题的章节加入审查范围
        scope.extend(affected_chapters_from(unresolved_p1 + unresolved_p2))
```

## Step 1: Agent — 事件架构师

**Agent指令**: `agents/event-architect.md`
**强制加载引擎**（编排器在 Step 0.4 调用 skill_loader，内容传给 Agent）：
- `engines/causality.md` — Agent **必须**集成因果逻辑网四步法设计事件因果链
- `engines/relationship.md` — Agent **必须**参考关系强度量表设计人物互动矩阵

### 编排器操作
1. 收集以下数据，打包传给 Agent：
   - 本卷大纲（`设定/大纲/V{N}-{卷名}.md`）
   - 全书骨架（`设定/全书大纲.md` 本卷部分）
   - 活跃角色列表 + 关键角色蒸馏卡（character_list + character_detail）
   - 未回收伏笔列表（foreshadow_list, status='planted'）
   - 上卷末角色状态（从上一卷大纲"人物弧光"表提取）
   - 卷定位（起/承/转/合）+ 全书第几卷
   - **🔒术语规范**：lorecraft/SKILL.md + term-map.md + quickref.md
   - **🔒世界元素索引**：world-element-registry.md
   - `engines/causality.md` 内容
   - `engines/relationship.md` 内容
2. 启动 Agent（subagent_type: "general-purpose"），传入数据 + `agents/event-architect.md`
3. Agent 输出事件架构（因果链+起承转合+人物弧光+悬念锚点+伏笔操作）

Agent 核心方法论见 `agents/event-architect.md`（已集成 causality.md 的因果逻辑网四步法）。

### Agent 硬约束
- 每章至少3个可辨识事件
- 费笔配额 ≥ 总章数×1.0（费笔定义见 agent 文件）
- 每个主要角色在卷内至少与2个不同角色有独立互动
- 任何角色连续3章无独立出场会导致配角边缘化，破坏群像感——应确保配角有独立出场节奏
- 因果链每个关键事件有显式前因
- 巧合计≤1次/卷且必须有伏笔支撑
- **🔒术语规范**：产出中无 term-map 禁止术语，新术语有文化出处

### 共享约束（编排器在启动Agent时通过 skill_loader 传入 `agents/shared-constraints.md`）

**Agent 必须遵守以下六类规则，详见 `shared-constraints.md`**：

| 规则集 | 核心内容 | 查阅文件 |
|--------|---------|---------|
| POV时间线铁律 | 主角时间线锚定、暗面标注、连续性、时间标注 | `agents/shared-constraints.md §1` |
| 内容密度规则 | 事件→字数映射、每章事件数、微事件、世界观展开 | `agents/shared-constraints.md §2` |
| 伏笔自然设计（冰山理论） | 表面动机、先果后因、场景自检 | `agents/shared-constraints.md §3` |
| 人物互动规则 | 组合多样性、罕见组合、费笔配额 | `agents/shared-constraints.md §4` |
| 巧合计规则 | ≤1次/卷、必须有伏笔支撑 | `agents/shared-constraints.md §5` |
| **🔒术语规范约束** | 禁止术语+替换对照+势力字根+新术语流程+已注册元素+层级区分+写后自检 | `agents/shared-constraints.md §6` |

编排器在 Step 0.4 加载 shared-constraints.md，在 Step 1/2 启动 Agent 时作为输入传入。Agent 在 `## 输入` 部分可见"共享约束"条目，**必须逐条遵守**。

## 🔒检查点A: 确认事件架构

编排器展示：

```
【V{N}《{卷名}》事件架构】

情感曲线: {起点} → {转折} → {终点}

起承转合:
  起(Ch?): {概要}
  承(Ch?): {概要}
  转(Ch?): {概要}
  合(Ch?): {概要} → 下卷钩子: {类型}

因果链: {事件1} → {事件2} → ... → {终点}

人物弧光:
  {角色A}: {起点状态} → {触发事件} → {终点状态}
  {角色B}: 不变（理由：{ }）

悬念: 回答了[?] / 新提出[?]

🔒术语自检: 全文无禁止术语 ✅/❌

确认后进入章节设计。输入"OK"或修改意见。
```

### 🔒检查点A-附加：新实体确认

如果事件架构师在设计中引入了**世界观中不存在的新实体**（新物品、新地点、新NPC、新能力、新概念等），编排器必须：

1. **列出所有新实体**：名称+类型+用途+为什么需要新增（参考 world-element-registry.md 的元素分类框架）
2. **查重**：对照 `world_query(novel_name="NOVEL_NAME")` 和已有设定文件确认不重复
3. **术语验证**：新实体命名是否使用灵能术语（非现代术语），是否有文化出处
4. **暂停等用户确认**：用户说"OK"才继续，否则修改或删除
5. **确认后保存**：
   - 文件：追加到 `novels/{小说名}/设定/世界观.md` / `物品.md` / `地图.md` 等对应文件
   - DB：调用 `world_upsert(novel_name="NOVEL_NAME", category, name, data)` 或 `character_create(novel_name="NOVEL_NAME", name, ...)`

**新实体类型与保存位置**：

| 新实体类型 | 保存文件 | DB操作 |
|-----------|---------|--------|
| 新地点 | 设定/地图.md | world_upsert(category='location') |
| 新物品 | 设定/物品.md | world_upsert(category='ability') |
| 新NPC | 设定/角色总览.md | character_create() |
| 新能力/概念 | 设定/世界观.md | world_upsert(category='ability') |
| 新势力/组织 | 设定/世界观.md | world_upsert(category='faction') |

**注册规范**（参考 world-element-registry.md）：
- 每个新实体必须包含：名称/类型/描述/关联元素/首次出现章节
- 新物品需定义：外观/功能/获取方式/限制条件
- 新地点需定义：位置/环境特征/势力归属/危险等级
- 新NPC需定义：身份/性格/动机/与现有角色的关系

**为什么不应该让 Agent 自行创建新实体后不通知编排器**：新实体需要经过查重、术语验证和用户确认才能确保世界观一致性。如果 Agent 静默创建，可能导致命名冲突、术语违规或重复定义，破坏世界观的完整性。所有新实体必须经过用户确认。

## Step 2: Agent — 章节设计师

**Agent指令**: `agents/chapter-designer.md`
**强制加载引擎**（编排器在 Step 0.4 调用 skill_loader，内容传给 Agent）：
- `engines/scene-type.md` — Agent **必须**按6种场景类型（对话/动作/氛围/心理/日常/混合）选择每章场景结构
- `engines/scene-composition.md` — Agent **必须**按场面密度分级（轻/中/重/大场面）+多人动力学设计场景
- `engines/author-voice.md` + 变体 — Agent **必须**标注每个场景的声音层

### 编排器操作
1. 将 Step 1 确认后的事件架构 + 角色蒸馏卡 + 世界观索引 + 引擎内容 + **🔒术语规范** + **🔒世界元素索引** 打包传给 Agent
2. 启动 Agent（subagent_type: "general-purpose"），传入数据 + `agents/chapter-designer.md`
3. Agent 输出逐章大纲

Agent 方法论/硬约束/铁律详见 `agents/chapter-designer.md`（已集成 scene-type/scene-composition/author-voice 强制规则）。

### 🔒检查点A2：确认逐章大纲

编排器展示 Agent 2 输出的逐章大纲（含每章场景序列+伏笔操作+声音适配），等待用户审查：

```
【V{N}《{卷名}》逐章大纲】（共{N}章）

Ch{1}: {标题} | {场景数}个场景 | {核心事件}
  - 场景类型: {对话/动作/氛围/心理/日常/混合} | 声音层: {类型}
  - 伏笔: {埋设/深化/回收}{N}条 | 费笔: {N}个
Ch{2}: ...
...
Ch{末}: {标题} | {场景数}个场景 | {章末钩子}
  - 下卷接口: {如何衔接V{N+1}}

【硬约束自检】
- 事件密度: ≥4/章 ✅/❌
- 费笔配额: ≥总章数×1.0 ✅/❌
- 罕见组合: ≥1个/卷 ✅/❌
- 伏笔场景化: 全部有具体场景 ✅/❌
- 主角在场: 占全卷章节数的一半以上 ✅/❌
- 时间线连续: 无跳跃 ✅/❌
- 🔒术语规范: 无禁止术语 ✅/❌

输入"OK"进入验证，或提修改意见（可指定某章修改）。
```

**修改循环**：用户提修改意见 → 编排器局部修改指定章节 → 重新展示 → 用户确认OK → 进入三视角审查。

## Step 3: 三视角审查（3Agent 并行 — 编排器直接启动）

**编排器启动 3 个独立 Agent 并行**（互不依赖、同时执行）：

| Agent | 加载引擎 | 审查维度 | 运行模式 |
|-------|---------|---------|---------|
| **Agent-读者** | `engines/reader-perspective-agent.md` | 开篇钩子/信息层级/悬念分布/爽点节奏/弃文风险 | 独立并行 |
| **Agent-作者** | `engines/author-perspective-agent.md` | 起承转合/因果链穿透/伏笔层级/主题一致性 | 独立并行 |
| **Agent-人物** | `engines/character-perspective-agent.md` | 弧光对齐/动机充分/选择必然/代价明确/OOC检测 | 独立并行 |

### 编排器操作（串行 → 并行 → 串行）

```
开始 → 编排器启动 3Agent（并行）→ 等待全部返回 → 编排器汇总交叉检查
```

1. 编排器将 Step 2 确认的逐章大纲 + 角色数据 + **🔒术语规范(term-map)** 打包，同时传给 3 个 Agent
2. 3 个 Agent **同时启动**（并行），各自加载自己的视角引擎
3. 编排器**等待全部返回**后才继续
4. 全部返回后编排器执行交叉检查（读者vs作者/读者vs人物/作者vs人物）
5. **🔒术语交叉扫描**：编排器对全部逐章大纲执行 term-map 禁止术语扫描，发现违规记为 P1
6. 输出审计报告到 `审阅报告/V{N}-卷级审计.md`

### 交叉检查
- [ ] 读者vs作者无冲突（结构服务读者体验）
- [ ] 读者vs人物无冲突（人物选择优先，但有动机）
- [ ] 作者vs人物无冲突（人物逻辑>结构需求）
- [ ] **🔒术语扫描无违规**（逐章检查 term-map 禁止术语）
**核心原则**：人物 > 读者 > 作者

### 问题分级
| 级别 | 判定标准 | 处理要求 |
|------|---------|---------|
| P0 | 三视角冲突/角色OOC/因果链断裂 | **必须修复**，阻断保存 |
| P1 | 单视角严重问题 / **🔒术语违规** | **必须修复**——本轮验证结束前完成修复 |
| P2 | 微调建议 | **必须修复**——下一轮迭代开始前完成 |

### 🔒检查点B: 确认验证通过

P0→必须修复（回到对应Step）。无P0→进入保存。

## Step 4: 保存

### 🔒输出确认流程（强制）

**在写入任何文件之前**，编排器必须：

1. **展示完整输出**：将Agent产出的完整内容展示给用户
2. **等待用户确认**：用户说"OK"才继续，否则按修改意见修改后重新展示
3. **修改循环**：用户修改→重新输出→再确认，直到用户说"OK"
4. **检查点确认**：Step 1事件架构、Step 2逐章大纲、Step 3审计结果，每个都要独立确认

```
编排器展示 → 用户确认
  ↓ OK           ↓ 修改意见
写入文件      修改内容 → 重新展示 → 用户确认
  ↓                                    ↓ OK
继续下一步                            写入文件
```

**为什么不应该未经用户确认直接写入文件**：即使Agent输出看起来完美，也可能存在用户未表达的新意图或调整需求。提前写入会导致文件与用户预期不一致，增加后续修改成本。必须展示后等确认。

### 文件落盘

大纲设计原则：**以章为单元，每章独立成块。** 用户扫读/修改只需要看对应章节，novel-chapter-writer 写作时逐章加载。

卷级大纲模板见 `references/volume-outline-template.md`。

```
novels/{小说名}/设定/大纲/V{N}-{卷名}.md          # 卷级故事大纲
```

##### 硬指标（不达标拒绝存盘）

- 故事脉络四段都有（起承转合），每段有事件清单+费笔清单
- 人物弧光覆盖所有主要角色（主角+至少3个配角）
- 伏笔清单每个操作有具体场景化方式（不应只写"在Ch{N}提到"，必须有动作/对话/物件/环境描述+表面动机）
- 下卷钩子在合段明确标注
- **🔒术语规范**：全文无 term-map 禁止术语

### 审计报告保存
```
novels/{小说名}/审阅报告/V{N}-卷级审计.md          # 审计结果持久化
```

审计报告格式见 `references/audit-report-template.md`。

### DB保存（强制——为正文生成提供数据支撑，含结果校验）
```python
# 🔒 每个 MCP 调用后必须检查返回值，失败时中止并提示
errors = []

def check_result(op_name, result):
    """检查 MCP 调用结果，失败则记录"""
    if '"ok": false' in result or '"error"' in result:
        errors.append(f"{op_name} 失败: {result}")

# 1. 更新卷级信息
result = volume_update_by_number(novel_name="NOVEL_NAME", number={volume_number}, main_plotlines=[...], notes="...")
check_result("volume_update", result)

# 2. 规划章节（每章一条）
for chapter in chapters:
    result = chapter_plan(novel_name="NOVEL_NAME", number, title, outline, chapter_type, volume_id)
    check_result(f"chapter_plan Ch{chapter.number}", result)

# 3. 埋设伏笔
for foreshadow in foreshadows:
    result = foreshadow_plant(novel_name="NOVEL_NAME", description, planned_recall_chapter, importance, tags)
    check_result("foreshadow_plant", result)

# 4. 同步世界观（确保正文生成时DB有完整数据）
for location in new_locations:
    result = world_upsert(novel_name="NOVEL_NAME", category='location', name=location.name, data={...},
        keys=location.keys, tags=location.tags, volume_range=location.volume_range,
        writing_guide=location.writing_guide)
    check_result(f"world_upsert 地点-{location.name}", result)

for item in new_items:
    result = world_upsert(novel_name="NOVEL_NAME", category='ability', name=item.name, data={...},
        keys=item.keys, tags=item.tags, volume_range=item.volume_range)
    check_result(f"world_upsert 物品-{item.name}", result)

for character in new_characters:
    result = character_create(novel_name="NOVEL_NAME", name=character.name, ...,
        appearance_detail=character.appearance_detail,
        decision_engine=character.decision_engine,
        voice_fingerprint=character.voice_fingerprint,
        behavior_pattern=character.behavior_pattern,
        current_snapshot=character.current_snapshot)
    check_result(f"character_create-{character.name}", result)

for faction in new_factions:
    result = world_upsert(novel_name="NOVEL_NAME", category='faction', name=faction.name, data={...},
        keys=faction.keys, tags=faction.tags, volume_range=faction.volume_range,
        writing_guide=faction.writing_guide)
    check_result(f"world_upsert 势力-{faction.name}", result)

# 5. 更新已有角色状态（如有变化）
for character in changed_characters:
    result = character_update_by_name(novel_name="NOVEL_NAME", character_name={character_name}, status=character.new_status, ...,
        current_snapshot=character.current_snapshot,
        growth_trajectory=character.growth_trajectory)
    check_result(f"character_update-{character_name}", result)

# 6. 创建人物关系（如有新关系）
for relation in new_relations:
    result = relation_create_by_name(novel_name="NOVEL_NAME", from_name={from_name}, to_name={to_name}, relation_type=..., ...)
    check_result(f"relation_create-{from_name}↔{to_name}", result)

# 7. 注册暗线/支线
for thread in volume_threads:
    result = plot_thread_create(
        novel_name="NOVEL_NAME", name=thread.name, thread_type=thread.type,
        description=thread.description, start_chapter_id=thread.start_chapter_id,
        volume_scope=json.dumps(thread.volume_scope),
        related_characters=json.dumps(thread.related_characters),
        related_foreshadows=json.dumps(thread.related_foreshadows))
    check_result(f"plot_thread_create-{thread.name}", result)

# 8. 更新已有暗线/支线状态
for thread in updated_threads:
    result = plot_thread_update(
        thread_id=thread.id, status=thread.new_status,
        end_chapter_id=thread.end_chapter_id,
        progress_notes=json.dumps(thread.progress_notes))
    check_result(f"plot_thread_update-{thread.id}", result)

# 🔒 结果校验
if errors:
    print(f"⚠️ DB保存失败（{len(errors)}个错误）：")
    for e in errors:
        print(f"  - {e}")
    print("文件已写入但DB未完全同步。请修复后重试，不执行 git commit。")
    # 中止流程
    return
else:
    print(f"✅ 全部 {total_ops} 个 DB 操作成功")
```

**DB同步原则**：大纲阶段产出的所有结构化数据（地点/物品/人物/势力/伏笔/章节）必须同步到DB，确保正文生成阶段（novel-chapter-writer）通过 `get_chapter_context` 聚合调用能获取到完整信息。

### git commit
```
B1: V{N}《{卷名}》卷级大纲{变更描述}
```

</what-to-do>

<supporting-info>

## 与上下层的关系

- **上层：novel-planner**：提供"每卷做什么"（卷目标/核心事件类型/钩子设计）
- **本层：novel-planner-volume**：设计"每章发生什么"——**把握脉络，不注册细节**
- **下层：novel-chapter-writer**：根据本层大纲生成正文。**世界元素注册在正文写作阶段完成**（Ch9-2老猎人事件后才会出现"源质分级名单"这种具体元素，卷级大纲无法预知具体描写）

## 本层不做的事（明确边界）

| 不做 | 原因 | 谁做 | 相关引擎 |
|------|------|------|---------|
| 世界元素注册（具体感官/功能/外观） | 卷级只知道事件框架，具体物品/地点/能力的五感细节是正文写作时才确定的 | novel-chapter-writer (Agent 2 Creative Director) | `engines/world-element-registry.md` |
| 感官5要素分配 | 每个场景的视觉/听觉/嗅觉在正文写作时才有意义 | novel-chapter-writer (Agent 3 Engine Coordinator) | `engines/environment.md` 环境5要素 |
| 逐章字数精确控制 | 大纲阶段预估章节字数，实际字数由 writing-constraints.md 在写作时控制 | novel-chapter-writer + validate_chapter | — |
| 完整对话撰写 | 大纲只留全书级核心句（≤3句），其余对话留给正文 | novel-chapter-writer (Agent 4 Text Generator) | `engines/dialogue.md` 对话系统 |
| 反AI指纹检测 | 正文生成后通过 validate_chapter 做硬约束校验 | novel-chapter-writer + `SENTENCE-PATTERNS.md` | `engines/anti-ai.md` + `engines/anti-ai-patterns.md` |

**本层扩展职责**：
| 新增职责 | 原因 | 参考引擎 |
|---------|------|---------|
| 费笔配额设计 | 费笔事件需要在因果链中有位置，不能正文时临时塞。大纲阶段规划"谁在哪里做了什么日常" | — |
| 人物互动矩阵 | 确保角色出场均衡、罕见组合不遗漏——这是结构问题不是正文细节 | `engines/relationship.md` 关系变化追踪+强度量表 |
| 伏笔场景化 | 每个伏笔必须有具体埋设场景设计——"在Ch{N}提到"不是大纲，是偷懒 | `engines/causality.md` 因果链编织 |
| 配角独立场景 | 确保配角有自己的生活线——大纲不规划，正文就会把所有配角写成围着主角转 | — |

## 声音适配规则

**相关引擎**: `engines/author-voice.md`（作者声音三层架构）+ 5个变体文件：
- `engines/author-voice-emotion.md` — 情感场景的感性与克制平衡
- `engines/author-voice-daily.md` — 日常场景的松弛与真实感
- `engines/author-voice-battle.md` — 战斗场景的节奏与压迫感
- `engines/author-voice-mystery.md` — 悬疑场景的克制与信息释放
- `engines/author-voice.md` 项目层：`设定/作者声音.md`

Agent 2（章节设计师）为每章标记声音层，写入大纲供正文写作时加载：

| 章节事件类型 | 加载声音层 | 参考引擎 |
|-------------|-----------|---------|
| 战斗/动作 | author-voice-battle | `engines/author-voice-battle.md` |
| 情感高潮/离别/重逢 | author-voice-emotion | `engines/author-voice-emotion.md` |
| 日常/世界呼吸/荒诞 | author-voice-daily | `engines/author-voice-daily.md` |
| 悬疑/揭秘/伏笔回收 | author-voice-mystery | `engines/author-voice-mystery.md` |
| 混合类型 | 主类型+辅助声音层 | 同时加载对应变体 |

Agent 2 输出每章大纲时标注 `声音层: {类型}` 字段，正文写作阶段（novel-chapter-writer）根据此字段加载对应声音引擎。

## 增量审计设计

### 为什么需要增量
百万字小说14卷，每卷15-20章。每次改几章就全量审计 = 浪费context和时间。

### 增量检测依据
- `git diff --stat` 计算变更比例
- 变更比例低于三分之一 → 增量（只审变更章+邻章）
- 变更比例达到或超过三分之一 → 全量
- 审计报告持久化在 `审阅报告/` 目录

### 审计报告的作用
- **断点续传**：下次审计时读取上次结果，未变更部分直接复用
- **变更追溯**：`修改记录` 表记录每次变更
- **问题追踪**：P0/P1问题的修复状态持续跟踪

## 项目专属数据

《NOVEL_NAME》的卷级数据存于：
`references/novel-planner/project-context.md`

Agent 设计时，编排器将此文件作为附加输入提供。

</supporting-info>
