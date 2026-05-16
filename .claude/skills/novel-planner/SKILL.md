---
name: novel-planner
description: 全书大纲设计 — 小说骨架+血管。从全局视角确定每卷目标/角色弧线/暗线规划/伏笔基础。不设计具体事件，只确定"每卷做什么"，为下层(novel-planner-volume)提供约束和指导。触发词：规划全书/设计大纲/全书框架/卷级规划
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, Agent, Task, mcp__novel-db__*, mcp__memory__*
lifecycle: core
---

# 全书大纲设计

> **定位**：小说骨架+血管。全局视角 → 每卷"做什么"（目标/角色弧线方向/暗线推进/伏笔基础）。下层 novel-planner-volume 据此设计"具体事件怎么做"。
> **与下层的关系**：骨架→肌肉→皮肤/动作（novel-planner → novel-planner-volume → novel-chapter-writer）

<what-to-do>

## 强制流程

```
Step 0: 断点检测 → 数据采集（世界观/人物/已有卷）+ 加载引擎
  ↓
Step 1: Agent — 框架建筑师 → 全书骨架（起承转合+卷功能定位+卷间关系）         agents/framework-architect.md
  ↓
Step 2: Agent — 脉络设计师 → 主线脉络+暗线递进+人物弧光总图+情绪曲线          agents/vein-designer.md
  ↓  🔒检查点A: 确认全书框架（骨架+脉络）
Step 3: 编排器 — 卷级目标卡 → 基于框架输出每卷目标/角色变化方向/暗线推进度     (编排器直接生成，不改agent)
  ↓
Step 4: Agent — 支线规划师 → 全书支线体系+支线-主线交织图                     agents/subplot-planner.md
  ↓  🔒检查点A2: 确认支线体系
Step 5: Agent — 框架验证器 → 12项全书检查+三视角审查(3Agent并行)               agents/framework-validator.md
  ↓  🔒检查点B: 确认验证通过(P0必须修复)
Step 6: 保存（DB + 文件）+ 跨卷伏笔总图+支线总图
Step 7: 🔒用户确认 → git commit
```

## 编排器职责

只负责：**MCP调用 + 引擎加载 + Agent启动 + 检查点确认 + Step3卷级目标卡生成**。不直接设计框架/脉络/支线。

## Step 0: 数据采集与引擎加载

```python
# 基础数据
novel_get(novel_id)          # 小说基本信息
world_query(novel_id)        # 世界观全部数据
character_list(novel_id)     # 角色列表（含主角/反派/关键配角）
volume_list(novel_id)        # 已有卷信息（如有）
foreshadow_list(novel_id)    # 全局伏笔（如有）

# 引擎加载（按步骤按需加载，编排器在启动对应Agent时传入）
# Step 1/2 需要：
skill_loader("novel-planner", "engine", "causality")        # 因果逻辑大纲法 — Agent 1/2 必须用因果链约束全书
skill_loader("novel-planner", "engine", "three-perspective") # 三视角框架 — Agent 2 用读者视角的爽点节奏标准
# Step 5 需要：
skill_loader("novel-planner", "engine", "reader-perspective-agent")
skill_loader("novel-planner", "engine", "author-perspective-agent")
skill_parser("novel-planner", "engine", "character-perspective-agent")
```

**强制原则**：以上引擎内容编排器在启动Agent时打包传入，Agent**必须使用**。因果逻辑法约束全书因果链，三视角框架约束爽点节奏。

## Step 1: Agent — 框架建筑师

**Agent指令**: `agents/framework-architect.md`
**强制加载引擎**: `engines/causality.md`（因果逻辑法约束卷间关系必须基于因果而非时间顺序）

### 编排器操作
1. 打包：世界观设定 + 主角初始状态 + 预估总卷数 → 传给 Agent
2. 启动 Agent（subagent_type: "general-purpose"），传入数据 + `agents/framework-architect.md`
3. Agent 输出：全书起承转合 + 每卷功能定位 + 卷间关系

### 输出验证
- [ ] 起承转合四段比例合理（起25%/承35%/转25%/合15%）
- [ ] 每卷功能定位唯一、不重复
- [ ] 卷间关系有因果链（因为V{N}的后果→所以V{N+1}面对什么）

