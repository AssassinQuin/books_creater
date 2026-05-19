---
name: novel-planner-volume
description: 卷级大纲设计。把握小说脉络——事件架构+因果链+人物弧光+伏笔节奏。不做细节注册，留给正文写作阶段。触发词：设计卷/卷大纲/章节规划/事件设计
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, Agent, Task, mcp__novel-db__*
depends_on: novel-planner, lorecraft, engines/causality, engines/relationship, engines/scene-type, engines/scene-composition, lorecraft/references/quickref
lifecycle: core
version: "1.5.0"
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

### 增量扩展模式

用户对已生成大纲提出**局部修改**时走捷径（完整流程详见 supporting-info §增量扩展模式）。
- **触发**："改Ch{N}""扩展Ch{N}""Ch{N}加个场景"等局部修改指令
- **不触发**："重新生成""重做大纲"→走全量模式
- **核心规则**：可跳过完整三视角审查，但**不可跳过 Step 2.5 P0+术语门控**

## 编排器职责

只负责：**增量检测 + MCP调用 + Agent启动 + 检查点确认 + 保存**。不直接设计事件。

## Step 0: 增量检测与数据采集

### 0.0 数据一致性校验（强制）
```python
# 校验 DB 与文件一致性，不一致自动同步
consistency_guard(novel_name="NOVEL_NAME", auto_sync=True)
```

### 0.1 增量检测（详见 supporting-info §增量检测算法）

检查上次审计报告是否存在，计算 `git diff --stat` 变更比例（changed_lines / total_lines）：
- **<30%** → 增量审计（只审变更章+前后各1章）
- **≥30% 或无报告** → 全量审计
- **强制全量**：用户要求、卷目标/核心设定变更、新增/删除整章

### 0.2 加载全书框架
```python
# 检查文件存在再加载，不存在则跳过（框架文件非必需）
for f in ["全书框架.md", "全书脉络.md", "卷级目标卡.md"]:
    path = f"novels/{{小说名}}/设定/大纲/{f}"
    if os.path.exists(path):
        Read(path)
```

### 0.3 加载本卷数据
```python
Read("novels/{小说名}/设定/大纲/V{N}-{卷名}.md")
character_list(novel_name="NOVEL_NAME")
foreshadow_list(novel_name="NOVEL_NAME", status='planted')
world_query(novel_name="NOVEL_NAME", volume="V{N}")  # 按卷过滤，减少无关设定
```

### 0.4 引擎加载（按步骤分批，编排器统一加载后分发）

编排器按步骤顺序加载所需引擎，**打包后传入对应 Agent**。编排器上下文只保留加载清单，不预加载全部引擎内容到编排器上下文。

**分发原则**：编排器加载完的文件直接打包传 Agent，Agent 自主使用。但对 Step 3 审查 Agent 采用**精简分发**——编排器预提取关键信息（术语禁止列表+势力字根表），作为字符串直接注入 Agent 指令，Agent **不再自主加载任何引擎或 lorecraft 文件**。

- **Step 1** (事件架构师)：causality, relationship, shared-constraints, lorecraft四件套, world-element-registry, **spiral-structure, plot-density**
- **Step 2** (章节设计师)：scene-type, scene-composition, anti-ai-quickref, shared-constraints, lorecraft四件套, world-element-registry
  + 声音层：编排器不从引擎文件全量加载 author-voice×5（详见 §0.4.5 声音层头部提取），而是用 Read(limit=5) 提取每个变体的**头部摘要**（标题+加载时机行），编译为速查表注入 Agent
- **Step 3** (三视角审查)：reader/author/character-perspective-agent + **精简分发**（只给 quickref 禁止术语+势力字根摘要，不给全量）
  - ❌已移除：world-element-registry, shared-constraints, lorecraft-core-principles, term-map

完整清单详见 supporting-info §引擎加载清单。

### 0.4.5 作者声音层头部提取（替代 author-voice 全量加载）

