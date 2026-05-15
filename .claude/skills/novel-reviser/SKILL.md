---
name: novel-reviser
description: 批量修订引擎。触发词：修复/去重/修文/润色
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, Agent, mcp__novel-db__*
lifecycle: quality
---

# 批量修订引擎

<what-to-do>

## 强制流程

```
Step 1 诊断 → Step 2 规划修改 → 🔒确认 → Step 3 批量执行 → Step 4 验证
```

修改原则：同类问题同一章内只改一次，其余用替代方案；情感高点保留；连续性修复与DB一致。

</what-to-do>

<supporting-info>

## 适用场景

- 审阅报告修复（P0-P3批量处理）
- 模式去重（相同描写/动作/意象重复）
- 连续性修复（人物状态/物品/时空矛盾）
- 风格打磨（去AI味/增强画面感/统一术语）

## Step 1: 诊断

- **模式去重**: 统计重复模式 → 标记情感高点(保留) → 其余替换 → 验证计数
- **连续性**: 读取章节+`character_get`+`world_query` → 交叉验证 → 矛盾点
- **风格**: AI味检测(`validate_chapter` / `skill_loader("novel-reviser", "engine", "anti-ai")`)

## Step 2-4: 执行

1. 每问题生成修改方案 → 🔒展示确认
2. 按方案逐条Edit执行（P0→P1→P2-P3，同一文件行号从后往前）
3. 验证：
   - `grep` 统计替换后次数 + 抽查通顺性
   - 检查是否引入新矛盾
   - `validate_chapter(text)` 硬约束仍达标

## 批量模式

- **多章批量**: 逐章扫描 → 汇总 → 🔒确认 → 批量执行 → 逐章验证
- **审阅报告修复**: 解析报告 → P0→P3排序 → 逐条方案 → 🔒确认 → 执行

</supporting-info>