## Step 2: Agent — 脉络设计师

**Agent指令**: `agents/vein-designer.md`
**强制加载引擎**:
- `engines/causality.md` — 主线因果链（每节点必须回答"因为什么→所以什么→逼出什么"）
- `engines/three-perspective.md` — 读者视角爽点节奏标准（每2-3卷小爽点/4-5卷大爽点）

### 编排器操作
1. 打包：Agent 1 输出 + 角色档案 + 暗线设定 → 传给 Agent
2. 启动 Agent，传入引擎内容
3. Agent 输出：主线脉络 + 暗线递进 + 人物弧光总图 + 情绪曲线

### 输出验证
- [ ] 主线因果链完整（每步"因为所以"，通过可替换性测试）
- [ ] 暗线每卷至少推进一次，不一次揭完
- [ ] 情绪曲线有起伏，无连续3卷无爽点

## 🔒检查点A: 确认全书框架

编排器展示：

```
【全书框架】
起(V1-V{N}): {功能概述}
承(V{N}-V{N}): {功能概述}
转(V{N}-V{N}): {功能概述}
合(V{N}-V{N}+尾声): {功能概述}

【卷功能定位】
V1: {1句} | V2: {1句} | ... | V{N}: {1句}

【主线脉络】
V1{节点} → V3{节点} → V7{节点} → V11{节点} → V14{结局}

【暗线递进】
V1-V3: {揭示程度} | V4-V7: {揭示程度} | V8-V11: {揭示程度} | V12-V14: 完全揭露

【情绪曲线】
高危区间标注：{哪些卷无小爽点}

输入"OK"进入卷级目标规划，或提修改意见。
```

## Step 3: 编排器 — 卷级目标卡（全书级→卷级的桥梁）

**不调用 Agent**，编排器基于 Step 1-2 的确认输出直接生成。

### 生成逻辑

对每卷，基于 Step 1 的"卷功能定位" + Step 2 的"人物弧光总图"+"暗线递进"生成该卷的约束卡片：

```
V{N}《{卷名}》目标卡
├─ 卷功能：{来自Step 1}
├─ 本卷必须达成的目标（2-3条）：{可衡量的目标}
│  ├─ 角色变化：{哪个角色从什么状态变到什么状态}
│  ├─ 暗线推进：{这条暗线在本卷揭示到什么程度}
│  ├─ 伏笔操作：{新埋/深化的伏笔}
├─ 核心冲突类型：{战斗/探索/对话/揭秘/成长/混合}
├─ 下卷接口：{本卷末留什么钩子给V{N+1}}
```

### 输出验证
- [ ] 每卷目标可衡量（能判断是否达成）
- [ ] 暗线推进度与暗线递进总图一致
- [ ] 角色变化与人物弧光总图一致
- [ ] 目标卡直接提供给 novel-planner-volume 作为输入约束

**目标卡的作用**：这是 novel-planner → novel-planner-volume 的正式输出。volume-planner 收到目标卡后，才知道"这卷要做什么"，然后设计"事件怎么做"。

## Step 4: Agent — 支线规划师

**Agent指令**: `agents/subplot-planner.md`

### 编排器操作
1. 打包：确认后的框架+脉络 + 全部角色档案 + 世界观设定 → 传给 Agent
2. 启动 Agent，传入 `agents/subplot-planner.md`
3. Agent 输出：支线清单 + 支线-主线交织图 + 支线弧光总图 + 支线角色管理

### 输出验证
- [ ] 每条支线通过三检验（删除/独立阅读/主题）
- [ ] 每条连续型支线每卷≥1交织节点
- [ ] 支线不与主线因果链冲突
- [ ] 支线角色出场不突兀

## 🔒检查点A2: 确认支线体系

编排器展示：

```
【支线清单】（共{N}条）
- {支线1}: {类型} | 跨{V1,V3,V5} | 三检验✅
- {支线2}: {类型} | 跨{V2,V4} | 三检验❌ → 建议删除
...

【支线-主线交织】
- {支线1} × 主线 @ V3: {交汇方式} → {结果}
- {支线1} × 主线 @ V5: {交汇方式} → {结果}

【支线角色】
- {支线1}: 核心{角色A} | 新角色需求: {是/否}

输入"OK"进入框架验证，或提修改意见。
```