编排器**不通过 skill_loader 也不设独立查表文件**，而是直接 Read 每个 author-voice 变体文件的**前 5 行**（标题+加载时机行），提取关键关联：

```python
# 提取各声音变体头部（标题+加载时机）编译为速查表
voice_layer_headers = {}
files = {
    "battle":  ".claude/skills/engines/author-voice-battle.md",
    "emotion": ".claude/skills/engines/author-voice-emotion.md",
    "daily":   ".claude/skills/engines/author-voice-daily.md",
    "mystery": ".claude/skills/engines/author-voice-mystery.md",
}
for variant, path in files.items():
    lines = Read(path, limit=5)  # 只读前5行
    # 第1行: # 作者声音 — {类型}剧情层
    # 第2-3行: > 加载时机：{场景类型}。在通用层基础上叠加。
    voice_layer_headers[variant] = lines

# 编译为速查表字符串直接注入 Agent 2 指令
# → 事件类型=情感/离别/重逢 → 标记声音层=emotion
# → 事件类型=战斗/动作 → 标记声音层=battle
```

**优势**：读取量仅 ~25 行（5 文件×前 5 行），约 1.5 KB，替代 17.5 KB 全量加载。**引擎源文件是唯一权威源，无需独立维护查表文件**。novel-chapter-writer 正文阶段仍然加载完整引擎文件。

### 0.5 引擎加载验证（确保Agent拿到完整约束）

完成 Step 0.4 加载后，在启动任何 Agent 之前验证全部资源加载成功。验证逻辑详见 supporting-info §引擎加载验证。加载失败的资源会影响Agent产出质量，如果上下文不足，编排器应提示用户并等待调整，而非静默跳过。

**世界观加载原则**：大纲设计必须基于已有世界观。世界观是创作的边界，不是建议。

### 0.6 加载上次审计报告（增量模式）

增量审计时读取审计报告，提取已通过项和未修复的P1/P2。未修复问题涉及的章节加入本轮审查范围。详细逻辑详见 supporting-info §审计报告增量加载。

## Step 1: Agent — 事件架构师

**Agent指令**: `agents/event-architect.md` | **引擎**: causality.md + relationship.md + **spiral-structure.md + plot-density.md**

### 编排器操作
1. 收集并打包传给 Agent：本卷大纲、全书骨架、活跃角色列表+蒸馏卡、未回收伏笔、上卷末角色状态、卷定位、🔒术语规范、🔒世界元素索引、引擎内容（含 spiral-structure + plot-density）
2. 启动 Agent（subagent_type: "general-purpose"），传入数据 + agent 指令
3. Agent 输出事件架构（因果链+起承转合+人物弧光+悬念锚点+伏笔操作+**螺旋结构+情节密度**）

### Agent 硬约束
- 每章至少3个可辨识事件
- 费笔配额 ≥ 总章数×1.0
- 每个主要角色在卷内至少与2个不同角色有独立互动
- 任何角色连续3章无独立出场→配角边缘化，破坏群像感
- 因果链每个关键事件有显式前因
- 巧合计≤1次/卷且必须有伏笔支撑
- **🔒术语规范**：产出中的世界观术语有文化根脉、与根隐喻字根一致
- **🔒螺旋结构**：三层信息矩阵完整（L1/L2/L3）+ 翻新型揭示 ≥1次/卷 + 回旋镖决策 ≥3个/卷
- **🔒情节密度**：并行活跃链 ≥3条 + 每章≥2条链推进 + NPC议程追踪表完整 + 复杂化每章≥1次

### 共享约束

Agent 必须遵守七类规则（事件驱动节奏铁律、内容密度、伏笔冰山理论、人物互动、巧合计、🔒术语规范约束、回响规则），编排器通过 skill_loader 传入 `shared-constraints.md`。详细规则表见 supporting-info §共享约束详细规则。

## 🔒检查点A: 确认事件架构

编排器展示：情感曲线 + 起承转合概要 + 因果链 + 人物弧光 + 悬念 + 🔒术语自检。
显示模板详见 supporting-info §检查点A显示模板。
用户说"OK"继续，否则修改。

