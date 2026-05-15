---
name: novel-planner
description: 小说卷规划 Multi-Agent Pipeline。编排器驱动4个子Agent协作：环境先行→事件架构→章节设计→大纲验证。触发词：规划卷/大纲/卷大纲
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, mcp__novel-db__novel_get, mcp__novel-db__world_query, mcp__novel-db__world_upsert, mcp__novel-db__character_list, mcp__novel-db__character_get, mcp__novel-db__relation_list, mcp__novel-db__volume_create, mcp__novel-db__volume_list, mcp__novel-db__volume_get, mcp__novel-db__volume_update, mcp__novel-db__chapter_plan, mcp__novel-db__scene_create, mcp__novel-db__scene_list, mcp__novel-db__foreshadow_plant, mcp__novel-db__foreshadow_list, mcp__novel-db__engine_detail, mcp__novel-db__rule_detail
lifecycle: core
---

# 小说卷规划 (Multi-Agent Pipeline)

<what-to-do>

## 强制流程

```
Step 0: 断点检测 → MCP 数据采集
  ↓
Step 1: 启动 Agent 1: World-Context Builder → 场景清单 + 环境约束包
  ↓
Step 2: 启动 Agent 2: Event Architect → 因果链 + 超级事件 + 支线
  ↓  🔒 检查点 A: 确认事件架构（起承转合/因果密度/支线三检验/人物弧光）
Step 3: 启动 Agent 3: Chapter Designer → 逐章大纲 + 微事件 + 伏笔分配
  ↓
Step 4: 启动 Agent 4: Outline Validator → 10项卷级检查
  ↓  🔒 检查点 B: 确认验证通过（P0必须修复）
Step 5: 双通道保存（DB + 文件）+ 跨卷伏笔对齐
Step 6: 🔒 用户确认全部 → git commit
```

## 编排器职责

编排器只负责：**MCP 调用 + Agent 启动 + 检查点确认 + 保存**。不直接设计事件、不写章节大纲。

| 步骤 | 职责 | 工具权限 |
|------|------|---------|
| Step 0 | 断点检测 + 数据采集 | MCP 全部 |
| Step 1-4 | 启动 Agent，传递上下文 | Task (subagent) |
| 🔒A/B | 检查 Agent 输出完整性，用户确认 | — |
| Step 5 | DB 写入 + 文件落盘 | MCP 全部 + Write |
| Step 6 | git commit | Bash |

## Step 0: 断点检测 + MCP 数据采集

### 0.1 断点检测

```python
volume_list(novel_id)  # 检查已有卷
chapter_list(novel_id, status='planned')  # 检查已规划章节
```

若已有数据 → 加载继续，避免重复设计。

### 0.2 数据采集

为 Agent 1 准备：
```python
novel_get(novel_id)  # 小说基本信息
world_query(novel_id)  # 世界观全部数据
character_list(novel_id)  # 角色列表
volume_list(novel_id)  # 已有卷信息
foreshadow_list(novel_id, status='planted')  # 未回收伏笔
```

为 Agent 2 准备（在 Agent 1 完成后）：
```python
character_get(id)  # 本卷活跃角色档案（批量）
relation_list(novel_id)  # 角色关系网
```

## Step 1: 启动 Agent 1 — World-Context Builder

### 输入
- 采集的全部世界观数据
- 卷主题（用户提供或从 novel_get 获取）

### Agent 指令文件
`agents/world-context-builder.md`

### 输出验证
编排器检查 Agent 1 输出是否包含：
- [ ] 场景清单（2-5个，每个含环境5要素）
- [ ] 世界观约束包（能力/势力/经济/日常/历史规则）
- [ ] 需创建的新场景列表（如有）

任一缺失 → 指出缺失项，要求 Agent 1 补充（最多重试 2 次）。

### 新场景创建
若 Agent 1 标记新场景 → 编排器调 `world_upsert(category='location')` 创建。

## Step 2: 启动 Agent 2 — Event Architect

### 输入
- Agent 1 的完整输出
- 本卷活跃角色档案（character_get 批量）
- 角色关系网
- 卷定位（起/承/转/合，由编排器根据卷号判断）

### Agent 指令文件
`agents/event-architect.md`

### 输出验证
编排器检查 Agent 2 输出是否包含：
- [ ] 卷级起承转合四段（含事件列表）
- [ ] 因果链（每事件含因为/所以/逼出/雪球/没变）
- [ ] 超级事件设计（如适用，含触发→升级→高潮→后果）
- [ ] 支线设计（含三检验结果）
- [ ] 人物弧光对齐表
- [ ] 悬念锚点（旧未知回答 + 新未知提出）

## 🔒 检查点 A: 确认事件架构

编排器展示 Agent 2 的核心产出，等待用户确认：

```
请确认以下事件架构：

【起承转合】
起(10-15%): {事件1} → {事件2}
承(40-50%): {事件3} → ... → {事件N}
转(20-25%): {超级事件(如适用)} → {事件N+1}
合(10-15%): {事件N+2} → 下卷钩子: {悬念类型}

【支线】（三检验结果）
{支线1}: 删除✅ 独立✅ 主题✅
{支线2}: 删除✅ 独立✅ 主题❌ → 建议删除或合并

【人物弧光】
{角色A}: 变化弧·挣扎期(V3) → 蜕变点(V5)
...

确认后进入章节设计。输入 "OK" 或指出修改意见。
```

