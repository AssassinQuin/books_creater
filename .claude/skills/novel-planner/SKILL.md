---
name: novel-planner
description: 全书大纲设计 — 小说骨架+血管。从全局视角确定每卷目标/角色弧线/暗线规划/伏笔基础。不设计具体事件，只确定"每卷做什么"。输出可被 novel-planner-volume 读取作为卷级设计输入。触发词：规划全书/设计大纲/全书框架/卷级规划
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, Agent, Task, mcp__novel-db__*, mcp__memory__*
lifecycle: core
depends_on: novel-setup, lorecraft, engines/causality, engines/three-perspective
version: "1.2.0"
---

# 全书大纲设计

> **定位**：小说骨架+血管。全局视角 → 每卷"做什么"（目标/角色弧线方向/暗线推进/伏笔基础）。不设计具体事件。
> **与 novel-planner-volume 的关系**：本 skill 输出的卷级目标卡可被 novel-planner-volume 读取作为输入约束。两者是独立 skill，各自有完整流程，输出通过文件共享。

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
novel_get(novel_name=NOVEL_NAME)          # 小说基本信息
world_query(novel_name=NOVEL_NAME)        # 世界观全部数据
character_list(novel_name=NOVEL_NAME)     # 角色列表（含主角/反派/关键配角）
volume_list(novel_name=NOVEL_NAME)        # 已有卷信息（如有）
foreshadow_list(novel_name=NOVEL_NAME)    # 全局伏笔（如有）
```

**🔒 上下文预算管理**：编排器在加载前**必须**执行 token 预算估算，超限时启用分层加载策略。详见 supporting-info §Token预算估算。

**引擎加载**：Step 1/2 加载 causality + three-perspective；Step 5 加载三个 perspective-agent。🔒 术语规范（lorecraft全套 + world-element-registry）全程强制加载。编排器打包传给所有Agent。详见 supporting-info §引擎加载执行。

**🔒 引擎加载验证**：编排器完成所有 skill_loader/Read 后，**必须**在启动任何 Agent 之前验证全部引擎加载成功，失败则阻断。详见 supporting-info §引擎加载验证。

**强制原则**：以上引擎内容编排器在启动Agent时打包传入，Agent**必须使用**。因果逻辑法约束全书因果链，三视角框架约束爽点节奏，**术语规范约束全书产出的世界观用词**。

## Step 1: Agent — 框架建筑师

**Agent指令**: `agents/framework-architect.md`
**强制加载引擎**: `engines/causality.md`（因果逻辑法约束卷间关系必须基于因果而非时间顺序）
**强制加载规范**: `lorecraft/SKILL.md` + `lorecraft/references/term-map.md` + `lorecraft/references/quickref.md` + `engines/world-element-registry.md`（术语规范约束卷级定位和骨架描述中的世界观用词）

编排器操作与输出验证详见 supporting-info §Step1框架建筑师。

## Step 2: Agent — 脉络设计师

**Agent指令**: `agents/vein-designer.md`
**强制加载引擎**:
- `engines/causality.md` — 主线因果链（每节点必须回答"因为什么→所以什么→逼出什么"）
- `engines/three-perspective.md` — 读者视角爽点节奏标准（每2-3卷小爽点/4-5卷大爽点）
**强制加载规范**: `lorecraft/SKILL.md` + `lorecraft/references/term-map.md` + `lorecraft/references/quickref.md` + `engines/world-element-registry.md`（术语规范约束暗线描述、人物弧光、情绪曲线中的世界观用词）

编排器操作与输出验证详见 supporting-info §Step2脉络设计师。

## 🔒检查点A: 确认全书框架（骨架+脉络）

编排器展示全书框架+卷功能定位+主线脉络+暗线递进+情绪曲线摘要，用户确认"OK"后进入Step 3。展示模板详见 supporting-info §检查点A展示模板。

## Step 3: 编排器 — 卷级目标卡（全书级→卷级的桥梁）

**不调用 Agent**，编排器基于 Step 1-2 的确认输出直接生成。

对每卷，基于 Step 1 的"卷功能定位" + Step 2 的"人物弧光总图"+"暗线递进"生成约束卡片（卷功能/必须目标/角色变化/暗线推进/伏笔操作/冲突类型/下卷接口）。目标卡直接提供给 novel-planner-volume 作为输入约束。输出验证详见 supporting-info §Step3卷级目标卡。

## Step 4: Agent — 支线规划师

**Agent指令**: `agents/subplot-planner.md`
**强制加载规范**: `lorecraft/SKILL.md` + `lorecraft/references/term-map.md` + `lorecraft/references/quickref.md` + `engines/world-element-registry.md`（术语规范约束支线中涉及的势力/地点/能力/世界观元素用词）

编排器操作与输出验证详见 supporting-info §Step4支线规划师。

## 🔒检查点A2: 确认支线体系

编排器展示支线清单+支线-主线交织图+支线角色，用户确认"OK"后进入Step 5。展示模板详见 supporting-info §检查点A2展示模板。

## Step 5: Agent — 框架验证器（13项全书检查+三视角审查）

**Agent指令**: `agents/framework-validator.md`
**强制加载引擎**: `engines/reader-perspective-agent.md`, `engines/author-perspective-agent.md`, `engines/character-perspective-agent.md`
**强制加载规范**: `lorecraft/SKILL.md` + `lorecraft/references/term-map.md`（术语规范作为第13项检查标准）

编排器内部启动3个审查Agent并行（读者/作者/人物），汇总三视角结果+交叉检查+术语规范扫描。核心原则：人物 > 读者 > 作者。编排器操作、交叉检查、问题分级详见 supporting-info §Step5框架验证器。

## 🔒检查点B: 确认验证通过

P0→必须修复（回对应Step）。无P0→进入保存。P0修复循环退出机制：最多3轮，超出升级为用户决策（①接受/②回退/③手动修复）。详见 supporting-info §P0修复循环详解。

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

### DB保存（含结果校验——失败即中止）

详见 supporting-info §DB保存。

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
| `lorecraft/SKILL.md` | 文化根脉术语命名引擎—禁用术语+命名方法 | Step 1-5（全程） |
| `lorecraft/references/term-map.md` | 现代→灵能术语映射表（~60+条） | Step 1-5（全程） |
| `lorecraft/references/quickref.md` | 术语速查卡（七势力字根+命名法） | Step 1-5（全程） |
| `engines/world-element-registry.md` | 世界观元素注册机制—已注册元素索引 | Step 1-5（全程） |

## 异常处理

| 场景 | 处理 |
|------|------|
| agents/目录缺少文件 | 需创建后再启动对应Step |
| Step 0 数据为空（新小说） | **阻断**，必须先完成 novel-setup（世界观≥3维度+角色≥2个）后才能进入全书大纲设计 |
| Step 0 世界观<3维度或角色<2个 | **阻断**，提示用户补充世界观/角色后再进入 |
| Step 5 发现P0 | 回到对应Step修复，修复后重跑验证（最多3轮，超出则升级为用户决策） |

## Token预算估算

```python
# Token 预算估算（粗略：引擎文件 ~2000 tokens/个，lorecraft 文件 ~1500 tokens/个）
TOKEN_BUDGET_LIMIT = 80000  # 留余量给 Agent 产出 + 对话

