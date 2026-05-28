# Skill 架构诊断报告

> 日期: 2026-05-28
> 问题: skill 太多/太大/指令遵循差/内容生成差/token消耗高/DB MCP使用率低

---

## 1. 现状量化

### 1.1 SKILL.md 体积

| Skill | 行数 | 字节 | 等价 token (约) |
|-------|------|------|----------------|
| novel-planner-volume | 760 | 41KB | ~14K |
| novel-chapter-writer | 427 | 16KB | ~5K |
| novel-qa | 287 | 13KB | ~4.5K |
| novel-setup | 237 | 11KB | ~3.5K |
| novel-reviser | 168 | 8KB | ~3K |
| novel-creative-analyze | 165 | 6KB | ~2K |
| novel-writer | 154 | 7KB | ~2K |
| novel-planner | 136 | 5KB | ~2K |
| novel-character | 135 | 8KB | ~3K |
| novel-skill-creator | 104 | 4KB | ~1.5K |
| novel-ability-designer (废弃) | 20 | 1KB | — |
| **合计** | **2593** | **117KB** | **~40K** |

### 1.2 引擎 + 参考文件

| 类型 | 文件数 | 体积 |
|------|--------|------|
| 引擎文件 (engines/) | 40 | 274KB |
| 参考/模板 (references/) | 11 | — |
| Agent 指令 (agents/) | 10 | — |

### 1.3 重复与膨胀指标

| 指标 | 数值 | 含义 |
|------|------|------|
| 🔒检查点标记 | 103个 | 平均每个 skill 10个检查点，模型无法全部遵循 |
| 引擎加载引用 | 98处 | skill 大量篇幅在说"加载什么"而非"做什么" |
| 术语规范重复 | 9个 skill | 同一条规则写 9 遍 |
| DB MCP 工具 | 56个 | 但 skill 中直接 Read 文件的次数远多于 MCP 调用 |

### 1.4 每次触发的实际 token 消耗估算

当用户触发 `novel-planner-volume` 时:
- SKILL.md 加载: ~14K tokens
- 引擎文件加载 (Step 0): ~50K tokens (约 15 个文件)
- Agent 指令 + 数据传递: ~30K tokens
- **总计: ~94K tokens 仅用于指令和框架，还没开始干活**

---

## 2. 根因分析

### 2.1 核心问题: 指令膨胀 (Instruction Bloat)

Skill 被写成了**规格说明书**，包含:
- 详尽的 Step 编号和子步骤
- 每步加载哪个文件的清单
- Agent 间数据传递格式 (伪代码)
- DB 保存的 Python 伪代码
- 每个检查点的显示模板
- 异常处理表格

这些是**开发者的设计文档**，不是**给 LLM 的执行指令**。LLM 读到 760 行指令时，前 100 行的约束到后面已经被淹没了。

### 2.2 问题链

```
指令太多 → 注意力稀释 → 规则不遵循 → 内容质量差
    ↓
每次都要 Read 大量文件 → token 消耗高
    ↓
规则写在 skill 里而非 DB → 改一条规则要改 N 个文件 → 维护困难
    ↓
skill 碎片化 → 路由器 (novel-writer) 需要理解 11 个 skill 的边界
```

### 2.3 具体问题清单

| # | 问题 | 举例 |
|---|------|------|
| 1 | skill 做了 MCP 该做的事 | planner-volume 里写了 50 行 Python 伪代码描述 DB 保存，但 MCP 工具自己就知道怎么存 |
| 2 | 规则散落在 N 个 skill | 术语规范在 setup/planner/planner-volume/chapter-writer/qa 都写了，改一处漏四处 |
| 3 | 引擎加载逻辑硬编码 | 每个 skill 写死了 `skill_loader("...", "engine", "...")` 清单，加新引擎要改 N 个文件 |
| 4 | skill 间通过文件耦合 | planner-volume 要 Read planner 的输出文件，而不是从 DB 查 |
| 5 | 检查点过度 | planner-volume 有 A/A2/B 三个检查点，每个还有子模板，用户要确认 3-4 次才能前进 |
| 6 | Agent 指令是 skill 的翻版 | agent 文件和 skill 文件大量内容重复 |

---

## 3. 改造方案

### 3.1 核心原则

| 原则 | 现状 | 目标 |
|------|------|------|
| **skill 只说"做什么"** | 说"做什么" + "怎么做" + "怎么验证" + "怎么存" | 只说目标和关键约束 |
| **规则存 DB，不在 skill** | 规则写在 SKILL.md 里 | `writing_rules` 表 + `world_settings` 表 |
| **数据通过 MCP 流动** | skill A 写文件，skill B Read 文件 | skill A 存 DB，skill B 用 MCP 查 |
| **引擎通过 MCP 加载** | 每个 skill 列引擎清单 | `resolve_engines` 根据场景自动匹配 |
| **每个 skill < 100 行** | 平均 259 行 | 目标 80 行 |