用户说 "OK" → 进入 Step 3。
用户提出修改 → 回到 Agent 2 修复（或手动修改后重新确认）。

## Step 3: 启动 Agent 3 — Chapter Designer

### 输入
- Agent 2 的完整输出（确认后的版本）
- 预估章数（编排器根据字数规划计算：总字数 ÷ 3500-5000字/章）
- 上一卷末角色状态（如有，从 DB 或文件读取）

### Agent 指令文件
`agents/chapter-designer.md`

### 输出验证
编排器检查 Agent 3 输出是否包含：
- [ ] 章节映射表（起/承/转/合 → 章节范围）
- [ ] 逐章大纲（每章含时间/场景/事件/角色/微事件/伏笔/状态/字数）
- [ ] 微事件多样性检查表
- [ ] 伏笔分配表
- [ ] 角色状态追踪表

## Step 4: 启动 Agent 4 — Outline Validator

### 输入
- Agent 3 的完整输出
- Agent 2 的事件架构（用于对比检查）
- 10项卷级检查清单

### Agent 指令文件
`agents/outline-validator.md`

### 输出验证
编排器检查 Agent 4 输出是否包含：
- [ ] 逐项结果（10项，每项含状态/证据/备注）
- [ ] 对比检查（设计意图 vs 实际产出）
- [ ] 问题分级（P0/P1）
- [ ] 总体评估（通过/有条件通过/不通过）

## 🔒 检查点 B: 确认验证通过

编排器展示 Agent 4 的验证报告：

```
验证结果: {通过/有条件通过/不通过}

通过项: {N}/10
不通过项: [列表]

P0（必须修复）:
- [问题1] → [修复建议]
...

P1（推荐修复）:
- [问题1] → [修复建议]
...
```

P0 问题 → 必须修复后才能继续。修复方式：
- 若问题在事件架构层 → 回到 Agent 2 修复 → 重新走 Step 3-4
- 若问题在章节设计层 → 回到 Agent 3 修复 → 重新走 Step 4

无 P0 问题 → 进入 Step 5。

## Step 5: 双通道保存

### 5.1 DB 保存

```python
# 卷信息
volume_create(novel_id, number=N, title="卷名",
  main_plotlines=[{name, description, purpose}, ...],
  notes="伏笔计划/配角安排/升级节点")

# 章节信息（逐章）
chapter_plan(novel_id, number, title, outline, chapter_type, volume_id)

# 场景信息（逐场景）
scene_create(chapter_id, scene_number, location, characters_involved, conflict, emotion_type, key_beats, notes)

# 伏笔
foreshadow_plant(novel_id, description, planned_recall_chapter, importance, tags)
```

### 5.2 文件落盘

组装为 Markdown 文件：

```
novels/{小说名}/设定/章节大纲/V{卷号}-{卷名}-事件大纲.md
```

文件格式参考 `references/outline-template.md`。

### 5.3 跨卷伏笔对齐

检查：
- 新埋伏笔 ≤2 个/章，回收 ≥1 个/章
- 未回收伏笔积压率 ≤30%
- 埋设→提起 ≤3 卷，提起→回收 ≤3 卷

更新 `设定/大纲/线索追踪.md`。

## Step 6: 验证 + git commit

```
B1: {卷名} 事件大纲完成 (Multi-Agent Pipeline)
```

</what-to-do>

<supporting-info>

## Agent 失败处理

每个 Agent 步骤最多重试 **2 次**。编排器在每次 Agent 返回后检查输出完整性：

| Agent | 完整性检查 | 不通过时 |
|-------|-----------|---------|
| Agent 1 | 场景清单+环境5要素+约束包 | 指出缺失项，要求补充 |
| Agent 2 | 起承转合+因果链+支线+弧光+悬念 | 指出缺失项，要求补充 |
| Agent 3 | 章节映射+逐章大纲+微事件+伏笔+状态 | 指出缺失项，要求补充 |
| Agent 4 | 逐项结果+对比检查+问题分级+总体评估 | 指出缺失项，要求补充 |

若同一 Agent 连续 2 次不通过 → 编排器降级处理：手动补全缺失部分后继续下一 Agent，并在 Memory 中记录 `bug: Agent{N}连续失败`。

## 调研注入：大纲级方法论（强制）

以下方法论来自 2026-05-15 大纲剧情设计深度调研，Agent 指令文件中已内嵌，编排器不重复说明。

### 起承转合循环嵌套
全书: 起(V1-V2) → 承(V3-V6) → 转(V7-V10) → 合(V11-V14+尾声)
每卷: 起(10-15%) → 承(40-50%) → 转(20-25%) → 合(10-15%)

### 伏笔五级分类
章级/卷级/跨卷/全书/烟雾弹。积压上限 30%。

### 支线三检验
删除检验 / 独立阅读检验 / 主题检验。

### 人物弧光对齐
变化弧(催化=激励事件同侧面，蜕变=剧情高潮同步) / 扁平弧 / 幻灭弧。

### 悬念五种"未知"轮换
谁/为什么/怎么/什么时候/会怎样。回答旧未知同时提出新未知。

## 项目专属数据

《这次不一样了》的专属数据（14卷情绪锚点、切视角场景、角色名单）存于：
`references/novel-planner/project-context.md`

Agent 2 设计事件时，编排器将此文件作为附加输入提供。

## 章节大纲文件模板

参考 `references/outline-template.md`。

</supporting-info>