estimated_tokens = (
    # 结构引擎（Step 1/2 + Step 5）
    5 * 2000 +  # causality + three-perspective + 3个perspective-agent
    # 术语规范（全程强制）
    4 * 1500 +  # lorecraft SKILL + term-map + quickref + world-element-registry
    # 基础数据（MCP 返回）
    5 * 1000    # novel_get + world_query + character_list + volume_list + foreshadow_list
)
# estimated_tokens ≈ 23000（正常情况不会超限）
# 但如果 novel 数据量极大（多卷+多角色+丰富世界观），需重新评估

if estimated_tokens > TOKEN_BUDGET_LIMIT:
    # 分层加载策略：
    # Tier 1（始终加载，核心约束）：
    #   lorecraft term-map + quickref + world-element-registry
    # Tier 2（按步骤加载）：
    #   Step 1/2 → causality + three-perspective
    #   Step 5 → reader-perspective + author-perspective + character-perspective
    # Tier 3（按需加载）：
    #   lorecraft SKILL.md 全文（如上下文紧张，只加载前20行：原则+关键约束）
    #   剩余引擎在对应 Step 启动时通过 skill_loader 按需加载
    print("⚠️ 上下文预算紧张，启用分层加载策略")
    apply_tiered_loading = True
else:
    apply_tiered_loading = False
