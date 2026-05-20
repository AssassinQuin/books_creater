---
name: novel-planner-volume
description: 卷级大纲设计。触发词：设计卷/卷大纲/章节规划/事件设计
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, Agent, Task, mcp__novel-db__*
depends_on: novel-planner, lorecraft, shared/engine-loading-protocol, shared/db-save-protocol, shared/checkpoint-protocol, shared/three-perspective-protocol, shared/consistency-protocol
lifecycle: core
version: "2.0.0"
---

# 卷级大纲设计

> 设计"每章发生什么"——事件架构+因果链+人物弧光+伏笔节奏。**把握脉络，不追求细节**。世界元素注册、感官5要素等留给正文写作阶段(novel-chapter-writer)。
> 可选输入：novel-planner 输出的卷级目标卡（非必需）。如存在则作为卷设计约束，不存在则自主设计。

<what-to-do>

## 流程

```
Step 0: 增量检测+数据采集+引擎加载 → 🔒加载验证
Step 1: Agent—事件架构师 → 🔒检查点A
Step 2: Agent—章节设计师 → 🔒检查点A2
Step 3: 三视角审查(3Agent并行) → 🔒检查点B
Step 4: 保存(DB+文件) → git commit
```

增量模式触发："改Ch{N}""扩展Ch{N}"等局部修改 → 跳过全流程，走增量路径（详见 references/incremental-algorithm.md）

编排器职责：**增量检测 + MCP调用 + Agent启动 + 检查点确认 + 保存**。不直接设计事件。

## Step 0: 增量检测与数据采集

- 一致性校验：按 shared/consistency-protocol.md 执行
- 增量检测：按 references/incremental-algorithm.md 执行
- 加载框架：全书框架.md / 全书脉络.md / 卷级目标卡.md（存在则读，非必需）
- 数据采集：volume_get + character_list + foreshadow_list + world_query（按卷过滤）
- 引擎加载：按 Step 分批（见 §引擎清单），Step 3 采用精简分发（编排器预提取术语摘要注入，Agent不自主加载）
- 声音层：编排器 Read(author-voice-{variant}.md, limit=5) 提取头部速查注入Agent 2（详见 references/display-templates.md §声音适配）
- 🔒 加载验证：按 shared/engine-loading-protocol.md 执行

## Step 1: Agent—事件架构师

- Agent指令：agents/event-architect.md
- 引擎：causality + relationship + spiral-structure + plot-density + shared-constraints + lorecraft四件套 + world-element-registry
- 硬约束：
  - 每章≥3事件、费笔配额≥总章数×1.0、每个主要角色与≥2不同角色独立互动
  - 连续3章无独立出场→配角边缘化、因果链显式前因、巧合计≤1/卷且需伏笔支撑
  - 🔒术语规范：文化根脉+字根一致
  - 🔒螺旋结构：L1/L2/L3完整+翻新≥1/卷+回旋镖≥3/卷
  - 🔒情节密度：并行链≥3+每章≥2链推进+NPC议程完整+复杂化≥1/章
- 🔒检查点A：确认事件架构+新实体确认（按 shared/checkpoint-protocol.md 执行，显示模板见 references/display-templates.md）
- Step 1→Step 2 手递：编排器提取传递摘要（章级事件流+角色弧线备忘+伏笔操作清单），不传全量架构

## Step 2: Agent—章节设计师

- Agent指令：agents/chapter-designer.md
- 引擎：scene-type + scene-composition + anti-ai-quickref + shared-constraints + lorecraft四件套 + world-element-registry + 声音层头部
- 硬约束：
  - 事件密度≥4/章、费笔配额达标、罕见组合≥1/卷、伏笔场景化、主角在场≥半数章
  - 🔒术语规范
  - 🔒螺旋结构：信息钩子Lv2/Lv3≥60%+回旋锚标注
  - 🔒情节密度：每章≥2链推进+每章≥1复杂化
- 🔒检查点A2：确认逐章大纲（按 shared/checkpoint-protocol.md 执行，显示模板见 references/display-templates.md）

## Step 3: 三视角审查

- 按 shared/three-perspective-protocol.md 执行
- 精简分发：编排器预提取quickref需替换术语+势力字根表，直接注入Agent指令。Step 3 Agent **不自主加载**任何引擎/lorecraft文件
- 问题分级：P0(三视角冲突/OOC/因果断裂)→必须修复 | P1(单视角严重/🔒术语违规)→本轮修 | P2→下轮前修
- 🔒检查点B：P0必须修复

## Step 4: 保存

- 🔒 输出确认：按 shared/checkpoint-protocol.md 执行
- 文件：V{N}-{卷名}.md（模板见 references/volume-outline-template.md）+ 审计报告（模板见 references/audit-report-template.md）
- 硬指标：起承转合完整+人物弧光覆盖主角+≥3配角+伏笔场景化+下卷钩子+🔒术语合规
- 🔒 DB保存：按 shared/db-save-protocol.md 执行
- git commit: `B1: V{N}《{卷名}》卷级大纲{变更描述}`

</what-to-do>

<supporting-info>

## 引擎清单

| Step | 引擎 | 加载方式 |
|------|------|---------|
| Step 1 | causality, relationship, spiral-structure, plot-density, shared-constraints, lorecraft四件套, world-element-registry | skill_loader |
| Step 2 | scene-type, scene-composition, anti-ai-quickref, shared-constraints, lorecraft四件套, world-element-registry, 声音层头部 | skill_loader + Read(limit=5) |
| Step 3 | reader/author/character-perspective-agent | skill_loader（精简分发） |

## 声音适配映射

| 章节事件类型 | 加载声音层 |
|-------------|-----------|
| 战斗/动作 | author-voice-battle |
| 情感高潮/离别/重逢 | author-voice-emotion |
| 日常/世界呼吸/荒诞 | author-voice-daily |
| 悬疑/揭秘/伏笔回收 | author-voice-mystery |
| 混合类型 | 主类型+辅助声音层 |

（详细规则见 references/display-templates.md §声音适配）

## 与上下层关系

- **上层 novel-planner**：提供"每卷做什么"（卷目标/核心事件/钩子）
- **本层**：设计"每章发生什么"——把握脉络，不注册细节
- **下层 novel-chapter-writer**：根据大纲生成正文，世界元素注册在正文阶段完成

| 本层不做 | 谁做 |
|---------|------|
| 世界元素注册（感官/功能/外观） | novel-chapter-writer Agent 2 |
| 感官5要素分配 | novel-chapter-writer Agent 3 |
| 逐章字数精确控制 | novel-chapter-writer + validate_chapter |
| 完整对话撰写 | novel-chapter-writer Agent 4 |
| 反AI指纹检测 | novel-chapter-writer + SENTENCE-PATTERNS.md |

## 异常处理

| 场景 | 处理 |
|------|------|
| Step 0 数据为空 | 阻断，需先完成 novel-setup |
| P0修复循环>3轮 | 升级为用户决策 |
| 上下文不足 | 提示用户分批处理 |

</supporting-info>
