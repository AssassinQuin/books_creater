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

- **模式去重**: `grep -c '{pattern}' novels/{小说名}/正文/*.md` 统计重复次数 → 标记情感高点(保留) → 其余替换 → 验证计数
- **连续性**: `character_get_by_name(novel_name="这次不一样了", character_name={name})` + `world_query(novel_name="这次不一样了")` 交叉验证 → 矛盾点
- **风格**: `validate_chapter(text)` 硬约束检测
- **🔒 术语合规**: 加载 `lorecraft/references/term-map.md`，逐章扫描禁止术语（数据/系统/信号/参数/权限/终端/频率等），标记违规位置并按映射表替换

## Step 2-4: 执行

1. 每问题生成修改方案 → 🔒展示确认
2. 按方案逐条Edit执行（P0→P1→P2-P3，同一文件行号从后往前）
3. 验证：
   - `grep` 统计替换后次数 + 抽查通顺性
   - 检查是否引入新矛盾
   - `validate_chapter(text)` 硬约束仍达标
4. **DB 同步（强制 — 数据一致性铁律）**：
   - 修订只改文件（Edit），但修改可能影响 DB 中的数据
   - **首先**调 `consistency_guard(novel_name="这次不一样了", auto_sync=True)` 自动同步文件权威数据（大纲/章节摘要）→ DB
   - 如果修订改变了**文件 authoritative 类型的数据**（如角色状态/世界观/伏笔），还需额外调对应 MCP 工具同步 DB：
     - **角色状态** → `character_update` 同步 DB
     - **世界观/地点/物品** → `world_upsert` 同步 DB
     - **回收了伏笔** → `foreshadow_recall` 同步 DB
   - 如果修订改变了**章节摘要/事件/伏笔操作** → `writing_finish` 重新提交更新后的元数据
   - **禁止**：修订文件后不同步 DB，导致下游 skill 读到旧数据

## 批量模式

- **多章批量**: 逐章扫描 → 汇总 → 🔒确认 → 批量执行 → 逐章验证
- **审阅报告修复**: 解析报告 → P0→P3排序 → 逐条方案 → 🔒确认 → 执行

## 边界条件
- 修改影响多章：先展示影响范围 → 🔒确认 → 批量执行
- 修改引入新矛盾：每条修改后验证相关章节一致性
- P0修复与P1冲突：P0优先，P1顺延
- 修改后硬约束不达标：validate_chapter 返回 violations → 回滚修改
- 批量修改超过10章：分批执行，每批5章，批间确认

## 修改回滚
- 每条修改前 git stash 保存当前状态
- 修改后验证不通过 → git stash pop 回滚
- 批量修改：保留每条修改的 diff，可逐条回滚

</supporting-info>