```

> **引擎精简版机制**：如果上下文仍然紧张，Agent 可只加载引擎的前 20 行（原则+关键约束），跳过示例和详细说明。这不会显著影响约束效果，因为核心规则集中在文件开头。

## 引擎加载执行

```python
# 引擎加载（按步骤按需加载，编排器在启动对应Agent时通过 skill_loader 传入）
# Step 1/2 需要：
skill_loader("novel-planner", "engine", "causality")
skill_loader("novel-planner", "engine", "three-perspective")
# Step 5 需要：
skill_loader("novel-planner", "engine", "reader-perspective-agent")
skill_loader("novel-planner", "engine", "author-perspective-agent")
skill_loader("novel-planner", "engine", "character-perspective-agent")

# 🔒 术语规范（全程强制加载——所有Agent生成前必读、生成后必检）：
# 以下三项在Step 0一次性加载，编排器打包传给所有Agent
Read(".claude/skills/lorecraft/SKILL.md")                          # 文化根脉命名引擎（禁用术语+四步法+层积命名法）
Read(".claude/skills/lorecraft/references/term-map.md")            # 现代→灵能术语映射表（~60+条）
Read(".claude/skills/lorecraft/references/quickref.md")             # 速查卡（七势力字根+五步命名法+多样性检查）
Read(".claude/skills/engines/world-element-registry.md")           # 世界观元素注册机制（已注册元素索引）
```

## 引擎加载验证

```python
# 编排器在 Step 0 最后执行：
loaded_engines = {
    # 结构引擎
    "Step1-因果链(causality)": causality_loaded,
    "Step2-三视角(three-perspective)": three_perspective_loaded,
    "Step5-读者视角(reader-perspective)": reader_loaded,
    "Step5-作者视角(author-perspective)": author_loaded,
    "Step5-人物视角(character-perspective)": character_loaded,
    # 🔒 术语规范（全程强制——不可跳过）
    "术语规范(lorecraft)": lorecraft_loaded,
    "术语映射(term-map)": term_map_loaded,
    "术语速查(quickref)": quickref_loaded,
    "世界元素注册表(world-element-registry)": world_element_registry_loaded,
}

failed = [k for k, v in loaded_engines.items() if not v]
if failed:
    print(f"⚠️ 以下引擎/规范加载失败（可能被上下文截断）：{failed}")
    print("加载失败的引擎不可跳过。请缩短其他内容或分批处理。")
    # 阻断：不允许启动 Agent
    return
else:
    print(f"✅ 全部 {len(loaded_engines)} 个引擎/规范加载成功")
    # 展示清单给用户确认