### 🔒检查点A-附加：新实体确认

事件架构引入新实体时：**列出所有新实体** → 查重(world_query+设定文件) → 术语验证 → 暂停等用户确认("OK") → 保存到文件+DB。
新实体类型对照表与注册规范详见 supporting-info §新实体注册。

## Step 2: Agent — 章节设计师

**Agent指令**: `agents/chapter-designer.md` | **引擎**: scene-type + scene-composition + 声音层头部提取(§0.4.5)

### 编排器操作
1. 打包：**传递摘要**（Step 1 的压缩版——见下方"Step 1→Step 2 手递格式"）+ 角色蒸馏卡 + 世界观索引 + 引擎内容 + 🔒术语规范 + 🔒世界元素索引
2. 启动 Agent（subagent_type: "general-purpose"），传入数据 + agent 指令
3. Agent 输出逐章大纲

### Step 1→Step 2 手递格式（结构化的传递摘要）

编排器从 Step 1 输出的完整事件架构中提取以下字段打包，**不传全量事件架构**：

```
## 传递摘要（仅用于Step 2的结构化输入）

### 章级事件流
Ch{N}: [事件A→事件B→事件C] | 功能: {起/承/转/合}
Ch{N+1}: [事件D→事件E→事件F→事件G] | 功能: {起/承/转/合}

### 角色弧线备忘
{角色X}: {卷初状态} → {关键触发} → {卷末状态}
{角色Y}: {不变+理由}

### 伏笔操作清单
| 操作 | 伏笔ID | 预期章节 | 表面动机 |
|------|--------|---------|---------|
| 埋设 | F{N} | Ch{N} | {动作动机} |
| 深化 | F{M} | Ch{N+2} | {场景动机} |
| 回收 | F{K} | Ch{N+3} | {触发条件} |
```

**重要**：这是编排器的手递动作，不是 Step 1 的输出格式。Step 1 Agent 仍按 `event-architect.md` 输出完整版（含因果链推理和悬念锚点）。编排器在 Step 1 输出中**提取传递摘要**，传给 Step 2 Agent。

### 🔒检查点A2：确认逐章大纲

展示逐章大纲（含每章场景序列+伏笔操作+声音适配）+ 硬约束自检。显示模板详见 supporting-info §检查点A2显示模板。

**硬约束自检项**：事件密度≥4/章、费笔配额≥总章数×1.0、罕见组合≥1/卷、伏笔场景化、主角在场≥半数章、事件弧节奏、🔒术语规范。

**修改循环**：用户提修改意见 → 编排器局部修改指定章节 → 重新展示 → 确认OK → 进入三视角审查。

## Step 3: 三视角审查（3Agent 并行·精简分发）

| Agent | 审查维度 | 运行模式 | 所获数据 |
|-------|---------|---------|---------|
| **Agent-读者** | 开篇钩子/信息层级/悬念分布/爽点节奏/弃文风险 | 独立并行 | 逐章大纲+角色出场表+🔒术语速查摘要 |
| **Agent-作者** | 起承转合/因果链穿透/伏笔层级/主题一致性 | 独立并行 | 逐章大纲+🔒术语速查摘要 |
| **Agent-人物** | 弧光对齐/动机充分/选择必然/代价明确/OOC检测 | 独立并行 | 逐章大纲+角色蒸馏卡+🔒术语速查摘要 |

### 编排器操作
1. 打包逐章大纲 + 🔒**术语精简摘要**（编排器预提取 quickref 中的禁止术语清单+势力字根表，直接注入）
2. 3Agent 同时启动（并行），各自加载视角引擎
3. 等待全部返回 → 交叉检查(读者vs作者/读者vs人物/作者vs人物) → 🔒术语交叉扫描 → 输出审计报告

