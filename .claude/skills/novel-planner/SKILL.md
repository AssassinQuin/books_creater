---
name: novel-planner
description: 全书大纲设计 — 小说骨架+血管。从全局视角确定每卷目标/角色弧线/暗线规划/伏笔基础。不设计具体事件，只确定"每卷做什么"。输出可被 novel-planner-volume 读取作为卷级设计输入。触发词：规划全书/设计大纲/全书框架/卷级规划
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, Agent, Task, mcp__novel-db__*, mcp__memory__*
lifecycle: core
depends_on: novel-setup, lorecraft, engines/causality, engines/three-perspective
version: "1.5.0"
---

# 全书大纲设计

> **定位**：小说骨架+血管。全局视角 → 每卷"做什么"（目标/角色弧线方向/暗线推进/伏笔基础）。不设计具体事件。
> **与 novel-planner-volume 的关系**：本 skill 输出的卷级目标卡可被 novel-planner-volume 读取作为输入约束。两者是独立 skill，各自有完整流程，输出通过文件共享。

<what-to-do>

## 强制流程

```
Step 0: 断点检测 → 数据采集（世界观/人物/已有卷）+ 加载引擎
  ↓  ✅ 进度写入 .claude/temp/novel-planner-progress.json
Step 1: Agent — 框架建筑师 → 全书骨架 → 立即写入 全书框架.md
  ↓  ✅ 进度更新
Step 2: Agent — 脉络设计师 → 主线脉络+暗线+弧光 → 立即写入 全书脉络.md
  ↓  ✅ 进度更新
  ↓  🔒检查点A: 确认全书框架（骨架+脉络）
Step 3: Agent — 卷级目标卡生成器 → 15卷目标卡 → 立即写入 卷级目标卡.md
  ↓  ✅ 进度更新
Step 4: Agent — 支线规划师 → 全书支线体系 → 立即写入 支线总图.md
  ↓  ✅ 进度更新
  ↓  🔒检查点A2: 确认支线体系
Step 5: Agent — 框架验证器(3Agent并行) → 审计报告 → 立即写入 全书框架审计.md
  ↓  🔒检查点B: 确认验证通过(P0必须修复)
Step 6: 保存（DB + 跨卷伏笔总图 + 新角色入库）+ sync_db_to_files → git commit
```

### 🔒 即时落盘原则

**每个 Agent/Step 完成后必须立即将输出写入文件**。不等到 Step 6 统一落盘。原因：
1. 防止 context 窗口断裂丢失全部产出
2. 续接时从文件恢复，无需重跑已完成的 Step
3. 减少主 context 中累积的中间内容

### 断点续传

```python
# 进度文件: .claude/temp/novel-planner-progress.json
{
    "novel_name": NOVEL_NAME,
    "current_step": 3,           # 下一步要执行的Step
    "completed_steps": [0,1,2],  # 已完成的Step
    "output_files": {
        "step1": "novels/{小说名}/设定/大纲/全书框架.md",
        "step2": "novels/{小说名}/设定/大纲/全书脉络.md"
    },
    "timestamp": "2026-05-19T..."
}
```

**续接逻辑**：Step 0 先检查进度文件。如果 `current_step > 0`，从对应文件读取已有产出，跳过已完成的 Step，直接进入 `current_step`。

## 编排器职责

只负责：**MCP调用 + 引擎加载 + Agent启动 + 检查点确认 + 进度管理**。不直接设计框架/脉络/支线、不直接生成目标卡。

## Step 0: 数据采集与引擎加载

