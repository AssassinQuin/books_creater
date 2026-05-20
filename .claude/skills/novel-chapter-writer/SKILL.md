---
name: novel-chapter-writer
description: 逐章写作编排器，驱动4个子Agent协作完成章节。触发词：写第N章/继续写/写一章
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, Agent, Task, mcp__novel-db__*
depends_on: novel-planner, lorecraft, shared/engine-loading-protocol, shared/db-save-protocol, shared/checkpoint-protocol, shared/consistency-protocol
lifecycle: core
version: "2.0.0"
---

# 逐章写作编排器（Multi-Agent Pipeline）

> 编排器负责MCP调用和数据流转，子Agent各司其职、上下文干净、互不污染。

<what-to-do>

## 流程

```
Step 0: 断点检测+一致性校验
Step 1: 编排器调MCP收集原始数据
Step 2: Agent 1—Context Curator → 上下文包
Step 3: Agent 2—Creative Director → 创意蓝图 → 🔒检查点A
Step 4: Agent 3—Engine Coordinator → 引擎指令包
Step 5: Agent 4—Text Generator → 章节正文 → 🔒检查点B
Step 6: 🔒writing_finish + 存盘
```

## Step 0: 断点检测+一致性校验

- 检查章节文件是否已存在
  - 存在且完整 → 提示「第N章已完成，是否写第N+1章？」
  - 不存在 → 进入 Step 1
  - 断点续传 → Memory搜索 `flow-state` 恢复中断位置
- 一致性校验：按 shared/consistency-protocol.md 执行

## Step 1: 编排器采集原始数据

- volume_get → 本章信息（MCP返回不完整时回退读文件）
- get_chapter_context → 全部写作上下文（一次调用）
  - 返回：章节信息+卷级大纲+前3章摘要+角色+伏笔+世界观+关系+时间线+质量历史+写作提示词
  - 无需再单独调用 volume_get/foreshadow_list/character_detail/relation_list/world_query/timeline_query
  - world_settings某分类为空 → 回退读设定文件
- 保存到 .tmp/ch{N}-raw-data.md
  - 必须包含：核心事件、声音适配标记、世界元素定义、人物档案/伏笔/时间线

## Step 2: Agent 1—Context Curator

- subagent_type: search
- Agent指令：agents/context-curator.md
- 输入：.tmp/ch{N}-raw-data.md
- 输出：上下文包 → .tmp/ch{N}-context-package.md
- 验证：按 references/agent-output-validation.md 执行
- 缺口标注 → 编排器补充查询MCP后更新

## Step 3: Agent 2—Creative Director

- subagent_type: general_purpose_task
- Agent指令：agents/creative-director.md
- 输入：.tmp/ch{N}-context-package.md
- 可直接调MCP创建新实体（character_create/world_upsert/foreshadow_plant）
- 输出：创意蓝图 → 创意决策/Ch{N}-创意蓝图.md
- 验证：按 references/agent-output-validation.md 执行
- 🔒检查点A：确认场面设计+因果链+角色弧线（按 shared/checkpoint-protocol.md 执行）

## Step 4: Agent 3—Engine Coordinator

- subagent_type: general_purpose_task
- Agent指令：agents/engine-coordinator.md
- 输入：创意蓝图
- 引擎加载：按 shared/engine-loading-protocol.md 执行（resolve_engines自动解析，不交给模型选择）
- 输出：引擎指令包 → .tmp/ch{N}-engine-package.md
- 验证：按 references/agent-output-validation.md 执行

## Step 5: Agent 4—Text Generator

- subagent_type: general_purpose_task
- Agent指令：agents/text-generator.md
- 输入：创意蓝图+引擎指令包
- 逐场面生成正文（起10-15%/承40-50%/转20-25%/合10-15%）
- 每段反AI自检；全文硬约束自检+术语合规
- 输出：章节正文+自检报告
- 🔒检查点B：字数达标+场面覆盖+反AI自检通过（按 shared/checkpoint-protocol.md 执行）
- 字数不足：先展开蓝图弹性事件，不循环重跑Agent 4

## Step 6: 🔒存盘+移交审计

> 生成与审计分离：本章只负责生成正文，审计由 novel-qa 独立进行。

- writing_finish（self_check='passed' 强制）
  - 参数：chapter_id, chapter_text, summary, key_events, characters_involved, new_foreshadows, resolved_foreshadows
- 角色状态更新：character_increment + snapshot + relation_snapshot + distillation_evolve
  - 详见 references/db-save-detail.md
- 正文写入 novels/{小说名}/正文/第{NNN}章-{标题}.md（纯净化，不含注释/统计）
- 一致性同步：按 shared/consistency-protocol.md 执行
- DB存盘校验：按 shared/db-save-protocol.md 执行
- 清理 .tmp/（保留创意决策/）
- 移交审计：用户选择"审计"→novel-qa 或"继续"→下一章

</what-to-do>

<supporting-info>

## Agent输出验证
详见 references/agent-output-validation.md

## DB存盘详细步骤
详见 references/db-save-detail.md

## 引擎加载映射
场面类型→引擎映射由 ENGINE_MATRIX（tools_writing.py）硬编码管理，编排器调用 resolve_engines 自动解析。

## 阶段指令
skill_loader("novel-chapter-writer", "phase", "b2-chapter") — 编排器在 Step 2 启动前加载。

## Agent重试与降级
- 每步预留1-3次重试，格式缺失快速修复，创意偏差需更多轮次
- 字数不足不属于重试问题：先展开蓝图弹性事件（2-3个，覆盖800-1500字余量）
- 同一Agent连续2+次失败 → 降级处理（手动补全后继续）+ Memory记录bug

## 异常处理
| 场景 | 处理 |
|------|------|
| Agent输出字段缺失 | 按失败处理表重试或手动补全 |
| 字数不足 | 先展开弹性事件，不循环重跑Agent 4 |
| Agent连续2+次失败 | 降级处理+Memory记录bug |

## 子Agent指令文件
- agents/context-curator.md — Agent 1
- agents/creative-director.md — Agent 2
- agents/engine-coordinator.md — Agent 3
- agents/text-generator.md — Agent 4

</supporting-info>