> 📌 **精简分发原则**：编排器在 Step 0.4 已加载完整的术语规范文件。Step 3 启动 Agent 时，编排器将 quickref 中最关键的部分——**禁止术语列表（§6.1）和势力字根表（§6.3）**——提取为一段摘要字符串直接注入 Agent 指令。Step 3 Agent **不自主加载** world-element-registry、shared-constraints、lorecraft-core-principles、term-map 或任何其他文件。**这是强制约束——审查 Agent 只需要做术语验证，不需要知道命名方法论。**

### 交叉检查 & 问题分级
**核心原则**：人物 > 读者 > 作者

| 级别 | 判定标准 | 处理 |
|------|---------|------|
| P0 | 三视角冲突/角色OOC/因果链断裂 | **必须修复**，阻断保存 |
| P1 | 单视角严重问题 / **🔒术语违规** | **必须修复**——本轮验证结束前 |
| P2 | 微调建议 | **必须修复**——下一轮迭代前 |

### 🔒检查点B: 确认验证通过

P0→必须修复（回到对应Step）。无P0→进入保存。

## Step 4: 保存

### 🔒输出确认流程（强制——详见 supporting-info §输出确认流程）

写入任何文件之前：展示完整输出 → 等用户确认("OK") → 才写入。Step 1/2/3 每个检查点独立确认。

### 文件落盘

大纲以章为单元，每章独立成块。模板见 `references/volume-outline-template.md`。

```
novels/{小说名}/设定/大纲/V{N}-{卷名}.md          # 卷级故事大纲
novels/{小说名}/审阅报告/V{N}-卷级审计.md          # 格式见 references/audit-report-template.md
```

**硬指标**（不达标拒绝存盘）：
- 起承转合四段完整（每段有事件清单+费笔清单）
- 人物弧光覆盖主角+≥3配角
- 伏笔清单场景化（有动作/对话/物件/环境描述+表面动机）
- 下卷钩子标注
- **🔒术语规范**全文合规

### DB保存（强制——详见 supporting-info §DB保存MCP调用）

全部结构化数据（章节/伏笔/地点/物品/人物/势力/关系/暗线支线）必须同步到DB，每个MCP调用含结果校验。失败则中止，不执行 git commit。

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

## 增量扩展模式（完整流程）

当用户对已生成大纲提出**局部修改**（如"Ch001加一个异灵追击场景""Ch003时间线不对"）时，**不重跑全流程**，走以下捷径：

```
Step 0: 定位影响范围
  ↓  读取目标章节行范围（不读全卷卷纲）：编排器利用 shell 提取修改章对应的 section 行范围
  ↓  检查因果链影响：改动是否波及邻章？
Step 1: 只修改目标章节
  ↓  编排器直接修改指定章节的场景/事件
  ↓  如需新增伏笔/角色，编排器调MCP创建
Step 2: 邻章校验
  ↓  检查修改后的章节与前后章的因果链/时间线是否连贯
  ↓  如有断裂，扩展修复范围
### Step 2.5 轻量级 P0+术语审查（增量模式必经关卡）
  ↓  编排器对修改章+邻章执行 P0 检查 + 🔒术语扫描（见下方检查清单）
  ↓  发现 P0 或术语违规 → 修复后重新检查，直到全部通过
  ↓  无问题 → 用户确认 → 继续
Step 3: 保存 → git commit
```

**Step 2.5 P0 检查清单**（增量模式下必须全部通过，否则阻断保存）：
- [ ] **角色OOC检测**：修改章中每个出场角色的行为/对话是否符合其角色蒸馏卡（character_detail）
- [ ] **因果链断裂检测**：修改引入的事件是否与前后章因果链连贯？是否有"因为剧情需要"式的无前因事件？
- [ ] **时间节奏合理性**：修改章是否按事件驱动组织？同一事件弧内时间连续，事件弧结束后允许跳跃？
- [ ] **新实体一致性**：新增的角色/地点/物品是否已调MCP注册（character_create/world_upsert）？
- [ ] **🔒术语质量**：修改章中世界观数术语是否有文化根脉？与 term-map 一致？

**增量模式下 Step 2.5 是必经关卡**——即使只是"加一句对话"，也需要确认改动没有引入角色OOC或术语不一致。增量模式可以跳过完整三视角审查。