```python
# ─── 基础数据（MCP查询，不读文件）───
novel_get(novel_name=NOVEL_NAME)          # 小说基本信息
world_query(novel_name=NOVEL_NAME)        # 世界观全部数据
character_list(novel_name=NOVEL_NAME)     # 角色列表（含主角/反派/关键配角）
foreshadow_list(novel_name=NOVEL_NAME)    # 全局伏笔（如有）

# ─── 已有卷信息（通过 volume_get 获取结构化摘要）───
# ✅ volume_get 每卷 notes 字段 = 结构化摘要（~5K tokens）
#    对比：读卷大纲原文 = 平均40K/卷 × 15卷 ≈ 600K/150K tokens（volume_get 省 97%）
volume_list(novel_name=NOVEL_NAME)        # 卷列表（获取卷号和标题）
for v in volumes:
    volume_get(novel_name=NOVEL_NAME, number=v.number)  # 每卷notes（含目标/角色变化/暗线）
```

**🔒 卷级信息用 volume_get 获取**：卷大纲原文（V01-V15 .md 文件）是 novel-planner-volume 的产物，平均 40K/卷。novel-planner 需要的是"这卷定位是什么"的结构化摘要，`volume_get` 返回的 `notes` 字段已包含。当 notes 为空时，回退读文件。

**🔒 上下文预算管理**：编排器在加载前**必须**执行 token 预算估算，超限时启用分层加载策略。详见 supporting-info §Token预算估算。

**引擎加载**：Step 1/2 加载 causality + three-perspective；Step 5 加载三个 perspective-agent。🔒 术语规范（lorecraft全套 + world-element-registry）全程强制加载。编排器打包传给所有Agent。详见 supporting-info §引擎加载执行。

**🔒 引擎加载验证**：编排器完成所有 skill_loader/Read 后，**必须**在启动任何 Agent 之前验证全部引擎加载成功，失败则阻断。详见 supporting-info §引擎加载验证。

**强制原则**：以上引擎内容编排器在启动Agent时打包传入，Agent**必须使用**。因果逻辑法约束全书因果链，三视角框架约束爽点节奏，**术语规范约束全书产出的世界观用词**。

## Step 1: Agent — 框架建筑师

**Agent指令**: `agents/framework-architect.md`
**强制加载引擎**: `engines/causality.md`（因果逻辑法约束卷间关系必须基于因果而非时间顺序）
**强制加载规范**: `lorecraft/references/core-principles.md` + `lorecraft/references/term-map.md` + `lorecraft/references/quickref.md` + `engines/world-element-registry.md`（术语规范约束卷级定位和骨架描述中的世界观用词）

编排器操作：
1. 打包：世界观设定 + 主角初始状态 + 预估总卷数 + 已有卷notes + **术语规范全套** → 传给 Agent
2. 启动 Agent（subagent_type: "general-purpose"），传入数据 + `agents/framework-architect.md`
3. **立即落盘**：Agent 输出 → 写入 `novels/{小说名}/设定/大纲/全书框架.md` + 更新进度文件

输出验证详见 supporting-info §Step1框架建筑师。

## Step 2: Agent — 脉络设计师

**Agent指令**: `agents/vein-designer.md`
**强制加载引擎**:
- `engines/causality.md` — 主线因果链（每节点必须回答"因为什么→所以什么→逼出什么"）
- `engines/three-perspective.md` — 读者视角爽点节奏标准（每2-3卷小爽点/4-5卷大爽点）
**强制加载规范**: `lorecraft/references/core-principles.md` + `lorecraft/references/term-map.md` + `lorecraft/references/quickref.md` + `engines/world-element-registry.md`（术语规范约束暗线描述、人物弧光、情绪曲线中的世界观用词）

编排器操作：
1. 从文件读取 Step 1 输出（不依赖 context 中的残留）+ 角色档案 + 暗线设定 + **术语规范全套** → 传给 Agent
2. 启动 Agent
3. **立即落盘**：Agent 输出 → 写入 `novels/{小说名}/设定/大纲/全书脉络.md` + 更新进度文件

输出验证详见 supporting-info §Step2脉络设计师。

## 🔒检查点A: 确认全书框架（骨架+脉络）