### 3.2 合并方案

**现状 11 个 skill → 目标 5 个**

| 目标 skill | 合并来源 | 核心职责 |
|-----------|---------|---------|
| **novel-setup** | setup + character | 项目创建 + 氛围DNA + 世界观 + 角色设计 |
| **novel-plan** | planner + planner-volume | 全书框架 + 卷级大纲（不再分两层） |
| **novel-write** | chapter-writer | 正文生成 |
| **novel-review** | qa + creative-analyze | 质量审查 + 创意评估 |
| **novel-fix** | reviser | 修复/润色 |

**删除/合并理由**:

| 被合并 | 理由 |
|--------|------|
| novel-writer (路由器) | 合并后 skill 足够少，路由器不再需要。用户直接说意图，Claude 匹配 |
| novel-planner + planner-volume | 用户不会先说"规划全书"再说"设计卷"，通常直接说"设计第N卷"。两层合一 |
| novel-qa + creative-analyze | 审查和评估是同一个用户意图的不同角度 |
| novel-setup + character | 建世界观和建角色是连续流程，不会分开触发 |
| novel-ability-designer | 已废弃 |

### 3.3 每个 skill 的目标结构 (80行模板)

```markdown
---
name: {name}
description: {一句话}
allowed-tools: {只列需要的}
depends_on: {只列 DB MCP + 引擎目录}
---

# {标题}

> 一句话说明这个 skill 做什么。

## 触发条件
{什么用户意图触发这个 skill}

## 流程
{3-5步，每步一句话，不说怎么实现}

## 约束
{只写本 skill 独有的约束，通用约束在 DB writing_rules 中}

## 输出
{期望产出格式}
```

### 3.4 规则迁移方案

| 规则类型 | 现在在哪 | 迁移到哪 |
|---------|---------|---------|
| 术语规范 (lorecraft) | 每个 skill 里重复 | `writing_rules` 表 (category='term') |
| 反AI模式 | skill + engines/anti-ai*.md | `writing_rules` 表 (category='ai_flavor') + `SENTENCE-PATTERNS.md` |
| 检查项 (内容丰富度等) | skill 里内联 | `writing_rules` 表 (category='structure') |
| 共享约束 | shared-constraints.md | `writing_rules` 表 (category='constraint') |
| 引擎加载清单 | 每个 skill 写死 | `resolve_engines` MCP 自动匹配 |
| DB 保存伪代码 | 每个 skill 50+ 行 | MCP 工具内部处理，skill 只调 MCP |
| 检查点模板 | 每个 skill 内嵌 | 删除，编排器自行决定展示格式 |

### 3.5 引擎文件处理

**现状**: 40个引擎文件 274KB，skill 按清单加载。

**目标**: 引擎文件保留作为参考库，但 **skill 不直接指定加载哪些**。由 `resolve_engines` MCP 根据场景类型自动匹配。

skill 里不再有 `skill_loader("...", "engine", "...")` 调用。

---

## 4. 预期收益

| 指标 | 现状 | 目标 | 改善 |
|------|------|------|------|
| SKILL.md 总体积 | 117KB / 2593行 | ~30KB / ~400行 | 75% 缩减 |
| 单次触发 token 消耗 | ~94K (planner-volume) | ~15K | 84% 缩减 |
| skill 数量 | 11 | 5 | 55% 减少 |
| 规则重复 | 9处 | 1处 (DB) | 消除重复 |
| 检查点数 | 103 | ~20 | 80% 减少 |
| DB MCP 使用率 | 低 | 高 (主要数据通道) | 质变 |

---

## 5. 风险

| 风险 | 缓解措施 |
|------|---------|
| 合并后 skill 职责不清 | 每个合并后的 skill 写明触发条件和边界 |
| 引擎文件失去入口 | resolve_engines 维护场景→引擎映射 |
| 规则迁移遗漏 | 迁移后跑 validate_chapter 对比，确保规则不丢失 |
| 用户习惯了旧 skill | 新旧可以共存一段时间，旧 skill 标记 deprecated |

---

## 6. 执行顺序建议

如果要做，建议按以下顺序:

1. **先建规则库** — 把散落在 skill 里的规则迁移到 DB `writing_rules` 表
2. **先合并再瘦身** — 把 11 个 skill 合并为 5 个，此时可以冗余
3. **逐个瘦身** — 每个合并后的 skill 精简到 <100 行
4. **验证** — 跑现有章节的生成，对比质量
5. **清理** — 删除废弃文件，更新 CLAUDE.md