## 增量检测算法（Step 0.1 完整逻辑）

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

## 引擎加载清单（Step 0.4 完整列表）

编排器按步骤加载并分发，**Step 3 采用精简分发**——编排器预提取 quickref 的禁止术语+势力字根，直接注入指令，Agent 不自主加载任何引擎文件。

```
Step 1 (事件架构师) 需要：
  skill_loader("novel-planner-volume", "engine", "causality")
  skill_loader("novel-planner-volume", "engine", "relationship")
  skill_loader("novel-planner-volume", "engine", "spiral-structure")
  skill_loader("novel-planner-volume", "engine", "plot-density")
  skill_loader("novel-planner-volume", "agent", "shared-constraints")
  Read(".claude/skills/lorecraft/references/core-principles.md")   # 核心原则+禁止术语+四步法
  Read(".claude/skills/lorecraft/references/term-map.md")          # 现代→灵能术语映射表
  Read(".claude/skills/lorecraft/references/quickref.md")           # 速查卡
  Read(".claude/skills/engines/world-element-registry.md")         # 已注册元素索引

Step 2 (章节设计师) 需要：
  skill_loader("novel-planner-volume", "engine", "scene-type")
  skill_loader("novel-planner-volume", "engine", "scene-composition")
  skill_loader("novel-planner-volume", "engine", "anti-ai-quickref")
  skill_loader("novel-planner-volume", "agent", "shared-constraints")
  Read(".claude/skills/lorecraft/references/core-principles.md")
  Read(".claude/skills/lorecraft/references/term-map.md")
  Read(".claude/skills/lorecraft/references/quickref.md")
  Read(".claude/skills/engines/world-element-registry.md")
  # 声音层：编排器 Read(author-voice-{variant}.md, limit=5) 提取头部速查，详见 §0.4.5
  Read(".claude/skills/engines/author-voice.md", limit=3)
  Read(".claude/skills/engines/author-voice-battle.md", limit=5)
  Read(".claude/skills/engines/author-voice-emotion.md", limit=5)
  Read(".claude/skills/engines/author-voice-daily.md", limit=5)
  Read(".claude/skills/engines/author-voice-mystery.md", limit=5)

Step 3 (三视角审查) 需要：
  skill_loader("novel-planner-volume", "engine", "reader-perspective-agent")
  skill_loader("novel-planner-volume", "engine", "author-perspective-agent")
  skill_loader("novel-planner-volume", "engine", "character-perspective-agent")
  # 📌 精简分发：编排器预提取 quickref 的禁止术语清单+势力字根表，作为字符串注入指令。
  # ❌ 不加载：world-element-registry, shared-constraints, lorecraft-core-principles, term-map
  # Step 3 Agent 收到的术语约束仅为精简摘要，禁止自行加载文件。
```

## 引擎加载验证（Step 0.5 完整逻辑）

编排器完成 Step 0.4 的所有加载后，**必须**在启动任何 Agent 之前执行以下验证：