编排器展示全书框架+卷功能定位+主线脉络+暗线递进+情绪曲线摘要，用户确认"OK"后进入Step 3。展示模板详见 supporting-info §检查点A展示模板。

## Step 3: Agent — 卷级目标卡生成器（全书级→卷级的桥梁）

**Agent指令**: `agents/target-card-generator.md`
**输入**: 从文件读取全书框架 + 全书脉络 + 已有卷notes + 术语规范

编排器操作：
1. 从文件读取 Step 1-2 的确认输出 + 已有卷notes + **术语规范** → 传给 Agent
2. 启动 Agent（subagent_type: "general-purpose"）
3. **立即落盘**：Agent 输出 → 写入 `novels/{小说名}/设定/大纲/卷级目标卡.md` + 更新进度文件

输出验证详见 supporting-info §Step3卷级目标卡。

## Step 4: Agent — 支线规划师

**Agent指令**: `agents/subplot-planner.md`
**强制加载规范**: `lorecraft/references/core-principles.md` + `lorecraft/references/term-map.md` + `lorecraft/references/quickref.md` + `engines/world-element-registry.md`（术语规范约束支线中涉及的势力/地点/能力/世界观元素用词）

编排器操作：
1. 从文件读取确认后的框架+脉络+目标卡 + 全部角色档案 + 世界观设定 + **术语规范全套** → 传给 Agent
2. 启动 Agent
3. **立即落盘**：Agent 输出 → 写入 `novels/{小说名}/设定/大纲/支线总图.md` + 更新进度文件

输出验证详见 supporting-info §Step4支线规划师。

## 🔒检查点A2: 确认支线体系

编排器展示支线清单+支线-主线交织图+支线角色，用户确认"OK"后进入Step 5。展示模板详见 supporting-info §检查点A2展示模板。

## Step 5: Agent — 框架验证器（13项全书检查+三视角审查）

**Agent指令**: `agents/framework-validator.md`
**强制加载引擎**: `engines/reader-perspective-agent.md`, `engines/author-perspective-agent.md`, `engines/character-perspective-agent.md`
**强制加载规范**: `lorecraft/references/core-principles.md` + `lorecraft/references/term-map.md`（术语规范作为第13项检查标准）

编排器操作：
1. 从文件读取框架+脉络+目标卡+支线体系 + **术语规范** → 传给 Agent
2. 启动3个审查Agent并行（读者/作者/人物），各自独立审查
3. 汇总三视角结果+交叉检查+术语规范扫描 → 输出验证报告
4. **立即落盘**：验证报告 → 写入 `novels/{小说名}/设定/大纲/全书框架审计.md` + 更新进度文件

核心原则：人物 > 读者 > 作者。交叉检查、问题分级详见 supporting-info §Step5框架验证器。

## 🔒检查点B: 确认验证通过

P0→必须修复（回对应Step）。无P0→进入保存。P0修复循环退出机制：最多3轮，超出升级为用户决策（①接受/②回退/③手动修复）。详见 supporting-info §P0修复循环详解。

## Step 6: 保存（DB + 文件 + 新角色入库 + git commit）

### 6A: 跨卷伏笔总图（编排器直接生成）

从卷级目标卡的伏笔操作段落提取+汇总跨卷伏笔总图，写入 `跨卷伏笔总图.md`。

### 6B: 新角色入库

从支线总图的"支线角色管理"表中提取标注为"新角色需求: 是"的角色，逐个调用 `character_create` 写入 DB：

```python
# 新角色入库（支线总图中标注的新NPC）
for npc in subplot_new_characters:
    result = character_create(
        novel_name=NOVEL_NAME,
        name=npc.name,
        role="npc",
        background=npc.function,
        first_appearance_chapter=npc.appearance_volume  # 第一个出场卷
    )
    if '"ok": false' in result or '"error"' in result:
        errors.append(f"character_create {npc.name} 失败: {result}")
```

