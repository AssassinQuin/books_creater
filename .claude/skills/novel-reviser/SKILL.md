---
name: novel-reviser
description: 批量修订引擎，处理模式去重、连续性修复和风格打磨。触发词：修复/去重/修文/润色
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, Agent, mcp__novel-db__novel_get, mcp__novel-db__character_get, mcp__novel-db__character_list, mcp__novel-db__world_query, mcp__novel-db__chapter_list, mcp__novel-db__foreshadow_list
lifecycle: quality
---

# 批量修订引擎

> 共享约定：读 `references/shared-conventions.md`
> **术语定义**: 读项目根目录 `NOVEL-CONTEXT.md`

<what-to-do>
## 强制流程

```
Step 1 诊断 → Step 2 规划修改 → 🔒确认 → Step 3 批量执行 → Step 4 验证
```
</what-to-do>

<supporting-info>

## 适用场景

- 审阅报告修复（P0-P3问题批量处理）
- 模式去重（同一描写/动作/意象重复过多）
- 连续性修复（人物状态/物品/时空矛盾）
- 风格打磨（去AI味/增强画面感/统一术语）

---

## Step 1: 诊断

### 模式去重

统计重复模式 → 标记情感高点（保留）→ 其余替换为不同表达 → 验证计数。

### 连续性检查

读取相关章节 → 交叉验证人物状态/物品/时空 → 定位矛盾点。

### 风格检查

AI味模式检测（→见 `references/writing-style.md`）/ 术语一致性 / 时间表达规范性。

---

## Step 2: 规划修改

对每个问题生成修改方案表，🔒**展示修改清单，等用户确认**。

规则：每处修改必须不同 / 保留情感高点 / 连续性修复必须与DB数据一致。

---

## Step 3: 批量执行

确认后按清单执行Edit修改。先修P0→P1→P2-P3。同一文件按行号从后往前。

---

## Step 4: 验证

1. 计数验证：grep统计替换后出现次数
2. 上下文验证：抽查修改点通顺性
3. 连续性验证：检查是否引入新矛盾
4. 输出修改摘要

---

## 批量模式

- **多章批量**: 逐章扫描 → 汇总问题 → 🔒确认 → 批量执行 → 逐章验证
- **审阅报告修复**: 解析报告 → P0→P3排序 → 逐条生成方案 → 🔒确认 → 执行

</supporting-info>