```python
# 编排器在 Step 0.5 最后执行：
loaded_resources = {
    # Step 1 引擎
    "Step1-因果链(causality)": causality_loaded,
    "Step1-关系(relationship)": relationship_loaded,
    "Step1-螺旋结构(spiral-structure)": spiral_structure_loaded,
    "Step1-情节密度(plot-density)": plot_density_loaded,
    # Step 2 引擎
    "Step2-场景类型(scene-type)": scene_type_loaded,
    "Step2-场面合成(scene-composition)": scene_composition_loaded,
    "Step2-反AI速查(anti-ai-quickref)": anti_ai_loaded,
    "Step2-声音层头部(voice-battle)": voice_battle_header_loaded,
    "Step2-声音层头部(voice-emotion)": voice_emotion_header_loaded,
    "Step2-声音层头部(voice-daily)": voice_daily_header_loaded,
    "Step2-声音层头部(voice-mystery)": voice_mystery_header_loaded,
    # 共享约束
    "Step1-共享约束(shared-constraints)": shared_loaded_s1,
    "Step2-共享约束(shared-constraints)": shared_loaded_s2,
    # 🔒 术语规范（Step 1/2 强制，Step 3 精简分发）
    "Step1-术语核心原则(lorecraft-core)": lorecraft_loaded_s1,
    "Step1-术语映射(term-map)": term_map_loaded_s1,
    "Step1-术语速查(quickref)": quickref_loaded_s1,
    "Step1-世界元素索引(world-element-registry)": registry_loaded_s1,
    "Step2-术语核心原则(lorecraft-core)": lorecraft_loaded_s2,
    "Step2-术语映射(term-map)": term_map_loaded_s2,
    "Step2-术语速查(quickref)": quickref_loaded_s2,
    "Step2-世界元素索引(world-element-registry)": registry_loaded_s2,
    # Step 3 引擎（只加载视角引擎，术语约束为编排器预提取的精简摘要）
    "Step3-读者视角(reader-perspective)": reader_loaded,
    "Step3-作者视角(author-perspective)": author_loaded,
    "Step3-人物视角(character-perspective)": character_loaded,
}

failed = [k for k, v in loaded_resources.items() if not v]
if failed:
    print("以下资源加载不完整，Agent产出质量可能受影响：{failed}")
    print("请缩短其他内容或分批处理。")
    return
else:
    print(f"✅ 全部 {len(loaded_resources)} 个资源加载成功")
    # 展示清单给用户确认
```

**引擎加载验证的作用**：Agent 依赖引擎文件中的方法论和约束来产出高质量内容。如果引擎加载失败，Agent 会在缺失关键约束的情况下工作，导致产出质量不可控，后续需要大量返工。如果上下文不足，编排器应提示用户并等待调整，而非静默跳过。

## 审计报告增量加载（Step 0.6 完整逻辑）

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

## 共享约束详细规则

Agent 必须遵守以下七类规则，详见 `shared-constraints.md`：

| 规则集 | 核心内容 | 查阅文件 |
|--------|---------|---------|
| 事件驱动节奏铁律 | 章节=事件单元、非主角暗面标注、时间跳跃合法、场景时间标注、主角戏份保底 | `agents/shared-constraints.md §1` |
| 内容密度规则 | 事件→字数映射、每章事件数、微事件、世界观展开、弹性事件储备 | `agents/shared-constraints.md §2` |
| 伏笔自然设计（冰山理论） | 表面动机、先果后因、场景自检 | `agents/shared-constraints.md §3` |
| 人物互动规则 | 组合多样性、罕见组合、费笔配额 | `agents/shared-constraints.md §4` |
| 巧合计规则 | ≤1次/卷、必须有伏笔支撑 | `agents/shared-constraints.md §5` |
| **🔒术语规范约束** | 文化根脉+字根一致性+势力区分+新术语四步法+已注册元素+层级区分 | `agents/shared-constraints.md §6` |
| 回响规则（Echo） | 大事件余波自然回溯、密度控制（≤2次/卷）、融入世界呼吸、可跨卷 | `agents/shared-constraints.md §7` |

编排器在 Step 0.4 加载 shared-constraints.md，在 Step 1/2 启动 Agent 时作为输入传入。Agent 在 `## 输入` 部分可见"共享约束"条目，**必须逐条遵守**。

## 检查点A显示模板

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

螺旋结构:
  信息矩阵: L1[?] L2[?] L3[?] ✅/❌
  翻新型揭示: {模式} {翻新事件} ✅/❌
  回旋镖: ≥3个 ✅/❌

情节密度:
  并行活跃链: {N}条 (需≥3) ✅/❌
  NPC议程: {已追踪NPC数} ✅/❌
  复杂化: 每章≥1次 ✅/❌

🔒术语自检: 术语有文化根脉 ✅/❌