### 6C: DB保存（含结果校验——失败即中止）

详见 supporting-info §DB保存。

### 6D: sync_db_to_files + git commit

```python
sync_db_to_files(novel_name=NOVEL_NAME)
# git commit
# B1: 全书框架+脉络+卷级目标卡+支线体系+审计通过
```

### 文件清单（全部已在对应Step即时落盘，此处只补伏笔总图）
```
novels/{小说名}/设定/大纲/
├── 全书框架.md            # Step 1 Agent 输出（即时落盘）
├── 全书脉络.md            # Step 2 Agent 输出（即时落盘）
├── 卷级目标卡.md           # Step 3 Agent 输出（即时落盘）
├── 支线总图.md            # Step 4 Agent 输出（即时落盘）
├── 全书框架审计.md         # Step 5 Agent 输出（即时落盘）
└── 跨卷伏笔总图.md         # Step 6A 编排器汇总（此处生成）
```

落盘后，novel-planner-volume 的 Step 0 读取以上文件作为输入约束。

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
| `lorecraft/references/core-principles.md` | 文化根脉术语生成指南—核心原则+四步法+生成方向 | Step 1-5（全程，替代全量SKILL.md） |
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
| context窗口断裂 | 续接时检查 `.claude/temp/novel-planner-progress.json`，从 `current_step` 恢复，已有文件从磁盘读取 |
| 用户指令范围不明确 | **必须主动确认**：全量重做还是增量校准？确认后再进入流程 |
| 已有卷大纲与新框架不一致 | **必须主动提出异议**：展示不一致点，等用户决定覆盖/保留/合并 |

## 进度文件格式

```json
// .claude/temp/novel-planner-progress.json
{
    "novel_name": "这次不一样了",
    "skill": "novel-planner",
    "current_step": 4,
    "completed_steps": [0, 1, 2, 3],
    "output_files": {
        "step1": "novels/这次不一样了/设定/大纲/全书框架.md",
        "step2": "novels/这次不一样了/设定/大纲/全书脉络.md",
        "step3": "novels/这次不一样了/设定/大纲/卷级目标卡.md"
    },
    "checkpoints_passed": ["A"],
    "timestamp": "2026-05-19T..."
}
```

## Token预算估算

```python
# Token 预算估算（v1.5 优化后）
TOKEN_BUDGET_LIMIT = 80000  # 留余量给 Agent 产出 + 对话

estimated_tokens = (
    # 结构引擎（Step 1/2 + Step 5，按步骤按需加载）
    5 * 2000 +  # causality + three-perspective + 3个perspective-agent
    # 术语规范（全程强制）
    4 * 1500 +  # lorecraft core-principles + term-map + quickref + world-element-registry
    # 基础数据（MCP 返回）
    5 * 1000 +  # novel_get + world_query + character_list + foreshadow_list
    # 已有卷信息（volume_get 获取notes，不读大纲文件）
    15 * 200    # 15卷 × 每卷notes约200 tokens（vs 读大纲文件每卷~10K tokens）
)
# estimated_tokens ≈ 24000（正常情况不会超限）
# v1.4 时: 读15卷大纲 ~150K tokens → v1.5: volume_get notes ~3K tokens
# 节省约 ~120K tokens (30%)

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
Read(".claude/skills/lorecraft/references/core-principles.md")     # 文化根脉术语生成指南（核心原则+四步法+生成方向）— 替代全量SKILL.md节省上下文
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
    # 术语规范（全程——确保所有Agent产出术语一致）
    "术语核心原则(lorecraft-core)": lorecraft_loaded,
    "术语映射(term-map)": term_map_loaded,
    "术语速查(quickref)": quickref_loaded,
    "世界元素注册表(world-element-registry)": world_element_registry_loaded,
}

failed = [k for k, v in loaded_engines.items() if not v]
if failed:
    print("以下资源加载不完整，Agent产出质量可能受影响：{failed}")
    print("请缩短其他内容或分批处理。")
    return
else:
    print(f"✅ 全部 {len(loaded_engines)} 个引擎/规范加载成功")
    # 展示清单给用户确认
```

