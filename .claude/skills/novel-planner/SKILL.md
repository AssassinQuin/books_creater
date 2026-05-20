---
name: novel-planner
description: 全书大纲设计 — 小说骨架+血管。触发词：规划全书/设计大纲/全书框架/卷级规划
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, Agent, Task, mcp__novel-db__*, mcp__memory__*
depends_on: novel-setup, lorecraft, shared/engine-loading-protocol, shared/db-save-protocol, shared/checkpoint-protocol, shared/three-perspective-protocol
lifecycle: core
version: "2.0.0"
---

# 全书大纲设计

> 小说骨架+血管。全局视角 → 每卷"做什么"。不设计具体事件。
> 输出可被 novel-planner-volume 读取作为卷级设计输入。

<what-to-do>

## 流程

```
Step 0: 断点检测+数据采集+引擎加载 → 🔒加载验证
Step 1: Agent—框架建筑师 → 即时落盘
Step 2: Agent—脉络设计师 → 即时落盘 → 🔒检查点A
Step 3: Agent—卷级目标卡生成器 → 即时落盘
Step 4: Agent—支线规划师 → 即时落盘 → 🔒检查点A2
Step 5: Agent—框架验证器(3Agent并行) → 🔒检查点B
Step 6: 保存(DB+文件) → git commit
```

### 即时落盘原则

每个 Agent 完成后必须立即写入文件。防 context 断裂丢失产出，续接时从文件恢复。

### 断点续传

进度文件: `.claude/temp/novel-planner-progress.json`（含 current_step/completed_steps/output_files/timestamp）。Step 0 先检查，有进度则从对应文件读取已有产出，跳过已完成 Step。

## 编排器职责

只负责：MCP调用 + 引擎加载 + Agent启动 + 检查点确认 + 进度管理。不直接设计框架/脉络/支线。

## Step 0: 数据采集与引擎加载

- 断点续传：检查进度文件
- 数据采集：novel_get + world_query + character_list + foreshadow_list + volume_list + volume_get
- 🔒 卷级信息用 volume_get 获取notes，不读大纲原文
- 引擎加载：按 Step 分批（见 §引擎清单）
- 🔒 加载验证：按 shared/engine-loading-protocol.md 执行
- Token预算：按 references/token-budget.md 执行

## Step 1: Agent—框架建筑师

- Agent指令：agents/framework-architect.md
- 引擎：causality + lorecraft全套
- 即时落盘：全书框架.md
- 输出验证核心项：起承转合比例合理 | 卷功能定位唯一 | 卷间因果链 | 🔒术语规范合规

## Step 2: Agent—脉络设计师

- Agent指令：agents/vein-designer.md
- 引擎：causality + three-perspective + lorecraft全套
- 即时落盘：全书脉络.md
- 输出验证核心项：主线因果链完整 | 暗线每卷推进 | 情绪曲线有起伏 | 🔒术语规范合规
- 🔒检查点A：确认全书框架（按 shared/checkpoint-protocol.md 执行）

## Step 3: Agent—卷级目标卡生成器

- Agent指令：agents/target-card-generator.md
- 即时落盘：卷级目标卡.md
- 输出验证核心项：每卷目标可衡量 | 暗线推进一致 | 角色变化一致

## Step 4: Agent—支线规划师

- Agent指令：agents/subplot-planner.md
- 引擎：lorecraft全套
- 即时落盘：支线总图.md
- 输出验证核心项：三检验通过 | 连续型支线每卷≥1交织 | 不与主线冲突 | 🔒术语规范合规
- 🔒检查点A2：确认支线体系（按 shared/checkpoint-protocol.md 执行）

## Step 5: Agent—框架验证器

- 按 shared/three-perspective-protocol.md 执行
- 🔒检查点B：P0必须修复（修复循环详见 references/p0-fix-loop.md）

## Step 6: 保存

- 跨卷伏笔总图：编排器从目标卡提取汇总
- 新角色入库：character_create
- 🔒 DB保存：按 shared/db-save-protocol.md 执行
- sync_db_to_files + git commit

### 文件清单

```
novels/{小说名}/设定/大纲/
├── 全书框架.md            # Step 1
├── 全书脉络.md            # Step 2
├── 卷级目标卡.md           # Step 3
├── 支线总图.md            # Step 4
├── 全书框架审计.md         # Step 5
└── 跨卷伏笔总图.md         # Step 6
```

</what-to-do>

<supporting-info>

## 三层架构

| 层 | Skill | 输出 | 粒度 |
|----|-------|------|------|
| **骨架+血管** | novel-planner（本skill） | 全书框架/脉络/卷级目标卡 | 卷级"做什么" |
| **肌肉** | novel-planner-volume | 逐章大纲+事件因果链+伏笔场景化 | 章级"怎么做" |
| **皮肤/动作** | novel-chapter-writer | 正文 | 场景级"怎么写" |

## 引擎清单

| Step | 引擎 |
|------|------|
| Step 1/2 | causality, three-perspective |
| Step 5 | reader/author/character-perspective-agent |
| 全程 | lorecraft core-principles + term-map + quickref + world-element-registry |

## 异常处理

| 场景 | 处理 |
|------|------|
| 数据为空（新小说） | 阻断，需先完成 novel-setup |
| 世界观<3维度或角色<2个 | 阻断，提示补充 |
| P0修复>3轮 | 升级为用户决策 |
| context断裂 | 从进度文件恢复 |
| 已有卷大纲与新框架不一致 | 主动提出异议，等用户决定 |
| 指令范围不明确 | 必须确认：全量重做还是增量校准 |

</supporting-info>
