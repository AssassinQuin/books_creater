---
name: novel-write
description: 单章正文生成。触发词：写第N章/继续写/写一章
allowed-tools: mcp__novel-db__*, Read, Write, Edit, Glob, Grep, Bash
thinking: disabled
version: "2.0.0"
---

# 单章正文生成

## 触发
用户说"写第N章""继续写""写一章"。

## 前置检查
- 卷级大纲存在（该章在 novel-plan 中已规划）
- 不满足 → 提示用户先做大纲

## 流程
1. `get_chapter_context(novel_name, chapter_number)` 获取上下文包（含约束层级：系统→品类→小说→卷→章）
2. 基于上下文做创意决策（场面/因果链/角色弧线/伏笔操作/新实体）
3. 写作前反思：加载 `engines/pre-write-reflection.md` → 输出四维反思（情绪定调/翻车预警/核心瞬间/禁用句式）→ 用户确认
4. 用户确认创意蓝图 + 反思结果
5. `engine(action="resolve", 场景类型)` 获取引擎
6. 逐场面生成正文
7. `validate_chapter(正文)` 校验 → 有违规必须修复
8. 通过 → `writing_finish(...)` 存盘 + 角色快照 + 关系快照
9. 正文写入 `novels/{小说名}/正文/第{NNN}章-{标题}.md`

## 约束
从 `get_chapter_context` 返回的约束层级加载（系统→品类→小说→卷→章，高层覆盖低层）。
- 字数 ≥ 3000（不含标点）

## 完成后
问用户：写下一章 / 审阅 / 其他。