确认后进入章节设计。输入"OK"或修改意见。
```

## 新实体注册

**新实体类型与保存位置**：

| 新实体类型 | 保存文件 | DB操作 |
|-----------|---------|--------|
| 新地点 | 设定/地图.md | world_upsert(category='location') |
| 新物品 | 设定/物品.md | world_upsert(category='item') |
| 新NPC | 设定/角色总览.md | character_create() |
| 新能力/概念 | 设定/世界观.md | world_upsert(category='ability') |
| 新势力/组织 | 设定/世界观.md | world_upsert(category='faction') |

**注册规范**（参考 world-element-registry.md）：
- 每个新实体必须包含：名称/类型/描述/关联元素/首次出现章节
- 新物品需定义：外观/功能/获取方式/限制条件
- 新地点需定义：位置/环境特征/势力归属/危险等级
- 新NPC需定义：身份/性格/动机/与现有角色的关系

**新实体确认的必要性**：新实体需要经过查重、术语验证和用户确认才能确保世界观一致性。如果 Agent 静默创建，可能导致命名冲突、术语不一致或重复定义，破坏世界观的完整性。所有新实体必须经过用户确认。

## 检查点A2显示模板

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
- 事件弧节奏: 高潮事件多章展开，日常压缩，无按天填充 ✅/❌
- 🔒术语规范: 无禁止术语 ✅/❌
- 🔒螺旋结构: 信息钩子Lv2/Lv3≥60% ✅/❌ | 回旋锚已标注 ✅/❌
- 🔒情节密度: 每章≥2条链推进 ✅/❌ | 每章≥1次复杂化 ✅/❌

输入"OK"进入验证，或提修改意见（可指定某章修改）。
```

## 输出确认流程（Step 4.1 完整逻辑）

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

## DB保存MCP调用（Step 4 完整逻辑）

```python
# 🔒 每个 MCP 调用后必须检查返回值，失败时中止并提示
errors = []

def check_result(op_name, result):
    """检查 MCP 调用结果，失败则记录"""
    if '"ok": false' in result or '"error"' in result:
        errors.append(f"{op_name} 失败: {result}")

# 1. 创建/更新卷级信息（走MCP：新卷用 volume_create，已有卷用 volume_update）
if is_new_volume:
    result = volume_create(novel_name="NOVEL_NAME", number={volume_number}, title="...", main_plotlines=[...], notes="...")
else:
    result = volume_update(novel_name="NOVEL_NAME", number={volume_number}, title="...", main_plotlines=[...], notes="...")
check_result("volume_save", result)

# 2. 规划章节（每章一条）
for chapter in chapters:
    result = chapter_plan(novel_name="NOVEL_NAME", number, title, outline, chapter_type, volume_id)
    check_result(f"chapter_plan Ch{chapter.number}", result)
    # 2a. 同时创建每章的场景大纲（如有结构化场景数据）
    if hasattr(chapter, 'scenes'):
        for scene in chapter.scenes:
            result = scene_create(
                novel_name="NOVEL_NAME", chapter_number=chapter.number,
                scene_number=scene.number, location=scene.location,
                characters_involved=scene.characters,
                conflict=scene.conflict, emotion_type=scene.emotion_type,
                key_beats=scene.key_beats, notes=scene.notes)
            check_result(f"scene_create Ch{chapter.number} S{scene.number}", result)

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

# 7a. 验证暗线/支线创建成功
result = plot_thread_list(novel_name="NOVEL_NAME")
created_threads = json.loads(result)
if len(created_threads) >= len(volume_threads):
    print(f"✅ {len(volume_threads)}个暗线/支线注册确认成功")
else:
    print(f"⚠️ 期望 {len(volume_threads)} 个暗线，实际查询到 {len(created_threads)} 个")
    errors.append("暗线/支线注册未完全成功")

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

## 声音适配规则

🔁 **novel-planner-volume 侧（章节设计师）**：编排器 Read(author-voice-{variant}.md, limit=5) 提取头部摘要①，编译速查表注入 Agent 2。不加载全量 author-voice 引擎。
🔁 **novel-chapter-writer 侧（正文生成）**：正文写作阶段按章内标注的声音层标签，加载对应的全量 author-voice 引擎文件：
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