## Step 5: Agent — 框架验证器（12项全书检查+三视角审查）

**Agent指令**: `agents/framework-validator.md`
**强制加载引擎**: `engines/reader-perspective-agent.md`, `engines/author-perspective-agent.md`, `engines/character-perspective-agent.md`

### 编排器操作
1. 收集：Agent 1-2 框架+脉络 + Step 3 卷级目标卡 + Agent 4 支线体系 → 传给 Agent
2. 编排器在 Agent 5 内部启动 3 个审查 Agent 并行（互不依赖）：
   - **Agent-读者**: 加载 `engines/reader-perspective-agent.md` → 框架级读者审查
   - **Agent-作者**: 加载 `engines/author-perspective-agent.md` → 框架级作者审查  
   - **Agent-人物**: 加载 `engines/character-perspective-agent.md` → 框架级人物审查
3. Agent 5 汇总三视角结果 + 执行交叉检查 → 输出验证报告

### 交叉检查
- [ ] 读者vs作者无冲突（结构服务读者体验）
- [ ] 读者vs人物无冲突（人物选择优先，但有动机）
- [ ] 作者vs人物无冲突（人物逻辑>结构需求）
**核心原则**：人物 > 读者 > 作者

### 问题分级
| 级别 | 判定标准 | 处理要求 |
|------|---------|---------|
| P0 | 因果链断裂/三视角冲突/角色OOC | **必须修复**，阻断保存 |
| P1 | 节奏断层/伏笔遗漏 | 建议修复 |
| P2 | 微调建议 | 可选 |

## 🔒检查点B: 确认验证通过

P0→必须修复（回对应Step）。无P0→进入保存。

## Step 6: 保存

### 文件落盘
```
novels/{小说名}/设定/大纲/
├── 全书框架.md            # Agent 1输出
├── 全书脉络.md            # Agent 2输出  
├── 卷级目标卡.md           # Step 3编排器生成
├── 支线总图.md            # Agent 4输出
├── 跨卷伏笔总图.md         # 编排器汇总
└── 全书框架审计.md         # Agent 5输出
```

落盘后，novel-planner-volume 的 Step 0 读取以上文件作为输入约束。

### DB保存
```python
# 卷级目标 → volume_update
for card in volume_target_cards:
    volume_update(card.volume_id, main_plotlines=card.targets)

# 伏笔 → foreshadow_plant
for f in cross_volume_foreshadows:
    foreshadow_plant(novel_id, description=f.desc, planned_recall_chapter=f.recall)

# 支线 → world_upsert
for s in subplots:
    world_upsert(novel_id, category='subplot', name=s.name, data={...})
```

## Step 7: git commit

```
B1: 全书框架+脉络+卷级目标卡+支线体系+审计通过
```

</what-to-do>

<supporting-info>

## 三层架构

| 层 | Skill | 输出 | 粒度 |
|----|-------|------|------|
| **骨架+血管** | novel-planner（本skill） | 全书框架/脉络/卷级目标卡 | 卷级"做什么" |
| **肌肉** | novel-planner-volume | 逐章大纲+事件因果链+伏笔场景化 | 章级"怎么做" |
| **皮肤/动作** | novel-chapter-writer | 正文（场景+对话+描写） | 场景级"怎么写" |

## 引用资源

| 引擎 | 用途 | 强制步骤 |
|------|------|---------|
| `engines/causality.md` | 因果逻辑大纲法—约束全书因果链 | Step 1/2 |
| `engines/three-perspective.md` | 三视角框架—读者爽点节奏标准 | Step 2 |
| `engines/reader-perspective-agent.md` | 读者视角审查清单 | Step 5 |
| `engines/author-perspective-agent.md` | 作者视角审查清单 | Step 5 |
| `engines/character-perspective-agent.md` | 人物视角审查清单 | Step 5 |

## 异常处理

| 场景 | 处理 |
|------|------|
| agents/目录缺少文件 | 需创建后再启动对应Step |
| Step 0 数据为空（新小说） | 允许，基于默认模板构建 |
| Step 5 发现P0 | 回到对应Step修复，修复后重跑验证 |

</supporting-info>