**引擎加载验证的作用**：引擎是后续所有步骤的约束条件，缺失引擎意味着 Agent 将在无约束状态下运行，产出可能违反因果逻辑、术语规范或三视角标准。修复成本远高于重新加载。如果上下文不足，编排器应提示用户并等待调整，而非静默跳过。

## Step1框架建筑师

### 编排器操作
1. 打包：世界观设定 + 主角初始状态 + 预估总卷数 + 已有卷notes + **术语规范全套** → 传给 Agent
2. 启动 Agent（subagent_type: "general-purpose"），传入数据 + `agents/framework-architect.md`
3. Agent 输出：全书起承转合 + 每卷功能定位 + 卷间关系
4. **立即写入文件** `全书框架.md` + 更新进度文件

### 输出验证
- [ ] 起承转合四段比例合理（起20%-30%/承30%-40%/转20%-30%/合10%-20%，总和100%）
- [ ] 每卷功能定位唯一、不重复
- [ ] 卷间关系有因果链（因为V{N}的后果→所以V{N+1}面对什么）
- [ ] 🔒 术语规范：产出中无禁用术语（数据/系统/信号/参数/权限/终端/频率等），全部使用 term-map 映射的灵能术语
- [ ] 🔒 术语规范：新增世界观术语遵循文化根脉四步法，有文化出处

## Step2脉络设计师

### 编排器操作
1. 从文件读取 Step 1 输出（不依赖 context） + 角色档案 + 暗线设定 + **术语规范全套** → 传给 Agent
2. 启动 Agent，传入引擎内容
3. Agent 输出：主线脉络 + 暗线递进 + 人物弧光总图 + 情绪曲线
4. **立即写入文件** `全书脉络.md` + 更新进度文件

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

### 编排器操作
1. 从文件读取 Step 1 全书框架 + Step 2 全书脉络 + 已有卷notes + **术语规范** → 传给 Agent
2. 启动 Agent（subagent_type: "general-purpose"），传入 `agents/target-card-generator.md`
3. Agent 输出：15卷目标卡 + 一致性校验结果
4. **立即写入文件** `卷级目标卡.md` + 更新进度文件

### 目标卡格式

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
1. 从文件读取确认后的框架+脉络+目标卡 + 全部角色档案 + 世界观设定 + **术语规范全套** → 传给 Agent
2. 启动 Agent，传入 `agents/subplot-planner.md`
3. Agent 输出：支线清单 + 支线-主线交织图 + 支线弧光总图 + 支线角色管理
4. **立即写入文件** `支线总图.md` + 更新进度文件

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

# 1. 卷级目标 → volume_update
for card in volume_target_cards:
    result = volume_update(novel_name=NOVEL_NAME, number=card.volume_id, notes=card.notes)
    if '"ok": false' in result or '"error"' in result:
        errors.append(f"volume_update V{card.volume_id} 失败: {result}")

# 2. 新角色入库（从支线总图提取）
for npc in subplot_new_characters:
    result = character_create(
        novel_name=NOVEL_NAME, name=npc.name, role="npc",
        background=npc.function, first_appearance_chapter=npc.appearance_volume
    )
    if '"ok": false' in result or '"error"' in result:
        errors.append(f"character_create {npc.name} 失败: {result}")

# 3. 伏笔 → foreshadow_plant
for f in cross_volume_foreshadows:
    result = foreshadow_plant(novel_name=NOVEL_NAME, description=f.desc, planned_recall_chapter=f.recall)
    if '"ok": false' in result or '"error"' in result:
        errors.append(f"foreshadow_plant 失败: {result}")

# 4. 支线 → world_upsert
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