```

**为什么不应该在引擎加载失败后启动 Agent**：引擎是后续所有步骤的约束条件，缺失引擎意味着 Agent 将在无约束状态下运行，产出可能违反因果逻辑、术语规范或三视角标准。修复成本远高于重新加载。如果上下文不足，编排器应提示用户并等待调整，而非静默跳过。

## Step1框架建筑师

### 编排器操作
1. 打包：世界观设定 + 主角初始状态 + 预估总卷数 + **术语规范全套** → 传给 Agent
2. 启动 Agent（subagent_type: "general-purpose"），传入数据 + `agents/framework-architect.md`
3. Agent 输出：全书起承转合 + 每卷功能定位 + 卷间关系

### 输出验证
- [ ] 起承转合四段比例合理（起20%-30%/承30%-40%/转20%-30%/合10%-20%，总和100%）
- [ ] 每卷功能定位唯一、不重复
- [ ] 卷间关系有因果链（因为V{N}的后果→所以V{N+1}面对什么）
- [ ] 🔒 术语规范：产出中无禁用术语（数据/系统/信号/参数/权限/终端/频率等），全部使用 term-map 映射的灵能术语
- [ ] 🔒 术语规范：新增世界观术语遵循文化根脉四步法，有文化出处

## Step2脉络设计师

### 编排器操作
1. 打包：Agent 1 输出 + 角色档案 + 暗线设定 + **术语规范全套** → 传给 Agent
2. 启动 Agent，传入引擎内容
3. Agent 输出：主线脉络 + 暗线递进 + 人物弧光总图 + 情绪曲线

### 输出验证
- [ ] 主线因果链完整（每步"因为所以"，通过可替换性测试）
- [ ] 暗线每卷至少推进一次，不一次揭完
- [ ] 情绪曲线有起伏，无连续3卷无爽点
- [ ] 🔒 术语规范：产出中无禁用术语，暗线/势力/能力相关描述使用灵能术语
- [ ] 🔒 术语规范：人物弧光描述中的世界观元素（能力/势力/地点）用词与 term-map 一致

## 检查点A展示模板

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

## Step3卷级目标卡

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

## Step4支线规划师

### 编排器操作
1. 打包：确认后的框架+脉络 + 全部角色档案 + 世界观设定 + **术语规范全套** → 传给 Agent
2. 启动 Agent，传入 `agents/subplot-planner.md`
3. Agent 输出：支线清单 + 支线-主线交织图 + 支线弧光总图 + 支线角色管理

### 输出验证
- [ ] 每条支线通过三检验（删除/独立阅读/主题）
- [ ] 每条连续型支线每卷≥1交织节点
- [ ] 支线不与主线因果链冲突
- [ ] 支线角色出场不突兀
- [ ] 🔒 术语规范：支线描述中的势力/地点/世界观元素用词与 term-map 一致
- [ ] 🔒 术语规范：新引入的世界观元素遵循文化根脉四步法，需同步注册到 world-element-registry

## 检查点A2展示模板

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

## Step5框架验证器

### 编排器操作
1. 收集：Agent 1-2 框架+脉络 + Step 3 卷级目标卡 + Agent 4 支线体系 + **术语规范** → 传给 Agent
2. 编排器在 Agent 5 内部启动 3 个审查 Agent 并行（互不依赖）：
   - **Agent-读者**: 加载 `engines/reader-perspective-agent.md` → 框架级读者审查
   - **Agent-作者**: 加载 `engines/author-perspective-agent.md` → 框架级作者审查
   - **Agent-人物**: 加载 `engines/character-perspective-agent.md` → 框架级人物审查
3. Agent 5 汇总三视角结果 + 执行交叉检查 + **术语规范扫描** → 输出验证报告

### 交叉检查
- [ ] 读者vs作者无冲突（结构服务读者体验）
- [ ] 读者vs人物无冲突（人物选择优先，但有动机）
- [ ] 作者vs人物无冲突（人物逻辑>结构需求）
**核心原则**：人物 > 读者 > 作者

### 问题分级
| 级别 | 判定标准 | 处理要求 |
|------|---------|---------|
| P0 | 因果链断裂/三视角冲突/角色OOC | **必须修复**，阻断保存 |
| P1 | 节奏断层/伏笔遗漏 | **必须修复**——本轮验证结束前完成修复，不允许留到下一轮 |
| P2 | 微调建议 | **必须修复**——下一轮迭代（下次触发本skill）开始前完成 |

## DB保存

```python
# 🔒 每个 MCP 调用后必须检查返回值，失败时中止并提示
errors = []

# 卷级目标 → volume_update
for card in volume_target_cards:
    result = volume_update_by_number(novel_name=NOVEL_NAME, number=card.volume_id, main_plotlines=card.targets)
    if '"ok": false' in result or '"error"' in result:
        errors.append(f"volume_update V{card.volume_id} 失败: {result}")

# 伏笔 → foreshadow_plant
for f in cross_volume_foreshadows:
    result = foreshadow_plant(novel_name=NOVEL_NAME, description=f.desc, planned_recall_chapter=f.recall)
    if '"ok": false' in result or '"error"' in result:
        errors.append(f"foreshadow_plant 失败: {result}")

# 支线 → world_upsert
for s in subplots:
    result = world_upsert(novel_name=NOVEL_NAME, category='subplot', name=s.name, data={...})
    if '"ok": false' in result or '"error"' in result:
        errors.append(f"world_upsert 支线失败: {result}")

# 🔒 结果校验
if errors:
    print(f"⚠️ DB保存失败（{len(errors)}个错误）：")
    for e in errors:
        print(f"  - {e}")
    print("文件已写入但DB未完全同步。请检查后重试。")
    # 中止流程，不执行 git commit
    return
else:
    print(f"✅ 全部 DB 操作成功")
```

## P0修复循环详解

```python
MAX_FIX_ROUNDS = 3
fix_rounds = 0

while p0_issues_exist:
    fix_rounds += 1
    if fix_rounds > MAX_FIX_ROUNDS:
        # 升级为用户决策：①接受 ②回退 ③手动修复
        user_choice = await user_input()
        if user_choice == "①": break  # 标记已知风险
        elif user_choice == "②": rollback_to_pre_fix_state(); return
        elif user_choice == "③": return  # 暂停等待手动修复
    fix_p0_issues(p0_issues)
    validation_result = run_step5_validation()
    p0_issues = validation_result.p0_issues
```

</supporting-info>
